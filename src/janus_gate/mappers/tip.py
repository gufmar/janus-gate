"""Tip / latest-block response mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any


def _koios_height(tip: dict[str, Any]) -> int | None:
    for key in ("block_height", "block_no"):
        value = tip.get(key)
        if value is not None:
            return int(value)
    return None


def koios_tip_to_blockfrost(tip_rows: Any, block_detail: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map Koios /tip (+ optional /blocks row) to Blockfrost /blocks/latest."""
    if isinstance(tip_rows, list):
        if not tip_rows:
            raise ValueError("Koios tip response was empty")
        tip = tip_rows[0]
    elif isinstance(tip_rows, dict):
        tip = tip_rows
    else:
        raise ValueError("Unexpected Koios tip payload")

    detail = block_detail or {}
    height = _koios_height(tip)

    return {
        "time": tip.get("block_time"),
        "height": height,
        "hash": tip.get("hash"),
        "slot": tip.get("abs_slot"),
        "epoch": tip.get("epoch_no"),
        "epoch_slot": tip.get("epoch_slot"),
        "slot_leader": detail.get("pool"),
        "size": None,
        "tx_count": detail.get("tx_count", 0) if detail else 0,
        "output": None,
        "fees": None,
        "block_vrf": detail.get("vrf_key"),
        "op_cert": None,
        "op_cert_counter": (
            str(detail["op_cert_counter"])
            if detail.get("op_cert_counter") is not None
            else None
        ),
        "previous_block": None,
        "next_block": None,
        "confirmations": 0,
    }


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
