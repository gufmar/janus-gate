"""Map cardano-db-sync query rows to Blockfrost face shapes."""

from __future__ import annotations

from typing import Any

from janus_gate.faces.errors import NotFoundError

# Genesis fields that db-sync meta does not fully carry; keyed by meta.network_name.
_NETWORK_GENESIS: dict[str, dict[str, Any]] = {
    "mainnet": {
        "active_slots_coefficient": 0.05,
        "update_quorum": 5,
        "max_lovelace_supply": "45000000000000000",
        "network_magic": 764824073,
        "epoch_length": 432000,
        "slots_per_kes_period": 129600,
        "slot_length": 1,
        "max_kes_evolutions": 62,
        "security_param": 2160,
    },
    "preprod": {
        "active_slots_coefficient": 0.05,
        "update_quorum": 5,
        "max_lovelace_supply": "45000000000000000",
        "network_magic": 1,
        "epoch_length": 432000,
        "slots_per_kes_period": 129600,
        "slot_length": 1,
        "max_kes_evolutions": 62,
        "security_param": 2160,
    },
    "preview": {
        "active_slots_coefficient": 0.05,
        "update_quorum": 5,
        "max_lovelace_supply": "45000000000000000",
        "network_magic": 2,
        "epoch_length": 86400,
        "slots_per_kes_period": 129600,
        "slot_length": 1,
        "max_kes_evolutions": 62,
        "security_param": 432,
    },
}


def _s(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _i(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _infer_address_type(address: str) -> str:
    if address.startswith(("Ae2", "DdzFF")):
        return "byron"
    return "shelley"


def dbsync_block_to_blockfrost(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        raise NotFoundError("The requested component has not been found.")
    return {
        "time": _i(row.get("block_time")),
        "height": _i(row.get("block_no")),
        "hash": row.get("hash"),
        "slot": _i(row.get("slot_no")),
        "epoch": _i(row.get("epoch_no")),
        "epoch_slot": _i(row.get("epoch_slot_no")),
        "slot_leader": row.get("slot_leader"),
        "size": _i(row.get("size")),
        "tx_count": _i(row.get("tx_count")) or 0,
        "output": _s(row.get("out_sum")),
        "fees": _s(row.get("fees")),
        "block_vrf": row.get("vrf_key"),
        "op_cert": row.get("op_cert"),
        "op_cert_counter": _s(row.get("op_cert_counter")),
        "previous_block": row.get("previous_hash"),
        "next_block": row.get("next_hash"),
        "confirmations": _i(row.get("confirmations")) or 0,
    }


def dbsync_genesis_to_blockfrost(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        raise NotFoundError("The requested component has not been found.")
    network = (row.get("network_name") or "").strip().lower()
    defaults = dict(_NETWORK_GENESIS.get(network, _NETWORK_GENESIS["mainnet"]))
    start = row.get("system_start")
    if start is not None:
        defaults["system_start"] = int(start)
    return defaults


def dbsync_epoch_to_blockfrost(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        raise NotFoundError("The requested component has not been found.")
    return {
        "epoch": _i(row.get("epoch_no")),
        "start_time": _i(row.get("start_time")),
        "end_time": _i(row.get("end_time")),
        "first_block_time": _i(row.get("first_block_time")),
        "last_block_time": _i(row.get("last_block_time")),
        "block_count": _i(row.get("blk_count")),
        "tx_count": _i(row.get("tx_count")),
        "output": _s(row.get("out_sum")),
        "fees": _s(row.get("fees")),
        "active_stake": _s(row.get("active_stake")),
    }


def dbsync_epoch_params_to_blockfrost(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        raise NotFoundError("The requested component has not been found.")
    coins = _s(row.get("coins_per_utxo_size"))
    return {
        "epoch": _i(row.get("epoch_no")),
        "min_fee_a": _i(row.get("min_fee_a")),
        "min_fee_b": _i(row.get("min_fee_b")),
        "max_block_size": _i(row.get("max_block_size")),
        "max_tx_size": _i(row.get("max_tx_size")),
        "max_block_header_size": _i(row.get("max_bh_size")),
        "key_deposit": _s(row.get("key_deposit")),
        "pool_deposit": _s(row.get("pool_deposit")),
        "e_max": _i(row.get("max_epoch")),
        "n_opt": _i(row.get("optimal_pool_count")),
        "a0": row.get("influence"),
        "rho": row.get("monetary_expand_rate"),
        "tau": row.get("treasury_growth_rate"),
        "decentralisation_param": row.get("decentralisation"),
        "extra_entropy": row.get("extra_entropy"),
        "protocol_major_ver": _i(row.get("protocol_major")),
        "protocol_minor_ver": _i(row.get("protocol_minor")),
        "min_utxo": _s(row.get("min_utxo_value")),
        "min_pool_cost": _s(row.get("min_pool_cost")),
        "nonce": row.get("nonce"),
        "cost_models": None,
        "cost_models_raw": row.get("cost_models"),
        "price_mem": row.get("price_mem"),
        "price_step": row.get("price_step"),
        "max_tx_ex_mem": _s(row.get("max_tx_ex_mem")),
        "max_tx_ex_steps": _s(row.get("max_tx_ex_steps")),
        "max_block_ex_mem": _s(row.get("max_block_ex_mem")),
        "max_block_ex_steps": _s(row.get("max_block_ex_steps")),
        "max_val_size": _s(row.get("max_val_size")),
        "collateral_percent": _i(row.get("collateral_percent")),
        "max_collateral_inputs": _i(row.get("max_collateral_inputs")),
        "coins_per_utxo_size": coins,
        "coins_per_utxo_word": coins,
    }


def dbsync_address_to_blockfrost(row: dict[str, Any] | None, address: str) -> dict[str, Any]:
    if not row:
        return {
            "address": address,
            "amount": [{"unit": "lovelace", "quantity": "0"}],
            "stake_address": None,
            "type": _infer_address_type(address),
            "script": False,
        }
    amounts = list(row.get("amount") or [])
    if not amounts:
        amounts = [{"unit": "lovelace", "quantity": _s(row.get("lovelace")) or "0"}]
    return {
        "address": row.get("address") or address,
        "amount": amounts,
        "stake_address": row.get("stake_address"),
        "type": _infer_address_type(row.get("address") or address),
        "script": bool(row.get("script")),
    }


def dbsync_address_utxos_to_blockfrost(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows or []:
        amounts = list(row.get("amount") or [])
        if not amounts:
            amounts = [{"unit": "lovelace", "quantity": _s(row.get("value")) or "0"}]
        out.append(
            {
                "address": row.get("address"),
                "tx_hash": row.get("tx_hash"),
                "tx_index": _i(row.get("tx_index")),
                "output_index": _i(row.get("tx_index")),
                "amount": amounts,
                "block": row.get("block_hash"),
                "data_hash": row.get("data_hash"),
                "inline_datum": None,
                "reference_script_hash": None,
            }
        )
    return out


def dbsync_account_to_blockfrost(
    row: dict[str, Any] | None, stake_address: str
) -> dict[str, Any]:
    if not row:
        return {
            "stake_address": stake_address,
            "active": False,
            "active_epoch": None,
            "controlled_amount": "0",
            "rewards_sum": "0",
            "withdrawals_sum": "0",
            "reserves_sum": "0",
            "treasury_sum": "0",
            "withdrawable_amount": "0",
            "pool_id": None,
        }
    return {
        "stake_address": row.get("stake_address") or stake_address,
        "active": bool(row.get("active")),
        "active_epoch": _i(row.get("active_epoch")),
        "controlled_amount": _s(row.get("controlled_amount")) or "0",
        "rewards_sum": _s(row.get("rewards_sum")) or "0",
        "withdrawals_sum": _s(row.get("withdrawals_sum")) or "0",
        "reserves_sum": _s(row.get("reserves_sum")) or "0",
        "treasury_sum": _s(row.get("treasury_sum")) or "0",
        "withdrawable_amount": _s(row.get("withdrawable_amount")) or "0",
        "pool_id": row.get("pool_id"),
    }


def dbsync_tx_to_blockfrost(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        raise NotFoundError("The requested component has not been found.")
    return {
        "hash": row.get("tx_hash"),
        "block": row.get("block_hash"),
        "block_height": _i(row.get("block_height")),
        "block_time": _i(row.get("block_time")),
        "slot": _i(row.get("slot_no")),
        "index": _i(row.get("block_index")),
        "output_amount": [
            {"unit": "lovelace", "quantity": _s(row.get("out_sum")) or "0"}
        ],
        "fees": _s(row.get("fee")),
        "deposit": _s(row.get("deposit")),
        "size": _i(row.get("size")),
        "invalid_before": _s(row.get("invalid_before")),
        "invalid_hereafter": _s(row.get("invalid_hereafter")),
        "utxo_count": _i(row.get("utxo_count")) or 0,
        "withdrawal_count": _i(row.get("withdrawal_count")) or 0,
        "mir_cert_count": 0,
        "delegation_count": 0,
        "stake_cert_count": 0,
        "pool_update_count": 0,
        "pool_retire_count": 0,
        "asset_mint_or_burn_count": 0,
        "redeemer_count": 0,
        "valid_contract": bool(row.get("valid_contract", True)),
    }
