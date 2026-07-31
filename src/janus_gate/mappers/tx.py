"""Transaction mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import (
    amount_from_value_and_assets,
    first_row,
    payment_address,
)


def koios_tx_info_to_blockfrost(rows: Any) -> dict[str, Any]:
    row = first_row(rows, "tx_info")
    outputs = row.get("outputs") or []
    inputs = row.get("inputs") or []
    withdrawals = row.get("withdrawals") or []
    assets_minted = row.get("assets_minted") or []

    output_amount = amount_from_value_and_assets(row.get("total_output"), None)
    # Prefer aggregated total_output lovelace; native assets from minted are separate.

    return {
        "hash": row.get("tx_hash"),
        "block": row.get("block_hash"),
        "block_height": row.get("block_height"),
        "block_time": row.get("tx_timestamp"),
        "slot": row.get("absolute_slot"),
        "index": row.get("tx_block_index"),
        "output_amount": output_amount,
        "fees": None if row.get("fee") is None else str(row.get("fee")),
        "deposit": None if row.get("deposit") is None else str(row.get("deposit")),
        "size": row.get("tx_size"),
        "invalid_before": (
            None if row.get("invalid_before") is None else str(row.get("invalid_before"))
        ),
        "invalid_hereafter": (
            None if row.get("invalid_after") is None else str(row.get("invalid_after"))
        ),
        "utxo_count": len(inputs) + len(outputs),
        "withdrawal_count": len(withdrawals),
        "mir_cert_count": 0,
        "delegation_count": 0,
        "stake_cert_count": 0,
        "pool_update_count": 0,
        "pool_retire_count": 0,
        "asset_mint_or_burn_count": len(assets_minted),
        "redeemer_count": 0,
        "valid_contract": True,
    }


def blockfrost_tx_to_koios_info(payload: dict[str, Any]) -> list[dict[str, Any]]:
    lovelace = "0"
    for item in payload.get("output_amount") or []:
        if item.get("unit") == "lovelace":
            lovelace = str(item.get("quantity", "0"))
            break
    return [
        {
            "tx_hash": payload.get("hash"),
            "block_hash": payload.get("block"),
            "block_height": payload.get("block_height"),
            "epoch_no": None,
            "epoch_slot": None,
            "absolute_slot": payload.get("slot"),
            "tx_timestamp": payload.get("block_time"),
            "tx_block_index": payload.get("index"),
            "tx_size": payload.get("size"),
            "total_output": lovelace,
            "fee": payload.get("fees"),
            "deposit": payload.get("deposit"),
            "invalid_before": payload.get("invalid_before"),
            "invalid_after": payload.get("invalid_hereafter"),
            "treasury_donation": "0",
            "inputs": [],
            "outputs": [],
            "collateral_inputs": [],
            "collateral_output": None,
            "reference_inputs": [],
            "withdrawals": [],
            "assets_minted": [],
            "metadata": None,
            "certificates": [],
            "native_scripts": [],
            "plutus_contracts": [],
        }
    ]


def _map_koios_utxo_side(
    entries: list[dict[str, Any]],
    *,
    is_input: bool,
    parent_tx_hash: str | None = None,
) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for entry in entries:
        item: dict[str, Any] = {
            "address": payment_address(entry),
            "amount": amount_from_value_and_assets(
                entry.get("value"), entry.get("asset_list")
            ),
            "output_index": entry.get("tx_index"),
            "data_hash": entry.get("datum_hash"),
            "inline_datum": entry.get("inline_datum"),
            "reference_script_hash": entry.get("reference_script_hash")
            or _koios_ref_script_hash(entry),
            "collateral": bool(entry.get("collateral") or False),
            "reference": bool(entry.get("reference") or False),
        }
        if is_input:
            item["tx_hash"] = entry.get("tx_hash")
            # Koios /tx_utxos does not expose collateral/reference flags.
            item["collateral"] = False
            item["reference"] = False
        else:
            # Native Blockfrost omits tx_hash on outputs; include consumed_by_tx Gap.
            item["consumed_by_tx"] = entry.get("consumed_by_tx")
        mapped.append(item)
    mapped.sort(key=lambda u: (u.get("output_index") is None, u.get("output_index") or 0))
    return mapped


def _koios_ref_script_hash(entry: dict[str, Any]) -> str | None:
    ref = entry.get("reference_script")
    if isinstance(ref, dict):
        return ref.get("hash") or ref.get("script_hash")
    if isinstance(ref, str) and ref:
        return ref
    return None


def koios_tx_utxos_to_blockfrost(rows: Any) -> dict[str, Any]:
    row = first_row(rows, "tx_utxos")
    tx_hash = row.get("tx_hash")
    return {
        "hash": tx_hash,
        "inputs": _map_koios_utxo_side(
            row.get("inputs") or [], is_input=True, parent_tx_hash=tx_hash
        ),
        "outputs": _map_koios_utxo_side(
            row.get("outputs") or [], is_input=False, parent_tx_hash=tx_hash
        ),
    }


def blockfrost_tx_utxos_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    def side(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entry in entries:
            lovelace = "0"
            assets: list[dict[str, str]] = []
            for amount in entry.get("amount") or []:
                unit = amount.get("unit")
                qty = str(amount.get("quantity", "0"))
                if unit == "lovelace":
                    lovelace = qty
                elif unit:
                    assets.append(
                        {
                            "policy_id": unit[:56],
                            "asset_name": unit[56:],
                            "quantity": qty,
                        }
                    )
            out.append(
                {
                    "tx_hash": entry.get("tx_hash"),
                    "tx_index": entry.get("output_index"),
                    "value": lovelace,
                    "asset_list": assets,
                    "datum_hash": entry.get("data_hash"),
                    "inline_datum": entry.get("inline_datum"),
                    "payment_addr": {"bech32": entry.get("address"), "cred": None},
                    "stake_addr": None,
                }
            )
        return out

    return [
        {
            "tx_hash": payload.get("hash"),
            "inputs": side(payload.get("inputs") or []),
            "outputs": side(payload.get("outputs") or []),
        }
    ]


def koios_tx_metadata_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    row = first_row(rows, "tx_metadata")
    metadata = row.get("metadata")
    if metadata is None:
        return []
    if isinstance(metadata, dict):
        # Koios often returns { "label": payload, ... }
        result: list[dict[str, Any]] = []
        for label, payload in metadata.items():
            result.append({"label": str(label), "json_metadata": payload})
        return result
    if isinstance(metadata, list):
        return metadata
    return [{"label": "0", "json_metadata": metadata}]


def blockfrost_tx_metadata_to_koios(
    rows: Any,
    tx_hash: str,
) -> list[dict[str, Any]]:
    metadata: dict[str, Any] | None = None
    if isinstance(rows, list) and rows:
        metadata = {}
        for item in rows:
            label = str(item.get("label"))
            metadata[label] = item.get("json_metadata")
    return [{"tx_hash": tx_hash, "metadata": metadata}]


def koios_tx_cbor_to_blockfrost(rows: Any) -> dict[str, Any]:
    row = first_row(rows, "tx_cbor")
    return {"cbor": row.get("cbor")}


def blockfrost_tx_cbor_to_koios(payload: dict[str, Any], tx_hash: str) -> list[dict[str, Any]]:
    return [
        {
            "tx_hash": tx_hash,
            "cbor": payload.get("cbor"),
            "block_hash": None,
            "block_height": None,
            "epoch_no": None,
            "absolute_slot": None,
            "tx_timestamp": None,
            "valid_contract": True,
        }
    ]
