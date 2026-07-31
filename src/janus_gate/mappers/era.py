"""Era summary mappers between Blockfrost and Koios (Partial / Gaps)."""

from __future__ import annotations

from typing import Any


def koios_era_summaries_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    """Map Koios /era_summaries to Blockfrost /network/eras (lossy)."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios era_summaries payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        start_epoch = row.get("epoch_no")
        start_time = row.get("first_block_time")
        out.append(
            {
                "start": {
                    "time": start_time,
                    "slot": None,
                    "epoch": start_epoch,
                },
                "end": {
                    "time": None,
                    "slot": None,
                    "epoch": None,
                },
                "parameters": {
                    "epoch_length": None,
                    "slot_length": None,
                    "safe_zone": None,
                },
            }
        )
    return out


def blockfrost_eras_to_koios(rows: Any) -> list[dict[str, Any]]:
    """Map Blockfrost /network/eras to Koios /era_summaries (lossy)."""
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost network/eras payload")
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        start = row.get("start") if isinstance(row.get("start"), dict) else {}
        end = row.get("end") if isinstance(row.get("end"), dict) else {}
        params = (
            row.get("parameters") if isinstance(row.get("parameters"), dict) else {}
        )
        out.append(
            {
                "era": idx,
                "protocol_major": None,
                "protocol_minor": None,
                "ledger_protocol": None,
                "consensus_mechanism": None,
                "notes": None,
                "epoch_no": start.get("epoch"),
                "first_block_time": start.get("time"),
                "first_block_hash": None,
                "end_epoch_no": end.get("epoch"),
                "epoch_length": params.get("epoch_length"),
                "slot_length": params.get("slot_length"),
                "safe_zone": params.get("safe_zone"),
            }
        )
    return out
