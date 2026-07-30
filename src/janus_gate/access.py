"""Optional client IP allowlist middleware."""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from janus_gate.audit import client_ip_from_request
from janus_gate.auth import request_app_path
from janus_gate.config import AccessDenyMode, AppConfig

logger = logging.getLogger("janus_gate.access")

# Always reachable in deny: endpoints mode (discovery + probes + OpenAPI).
_ENDPOINTS_MODE_OPEN_PATHS = frozenset(
    {
        "/",
        "/health",
        "/endpoints",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/openapi.json",
    }
)


def ip_is_allowed(client_ip: str, allowed_ips: list[str]) -> bool:
    """Return True if client_ip matches any exact address or CIDR in allowed_ips."""
    if not allowed_ips:
        return True
    if client_ip in ("", "unknown"):
        return False
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for entry in allowed_ips:
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            logger.warning("Ignoring invalid access.allowed_ips entry: %r", entry)
    return False


def path_is_open_in_endpoints_mode(path: str) -> bool:
    return path in _ENDPOINTS_MODE_OPEN_PATHS


class AccessMiddleware(BaseHTTPMiddleware):
    """Enforce access.allowed_ips when configured."""

    def __init__(self, app: Any, config: AppConfig) -> None:
        super().__init__(app)
        self._config = config

    def _trusted_proxy_hops(self) -> int:
        access = self._config.access
        if access.trusted_proxy_hops is not None:
            return access.trusted_proxy_hops
        return self._config.audit.trusted_proxy_hops

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        allowed = self._config.access.allowed_ips
        if not allowed:
            return await call_next(request)

        path = request_app_path(request, self._config.server.base_path)
        deny = self._config.access.deny
        if deny is AccessDenyMode.ENDPOINTS and path_is_open_in_endpoints_mode(path):
            return await call_next(request)

        client_ip = client_ip_from_request(
            request, trusted_proxy_hops=self._trusted_proxy_hops()
        )
        if ip_is_allowed(client_ip, allowed):
            return await call_next(request)

        logger.warning(
            "Denied %s %s from %s (access.deny=%s)",
            request.method,
            path,
            client_ip,
            deny.value,
        )
        return JSONResponse(
            status_code=403,
            content={
                "status_code": 403,
                "error": "Forbidden",
                "message": "client IP is not allowed",
            },
        )
