"""Endpoint translation helpers used by public faces."""

from __future__ import annotations

from typing import Any

from janus_gate.config import ProviderName
from janus_gate.mappers import account as account_mapper
from janus_gate.mappers import address as address_mapper
from janus_gate.mappers import asset as asset_mapper
from janus_gate.mappers import block as block_mapper
from janus_gate.mappers import epoch as epoch_mapper
from janus_gate.mappers import genesis as genesis_mapper
from janus_gate.mappers import governance as governance_mapper
from janus_gate.mappers import pool as pool_mapper
from janus_gate.mappers import script as script_mapper
from janus_gate.mappers import tx as tx_mapper
from janus_gate.providers.base import BackendProvider
from janus_gate.providers.koios import KoiosProvider


async def fetch_tip_as(face: ProviderName, backend: BackendProvider) -> Any:
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


async def fetch_epoch_blocks_as(
    face: ProviderName,
    backend: BackendProvider,
    number: int,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_epoch_blocks(
        number, count=count, page=page, order=order
    )
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return epoch_mapper.koios_epoch_blocks_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return epoch_mapper.blockfrost_epoch_blocks_to_koios(raw, number)
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
    return await backend.submit_tx(cbor)


async def fetch_tx_as(face: ProviderName, backend: BackendProvider, tx_hash: str) -> Any:
    raw = await backend.get_tx(tx_hash)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return tx_mapper.koios_tx_info_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return tx_mapper.blockfrost_tx_to_koios_info(raw)
    return raw


async def fetch_tx_utxos_as(
    face: ProviderName, backend: BackendProvider, tx_hash: str
) -> Any:
    raw = await backend.get_tx_utxos(tx_hash)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return tx_mapper.koios_tx_utxos_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return tx_mapper.blockfrost_tx_utxos_to_koios(raw)
    return raw


async def fetch_tx_metadata_as(
    face: ProviderName, backend: BackendProvider, tx_hash: str
) -> Any:
    raw = await backend.get_tx_metadata(tx_hash)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return tx_mapper.koios_tx_metadata_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return tx_mapper.blockfrost_tx_metadata_to_koios(raw, tx_hash)
    return raw


async def fetch_tx_cbor_as(
    face: ProviderName, backend: BackendProvider, tx_hash: str
) -> Any:
    raw = await backend.get_tx_cbor(tx_hash)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return tx_mapper.koios_tx_cbor_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return tx_mapper.blockfrost_tx_cbor_to_koios(raw, tx_hash)
    return raw


async def fetch_account_as(
    face: ProviderName, backend: BackendProvider, stake_address: str
) -> Any:
    raw = await backend.get_account_info(stake_address)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return account_mapper.koios_account_to_blockfrost(raw, stake_address)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return account_mapper.blockfrost_account_to_koios(raw)
    return raw


async def fetch_account_rewards_as(
    face: ProviderName,
    backend: BackendProvider,
    stake_address: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_account_rewards(stake_address)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return account_mapper.koios_account_rewards_to_blockfrost(
            raw, count=count, page=page, order=order
        )
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return account_mapper.blockfrost_account_rewards_to_koios(raw, stake_address)
    return raw


async def fetch_account_history_as(
    face: ProviderName,
    backend: BackendProvider,
    stake_address: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_account_history(stake_address)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return account_mapper.koios_account_history_to_blockfrost(
            raw, count=count, page=page, order=order
        )
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return account_mapper.blockfrost_account_history_to_koios(raw, stake_address)
    return raw


async def fetch_account_addresses_as(
    face: ProviderName, backend: BackendProvider, stake_address: str
) -> Any:
    raw = await backend.get_account_addresses(stake_address)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return account_mapper.koios_account_addresses_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return account_mapper.blockfrost_account_addresses_to_koios(raw, stake_address)
    return raw


async def fetch_account_delegations_as(
    face: ProviderName,
    backend: BackendProvider,
    stake_address: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    # Partial: derive from stake history when backend is Koios.
    raw = await backend.get_account_history(stake_address)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return account_mapper.koios_account_delegations_to_blockfrost(
            raw, count=count, page=page, order=order
        )
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return account_mapper.blockfrost_account_delegations_to_koios(
            raw, stake_address
        )
    return raw


async def fetch_pools_as(
    face: ProviderName,
    backend: BackendProvider,
    *,
    count: int = 100,
    page: int = 1,
    extended: bool = False,
) -> Any:
    if extended:
        raw = await backend.get_pools_extended(count=count, page=page)
    else:
        raw = await backend.get_pools(count=count, page=page)

    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        if extended:
            return pool_mapper.koios_pool_list_to_blockfrost_extended(raw)
        return pool_mapper.koios_pool_list_to_blockfrost_ids(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        if extended:
            if raw and isinstance(raw, list) and isinstance(raw[0], str):
                return pool_mapper.blockfrost_pool_ids_to_koios_list(raw)
            return raw
        return pool_mapper.blockfrost_pool_ids_to_koios_list(raw)
    return raw


async def fetch_pool_as(
    face: ProviderName, backend: BackendProvider, pool_id: str
) -> Any:
    raw = await backend.get_pool(pool_id)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return pool_mapper.koios_pool_info_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return pool_mapper.blockfrost_pool_to_koios_info(raw)
    return raw


async def fetch_pool_history_as(
    face: ProviderName,
    backend: BackendProvider,
    pool_id: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_pool_history(
        pool_id, count=count, page=page, order=order
    )
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return pool_mapper.koios_pool_history_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return pool_mapper.blockfrost_pool_history_to_koios(raw)
    return raw


async def fetch_pool_metadata_as(
    face: ProviderName, backend: BackendProvider, pool_id: str
) -> Any:
    raw = await backend.get_pool_metadata(pool_id)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return pool_mapper.koios_pool_metadata_to_blockfrost(raw, pool_id)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return pool_mapper.blockfrost_pool_metadata_to_koios(raw)
    return raw


async def fetch_pool_delegators_as(
    face: ProviderName,
    backend: BackendProvider,
    pool_id: str,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_pool_delegators(pool_id, count=count, page=page)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return pool_mapper.koios_pool_delegators_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return pool_mapper.blockfrost_pool_delegators_to_koios(raw)
    return raw


async def fetch_pool_relays_as(
    face: ProviderName, backend: BackendProvider, pool_id: str
) -> Any:
    raw = await backend.get_pool_relays(pool_id)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return pool_mapper.koios_pool_relays_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return pool_mapper.blockfrost_pool_relays_to_koios(raw, pool_id)
    return raw


async def fetch_committee_as(face: ProviderName, backend: BackendProvider) -> Any:
    raw = await backend.get_committee()
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return governance_mapper.koios_committee_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return governance_mapper.blockfrost_committee_to_koios(raw)
    return raw


async def fetch_dreps_as(
    face: ProviderName,
    backend: BackendProvider,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_dreps(count=count, page=page)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return governance_mapper.koios_drep_list_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return governance_mapper.blockfrost_drep_ids_to_koios(raw)
    return raw


async def fetch_drep_as(
    face: ProviderName, backend: BackendProvider, drep_id: str
) -> Any:
    raw = await backend.get_drep(drep_id)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return governance_mapper.koios_drep_info_to_blockfrost(raw, drep_id)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return governance_mapper.blockfrost_drep_to_koios(raw)
    return raw


async def fetch_proposals_as(
    face: ProviderName,
    backend: BackendProvider,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_proposals(count=count, page=page)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return governance_mapper.koios_proposal_list_to_blockfrost(raw)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return governance_mapper.blockfrost_proposals_to_koios(raw)
    return raw


async def fetch_script_as(
    face: ProviderName, backend: BackendProvider, script_hash: str
) -> Any:
    raw = await backend.get_script(script_hash)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return script_mapper.koios_script_info_to_blockfrost(raw, script_hash)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return script_mapper.blockfrost_script_to_koios(raw)
    return raw


async def fetch_datum_as(
    face: ProviderName, backend: BackendProvider, datum_hash: str
) -> Any:
    raw = await backend.get_datum(datum_hash)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return script_mapper.koios_datum_to_blockfrost(raw, datum_hash)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return script_mapper.blockfrost_datum_to_koios(raw, datum_hash)
    return raw


async def fetch_asset_as(
    face: ProviderName, backend: BackendProvider, asset: str
) -> Any:
    raw = await backend.get_asset(asset)
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        return asset_mapper.koios_asset_info_to_blockfrost(raw, asset)
    if face is ProviderName.KOIOS and backend.name == "blockfrost":
        return asset_mapper.blockfrost_asset_to_koios(raw)
    return raw
