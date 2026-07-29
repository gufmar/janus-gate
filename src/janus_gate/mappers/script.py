"""Script / datum mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def koios_datum_to_blockfrost(rows: Any, datum_hash: str) -> dict[str, Any]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("Datum not found")
    row = first_row(rows, "datum_info")
    value = row.get("value")
    if value is None and row.get("bytes") is not None:
        # Some Koios variants expose CBOR bytes only.
        value = {"bytes": row.get("bytes")}
    return {
        "json_value": value if isinstance(value, dict) else {"value": value},
    }


def blockfrost_datum_to_koios(
    payload: dict[str, Any], datum_hash: str
) -> list[dict[str, Any]]:
    return [
        {
            "datum_hash": datum_hash,
            "value": payload.get("json_value"),
            "bytes": None,
        }
    ]


def koios_script_info_to_blockfrost(rows: Any, script_hash: str) -> dict[str, Any]:
    if not isinstance(rows, list) or not rows:
        return {"script_hash": script_hash, "type": "plutusV2", "serialised_size": None}
    row = first_row(rows, "script_info")
    script_type = row.get("type") or row.get("script_type") or "plutusV2"
    return {
        "script_hash": row.get("script_hash") or script_hash,
        "type": script_type,
        "serialised_size": row.get("size") or row.get("serialised_size"),
    }


def blockfrost_script_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "script_hash": payload.get("script_hash"),
            "type": payload.get("type"),
            "size": payload.get("serialised_size"),
        }
    ]
