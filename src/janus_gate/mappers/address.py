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


def koios_address_to_blockfrost_extended(rows: Any, address: str) -> dict[str, Any]:
    """Map Koios address_info to Blockfrost /addresses/{address}/extended (Partial)."""
    base = koios_address_to_blockfrost(rows, address)
    extended_amount: list[dict[str, Any]] = []
    for item in base.get("amount") or []:
        if not isinstance(item, dict):
            continue
        extended_amount.append(
            {
                "unit": item.get("unit"),
                "quantity": item.get("quantity"),
                "decimals": None,
                "has_nft_onchain_metadata": False,
            }
        )
    return {
        "address": base.get("address"),
        "amount": extended_amount,
        "stake_address": base.get("stake_address"),
        "type": base.get("type"),
        "script": base.get("script"),
    }


def blockfrost_extended_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Reuse summary mapping; decimals/NFT flags are Gap when facing Koios."""
    summary = {
        "address": payload.get("address"),
        "amount": [
            {"unit": a.get("unit"), "quantity": a.get("quantity")}
            for a in (payload.get("amount") or [])
            if isinstance(a, dict)
        ],
        "stake_address": payload.get("stake_address"),
        "script": payload.get("script"),
    }
    return blockfrost_address_to_koios(summary)


def koios_address_assets_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    """Map Koios address_assets (flat rows) to BF amount-like unit/quantity list."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios address_assets payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nested = row.get("asset_list")
        if isinstance(nested, list):
            for asset in nested:
                if not isinstance(asset, dict):
                    continue
                policy = asset.get("policy_id") or ""
                name = asset.get("asset_name") or ""
                out.append(
                    {
                        "unit": f"{policy}{name}",
                        "quantity": (
                            None
                            if asset.get("quantity") is None
                            else str(asset.get("quantity"))
                        ),
                    }
                )
            continue
        if row.get("policy_id"):
            policy = row.get("policy_id") or ""
            name = row.get("asset_name") or ""
            out.append(
                {
                    "unit": f"{policy}{name}",
                    "quantity": (
                        None
                        if row.get("quantity") is None
                        else str(row.get("quantity"))
                    ),
                }
            )
    return out


def blockfrost_amounts_to_koios_address_assets(
    rows: Any, address: str
) -> list[dict[str, Any]]:
    """Map BF amount[] (or address summary) into Koios flat address_assets rows."""
    if isinstance(rows, dict):
        amounts = rows.get("amount") or []
        address = str(rows.get("address") or address)
    else:
        amounts = rows if isinstance(rows, list) else []
    out: list[dict[str, Any]] = []
    for item in amounts:
        if not isinstance(item, dict):
            continue
        unit = str(item.get("unit") or "")
        if not unit or unit == "lovelace" or len(unit) < 56:
            continue
        out.append(
            {
                "address": address,
                "policy_id": unit[:56],
                "asset_name": unit[56:],
                "fingerprint": None,
                "decimals": None,
                "quantity": item.get("quantity"),
            }
        )
    return out


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


def _utxo_amount(utxo: dict[str, Any]) -> list[dict[str, str]]:
    amounts: list[dict[str, str]] = []
    value = utxo.get("value")
    if value is not None:
        amounts.append({"unit": "lovelace", "quantity": str(value)})
    for asset in utxo.get("asset_list") or []:
        policy = asset.get("policy_id") or ""
        name = asset.get("asset_name") or ""
        quantity = asset.get("quantity")
        if quantity is None:
            continue
        amounts.append({"unit": f"{policy}{name}", "quantity": str(quantity)})
    if not amounts:
        amounts = [{"unit": "lovelace", "quantity": "0"}]
    return amounts


def _ref_script_hash(reference_script: Any) -> str | None:
    if reference_script is None:
        return None
    if isinstance(reference_script, dict):
        return reference_script.get("hash") or reference_script.get("script_hash")
    if isinstance(reference_script, str):
        return reference_script
    return None


def koios_address_utxos_to_blockfrost(rows: Any, address: str) -> list[dict[str, Any]]:
    """Map Koios /address_utxos to Blockfrost GET /addresses/{address}/utxos."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios address_utxos payload")
    mapped: list[dict[str, Any]] = []
    for utxo in rows:
        tx_index = utxo.get("tx_index")
        if tx_index is None:
            tx_index = utxo.get("tx_out_index")
        mapped.append(
            {
                "address": utxo.get("address") or address,
                "tx_hash": utxo.get("tx_hash"),
                "tx_index": tx_index,
                "output_index": tx_index,
                "amount": _utxo_amount(utxo),
                # Koios address_utxos typically lacks block hash (height/time only).
                "block": None,
                "data_hash": utxo.get("datum_hash"),
                "inline_datum": utxo.get("inline_datum"),
                "reference_script_hash": _ref_script_hash(utxo.get("reference_script")),
            }
        )
    return mapped


def blockfrost_address_utxos_to_koios(rows: Any) -> list[dict[str, Any]]:
    """Map Blockfrost address UTxOs to Koios /address_utxos array shape."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost address utxos payload")
    mapped: list[dict[str, Any]] = []
    for utxo in rows:
        lovelace = "0"
        asset_list: list[dict[str, str]] = []
        for item in utxo.get("amount") or []:
            unit = item.get("unit")
            quantity = str(item.get("quantity", "0"))
            if unit == "lovelace":
                lovelace = quantity
            elif unit:
                asset_list.append(
                    {
                        "policy_id": unit[:56],
                        "asset_name": unit[56:],
                        "quantity": quantity,
                    }
                )
        mapped.append(
            {
                "address": utxo.get("address"),
                "tx_hash": utxo.get("tx_hash"),
                "tx_index": utxo.get("output_index", utxo.get("tx_index")),
                "value": lovelace,
                "asset_list": asset_list,
                "datum_hash": utxo.get("data_hash"),
                "inline_datum": utxo.get("inline_datum"),
                "reference_script": (
                    {"hash": utxo["reference_script_hash"]}
                    if utxo.get("reference_script_hash")
                    else None
                ),
                "block_height": None,
                "block_time": None,
            }
        )
    return mapped


def koios_address_txs_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    """Map Koios /address_txs to Blockfrost GET /addresses/{address}/transactions."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios address_txs payload")
    return [
        {
            "tx_hash": row.get("tx_hash"),
            # Koios address_txs has no tx_index in the address list response.
            "tx_index": 0,
            "block_height": row.get("block_height"),
            "block_time": row.get("block_time"),
        }
        for row in rows
    ]


def blockfrost_address_txs_to_koios(rows: Any) -> list[dict[str, Any]]:
    """Map Blockfrost address transactions to Koios /address_txs array shape."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost address transactions payload")
    return [
        {
            "tx_hash": row.get("tx_hash"),
            "epoch_no": None,
            "block_height": row.get("block_height"),
            "block_time": row.get("block_time"),
        }
        for row in rows
    ]
