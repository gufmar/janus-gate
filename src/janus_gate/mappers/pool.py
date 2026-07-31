"""Pool mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def koios_pool_list_to_blockfrost_ids(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_list payload")
    return [
        row.get("pool_id_bech32")
        for row in rows
        if isinstance(row, dict) and row.get("pool_id_bech32")
    ]


def koios_pool_list_to_blockfrost_extended(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_list payload")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                "pool_id": row.get("pool_id_bech32"),
                "hex": row.get("pool_id_hex"),
                "active_stake": (
                    None if row.get("active_stake") is None else str(row.get("active_stake"))
                ),
                "live_stake": None,
                "live_saturation": None,
                "blocks_minted": None,
                "live_delegators": None,
                "reward_account": row.get("reward_addr"),
                "owners": row.get("owners") or [],
                "declared_pledge": (
                    None if row.get("pledge") is None else str(row.get("pledge"))
                ),
                "margin_cost": row.get("margin"),
                "fixed_cost": (
                    None if row.get("fixed_cost") is None else str(row.get("fixed_cost"))
                ),
                "metadata": {
                    "url": row.get("meta_url"),
                    "hash": _clean_meta_hash(row.get("meta_hash")),
                    "ticker": row.get("ticker"),
                    "name": None,
                    "description": None,
                    "homepage": None,
                },
            }
        )
    return result


def koios_pool_info_to_blockfrost(rows: Any) -> dict[str, Any]:
    row = first_row(rows, "pool_info")
    return {
        "pool_id": row.get("pool_id_bech32"),
        "hex": row.get("pool_id_hex"),
        "vrf_key": row.get("vrf_key_hash"),
        "blocks_minted": row.get("block_count") or 0,
        "blocks_epoch": 0,
        "live_stake": None if row.get("live_stake") is None else str(row.get("live_stake")),
        "live_size": row.get("sigma"),
        "live_saturation": row.get("live_saturation"),
        "live_delegators": row.get("live_delegators") or 0,
        "active_stake": (
            None if row.get("active_stake") is None else str(row.get("active_stake"))
        ),
        "active_size": row.get("sigma"),
        "declared_pledge": None if row.get("pledge") is None else str(row.get("pledge")),
        "live_pledge": (
            None if row.get("live_pledge") is None else str(row.get("live_pledge"))
        ),
        "margin_cost": row.get("margin"),
        "fixed_cost": None if row.get("fixed_cost") is None else str(row.get("fixed_cost")),
        "reward_account": row.get("reward_addr"),
        "owners": row.get("owners") or [],
        "registration": [],
        "retirement": (
            []
            if row.get("retiring_epoch") is None
            else [str(row.get("retiring_epoch"))]
        ),
    }


def blockfrost_pool_to_koios_info(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pool_id_bech32": payload.get("pool_id"),
            "pool_id_hex": payload.get("hex"),
            "active_epoch_no": None,
            "vrf_key_hash": payload.get("vrf_key"),
            "margin": payload.get("margin_cost"),
            "fixed_cost": payload.get("fixed_cost"),
            "pledge": payload.get("declared_pledge"),
            "deposit": None,
            "reward_addr": payload.get("reward_account"),
            "owners": payload.get("owners") or [],
            "relays": _bf_relays_inline(payload.get("relays")),
            "meta_url": None,
            "meta_hash": None,
            "meta_json": None,
            "pool_status": "registered",
            "retiring_epoch": None,
            "op_cert": None,
            "op_cert_counter": None,
            "active_stake": payload.get("active_stake"),
            "sigma": payload.get("live_size"),
            "block_count": payload.get("blocks_minted"),
            "live_pledge": payload.get("live_pledge"),
            "live_stake": payload.get("live_stake"),
            "live_delegators": payload.get("live_delegators"),
            "live_saturation": payload.get("live_saturation"),
            "voting_power": None,
        }
    ]


def blockfrost_pool_ids_to_koios_list(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost pools payload")
    return [
        {
            "pool_id_bech32": pool_id,
            "pool_id_hex": None,
            "active_epoch_no": None,
            "margin": None,
            "fixed_cost": None,
            "pledge": None,
            "reward_addr": None,
            "owners": [],
            "relays": [],
            "ticker": None,
            "meta_url": None,
            "meta_hash": None,
            "pool_status": "registered",
            "active_stake": None,
            "retiring_epoch": None,
        }
        for pool_id in rows
        if isinstance(pool_id, str)
    ]


def _clean_meta_hash(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("\\x"):
        return value[2:]
    return value


def _pct_to_fraction(value: Any) -> Any:
    """Koios active_stake_pct (percent units) -> Blockfrost active_size (0..1)."""
    if value is None or value == "":
        return None
    return float(value) / 100.0


def _fraction_to_pct(value: Any) -> Any:
    """Blockfrost active_size (0..1) -> Koios active_stake_pct (percent units)."""
    if value is None or value == "":
        return None
    return float(value) * 100.0


def _bf_relays_inline(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [
        {
            "dns": relay.get("dns"),
            "srv": relay.get("dns_srv"),
            "ipv4": relay.get("ipv4"),
            "ipv6": relay.get("ipv6"),
            "port": relay.get("port"),
        }
        for relay in rows
        if isinstance(relay, dict)
    ]


def koios_pool_history_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_history payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Blockfrost ``rewards`` is total operator+member rewards (deleg + fees).
        rewards = _sum_lovelace(row.get("deleg_rewards"), row.get("pool_fees"))
        if rewards is None:
            rewards = (
                None
                if row.get("deleg_rewards") is None
                else str(row.get("deleg_rewards"))
            )
        out.append(
            {
                "epoch": row.get("epoch_no"),
                "blocks": row.get("block_cnt") or 0,
                "active_stake": (
                    None
                    if row.get("active_stake") is None
                    else str(row.get("active_stake"))
                ),
                "active_size": _pct_to_fraction(row.get("active_stake_pct")),
                "delegators_count": row.get("delegator_cnt") or 0,
                "rewards": rewards,
                "fees": (
                    None if row.get("pool_fees") is None else str(row.get("pool_fees"))
                ),
            }
        )
    return out


def blockfrost_pool_history_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost pool history payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        fees = row.get("fees")
        # Undo BF total: deleg_rewards ~= rewards - fees.
        deleg = _sub_lovelace(row.get("rewards"), fees)
        if deleg is None and row.get("rewards") is not None:
            deleg = str(row.get("rewards"))
        out.append(
            {
                "epoch_no": row.get("epoch"),
                "active_stake": row.get("active_stake"),
                "active_stake_pct": _fraction_to_pct(row.get("active_size")),
                "saturation_pct": None,
                "block_cnt": row.get("blocks"),
                "delegator_cnt": row.get("delegators_count"),
                "margin": None,
                "fixed_cost": None,
                "pool_fees": None if fees is None else str(fees),
                "deleg_rewards": deleg,
                "member_rewards": None,
                "epoch_ros": None,
            }
        )
    return out


def _sum_lovelace(left: Any, right: Any) -> str | None:
    if left is None or right is None:
        return None
    try:
        return str(int(left) + int(right))
    except (TypeError, ValueError):
        return None


def _sub_lovelace(left: Any, right: Any) -> str | None:
    if left is None or right is None:
        return None
    try:
        return str(int(left) - int(right))
    except (TypeError, ValueError):
        return None


def koios_pool_metadata_to_blockfrost(rows: Any, pool_id: str) -> dict[str, Any] | None:
    if not isinstance(rows, list) or not rows:
        return None
    row = first_row(rows, "pool_metadata")
    meta = row.get("meta_json") if isinstance(row.get("meta_json"), dict) else {}
    return {
        "pool_id": row.get("pool_id_bech32") or pool_id,
        "hex": None,
        "url": row.get("meta_url"),
        "hash": _clean_meta_hash(row.get("meta_hash")),
        "ticker": meta.get("ticker"),
        "name": meta.get("name"),
        "description": meta.get("description"),
        "homepage": meta.get("homepage"),
    }


def blockfrost_pool_metadata_to_koios(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    return [
        {
            "pool_id_bech32": payload.get("pool_id"),
            "meta_url": payload.get("url"),
            "meta_hash": payload.get("hash"),
            "meta_json": {
                "name": payload.get("name"),
                "ticker": payload.get("ticker"),
                "homepage": payload.get("homepage"),
                "description": payload.get("description"),
            },
        }
    ]


def koios_pool_delegators_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_delegators payload")
    return [
        {
            "address": row.get("stake_address"),
            "live_stake": None if row.get("amount") is None else str(row.get("amount")),
        }
        for row in rows
        if isinstance(row, dict)
    ]


def blockfrost_pool_delegators_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost pool delegators payload")
    return [
        {
            "stake_address": row.get("address"),
            "amount": row.get("live_stake"),
            "active_epoch_no": None,
            "latest_delegation_tx_hash": None,
        }
        for row in rows
        if isinstance(row, dict)
    ]


def koios_pool_relays_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        return []
    row = first_row(rows, "pool_relays")
    relays = row.get("relays") or []
    mapped: list[dict[str, Any]] = []
    for relay in relays:
        if not isinstance(relay, dict):
            continue
        mapped.append(
            {
                "ipv4": relay.get("ipv4"),
                "ipv6": relay.get("ipv6"),
                "dns": relay.get("dns"),
                "dns_srv": relay.get("srv"),
                "port": relay.get("port"),
            }
        )
    return mapped


def blockfrost_pool_relays_to_koios(
    rows: Any, pool_id: str
) -> list[dict[str, Any]]:
    relays = []
    if isinstance(rows, list):
        for relay in rows:
            relays.append(
                {
                    "dns": relay.get("dns"),
                    "srv": relay.get("dns_srv"),
                    "ipv4": relay.get("ipv4"),
                    "ipv6": relay.get("ipv6"),
                    "port": relay.get("port"),
                }
            )
    return [{"pool_id_bech32": pool_id, "relays": relays}]


def koios_pool_blocks_to_blockfrost(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_blocks payload")
    return [
        str(row.get("block_hash"))
        for row in rows
        if isinstance(row, dict) and row.get("block_hash")
    ]


def blockfrost_pool_blocks_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost pool blocks payload")
    return [
        {
            "block_hash": h,
            "epoch_no": None,
            "epoch_slot": None,
            "abs_slot": None,
            "block_height": None,
            "block_time": None,
        }
        for h in rows
        if isinstance(h, str)
    ]


def koios_pool_updates_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_updates payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        update_type = (row.get("update_type") or "").lower()
        if update_type.startswith("dereg"):
            action = "deregistered"
        else:
            action = "registered"
        out.append(
            {
                "tx_hash": row.get("tx_hash") or row.get("meta_tx_hash"),
                "cert_index": row.get("cert_index") if row.get("cert_index") is not None else 0,
                "action": action,
            }
        )
    return out


def blockfrost_pool_updates_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost pool updates payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        action = (row.get("action") or "").lower()
        update_type = (
            "deregistration" if action.startswith("dereg") else "registration"
        )
        out.append(
            {
                "tx_hash": row.get("tx_hash"),
                "block_time": None,
                "pool_id_bech32": None,
                "pool_id_hex": None,
                "active_epoch_no": None,
                "vrf_key_hash": None,
                "margin": None,
                "fixed_cost": None,
                "pledge": None,
                "reward_addr": None,
                "owners": None,
                "relays": None,
                "meta_url": None,
                "meta_hash": None,
                "meta_json": None,
                "pool_status": None,
                "retiring_epoch": None,
                "update_type": update_type,
            }
        )
    return out


def koios_pool_votes_to_blockfrost(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios pool_votes payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        vote_raw = str(row.get("vote") or "").lower()
        if vote_raw in {"yes", "y"}:
            vote = "yes"
        elif vote_raw in {"no", "n"}:
            vote = "no"
        else:
            vote = "abstain"
        out.append(
            {
                "tx_hash": row.get("proposal_tx_hash") or row.get("tx_hash"),
                "cert_index": row.get("proposal_index")
                if row.get("proposal_index") is not None
                else 0,
                "vote": vote,
            }
        )
    return out


def blockfrost_pool_votes_to_koios(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost pool votes payload")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        vote = str(row.get("vote") or "abstain")
        out.append(
            {
                "proposal_tx_hash": row.get("tx_hash"),
                "proposal_index": row.get("cert_index"),
                "vote": vote[:1].upper() + vote[1:].lower() if vote else "Abstain",
                "block_time": None,
                "meta_url": None,
                "meta_hash": None,
            }
        )
    return out
