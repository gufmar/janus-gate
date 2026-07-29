"""Transaction metadata label mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any


def koios_metalabels_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    """Map Koios /tx_metalabels to Blockfrost /metadata/txs/labels."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios tx_metalabels payload")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = row.get("key")
        if label is None:
            continue
        result.append(
            {
                "label": str(label),
                "cip10": None,
                "count": None,
            }
        )
    return result


def blockfrost_metalabels_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost metadata labels payload")
    return [
        {"key": row.get("label")}
        for row in rows
        if isinstance(row, dict) and row.get("label") is not None
    ]


def koios_tx_by_metalabel_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    """Partial: Koios list has no json_metadata; leave null (fetch via /txs/{hash}/metadata)."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios tx_by_metalabel payload")
    return [
        {
            "tx_hash": row.get("tx_hash"),
            "json_metadata": None,
        }
        for row in rows
        if isinstance(row, dict) and row.get("tx_hash")
    ]


def blockfrost_metadata_label_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost metadata-by-label payload")
    return [
        {
            "tx_hash": row.get("tx_hash"),
            "block_hash": None,
            "block_height": None,
            "epoch_no": None,
            "absolute_slot": None,
            "tx_timestamp": None,
        }
        for row in rows
        if isinstance(row, dict) and row.get("tx_hash")
    ]
