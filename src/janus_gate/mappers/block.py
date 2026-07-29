"""Block response mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def koios_block_to_blockfrost(rows: Any) -> dict[str, Any]:
    """Map Koios /block_info (or enriched /blocks row) to Blockfrost block_content."""
    row = first_row(rows, "block")
    height = row.get("block_height", row.get("block_no"))
    op_cert_counter = row.get("op_cert_counter")
    return {
        "time": row.get("block_time"),
        "height": height,
        "hash": row.get("hash"),
        "slot": row.get("abs_slot"),
        "epoch": row.get("epoch_no"),
        "epoch_slot": row.get("epoch_slot"),
        "slot_leader": row.get("pool"),
        "size": row.get("block_size"),
        "tx_count": row.get("tx_count") or 0,
        "output": None if row.get("total_output") is None else str(row.get("total_output")),
        "fees": None if row.get("total_fees") is None else str(row.get("total_fees")),
        "block_vrf": row.get("vrf_key"),
        "op_cert": row.get("op_cert"),
        "op_cert_counter": None if op_cert_counter is None else str(op_cert_counter),
        "previous_block": row.get("parent_hash"),
        "next_block": row.get("child_hash"),
        "confirmations": row.get("num_confirmations") or 0,
    }


def blockfrost_block_to_koios_info(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Map Blockfrost block_content to Koios /block_info array shape."""
    return [
        {
            "hash": payload.get("hash"),
            "epoch_no": payload.get("epoch"),
            "abs_slot": payload.get("slot"),
            "epoch_slot": payload.get("epoch_slot"),
            "block_height": payload.get("height"),
            "block_size": payload.get("size"),
            "block_time": payload.get("time"),
            "tx_count": payload.get("tx_count"),
            "vrf_key": payload.get("block_vrf"),
            "op_cert": payload.get("op_cert"),
            "op_cert_counter": (
                int(payload["op_cert_counter"])
                if payload.get("op_cert_counter") not in (None, "")
                else None
            ),
            "pool": payload.get("slot_leader"),
            "total_output": payload.get("output"),
            "total_fees": payload.get("fees"),
            "num_confirmations": payload.get("confirmations"),
            "parent_hash": payload.get("previous_block"),
            "child_hash": payload.get("next_block"),
            "era": None,
            "proto_major": None,
            "proto_minor": None,
        }
    ]


def koios_tip_to_blockfrost(tip_rows: Any, block_detail: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map Koios /tip (+ optional detail) to Blockfrost /blocks/latest."""
    tip = first_row(tip_rows, "tip")
    if block_detail:
        merged = {**tip, **block_detail}
        return koios_block_to_blockfrost(merged)
    return koios_block_to_blockfrost(tip)


def blockfrost_latest_to_koios_tip(block: dict[str, Any]) -> list[dict[str, Any]]:
    """Map Blockfrost /blocks/latest to Koios /tip array shape."""
    height = block.get("height")
    return [
        {
            "hash": block.get("hash"),
            "epoch_no": block.get("epoch"),
            "abs_slot": block.get("slot"),
            "epoch_slot": block.get("epoch_slot"),
            "block_height": height,
            "block_no": height,
            "block_time": block.get("time"),
        }
    ]


def koios_block_txs_to_blockfrost(rows: Any) -> list[str]:
    """Map Koios /block_txs rows to Blockfrost list of tx hashes."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios block_txs payload")
    # Preserve order as returned (already paginated by provider when needed).
    return [
        row.get("tx_hash")
        for row in rows
        if isinstance(row, dict) and row.get("tx_hash")
    ]


def blockfrost_block_txs_to_koios(
    rows: Any, block_hash: str
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost block txs payload")
    return [
        {
            "block_hash": block_hash,
            "tx_hash": tx_hash,
            "epoch_no": None,
            "block_height": None,
            "block_time": None,
        }
        for tx_hash in rows
        if isinstance(tx_hash, str)
    ]
