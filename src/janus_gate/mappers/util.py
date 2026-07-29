"""Small shared helpers for response mappers."""

from __future__ import annotations

from typing import Any

from janus_gate.faces.errors import MappingError, NotFoundError


def first_row(rows: Any, label: str) -> dict[str, Any]:
    if isinstance(rows, list):
        if not rows:
            raise NotFoundError(f"The requested {label} has not been found.")
        row = rows[0]
        if not isinstance(row, dict):
            raise MappingError(f"Unexpected {label} row type")
        return row
    if isinstance(rows, dict):
        return rows
    raise MappingError(f"Unexpected {label} payload")


def amount_from_value_and_assets(
    value: Any,
    asset_list: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    amounts: list[dict[str, str]] = []
    if value is not None:
        amounts.append({"unit": "lovelace", "quantity": str(value)})
    for asset in asset_list or []:
        policy = asset.get("policy_id") or ""
        name = asset.get("asset_name") or ""
        quantity = asset.get("quantity")
        if quantity is None:
            continue
        amounts.append({"unit": f"{policy}{name}", "quantity": str(quantity)})
    if not amounts:
        amounts = [{"unit": "lovelace", "quantity": "0"}]
    return amounts


def payment_address(entry: dict[str, Any]) -> str | None:
    payment = entry.get("payment_addr")
    if isinstance(payment, dict):
        return payment.get("bech32") or payment.get("cred")
    if isinstance(payment, str):
        return payment
    return entry.get("address")
