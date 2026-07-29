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


def _paginate(
    items: list[Any],
    *,
    count: int,
    page: int,
    order: str,
) -> list[Any]:
    ordered = items if order != "desc" else list(reversed(items))
    start = max(page - 1, 0) * max(count, 1)
    return ordered[start : start + max(count, 1)]


def koios_account_rewards_to_blockfrost(
    rows: Any,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        return []
    rewards = first_row(rows, "account_rewards").get("rewards") or []
    mapped = [
        {
            "epoch": item.get("earned_epoch"),
            "amount": str(item.get("amount") or "0"),
            "pool_id": item.get("pool_id"),
            "type": item.get("type") or "member",
        }
        for item in rewards
        if isinstance(item, dict)
    ]
    return _paginate(mapped, count=count, page=page, order=order)


def blockfrost_account_rewards_to_koios(
    rows: Any, stake_address: str
) -> list[dict[str, Any]]:
    rewards = []
    if isinstance(rows, list):
        for item in rows:
            rewards.append(
                {
                    "type": item.get("type") or "member",
                    "amount": item.get("amount"),
                    "pool_id": item.get("pool_id"),
                    "earned_epoch": item.get("epoch"),
                    "spendable_epoch": None,
                }
            )
    return [{"stake_address": stake_address, "rewards": rewards}]


def koios_account_history_to_blockfrost(
    rows: Any,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        return []
    history = first_row(rows, "account_history").get("history") or []
    mapped = [
        {
            "active_epoch": item.get("epoch_no"),
            "amount": str(item.get("active_stake") or "0"),
            "pool_id": item.get("pool_id"),
        }
        for item in history
        if isinstance(item, dict)
    ]
    return _paginate(mapped, count=count, page=page, order=order)


def blockfrost_account_history_to_koios(
    rows: Any, stake_address: str
) -> list[dict[str, Any]]:
    history = []
    if isinstance(rows, list):
        for item in rows:
            history.append(
                {
                    "pool_id": item.get("pool_id"),
                    "epoch_no": item.get("active_epoch"),
                    "active_stake": item.get("amount"),
                }
            )
    return [{"stake_address": stake_address, "history": history}]


def koios_account_addresses_to_blockfrost(rows: Any) -> list[str]:
    if not isinstance(rows, list) or not rows:
        return []
    addresses = first_row(rows, "account_addresses").get("addresses") or []
    return [a for a in addresses if isinstance(a, str)]


def blockfrost_account_addresses_to_koios(
    rows: Any, stake_address: str
) -> list[dict[str, Any]]:
    addresses = rows if isinstance(rows, list) else []
    return [{"stake_address": stake_address, "addresses": addresses}]


def koios_account_delegations_to_blockfrost(
    rows: Any,
    *,
    count: int = 100,
    page: int = 1,
    order: str = "asc",
) -> list[dict[str, Any]]:
    """Derive Partial BF delegations from Koios account history pool changes."""
    if not isinstance(rows, list) or not rows:
        return []
    history = first_row(rows, "account_history").get("history") or []
    mapped: list[dict[str, Any]] = []
    prev_pool: Any = object()
    for item in history:
        if not isinstance(item, dict):
            continue
        pool_id = item.get("pool_id")
        if pool_id == prev_pool:
            continue
        prev_pool = pool_id
        mapped.append(
            {
                "active_epoch": item.get("epoch_no"),
                "tx_hash": None,
                "amount": str(item.get("active_stake") or "0"),
                "pool_id": pool_id,
            }
        )
    return _paginate(mapped, count=count, page=page, order=order)


def blockfrost_account_delegations_to_koios(
    rows: Any, stake_address: str
) -> list[dict[str, Any]]:
    history = []
    if isinstance(rows, list):
        for item in rows:
            history.append(
                {
                    "pool_id": item.get("pool_id"),
                    "epoch_no": item.get("active_epoch"),
                    "active_stake": item.get("amount"),
                }
            )
    return [{"stake_address": stake_address, "history": history}]


def koios_account_txs_to_blockfrost(
    rows: Any, stake_address: str
) -> list[dict[str, Any]]:
    """Partial: Koios has no payment address / tx_index; use stake as address Gap."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios account_txs payload")
    return [
        {
            "address": stake_address,
            "tx_hash": row.get("tx_hash"),
            "tx_index": 0,
            "block_height": row.get("block_height"),
            "block_time": row.get("block_time"),
        }
        for row in rows
        if isinstance(row, dict)
    ]


def blockfrost_account_txs_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost account transactions payload")
    return [
        {
            "tx_hash": row.get("tx_hash"),
            "epoch_no": None,
            "block_height": row.get("block_height"),
            "block_time": row.get("block_time"),
        }
        for row in rows
        if isinstance(row, dict)
    ]
