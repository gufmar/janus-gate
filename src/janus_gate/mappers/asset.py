"""Asset mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def split_blockfrost_asset_id(asset: str) -> tuple[str, str]:
    """Blockfrost asset id is policy_id (56 hex) + asset_name hex."""
    if len(asset) < 56:
        raise ValueError("Invalid Blockfrost asset id")
    return asset[:56], asset[56:]


def koios_asset_info_to_blockfrost(rows: Any, asset_id: str) -> dict[str, Any]:
    row = first_row(rows, "asset_info")
    policy = row.get("policy_id") or ""
    name = row.get("asset_name") or ""
    computed = f"{policy}{name}"
    mint = int(row.get("mint_cnt") or 0)
    burn = int(row.get("burn_cnt") or 0)
    return {
        "asset": computed or asset_id,
        "policy_id": policy,
        "asset_name": name,
        "fingerprint": row.get("fingerprint"),
        "quantity": None if row.get("total_supply") is None else str(row.get("total_supply")),
        "initial_mint_tx_hash": row.get("minting_tx_hash"),
        "mint_or_burn_count": mint + burn,
        "onchain_metadata": row.get("minting_tx_metadata"),
        "onchain_metadata_standard": None,
        "onchain_metadata_extra": None,
        "metadata": row.get("token_registry_metadata") or row.get("token_registry_metada"),
    }


def blockfrost_asset_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "policy_id": payload.get("policy_id"),
            "asset_name": payload.get("asset_name"),
            "asset_name_ascii": None,
            "fingerprint": payload.get("fingerprint"),
            "minting_tx_hash": payload.get("initial_mint_tx_hash"),
            "total_supply": payload.get("quantity"),
            "mint_cnt": payload.get("mint_or_burn_count"),
            "burn_cnt": 0,
            "creation_time": None,
            "minting_tx_metadata": payload.get("onchain_metadata"),
            "token_registry_metadata": payload.get("metadata"),
        }
    ]
