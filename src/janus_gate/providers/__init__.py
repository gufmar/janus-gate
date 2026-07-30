"""Provider factory helpers."""

from __future__ import annotations

from janus_gate.config import AppConfig, BackendSource
from janus_gate.providers.base import BackendProvider
from janus_gate.providers.blockfrost import BlockfrostProvider
from janus_gate.providers.koios import KoiosProvider


def create_backend(config: AppConfig) -> BackendProvider:
    provider = config.backend.provider
    base_url = config.backend.base_url
    api_key = config.backend.api_key

    if provider is BackendSource.BLOCKFROST:
        if not base_url:
            raise ValueError("backend.base_url is required for blockfrost")
        return BlockfrostProvider(base_url, api_key)
    if provider is BackendSource.KOIOS:
        if not base_url:
            raise ValueError("backend.base_url is required for koios")
        return KoiosProvider(base_url, api_key)
    if provider is BackendSource.DBSYNC:
        raise NotImplementedError(
            "dbsync backend is not implemented yet (Phase 2); "
            "config validates, but create_backend cannot build a provider"
        )
    if provider in (BackendSource.OGMIOS, BackendSource.YACI):
        raise NotImplementedError(
            f"{provider.value} backend is reserved for a later phase "
            "and is not implemented yet"
        )
    raise ValueError(f"Unsupported backend provider: {provider}")
