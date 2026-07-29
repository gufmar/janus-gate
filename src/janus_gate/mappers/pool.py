"""Pool mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def koios_pool_list_to_blockfrost_ids(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_list payload")
    return [
        row.get("pool_id_bech32")
        for row in rows
        if isinstance(row, dict) and row.get("pool_id_bech32")
    ]


def koios_pool_list_to_blockfrost_extended(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_list payload")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                "pool_id": row.get("pool_id_bech32"),
                "hex": row.get("pool_id_hex"),
                "active_stake": (
                    None if row.get("active_stake") is None else str(row.get("active_stake"))
                ),
                "live_stake": None,
                "live_saturation": None,
                "blocks_minted": None,
                "live_delegators": None,
                "reward_account": row.get("reward_addr"),
                "owners": row.get("owners") or [],
                "declared_pledge": (
                    None if row.get("pledge") is None else str(row.get("pledge"))
                ),
                "margin_cost": row.get("margin"),
                "fixed_cost": (
                    None if row.get("fixed_cost") is None else str(row.get("fixed_cost"))
                ),
                "metadata": {
                    "url": row.get("meta_url"),
                    "hash": _clean_meta_hash(row.get("meta_hash")),
                    "ticker": row.get("ticker"),
                    "name": None,
                    "description": None,
                    "homepage": None,
                },
            }
        )
    return result


def koios_pool_info_to_blockfrost(rows: Any) -> dict[str, Any]:
    row = first_row(rows, "pool_info")
    return {
        "pool_id": row.get("pool_id_bech32"),
        "hex": row.get("pool_id_hex"),
        "vrf_key": row.get("vrf_key_hash"),
        "blocks_minted": row.get("block_count") or 0,
        "blocks_epoch": 0,
        "live_stake": None if row.get("live_stake") is None else str(row.get("live_stake")),
        "live_size": row.get("sigma"),
        "live_saturation": row.get("live_saturation"),
        "live_delegators": row.get("live_delegators") or 0,
        "active_stake": (
            None if row.get("active_stake") is None else str(row.get("active_stake"))
        ),
        "active_size": row.get("sigma"),
        "declared_pledge": None if row.get("pledge") is None else str(row.get("pledge")),
        "live_pledge": (
            None if row.get("live_pledge") is None else str(row.get("live_pledge"))
        ),
        "margin_cost": row.get("margin"),
        "fixed_cost": None if row.get("fixed_cost") is None else str(row.get("fixed_cost")),
        "reward_account": row.get("reward_addr"),
        "owners": row.get("owners") or [],
        "registration": [],
        "retirement": (
            []
            if row.get("retiring_epoch") is None
            else [str(row.get("retiring_epoch"))]
        ),
    }


def blockfrost_pool_to_koios_info(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pool_id_bech32": payload.get("pool_id"),
            "pool_id_hex": payload.get("hex"),
            "active_epoch_no": None,
            "vrf_key_hash": payload.get("vrf_key"),
            "margin": payload.get("margin_cost"),
            "fixed_cost": payload.get("fixed_cost"),
            "pledge": payload.get("declared_pledge"),
            "deposit": None,
            "reward_addr": payload.get("reward_account"),
            "owners": payload.get("owners") or [],
            "relays": [],
            "meta_url": None,
            "meta_hash": None,
            "meta_json": None,
            "pool_status": "registered",
            "retiring_epoch": None,
            "op_cert": None,
            "op_cert_counter": None,
            "active_stake": payload.get("active_stake"),
            "sigma": payload.get("live_size"),
            "block_count": payload.get("blocks_minted"),
            "live_pledge": payload.get("live_pledge"),
            "live_stake": payload.get("live_stake"),
            "live_delegators": payload.get("live_delegators"),
            "live_saturation": payload.get("live_saturation"),
            "voting_power": None,
        }
    ]


def blockfrost_pool_ids_to_koios_list(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost pools payload")
    return [
        {
            "pool_id_bech32": pool_id,
            "pool_id_hex": None,
            "active_epoch_no": None,
            "margin": None,
            "fixed_cost": None,
            "pledge": None,
            "reward_addr": None,
            "owners": [],
            "relays": [],
            "ticker": None,
            "meta_url": None,
            "meta_hash": None,
            "pool_status": "registered",
            "active_stake": None,
            "retiring_epoch": None,
        }
        for pool_id in rows
        if isinstance(pool_id, str)
    ]


def _clean_meta_hash(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("\\x"):
        return value[2:]
    return value
