"""Address info mappers between Blockfrost and Koios."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _infer_address_type(address: str) -> str:
    if address.startswith("addr") or address.startswith("stake"):
        return "shelley"
    if address.startswith("Ae2") or address.startswith("DdzFF"):
        return "byron"
    return "shelley"


def _aggregate_assets_from_utxo_set(utxo_set: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    totals: dict[str, int] = defaultdict(int)
    for utxo in utxo_set or []:
        value = utxo.get("value")
        if value is not None:
            totals["lovelace"] += int(value)
        for asset in utxo.get("asset_list") or []:
            policy = asset.get("policy_id") or ""
            name = asset.get("asset_name") or ""
            unit = f"{policy}{name}"
            quantity = asset.get("quantity")
            if quantity is not None:
                totals[unit] += int(quantity)
    return [{"unit": unit, "quantity": str(qty)} for unit, qty in totals.items()]


def koios_address_to_blockfrost(rows: Any, address: str) -> dict[str, Any]:
    """Map Koios /address_info to Blockfrost GET /addresses/{address}."""
    if not isinstance(rows, list) or not rows:
        # Empty Koios result: unused address behaves like zero balance.
        return {
            "address": address,
            "amount": [{"unit": "lovelace", "quantity": "0"}],
            "stake_address": None,
            "type": _infer_address_type(address),
            "script": False,
        }

    row = rows[0]
    balance = row.get("balance")
    amounts = [{"unit": "lovelace", "quantity": str(balance if balance is not None else "0")}]

    # Prefer aggregated assets from utxo_set when present (native tokens).
    assets = _aggregate_assets_from_utxo_set(row.get("utxo_set"))
    if assets:
        # Replace lovelace-only stub with full aggregation when utxos exist.
        amounts = assets
    elif balance is not None:
        amounts = [{"unit": "lovelace", "quantity": str(balance)}]

    return {
        "address": row.get("address") or address,
        "amount": amounts,
        "stake_address": row.get("stake_address"),
        "type": _infer_address_type(row.get("address") or address),
        "script": bool(row.get("script_address", False)),
    }


def blockfrost_address_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Map Blockfrost address content to Koios /address_info array shape."""
    lovelace = "0"
    for item in payload.get("amount") or []:
        if item.get("unit") == "lovelace":
            lovelace = str(item.get("quantity", "0"))
            break

    return [
        {
            "address": payload.get("address"),
            "balance": lovelace,
            "stake_address": payload.get("stake_address"),
            "script_address": bool(payload.get("script", False)),
            # Blockfrost address summary does not include UTxO set; leave empty.
            "utxo_set": [],
        }
    ]
