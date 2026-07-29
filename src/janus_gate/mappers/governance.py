"""Governance mappers (committee, DReps, proposals)."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def koios_committee_to_blockfrost(rows: Any) -> dict[str, Any]:
    """Best-effort Partial mapping; shapes differ significantly."""
    if isinstance(rows, list):
        row = rows[0] if rows else {}
    elif isinstance(rows, dict):
        row = rows
    else:
        row = {}
    members = []
    for member in row.get("members") or []:
        if not isinstance(member, dict):
            continue
        members.append(
            {
                "status": member.get("status"),
                "cc_hot_id": member.get("cc_hot_id"),
                "cc_cold_id": member.get("cc_cold_id"),
                "expiration_epoch": member.get("expiration_epoch"),
            }
        )
    return {
        "proposal_id": row.get("proposal_id"),
        "proposal_tx_hash": row.get("proposal_tx_hash"),
        "proposal_index": row.get("proposal_index"),
        "quorum_numerator": row.get("quorum_numerator"),
        "quorum_denominator": row.get("quorum_denominator"),
        "members": members,
    }


def blockfrost_committee_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [payload]


def koios_drep_list_to_blockfrost(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios drep_list payload")
    return [
        row.get("drep_id")
        for row in rows
        if isinstance(row, dict) and row.get("drep_id")
    ]


def blockfrost_drep_ids_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost dreps payload")
    return [
        {
            "drep_id": drep_id,
            "hex": None,
            "has_script": False,
            "registered": True,
        }
        for drep_id in rows
        if isinstance(drep_id, str)
    ]


def koios_drep_info_to_blockfrost(rows: Any, drep_id: str) -> dict[str, Any]:
    if not isinstance(rows, list) or not rows:
        return {
            "drep_id": drep_id,
            "hex": None,
            "amount": "0",
            "active": False,
            "active_epoch": None,
            "has_script": False,
            "retired": True,
            "expired": False,
            "anchor": None,
        }
    row = first_row(rows, "drep_info")
    status = (row.get("drep_status") or "").lower()
    return {
        "drep_id": row.get("drep_id") or drep_id,
        "hex": row.get("hex"),
        "amount": str(row.get("amount") or "0"),
        "active": bool(row.get("active")),
        "active_epoch": None,
        "has_script": bool(row.get("has_script")),
        "retired": status in {"deregistered", "retired"},
        "expired": row.get("expires_epoch_no") is not None and not row.get("active"),
        "anchor": (
            None
            if not row.get("meta_url")
            else {"url": row.get("meta_url"), "hash": row.get("meta_hash")}
        ),
    }


def blockfrost_drep_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    anchor = payload.get("anchor") if isinstance(payload.get("anchor"), dict) else {}
    return [
        {
            "drep_id": payload.get("drep_id"),
            "hex": payload.get("hex"),
            "has_script": payload.get("has_script"),
            "drep_status": "deregistered" if payload.get("retired") else "registered",
            "deposit": None,
            "active": payload.get("active"),
            "expires_epoch_no": None,
            "amount": payload.get("amount"),
            "meta_url": anchor.get("url"),
            "meta_hash": anchor.get("hash"),
            "live_delegator_count": None,
        }
    ]


def koios_proposal_list_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios proposal_list payload")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                "tx_hash": row.get("proposal_tx_hash"),
                "cert_index": row.get("proposal_index"),
                "governance_type": row.get("proposal_type"),
                "deposit": (
                    None if row.get("deposit") is None else str(row.get("deposit"))
                ),
                "return_address": row.get("return_address"),
                "expiration": row.get("expiration"),
                "metadata_url": row.get("meta_url"),
                "metadata_hash": row.get("meta_hash"),
                "title": None,
                "abstract": None,
                "rationale": None,
                "json_metadata": row.get("meta_json"),
            }
        )
    return result


def blockfrost_proposals_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost proposals payload")
    return [
        {
            "proposal_tx_hash": row.get("tx_hash"),
            "proposal_index": row.get("cert_index"),
            "proposal_type": row.get("governance_type"),
            "deposit": row.get("deposit"),
            "return_address": row.get("return_address"),
            "expiration": row.get("expiration"),
            "meta_url": row.get("metadata_url"),
            "meta_hash": row.get("metadata_hash"),
            "meta_json": row.get("json_metadata"),
            "proposal_id": None,
            "proposed_epoch": None,
        }
        for row in rows
        if isinstance(row, dict)
    ]
