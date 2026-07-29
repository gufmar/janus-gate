"""Provider factory helpers."""

from __future__ import annotations

from janus_gate.config import AppConfig, ProviderName
from janus_gate.providers.base import BackendProvider
from janus_gate.providers.blockfrost import BlockfrostProvider
from janus_gate.providers.koios import KoiosProvider


def create_backend(config: AppConfig) -> BackendProvider:
    provider = config.backend.provider
    base_url = config.backend.base_url
    api_key = config.backend.api_key

    if provider is ProviderName.BLOCKFROST:
        return BlockfrostProvider(base_url, api_key)
    if provider is ProviderName.KOIOS:
        return KoiosProvider(base_url, api_key)
    raise ValueError(f"Unsupported backend provider: {provider}")
