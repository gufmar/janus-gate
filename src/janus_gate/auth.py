"""Per-request backend API key resolution (public face key -> upstream key)."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from janus_gate.config import AppConfig, AuthConfig, ProviderName

logger = logging.getLogger("janus_gate.auth")

_UNSET: Any = object()
_backend_api_key: ContextVar[Any] = ContextVar("janus_backend_api_key", default=_UNSET)
_auth_fallback: str | None = None

# Janus-native / docs paths: no public-key mapping warnings.
_SKIP_AUTH_PATHS = frozenset(
    {
        "/",
        "/health",
        "/endpoints",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/openapi.json",
        "/audit/start",
        "/audit/report",
    }
)


@dataclass(frozen=True, slots=True)
class ResolvedAuth:
    public_key: str | None
    backend_key: str | None
    used_fallback: bool
    matched: bool
    label: str | None = None


def configure_auth_fallback(key: str | None) -> None:
    """Default backend key when no request context is active (startup / tests)."""
    global _auth_fallback
    _auth_fallback = _normalize_key(key)


def get_backend_api_key() -> str | None:
    value = _backend_api_key.get()
    if value is _UNSET:
        return _auth_fallback
    return value


def set_backend_api_key(key: str | None) -> Token:
    return _backend_api_key.set(_normalize_key(key))


def reset_backend_api_key(token: Token) -> None:
    _backend_api_key.reset(token)


def resolve_auth(auth: AuthConfig, public_key: str | None) -> ResolvedAuth:
    normalized = _normalize_key(public_key)
    if normalized:
        for mapping in auth.key_map:
            if mapping.public_key == normalized:
                return ResolvedAuth(
                    public_key=normalized,
                    backend_key=_normalize_key(mapping.backend_key),
                    used_fallback=False,
                    matched=True,
                    label=mapping.label,
                )
    return ResolvedAuth(
        public_key=normalized,
        backend_key=_normalize_key(auth.fallback_backend_key),
        used_fallback=True,
        matched=False,
    )


def extract_public_api_key(request: Request, public_face: ProviderName) -> str | None:
    if public_face is ProviderName.BLOCKFROST:
        return _normalize_key(request.headers.get("project_id"))
    if public_face is ProviderName.KOIOS:
        authorization = request.headers.get("authorization") or ""
        if authorization.lower().startswith("bearer "):
            return _normalize_key(authorization[7:])
        return _normalize_key(authorization) or None
    return None


def mask_api_key(key: str | None) -> str | None:
    """Mask API keys for logs (never log full secrets)."""
    if key is None:
        return None
    if key == "":
        return "(empty)"
    if len(key) <= 20:
        if len(key) <= 6:
            return "***"
        return f"{key[:3]}...{key[-3:]}"
    return f"{key[:10]}...{key[-10:]}"


def request_app_path(request: Request, base_path: str = "") -> str:
    """Face/router path with public mount prefix removed.

    When ``server.base_path`` / ASGI ``root_path`` is ``/janus``, nginx may forward
    ``/janus/blocks/latest`` while FastAPI still routes it (via root_path). Catalog
    matching and audit skip-lists need the face path ``/blocks/latest``.
    """
    path = request.scope.get("path") or "/"
    if not isinstance(path, str):
        path = str(path)
    if not path.startswith("/"):
        path = f"/{path}"

    prefixes: list[str] = []
    for raw in (base_path, request.scope.get("root_path") or ""):
        text = str(raw).strip().rstrip("/")
        if text and text not in prefixes:
            prefixes.append(text)

    for prefix in prefixes:
        if path == prefix:
            return "/"
        if path.startswith(f"{prefix}/"):
            return path[len(prefix) :] or "/"
    return path


def auth_health_payload(auth: AuthConfig) -> dict[str, Any]:
    """Non-secret auth status for /health (no key material or previews)."""
    return {
        "key_map_count": len(auth.key_map),
        "has_fallback_backend_key": bool(auth.fallback_backend_key),
        "expose_janus_headers": auth.expose_janus_headers,
        "debug_log_keys": auth.debug_log_keys,
    }


def _normalize_key(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _resolution_label(resolved: ResolvedAuth) -> str:
    if resolved.matched:
        return "mapped"
    if resolved.backend_key:
        return "fallback"
    return "anonymous"


class ApiKeyMappingMiddleware(BaseHTTPMiddleware):
    """Map public-face API keys to backend keys for each request."""

    def __init__(self, app: Any, config: AppConfig) -> None:
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request_app_path(request, self._config.server.base_path)
        if path in _SKIP_AUTH_PATHS:
            return await call_next(request)

        public_key = extract_public_api_key(request, self._config.public_face)
        resolved = resolve_auth(self._config.auth, public_key)
        request.state.auth = resolved

        if self._config.auth.debug_log_keys:
            logger.info(
                "auth keys %s %s face=%s resolution=%s label=%s "
                "public=%s backend=%s",
                request.method,
                path,
                self._config.public_face.value,
                _resolution_label(resolved),
                resolved.label or "-",
                mask_api_key(resolved.public_key) or "(missing)",
                mask_api_key(resolved.backend_key) or "(none)",
            )
        elif resolved.used_fallback:
            logger.warning(
                "No matching public API key for %s face (key %s); "
                "using fallback backend credentials%s",
                self._config.public_face.value,
                mask_api_key(public_key) or "(missing)",
                " (anonymous upstream)" if not resolved.backend_key else "",
            )

        token = set_backend_api_key(resolved.backend_key)
        try:
            response = await call_next(request)
        finally:
            reset_backend_api_key(token)

        if self._config.auth.expose_janus_headers:
            if resolved.used_fallback:
                response.headers["X-Janus-Auth-Warning"] = (
                    "no matching public API key; using fallback backend credentials"
                )
                response.headers["X-Janus-Auth"] = "fallback"
            else:
                response.headers["X-Janus-Auth"] = "mapped"
        return response
