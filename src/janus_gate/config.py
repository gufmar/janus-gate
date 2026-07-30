"""Configuration loading and validation."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ProviderName(StrEnum):
    BLOCKFROST = "blockfrost"
    KOIOS = "koios"


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    # Public URL prefix when Janus is behind a reverse proxy that strips it
    # (e.g. browser uses /janus/..., nginx forwards / to Janus). Example: /janus
    base_path: str = ""

    @field_validator("base_path", mode="before")
    @classmethod
    def normalize_base_path(cls, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text or text == "/":
            return ""
        if not text.startswith("/"):
            text = f"/{text}"
        return text.rstrip("/")


class BackendConfig(BaseModel):
    provider: ProviderName
    base_url: str
    # Deprecated alias for auth.fallback_backend_key (kept for older configs).
    api_key: str | None = None


class KeyMapping(BaseModel):
    """Map a public-face API key to the upstream backend API key."""

    public_key: str
    backend_key: str
    label: str | None = None

    @field_validator("public_key", "backend_key", mode="before")
    @classmethod
    def strip_keys(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class AuthConfig(BaseModel):
    """Public-face API key -> backend API key mapping."""

    key_map: list[KeyMapping] = Field(default_factory=list)
    # Used when the client key is missing or not listed in key_map.
    # Empty/null means call the backend without an API key (e.g. Koios free tier).
    fallback_backend_key: str | None = None
    # When true, set X-Janus-Auth / X-Janus-Auth-Warning on responses.
    # Default false so the public face looks closer to native BF/Koios.
    expose_janus_headers: bool = False

    @field_validator("key_map", mode="before")
    @classmethod
    def empty_key_map(cls, value: Any) -> Any:
        return [] if value is None else value

    @field_validator("fallback_backend_key", mode="before")
    @classmethod
    def empty_fallback_to_none(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value


class AuditConfig(BaseModel):
    """Compatibility audit: bind sessions by client IP or public API key."""

    enabled: bool = True
    session_ttl_minutes: int = Field(default=60, ge=1, le=24 * 60)
    # Number of reverse-proxy hops to peel from X-Forwarded-For (nginx = 1).
    trusted_proxy_hops: int = Field(default=1, ge=0, le=10)
    max_events_per_session: int = Field(default=5000, ge=1, le=100_000)


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    public_face: ProviderName
    backend: BackendConfig
    auth: AuthConfig = Field(default_factory=AuthConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)

    @field_validator("backend", mode="before")
    @classmethod
    def _coerce_backend(cls, value: Any) -> Any:
        return value

    @model_validator(mode="after")
    def face_must_differ_from_backend(self) -> AppConfig:
        if self.public_face == self.backend.provider:
            raise ValueError(
                "public_face and backend.provider must differ "
                f"(both are {self.public_face!r}); Janus translates between providers"
            )
        return self

    @model_validator(mode="after")
    def migrate_legacy_backend_api_key(self) -> AppConfig:
        if self.auth.fallback_backend_key is None and self.backend.api_key:
            self.auth.fallback_backend_key = self.backend.api_key.strip() or None
        return self


DEFAULT_BASE_URLS: dict[ProviderName, str] = {
    ProviderName.BLOCKFROST: "https://cardano-mainnet.blockfrost.io/api/v0",
    ProviderName.KOIOS: "https://api.koios.rest/api/v1",
}


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment overrides for secrets and common settings."""
    backend = data.setdefault("backend", {})
    if not isinstance(backend, dict):
        raise ValueError("backend must be a mapping")

    api_key = os.environ.get("JANUS_BACKEND_API_KEY")
    if api_key:
        backend["api_key"] = api_key
        auth = data.setdefault("auth", {})
        if isinstance(auth, dict) and auth.get("fallback_backend_key") in (None, ""):
            auth["fallback_backend_key"] = api_key

    base_url = os.environ.get("JANUS_BACKEND_BASE_URL")
    if base_url:
        backend["base_url"] = base_url

    provider = os.environ.get("JANUS_BACKEND_PROVIDER")
    if provider:
        backend["provider"] = provider

    face = os.environ.get("JANUS_PUBLIC_FACE")
    if face:
        data["public_face"] = face

    host = os.environ.get("JANUS_HOST")
    port = os.environ.get("JANUS_PORT")
    base_path = os.environ.get("JANUS_BASE_PATH")
    if host or port or base_path is not None:
        server = data.setdefault("server", {})
        if not isinstance(server, dict):
            raise ValueError("server must be a mapping")
        if host:
            server["host"] = host
        if port:
            server["port"] = int(port)
        if base_path is not None:
            server["base_path"] = base_path

    return data


def _fill_default_base_url(data: dict[str, Any]) -> dict[str, Any]:
    backend = data.get("backend")
    if isinstance(backend, dict) and not backend.get("base_url"):
        provider = backend.get("provider")
        if provider in DEFAULT_BASE_URLS:
            backend["base_url"] = DEFAULT_BASE_URLS[ProviderName(provider)]
        elif provider in {p.value for p in ProviderName}:
            backend["base_url"] = DEFAULT_BASE_URLS[ProviderName(provider)]
    return data


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load config from YAML (optional) and environment overrides."""
    data: dict[str, Any] = {}
    if path is not None:
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with config_path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Config root must be a mapping")
        data = loaded

    data = _fill_default_base_url(data)
    data = _apply_env_overrides(data)

    if "public_face" not in data:
        raise ValueError("public_face is required (set in config or JANUS_PUBLIC_FACE)")
    if "backend" not in data or not isinstance(data["backend"], dict):
        raise ValueError("backend is required")
    if "provider" not in data["backend"]:
        raise ValueError("backend.provider is required")
    if not data["backend"].get("base_url"):
        raise ValueError("backend.base_url is required")

    return AppConfig.model_validate(data)


def public_url(base_path: str, path: str) -> str:
    """Join configured public base_path with an app-absolute path."""
    if not path.startswith("/"):
        path = f"/{path}"
    prefix = (base_path or "").rstrip("/")
    if not prefix:
        return path
    return f"{prefix}{path}"
