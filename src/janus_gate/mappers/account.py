"""Account (stake address) mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def koios_account_to_blockfrost(rows: Any, stake_address: str) -> dict[str, Any]:
    if not isinstance(rows, list) or not rows:
        return {
            "stake_address": stake_address,
            "active": False,
            "active_epoch": None,
            "controlled_amount": "0",
            "rewards_sum": "0",
            "withdrawals_sum": "0",
            "reserves_sum": "0",
            "treasury_sum": "0",
            "withdrawable_amount": "0",
            "pool_id": None,
        }
    row = first_row(rows, "account_info")
    status = (row.get("status") or "").lower()
    return {
        "stake_address": row.get("stake_address") or stake_address,
        "active": status in {"registered", "active"},
        "active_epoch": None,
        "controlled_amount": str(row.get("total_balance") or "0"),
        "rewards_sum": str(row.get("rewards") or "0"),
        "withdrawals_sum": str(row.get("withdrawals") or "0"),
        "reserves_sum": str(row.get("reserves") or "0"),
        "treasury_sum": str(row.get("treasury") or "0"),
        "withdrawable_amount": str(row.get("rewards_available") or "0"),
        "pool_id": row.get("delegated_pool"),
    }


def blockfrost_account_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "stake_address": payload.get("stake_address"),
            "status": "registered" if payload.get("active") else "not registered",
            "delegated_pool": payload.get("pool_id"),
            "delegated_drep": None,
            "total_balance": payload.get("controlled_amount"),
            "utxo": None,
            "rewards": payload.get("rewards_sum"),
            "withdrawals": payload.get("withdrawals_sum"),
            "rewards_available": payload.get("withdrawable_amount"),
            "deposit": None,
            "reserves": payload.get("reserves_sum"),
            "treasury": payload.get("treasury_sum"),
            "proposal_refund": "0",
        }
    ]
