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


def koios_asset_list_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios asset_list payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        policy = row.get("policy_id") or ""
        name = row.get("asset_name") or ""
        out.append(
            {
                "asset": f"{policy}{name}",
                "quantity": (
                    None
                    if row.get("quantity") is None and row.get("total_supply") is None
                    else str(row.get("quantity") or row.get("total_supply") or "0")
                ),
            }
        )
    return out


def blockfrost_asset_list_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost assets payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        asset = str(row.get("asset") or "")
        if len(asset) < 56:
            continue
        out.append(
            {
                "policy_id": asset[:56],
                "asset_name": asset[56:],
                "fingerprint": None,
                "quantity": row.get("quantity"),
            }
        )
    return out


def koios_asset_history_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios asset_history payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nested = row.get("minting_txs")
        if isinstance(nested, list):
            for mint in nested:
                if not isinstance(mint, dict):
                    continue
                qty = mint.get("quantity")
                try:
                    q = int(qty) if qty is not None else 0
                except (TypeError, ValueError):
                    q = 0
                out.append(
                    {
                        "tx_hash": mint.get("tx_hash"),
                        "amount": str(abs(q)),
                        "action": "burned" if q < 0 else "minted",
                    }
                )
        elif row.get("tx_hash"):
            qty = row.get("quantity")
            try:
                q = int(qty) if qty is not None else 0
            except (TypeError, ValueError):
                q = 0
            out.append(
                {
                    "tx_hash": row.get("tx_hash"),
                    "amount": str(abs(q)),
                    "action": "burned" if q < 0 else "minted",
                }
            )
    return out


def blockfrost_asset_history_to_koios(
    rows: Any, policy_id: str, asset_name: str
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost asset history payload")
    minting: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        action = (row.get("action") or "").lower()
        amount = row.get("amount") or "0"
        try:
            q = int(amount)
        except (TypeError, ValueError):
            q = 0
        if action.startswith("burn"):
            q = -abs(q)
        else:
            q = abs(q)
        minting.append({"tx_hash": row.get("tx_hash"), "quantity": str(q)})
    return [
        {
            "policy_id": policy_id,
            "asset_name": asset_name,
            "fingerprint": None,
            "minting_txs": minting,
        }
    ]


def koios_asset_addresses_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios asset_addresses payload")
    return [
        {
            "address": row.get("payment_address") or row.get("address"),
            "quantity": (
                None if row.get("quantity") is None else str(row.get("quantity"))
            ),
        }
        for row in rows
        if isinstance(row, dict)
        and (row.get("payment_address") or row.get("address"))
    ]


def blockfrost_asset_addresses_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost asset addresses payload")
    return [
        {
            "payment_address": row.get("address"),
            "quantity": row.get("quantity"),
        }
        for row in rows
        if isinstance(row, dict) and row.get("address")
    ]


def koios_asset_txs_to_blockfrost(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios asset_txs payload")
    out: list[str] = []
    for row in rows:
        if isinstance(row, str):
            out.append(row)
        elif isinstance(row, dict) and row.get("tx_hash"):
            out.append(str(row["tx_hash"]))
    return out


def blockfrost_asset_txs_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost asset txs payload")
    return [
        {
            "tx_hash": h,
            "epoch_no": None,
            "block_height": None,
            "block_time": None,
        }
        for h in rows
        if isinstance(h, str)
    ]
