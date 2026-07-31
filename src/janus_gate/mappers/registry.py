"""Endpoint translation helpers used by public faces."""

from __future__ import annotations

from typing import Any

from janus_gate.config import ProviderName
from janus_gate.mapping import adapt as concepts
from janus_gate.mapping.adapt import adapt_to_face
from janus_gate.providers.base import BackendProvider
from janus_gate.providers.koios import KoiosProvider


async def fetch_tip_as(face: ProviderName, backend: BackendProvider) -> Any:
    raw = await backend.get_tip()
    block_detail = None
    # Tip enrichment stays here: Koios tip lacks some BF latest-block fields.
    if face is ProviderName.BLOCKFROST and backend.name == "koios":
        tip_row = raw[0] if isinstance(raw, list) and raw else raw
        height = None
        if isinstance(tip_row, dict):
            height = tip_row.get("block_height", tip_row.get("block_no"))
        if height is not None and isinstance(backend, KoiosProvider):
            try:
                block_detail = await backend.get_block_by_height(int(height))
            except Exception:
                block_detail = None
    return adapt_to_face(
        face, backend.name, concepts.TIP, raw, block_detail=block_detail
    )


async def fetch_genesis_as(face: ProviderName, backend: BackendProvider) -> Any:
    raw = await backend.get_genesis()
    return adapt_to_face(face, backend.name, concepts.GENESIS, raw)


async def fetch_epoch_as(
    face: ProviderName,
    backend: BackendProvider,
    number: int | None = None,
) -> Any:
    raw = await backend.get_epoch(number)
    return adapt_to_face(face, backend.name, concepts.EPOCH, raw)


async def fetch_epoch_parameters_as(
    face: ProviderName,
    backend: BackendProvider,
    number: int | None = None,
) -> Any:
    raw = await backend.get_epoch_parameters(number)
    return adapt_to_face(face, backend.name, concepts.EPOCH_PARAMETERS, raw)


async def fetch_epochs_next_as(
    face: ProviderName,
    backend: BackendProvider,
    number: int,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_epochs_next(number, count=count, page=page)
    return _adapt_epoch_list(face, backend.name, raw)


async def fetch_epochs_previous_as(
    face: ProviderName,
    backend: BackendProvider,
    number: int,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_epochs_previous(number, count=count, page=page)
    return _adapt_epoch_list(face, backend.name, raw)


def _adapt_epoch_list(face: ProviderName, source: str, raw: Any) -> list[Any]:
    if not isinstance(raw, list):
        raise TypeError("epochs next/previous payload must be a list")
    # Same-provider passthrough (Blockfrost list of epoch objects).
    if (face is ProviderName.BLOCKFROST and source == "blockfrost") or (
        face is ProviderName.KOIOS and source == "koios"
    ):
        return raw
    out: list[Any] = []
    for item in raw:
        if source == "koios":
            payload: Any = item if isinstance(item, list) else [item]
        else:
            payload = item
        out.append(adapt_to_face(face, source, concepts.EPOCH, payload))
    return out


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
    return adapt_to_face(
        face, backend.name, concepts.EPOCH_BLOCKS, raw, epoch_number=number
    )


async def fetch_block_as(
    face: ProviderName,
    backend: BackendProvider,
    hash_or_number: str,
) -> Any:
    raw = await backend.get_block(hash_or_number)
    return adapt_to_face(face, backend.name, concepts.BLOCK, raw)


async def fetch_blocks_next_as(
    face: ProviderName,
    backend: BackendProvider,
    hash_or_number: str,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_blocks_next(hash_or_number, count=count, page=page)
    return _adapt_block_list(face, backend.name, raw)


async def fetch_blocks_previous_as(
    face: ProviderName,
    backend: BackendProvider,
    hash_or_number: str,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_blocks_previous(hash_or_number, count=count, page=page)
    return _adapt_block_list(face, backend.name, raw)


def _adapt_block_list(face: ProviderName, source: str, raw: Any) -> list[Any]:
    if not isinstance(raw, list):
        raise TypeError("blocks next/previous payload must be a list")
    if (face is ProviderName.BLOCKFROST and source == "blockfrost") or (
        face is ProviderName.KOIOS and source == "koios"
    ):
        return raw
    out: list[Any] = []
    for item in raw:
        if source == "koios":
            payload: Any = item if isinstance(item, list) else [item]
        else:
            payload = item
        out.append(adapt_to_face(face, source, concepts.BLOCK, payload))
    return out


async def fetch_block_by_slot_as(
    face: ProviderName,
    backend: BackendProvider,
    slot: int,
) -> Any:
    raw = await backend.get_block_by_slot(slot)
    return adapt_to_face(face, backend.name, concepts.BLOCK, raw)


async def fetch_block_by_epoch_slot_as(
    face: ProviderName,
    backend: BackendProvider,
    epoch: int,
    slot: int,
) -> Any:
    raw = await backend.get_block_by_epoch_slot(epoch, slot)
    return adapt_to_face(face, backend.name, concepts.BLOCK, raw)


async def fetch_era_summaries_as(
    face: ProviderName,
    backend: BackendProvider,
) -> Any:
    raw = await backend.get_era_summaries()
    return adapt_to_face(face, backend.name, concepts.ERA_SUMMARIES, raw)


async def fetch_block_transactions_as(
    face: ProviderName,
    backend: BackendProvider,
    hash_or_number: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_block_transactions(
        hash_or_number, count=count, page=page, order=order
    )
    block_hash = hash_or_number if not hash_or_number.isdigit() else hash_or_number
    return adapt_to_face(
        face, backend.name, concepts.BLOCK_TXS, raw, block_hash=block_hash
    )


async def fetch_address_as(
    face: ProviderName,
    backend: BackendProvider,
    address: str,
) -> Any:
    raw = await backend.get_address_info(address)
    return adapt_to_face(
        face, backend.name, concepts.ADDRESS, raw, address=address
    )


async def fetch_address_extended_as(
    face: ProviderName,
    backend: BackendProvider,
    address: str,
) -> Any:
    raw = await backend.get_address_extended(address)
    return adapt_to_face(
        face, backend.name, concepts.ADDRESS_EXTENDED, raw, address=address
    )


async def fetch_address_assets_as(
    face: ProviderName,
    backend: BackendProvider,
    address: str,
) -> Any:
    raw = await backend.get_address_assets(address)
    return adapt_to_face(
        face, backend.name, concepts.ADDRESS_ASSETS, raw, address=address
    )


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
    return adapt_to_face(
        face, backend.name, concepts.ADDRESS_UTXOS, raw, address=address
    )


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
    return adapt_to_face(face, backend.name, concepts.ADDRESS_TXS, raw)


async def submit_tx_as(backend: BackendProvider, cbor: bytes) -> Any:
    return await backend.submit_tx(cbor)


async def fetch_tx_as(face: ProviderName, backend: BackendProvider, tx_hash: str) -> Any:
    raw = await backend.get_tx(tx_hash)
    return adapt_to_face(face, backend.name, concepts.TX, raw)


async def fetch_tx_utxos_as(
    face: ProviderName, backend: BackendProvider, tx_hash: str
) -> Any:
    raw = await backend.get_tx_utxos(tx_hash)
    return adapt_to_face(face, backend.name, concepts.TX_UTXOS, raw)


async def fetch_tx_metadata_as(
    face: ProviderName, backend: BackendProvider, tx_hash: str
) -> Any:
    raw = await backend.get_tx_metadata(tx_hash)
    return adapt_to_face(
        face, backend.name, concepts.TX_METADATA, raw, tx_hash=tx_hash
    )


async def fetch_tx_cbor_as(
    face: ProviderName, backend: BackendProvider, tx_hash: str
) -> Any:
    raw = await backend.get_tx_cbor(tx_hash)
    return adapt_to_face(face, backend.name, concepts.TX_CBOR, raw, tx_hash=tx_hash)


async def fetch_account_as(
    face: ProviderName, backend: BackendProvider, stake_address: str
) -> Any:
    raw = await backend.get_account_info(stake_address)
    return adapt_to_face(
        face, backend.name, concepts.ACCOUNT, raw, stake_address=stake_address
    )


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
    return adapt_to_face(
        face,
        backend.name,
        concepts.ACCOUNT_REWARDS,
        raw,
        stake_address=stake_address,
        count=count,
        page=page,
        order=order,
    )


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
    return adapt_to_face(
        face,
        backend.name,
        concepts.ACCOUNT_HISTORY,
        raw,
        stake_address=stake_address,
        count=count,
        page=page,
        order=order,
    )


async def fetch_account_addresses_as(
    face: ProviderName,
    backend: BackendProvider,
    stake_address: str,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_account_addresses(stake_address)
    return adapt_to_face(
        face,
        backend.name,
        concepts.ACCOUNT_ADDRESSES,
        raw,
        stake_address=stake_address,
        count=count,
        page=page,
    )


async def fetch_account_transactions_as(
    face: ProviderName,
    backend: BackendProvider,
    stake_address: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_account_transactions(
        stake_address, count=count, page=page, order=order
    )
    return adapt_to_face(
        face,
        backend.name,
        concepts.ACCOUNT_TXS,
        raw,
        stake_address=stake_address,
    )


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
    return adapt_to_face(
        face,
        backend.name,
        concepts.ACCOUNT_DELEGATIONS,
        raw,
        stake_address=stake_address,
        count=count,
        page=page,
        order=order,
    )


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
    return adapt_to_face(
        face, backend.name, concepts.POOLS, raw, extended=extended
    )


async def fetch_pool_as(
    face: ProviderName, backend: BackendProvider, pool_id: str
) -> Any:
    raw = await backend.get_pool(pool_id)
    adapted = adapt_to_face(face, backend.name, concepts.POOL, raw)
    # Blockfrost /pools/{id} omits relays; merge from /relays for Koios face.
    if (
        face is ProviderName.KOIOS
        and backend.name == "blockfrost"
        and isinstance(adapted, list)
        and adapted
        and isinstance(adapted[0], dict)
    ):
        try:
            relays_raw = await backend.get_pool_relays(pool_id)
            relays_face = adapt_to_face(
                face,
                backend.name,
                concepts.POOL_RELAYS,
                relays_raw,
                pool_id=pool_id,
            )
            if (
                isinstance(relays_face, list)
                and relays_face
                and isinstance(relays_face[0], dict)
            ):
                adapted[0]["relays"] = relays_face[0].get("relays") or []
        except Exception:  # noqa: BLE001
            adapted[0]["relays"] = adapted[0].get("relays") or []
    return adapted


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
    return adapt_to_face(face, backend.name, concepts.POOL_HISTORY, raw)


async def fetch_pool_metadata_as(
    face: ProviderName, backend: BackendProvider, pool_id: str
) -> Any:
    raw = await backend.get_pool_metadata(pool_id)
    return adapt_to_face(
        face, backend.name, concepts.POOL_METADATA, raw, pool_id=pool_id
    )


async def fetch_pool_delegators_as(
    face: ProviderName,
    backend: BackendProvider,
    pool_id: str,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_pool_delegators(pool_id, count=count, page=page)
    return adapt_to_face(face, backend.name, concepts.POOL_DELEGATORS, raw)


async def fetch_pool_relays_as(
    face: ProviderName, backend: BackendProvider, pool_id: str
) -> Any:
    raw = await backend.get_pool_relays(pool_id)
    return adapt_to_face(
        face, backend.name, concepts.POOL_RELAYS, raw, pool_id=pool_id
    )


async def fetch_pool_blocks_as(
    face: ProviderName,
    backend: BackendProvider,
    pool_id: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_pool_blocks(
        pool_id, count=count, page=page, order=order
    )
    return adapt_to_face(face, backend.name, concepts.POOL_BLOCKS, raw)


async def fetch_pool_updates_as(
    face: ProviderName,
    backend: BackendProvider,
    pool_id: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_pool_updates(
        pool_id, count=count, page=page, order=order
    )
    return adapt_to_face(face, backend.name, concepts.POOL_UPDATES, raw)


async def fetch_pool_votes_as(
    face: ProviderName,
    backend: BackendProvider,
    pool_id: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_pool_votes(
        pool_id, count=count, page=page, order=order
    )
    return adapt_to_face(face, backend.name, concepts.POOL_VOTES, raw)


async def fetch_committee_as(face: ProviderName, backend: BackendProvider) -> Any:
    raw = await backend.get_committee()
    return adapt_to_face(face, backend.name, concepts.COMMITTEE, raw)


async def fetch_dreps_as(
    face: ProviderName,
    backend: BackendProvider,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_dreps(count=count, page=page)
    return adapt_to_face(face, backend.name, concepts.DREPS, raw)


async def fetch_drep_as(
    face: ProviderName, backend: BackendProvider, drep_id: str
) -> Any:
    raw = await backend.get_drep(drep_id)
    return adapt_to_face(face, backend.name, concepts.DREP, raw, drep_id=drep_id)


async def fetch_proposals_as(
    face: ProviderName,
    backend: BackendProvider,
    *,
    count: int = 100,
    page: int = 1,
) -> Any:
    raw = await backend.get_proposals(count=count, page=page)
    return adapt_to_face(face, backend.name, concepts.PROPOSALS, raw)


async def fetch_script_as(
    face: ProviderName, backend: BackendProvider, script_hash: str
) -> Any:
    raw = await backend.get_script(script_hash)
    return adapt_to_face(
        face, backend.name, concepts.SCRIPT, raw, script_hash=script_hash
    )


async def fetch_datum_as(
    face: ProviderName, backend: BackendProvider, datum_hash: str
) -> Any:
    raw = await backend.get_datum(datum_hash)
    return adapt_to_face(
        face, backend.name, concepts.DATUM, raw, datum_hash=datum_hash
    )


async def fetch_metadata_labels_as(
    face: ProviderName,
    backend: BackendProvider,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_metadata_labels(count=count, page=page, order=order)
    return adapt_to_face(face, backend.name, concepts.METADATA_LABELS, raw)


async def fetch_metadata_by_label_as(
    face: ProviderName,
    backend: BackendProvider,
    label: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_metadata_by_label(
        label, count=count, page=page, order=order
    )
    return adapt_to_face(face, backend.name, concepts.METADATA_BY_LABEL, raw)


async def fetch_asset_as(
    face: ProviderName, backend: BackendProvider, asset: str
) -> Any:
    raw = await backend.get_asset(asset)
    return adapt_to_face(face, backend.name, concepts.ASSET, raw, asset=asset)


async def fetch_assets_as(
    face: ProviderName,
    backend: BackendProvider,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_assets(count=count, page=page, order=order)
    return adapt_to_face(face, backend.name, concepts.ASSETS, raw)


async def fetch_asset_history_as(
    face: ProviderName,
    backend: BackendProvider,
    asset: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_asset_history(
        asset, count=count, page=page, order=order
    )
    return adapt_to_face(
        face, backend.name, concepts.ASSET_HISTORY, raw, asset=asset
    )


async def fetch_asset_transactions_as(
    face: ProviderName,
    backend: BackendProvider,
    asset: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_asset_transactions(
        asset, count=count, page=page, order=order
    )
    return adapt_to_face(face, backend.name, concepts.ASSET_TXS, raw)


async def fetch_asset_addresses_as(
    face: ProviderName,
    backend: BackendProvider,
    asset: str,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> Any:
    raw = await backend.get_asset_addresses(
        asset, count=count, page=page, order=order
    )
    return adapt_to_face(face, backend.name, concepts.ASSET_ADDRESSES, raw)
