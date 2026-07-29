"""Endpoint translation helpers used by public faces."""

from __future__ import annotations

from typing import Any

from janus_gate.config import ProviderName
from janus_gate.mappers import address as address_mapper
from janus_gate.mappers import tip as tip_mapper
from janus_gate.providers.base import BackendProvider
from janus_gate.providers.koios import KoiosProvider


async def fetch_tip_as(face: ProviderName, backend: BackendProvider) -> Any:
    """Return tip/latest-block data shaped for the configured public face."""
    raw = await backend.get_tip()

    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        block_detail = None
        height = None
        tip_row = raw[0] if isinstance(raw, list) and raw else raw
        if isinstance(tip_row, dict):
            height = tip_row.get("block_height", tip_row.get("block_no"))
        if height is not None and isinstance(backend, KoiosProvider):
            try:
                block_detail = await backend.get_block_by_height(int(height))
            except Exception:
                block_detail = None
        return tip_mapper.koios_tip_to_blockfrost(raw, block_detail)

    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return tip_mapper.blockfrost_latest_to_koios_tip(raw)

    # Same-shape passthrough should not occur (validated at config), but keep safe.
    return raw


async def fetch_address_as(
    face: ProviderName,
    backend: BackendProvider,
    address: str,
) -> Any:
    """Return address info shaped for the configured public face."""
    raw = await backend.get_address_info(address)

    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return address_mapper.koios_address_to_blockfrost(raw, address)

    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return address_mapper.blockfrost_address_to_koios(raw)

    return raw
