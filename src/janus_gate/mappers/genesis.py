"""Genesis response mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def koios_genesis_to_blockfrost(rows: Any) -> dict[str, Any]:
    if isinstance(rows, list):
        if not rows:
            raise ValueError("Koios genesis response was empty")
        row = rows[0]
    elif isinstance(rows, dict):
        row = rows
    else:
        raise ValueError("Unexpected Koios genesis payload")

    return {
        "active_slots_coefficient": _as_float(row.get("activeslotcoeff")),
        "update_quorum": _as_int(row.get("updatequorum")),
        "max_lovelace_supply": str(row.get("maxlovelacesupply") or ""),
        "network_magic": _as_int(row.get("networkmagic")),
        "epoch_length": _as_int(row.get("epochlength")),
        "system_start": _as_int(row.get("systemstart")),
        "slots_per_kes_period": _as_int(row.get("slotsperkesperiod")),
        "slot_length": _as_int(row.get("slotlength")),
        "max_kes_evolutions": _as_int(row.get("maxkesrevolutions")),
        "security_param": _as_int(row.get("securityparam")),
    }


def blockfrost_genesis_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "networkmagic": str(payload.get("network_magic") or ""),
            "networkid": "Mainnet",
            "activeslotcoeff": str(payload.get("active_slots_coefficient") or ""),
            "updatequorum": str(payload.get("update_quorum") or ""),
            "maxlovelacesupply": str(payload.get("max_lovelace_supply") or ""),
            "epochlength": str(payload.get("epoch_length") or ""),
            "systemstart": payload.get("system_start"),
            "slotsperkesperiod": str(payload.get("slots_per_kes_period") or ""),
            "slotlength": str(payload.get("slot_length") or ""),
            "maxkesrevolutions": str(payload.get("max_kes_evolutions") or ""),
            "securityparam": str(payload.get("security_param") or ""),
            "alonzogenesis": None,
        }
    ]
