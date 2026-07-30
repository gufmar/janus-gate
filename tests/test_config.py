"""Config validation for faces, sources, and passthrough."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from janus_gate.config import (
    AppConfig,
    BackendConfig,
    BackendSource,
    FaceName,
    ServerConfig,
)
from janus_gate.providers import create_backend


def test_same_api_face_rejected_without_passthrough() -> None:
    with pytest.raises(ValidationError, match="passthrough"):
        AppConfig(
            server=ServerConfig(host="127.0.0.1", port=8080),
            public_face=FaceName.BLOCKFROST,
            backend=BackendConfig(
                provider=BackendSource.BLOCKFROST,
                base_url="https://example.invalid",
            ),
        )


def test_same_api_face_allowed_with_passthrough() -> None:
    cfg = AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080),
        public_face=FaceName.BLOCKFROST,
        backend=BackendConfig(
            provider=BackendSource.BLOCKFROST,
            base_url="https://example.invalid",
            passthrough=True,
        ),
    )
    assert cfg.backend.passthrough is True
    backend = create_backend(cfg)
    assert backend.name == "blockfrost"


def test_dbsync_factory_builds_provider() -> None:
    cfg = AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080),
        public_face=FaceName.BLOCKFROST,
        backend=BackendConfig(
            provider=BackendSource.DBSYNC,
            dsn="postgresql://user:pass@localhost:5432/dbsync",
        ),
    )
    backend = create_backend(cfg)
    assert backend.name == "dbsync"


def test_dbsync_requires_dsn() -> None:
    with pytest.raises(ValidationError, match="dsn"):
        AppConfig(
            server=ServerConfig(host="127.0.0.1", port=8080),
            public_face=FaceName.KOIOS,
            backend=BackendConfig(provider=BackendSource.DBSYNC),
        )


def test_translate_mode_still_works() -> None:
    cfg = AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080),
        public_face=FaceName.BLOCKFROST,
        backend=BackendConfig(
            provider=BackendSource.KOIOS,
            base_url="https://example.invalid",
        ),
    )
    assert cfg.public_face is FaceName.BLOCKFROST
    assert cfg.backend.provider is BackendSource.KOIOS
