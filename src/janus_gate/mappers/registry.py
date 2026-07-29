"""Endpoint translation helpers used by public faces."""

from __future__ import annotations

from typing import Any

from janus_gate.config import ProviderName
from janus_gate.mappers import address as address_mapper
from janus_gate.mappers import block as block_mapper
from janus_gate.mappers import epoch as epoch_mapper
from janus_gate.mappers import genesis as genesis_mapper
from janus_gate.providers.base import BackendProvider
from janus_gate.providers.koios import KoiosProvider


async def fetch_tip_as(face: ProviderName, backend: BackendProvider) -> Any:
    """Return tip/latest-block data shaped for the configured public face."""
    raw = await backend.get_tip()

    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        block_detail = None
        tip_row = raw[0] if isinstance(raw, list) and raw else raw
        height = None
        if isinstance(tip_row, dict):
            height = tip_row.get("block_height", tip_row.get("block_no"))
        if height is not None and isinstance(backend, KoiosProvider):
            try:
                block_detail = await backend.get_block_by_height(int(height))
            except Exception:
                block_detail = None
        return block_mapper.koios_tip_to_blockfrost(raw, block_detail)

    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return block_mapper.blockfrost_latest_to_koios_tip(raw)

    return raw


async def fetch_genesis_as(face: ProviderName, backend: BackendProvider) -> Any:
    raw = await backend.get_genesis()
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return genesis_mapper.koios_genesis_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return genesis_mapper.blockfrost_genesis_to_koios(raw)
    return raw


async def fetch_epoch_as(
    face: ProviderName,
    backend: BackendProvider,
    number: int | None = None,
) -> Any:
    raw = await backend.get_epoch(number)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return epoch_mapper.koios_epoch_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return epoch_mapper.blockfrost_epoch_to_koios(raw)
    return raw


async def fetch_epoch_parameters_as(
    face: ProviderName,
    backend: BackendProvider,
    number: int | None = None,
) -> Any:
    raw = await backend.get_epoch_parameters(number)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return epoch_mapper.koios_epoch_params_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return epoch_mapper.blockfrost_epoch_params_to_koios(raw)
    return raw


async def fetch_block_as(
    face: ProviderName,
    backend: BackendProvider,
    hash_or_number: str,
) -> Any:
    raw = await backend.get_block(hash_or_number)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return block_mapper.koios_block_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return block_mapper.blockfrost_block_to_koios_info(raw)
    return raw


async def fetch_address_as(
    face: ProviderName,
    backend: BackendProvider,
    address: str,
) -> Any:
    raw = await backend.get_address_info(address)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return address_mapper.koios_address_to_blockfrost(raw, address)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return address_mapper.blockfrost_address_to_koios(raw)
    return raw


async def fetch_address_utxos_as(
    face: ProviderName,
    backend: BackendProvider,
    address: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_address_utxos(
        address, count=count, page=page, order=order
    )
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return address_mapper.koios_address_utxos_to_blockfrost(raw, address)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return address_mapper.blockfrost_address_utxos_to_koios(raw)
    return raw


async def fetch_address_transactions_as(
    face: ProviderName,
    backend: BackendProvider,
    address: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_address_transactions(
        address, count=count, page=page, order=order
    )
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return address_mapper.koios_address_txs_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return address_mapper.blockfrost_address_txs_to_koios(raw)
    return raw


async def submit_tx_as(backend: BackendProvider, cbor: bytes) -> Any:
    """Submit raw CBOR transaction via the configured backend (shape is provider-native)."""
    return await backend.submit_tx(cbor)
