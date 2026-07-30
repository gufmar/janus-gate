"""Face adaptation dispatch: source-shaped JSON -> public face JSON."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from janus_gate.faces.errors import MappingError
from janus_gate.mappers import account as account_mapper
from janus_gate.mappers import address as address_mapper
from janus_gate.mappers import asset as asset_mapper
from janus_gate.mappers import block as block_mapper
from janus_gate.mappers import epoch as epoch_mapper
from janus_gate.mappers import genesis as genesis_mapper
from janus_gate.mappers import governance as governance_mapper
from janus_gate.mappers import metadata as metadata_mapper
from janus_gate.mappers import pool as pool_mapper
from janus_gate.mappers import script as script_mapper
from janus_gate.mappers import tx as tx_mapper

Adapter = Callable[..., Any]


def _one(fn: Callable[[Any], Any]) -> Adapter:
    """Adapt a single-arg mapper so unused ctx kwargs are ignored."""

    def _wrapped(raw: Any, **_ctx: Any) -> Any:
        return fn(raw)

    return _wrapped


# Concept keys used by the registry.
TIP = "tip"
GENESIS = "genesis"
EPOCH = "epoch"
EPOCH_PARAMETERS = "epoch_parameters"
EPOCH_BLOCKS = "epoch_blocks"
BLOCK = "block"
BLOCK_TXS = "block_txs"
ADDRESS = "address"
ADDRESS_UTXOS = "address_utxos"
ADDRESS_TXS = "address_txs"
TX = "tx"
TX_UTXOS = "tx_utxos"
TX_METADATA = "tx_metadata"
TX_CBOR = "tx_cbor"
ACCOUNT = "account"
ACCOUNT_REWARDS = "account_rewards"
ACCOUNT_HISTORY = "account_history"
ACCOUNT_ADDRESSES = "account_addresses"
ACCOUNT_TXS = "account_txs"
ACCOUNT_DELEGATIONS = "account_delegations"
POOLS = "pools"
POOL = "pool"
POOL_HISTORY = "pool_history"
POOL_METADATA = "pool_metadata"
POOL_DELEGATORS = "pool_delegators"
POOL_RELAYS = "pool_relays"
COMMITTEE = "committee"
DREPS = "dreps"
DREP = "drep"
PROPOSALS = "proposals"
SCRIPT = "script"
DATUM = "datum"
METADATA_LABELS = "metadata_labels"
METADATA_BY_LABEL = "metadata_by_label"
ASSET = "asset"


def _face_key(face: Any) -> str:
    return face.value if hasattr(face, "value") else str(face)


def _source_key(source: Any) -> str:
    return source.value if hasattr(source, "value") else str(source)


def _koios_tip_to_bf(raw: Any, **ctx: Any) -> Any:
    return block_mapper.koios_tip_to_blockfrost(raw, ctx.get("block_detail"))


def _bf_epoch_blocks_to_koios(raw: Any, **ctx: Any) -> Any:
    return epoch_mapper.blockfrost_epoch_blocks_to_koios(raw, ctx["epoch_number"])


def _bf_block_txs_to_koios(raw: Any, **ctx: Any) -> Any:
    return block_mapper.blockfrost_block_txs_to_koios(raw, ctx["block_hash"])


def _koios_address_to_bf(raw: Any, **ctx: Any) -> Any:
    return address_mapper.koios_address_to_blockfrost(raw, ctx["address"])


def _koios_address_utxos_to_bf(raw: Any, **ctx: Any) -> Any:
    return address_mapper.koios_address_utxos_to_blockfrost(raw, ctx["address"])


def _bf_tx_metadata_to_koios(raw: Any, **ctx: Any) -> Any:
    return tx_mapper.blockfrost_tx_metadata_to_koios(raw, ctx["tx_hash"])


def _bf_tx_cbor_to_koios(raw: Any, **ctx: Any) -> Any:
    return tx_mapper.blockfrost_tx_cbor_to_koios(raw, ctx["tx_hash"])


def _koios_account_to_bf(raw: Any, **ctx: Any) -> Any:
    return account_mapper.koios_account_to_blockfrost(raw, ctx["stake_address"])


def _koios_account_rewards_to_bf(raw: Any, **ctx: Any) -> Any:
    return account_mapper.koios_account_rewards_to_blockfrost(
        raw,
        count=ctx.get("count", 100),
        page=ctx.get("page", 1),
        order=ctx.get("order", "asc"),
    )


def _bf_account_rewards_to_koios(raw: Any, **ctx: Any) -> Any:
    return account_mapper.blockfrost_account_rewards_to_koios(
        raw, ctx["stake_address"]
    )


def _koios_account_history_to_bf(raw: Any, **ctx: Any) -> Any:
    return account_mapper.koios_account_history_to_blockfrost(
        raw,
        count=ctx.get("count", 100),
        page=ctx.get("page", 1),
        order=ctx.get("order", "asc"),
    )


def _bf_account_history_to_koios(raw: Any, **ctx: Any) -> Any:
    return account_mapper.blockfrost_account_history_to_koios(
        raw, ctx["stake_address"]
    )


def _bf_account_addresses_to_koios(raw: Any, **ctx: Any) -> Any:
    return account_mapper.blockfrost_account_addresses_to_koios(
        raw, ctx["stake_address"]
    )


def _koios_account_txs_to_bf(raw: Any, **ctx: Any) -> Any:
    return account_mapper.koios_account_txs_to_blockfrost(raw, ctx["stake_address"])


def _koios_account_delegations_to_bf(raw: Any, **ctx: Any) -> Any:
    return account_mapper.koios_account_delegations_to_blockfrost(
        raw,
        count=ctx.get("count", 100),
        page=ctx.get("page", 1),
        order=ctx.get("order", "asc"),
    )


def _bf_account_delegations_to_koios(raw: Any, **ctx: Any) -> Any:
    return account_mapper.blockfrost_account_delegations_to_koios(
        raw, ctx["stake_address"]
    )


def _koios_pools_to_bf(raw: Any, **ctx: Any) -> Any:
    if ctx.get("extended"):
        return pool_mapper.koios_pool_list_to_blockfrost_extended(raw)
    return pool_mapper.koios_pool_list_to_blockfrost_ids(raw)


def _bf_pools_to_koios(raw: Any, **ctx: Any) -> Any:
    if ctx.get("extended"):
        if raw and isinstance(raw, list) and isinstance(raw[0], str):
            return pool_mapper.blockfrost_pool_ids_to_koios_list(raw)
        return raw
    return pool_mapper.blockfrost_pool_ids_to_koios_list(raw)


def _koios_pool_metadata_to_bf(raw: Any, **ctx: Any) -> Any:
    return pool_mapper.koios_pool_metadata_to_blockfrost(raw, ctx["pool_id"])


def _bf_pool_relays_to_koios(raw: Any, **ctx: Any) -> Any:
    return pool_mapper.blockfrost_pool_relays_to_koios(raw, ctx["pool_id"])


def _koios_drep_to_bf(raw: Any, **ctx: Any) -> Any:
    return governance_mapper.koios_drep_info_to_blockfrost(raw, ctx["drep_id"])


def _koios_script_to_bf(raw: Any, **ctx: Any) -> Any:
    return script_mapper.koios_script_info_to_blockfrost(raw, ctx["script_hash"])


def _koios_datum_to_bf(raw: Any, **ctx: Any) -> Any:
    return script_mapper.koios_datum_to_blockfrost(raw, ctx["datum_hash"])


def _bf_datum_to_koios(raw: Any, **ctx: Any) -> Any:
    return script_mapper.blockfrost_datum_to_koios(raw, ctx["datum_hash"])


def _koios_asset_to_bf(raw: Any, **ctx: Any) -> Any:
    return asset_mapper.koios_asset_info_to_blockfrost(raw, ctx["asset"])


# (face, source, concept) -> adapter
_ADAPTERS: dict[tuple[str, str, str], Adapter] = {
    ("blockfrost", "koios", TIP): _koios_tip_to_bf,
    ("koios", "blockfrost", TIP): _one(block_mapper.blockfrost_latest_to_koios_tip),
    ("blockfrost", "koios", GENESIS): _one(genesis_mapper.koios_genesis_to_blockfrost),
    ("koios", "blockfrost", GENESIS): _one(genesis_mapper.blockfrost_genesis_to_koios),
    ("blockfrost", "koios", EPOCH): _one(epoch_mapper.koios_epoch_to_blockfrost),
    ("koios", "blockfrost", EPOCH): _one(epoch_mapper.blockfrost_epoch_to_koios),
    ("blockfrost", "koios", EPOCH_PARAMETERS): _one(
        epoch_mapper.koios_epoch_params_to_blockfrost
    ),
    ("koios", "blockfrost", EPOCH_PARAMETERS): _one(
        epoch_mapper.blockfrost_epoch_params_to_koios
    ),
    ("blockfrost", "koios", EPOCH_BLOCKS): _one(
        epoch_mapper.koios_epoch_blocks_to_blockfrost
    ),
    ("koios", "blockfrost", EPOCH_BLOCKS): _bf_epoch_blocks_to_koios,
    ("blockfrost", "koios", BLOCK): _one(block_mapper.koios_block_to_blockfrost),
    ("koios", "blockfrost", BLOCK): _one(block_mapper.blockfrost_block_to_koios_info),
    ("blockfrost", "koios", BLOCK_TXS): _one(block_mapper.koios_block_txs_to_blockfrost),
    ("koios", "blockfrost", BLOCK_TXS): _bf_block_txs_to_koios,
    ("blockfrost", "koios", ADDRESS): _koios_address_to_bf,
    ("koios", "blockfrost", ADDRESS): _one(address_mapper.blockfrost_address_to_koios),
    ("blockfrost", "koios", ADDRESS_UTXOS): _koios_address_utxos_to_bf,
    ("koios", "blockfrost", ADDRESS_UTXOS): _one(
        address_mapper.blockfrost_address_utxos_to_koios
    ),
    ("blockfrost", "koios", ADDRESS_TXS): _one(
        address_mapper.koios_address_txs_to_blockfrost
    ),
    ("koios", "blockfrost", ADDRESS_TXS): _one(
        address_mapper.blockfrost_address_txs_to_koios
    ),
    ("blockfrost", "koios", TX): _one(tx_mapper.koios_tx_info_to_blockfrost),
    ("koios", "blockfrost", TX): _one(tx_mapper.blockfrost_tx_to_koios_info),
    ("blockfrost", "koios", TX_UTXOS): _one(tx_mapper.koios_tx_utxos_to_blockfrost),
    ("koios", "blockfrost", TX_UTXOS): _one(tx_mapper.blockfrost_tx_utxos_to_koios),
    ("blockfrost", "koios", TX_METADATA): _one(tx_mapper.koios_tx_metadata_to_blockfrost),
    ("koios", "blockfrost", TX_METADATA): _bf_tx_metadata_to_koios,
    ("blockfrost", "koios", TX_CBOR): _one(tx_mapper.koios_tx_cbor_to_blockfrost),
    ("koios", "blockfrost", TX_CBOR): _bf_tx_cbor_to_koios,
    ("blockfrost", "koios", ACCOUNT): _koios_account_to_bf,
    ("koios", "blockfrost", ACCOUNT): _one(account_mapper.blockfrost_account_to_koios),
    ("blockfrost", "koios", ACCOUNT_REWARDS): _koios_account_rewards_to_bf,
    ("koios", "blockfrost", ACCOUNT_REWARDS): _bf_account_rewards_to_koios,
    ("blockfrost", "koios", ACCOUNT_HISTORY): _koios_account_history_to_bf,
    ("koios", "blockfrost", ACCOUNT_HISTORY): _bf_account_history_to_koios,
    ("blockfrost", "koios", ACCOUNT_ADDRESSES): _one(
        account_mapper.koios_account_addresses_to_blockfrost
    ),
    ("koios", "blockfrost", ACCOUNT_ADDRESSES): _bf_account_addresses_to_koios,
    ("blockfrost", "koios", ACCOUNT_TXS): _koios_account_txs_to_bf,
    ("koios", "blockfrost", ACCOUNT_TXS): _one(
        account_mapper.blockfrost_account_txs_to_koios
    ),
    ("blockfrost", "koios", ACCOUNT_DELEGATIONS): _koios_account_delegations_to_bf,
    ("koios", "blockfrost", ACCOUNT_DELEGATIONS): _bf_account_delegations_to_koios,
    ("blockfrost", "koios", POOLS): _koios_pools_to_bf,
    ("koios", "blockfrost", POOLS): _bf_pools_to_koios,
    ("blockfrost", "koios", POOL): _one(pool_mapper.koios_pool_info_to_blockfrost),
    ("koios", "blockfrost", POOL): _one(pool_mapper.blockfrost_pool_to_koios_info),
    ("blockfrost", "koios", POOL_HISTORY): _one(
        pool_mapper.koios_pool_history_to_blockfrost
    ),
    ("koios", "blockfrost", POOL_HISTORY): _one(
        pool_mapper.blockfrost_pool_history_to_koios
    ),
    ("blockfrost", "koios", POOL_METADATA): _koios_pool_metadata_to_bf,
    ("koios", "blockfrost", POOL_METADATA): _one(
        pool_mapper.blockfrost_pool_metadata_to_koios
    ),
    ("blockfrost", "koios", POOL_DELEGATORS): _one(
        pool_mapper.koios_pool_delegators_to_blockfrost
    ),
    ("koios", "blockfrost", POOL_DELEGATORS): _one(
        pool_mapper.blockfrost_pool_delegators_to_koios
    ),
    ("blockfrost", "koios", POOL_RELAYS): _one(
        pool_mapper.koios_pool_relays_to_blockfrost
    ),
    ("koios", "blockfrost", POOL_RELAYS): _bf_pool_relays_to_koios,
    ("blockfrost", "koios", COMMITTEE): _one(
        governance_mapper.koios_committee_to_blockfrost
    ),
    ("koios", "blockfrost", COMMITTEE): _one(
        governance_mapper.blockfrost_committee_to_koios
    ),
    ("blockfrost", "koios", DREPS): _one(
        governance_mapper.koios_drep_list_to_blockfrost
    ),
    ("koios", "blockfrost", DREPS): _one(
        governance_mapper.blockfrost_drep_ids_to_koios
    ),
    ("blockfrost", "koios", DREP): _koios_drep_to_bf,
    ("koios", "blockfrost", DREP): _one(governance_mapper.blockfrost_drep_to_koios),
    ("blockfrost", "koios", PROPOSALS): _one(
        governance_mapper.koios_proposal_list_to_blockfrost
    ),
    ("koios", "blockfrost", PROPOSALS): _one(
        governance_mapper.blockfrost_proposals_to_koios
    ),
    ("blockfrost", "koios", SCRIPT): _koios_script_to_bf,
    ("koios", "blockfrost", SCRIPT): _one(script_mapper.blockfrost_script_to_koios),
    ("blockfrost", "koios", DATUM): _koios_datum_to_bf,
    ("koios", "blockfrost", DATUM): _bf_datum_to_koios,
    ("blockfrost", "koios", METADATA_LABELS): _one(
        metadata_mapper.koios_metalabels_to_blockfrost
    ),
    ("koios", "blockfrost", METADATA_LABELS): _one(
        metadata_mapper.blockfrost_metalabels_to_koios
    ),
    ("blockfrost", "koios", METADATA_BY_LABEL): _one(
        metadata_mapper.koios_tx_by_metalabel_to_blockfrost
    ),
    ("koios", "blockfrost", METADATA_BY_LABEL): _one(
        metadata_mapper.blockfrost_metadata_label_to_koios
    ),
    ("blockfrost", "koios", ASSET): _koios_asset_to_bf,
    ("koios", "blockfrost", ASSET): _one(asset_mapper.blockfrost_asset_to_koios),
}


def adapt_to_face(
    face: Any,
    source: Any,
    concept: str,
    raw: Any,
    **ctx: Any,
) -> Any:
    """Adapt backend-native JSON to the public face shape.

    When face and source match (passthrough), returns ``raw`` unchanged.
    Unknown (face, source, concept) triples raise MappingError.
    """
    face_k = _face_key(face)
    source_k = _source_key(source)
    if face_k == source_k:
        return raw

    adapter = _ADAPTERS.get((face_k, source_k, concept))
    if adapter is None:
        raise MappingError(
            f"No face adapter for concept={concept!r} "
            f"face={face_k!r} source={source_k!r}"
        )
    return adapter(raw, **ctx)
