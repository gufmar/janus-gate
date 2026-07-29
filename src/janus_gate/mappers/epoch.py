"""Epoch info and parameter mappers between Blockfrost and Koios."""

from __future__ import annotations

from typing import Any

from janus_gate.mappers.util import first_row


def koios_epoch_to_blockfrost(rows: Any) -> dict[str, Any]:
    row = first_row(rows, "epoch_info")
    return {
        "epoch": row.get("epoch_no"),
        "start_time": row.get("start_time"),
        "end_time": row.get("end_time"),
        "first_block_time": row.get("first_block_time"),
        "last_block_time": row.get("last_block_time"),
        "block_count": row.get("blk_count"),
        "tx_count": row.get("tx_count"),
        "output": None if row.get("out_sum") is None else str(row.get("out_sum")),
        "fees": None if row.get("fees") is None else str(row.get("fees")),
        "active_stake": (
            None if row.get("active_stake") is None else str(row.get("active_stake"))
        ),
    }


def blockfrost_epoch_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "epoch_no": payload.get("epoch"),
            "out_sum": payload.get("output"),
            "fees": payload.get("fees"),
            "tx_count": payload.get("tx_count"),
            "blk_count": payload.get("block_count"),
            "start_time": payload.get("start_time"),
            "end_time": payload.get("end_time"),
            "first_block_time": payload.get("first_block_time"),
            "last_block_time": payload.get("last_block_time"),
            "active_stake": payload.get("active_stake"),
            "total_rewards": None,
            "avg_blk_reward": None,
            "era": None,
        }
    ]


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def koios_epoch_params_to_blockfrost(rows: Any) -> dict[str, Any]:
    row = first_row(rows, "epoch_params")
    cost_models = row.get("cost_models")
    # Koios commonly returns list-form cost models; expose as cost_models_raw on BF.
    cost_models_raw = cost_models if isinstance(cost_models, dict) else None

    return {
        "epoch": row.get("epoch_no"),
        "min_fee_a": row.get("min_fee_a"),
        "min_fee_b": row.get("min_fee_b"),
        "max_block_size": row.get("max_block_size"),
        "max_tx_size": row.get("max_tx_size"),
        "max_block_header_size": row.get("max_bh_size"),
        "key_deposit": _str_or_none(row.get("key_deposit")),
        "pool_deposit": _str_or_none(row.get("pool_deposit")),
        "e_max": row.get("max_epoch"),
        "n_opt": row.get("optimal_pool_count"),
        "a0": row.get("influence"),
        "rho": row.get("monetary_expand_rate"),
        "tau": row.get("treasury_growth_rate"),
        "decentralisation_param": row.get("decentralisation"),
        "extra_entropy": row.get("extra_entropy"),
        "protocol_major_ver": row.get("protocol_major"),
        "protocol_minor_ver": row.get("protocol_minor"),
        "min_utxo": _str_or_none(row.get("min_utxo_value")),
        "min_pool_cost": _str_or_none(row.get("min_pool_cost")),
        "nonce": row.get("nonce"),
        "cost_models": None,
        "cost_models_raw": cost_models_raw,
        "price_mem": row.get("price_mem"),
        "price_step": row.get("price_step"),
        "max_tx_ex_mem": _str_or_none(row.get("max_tx_ex_mem")),
        "max_tx_ex_steps": _str_or_none(row.get("max_tx_ex_steps")),
        "max_block_ex_mem": _str_or_none(row.get("max_block_ex_mem")),
        "max_block_ex_steps": _str_or_none(row.get("max_block_ex_steps")),
        "max_val_size": _str_or_none(row.get("max_val_size")),
        "collateral_percent": row.get("collateral_percent"),
        "max_collateral_inputs": row.get("max_collateral_inputs"),
        "coins_per_utxo_size": _str_or_none(row.get("coins_per_utxo_size")),
        "coins_per_utxo_word": _str_or_none(row.get("coins_per_utxo_size")),
    }


def blockfrost_epoch_params_to_koios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cost_models = payload.get("cost_models_raw") or payload.get("cost_models")
    return [
        {
            "epoch_no": payload.get("epoch"),
            "min_fee_a": payload.get("min_fee_a"),
            "min_fee_b": payload.get("min_fee_b"),
            "max_block_size": payload.get("max_block_size"),
            "max_tx_size": payload.get("max_tx_size"),
            "max_bh_size": payload.get("max_block_header_size"),
            "key_deposit": payload.get("key_deposit"),
            "pool_deposit": payload.get("pool_deposit"),
            "max_epoch": payload.get("e_max"),
            "optimal_pool_count": payload.get("n_opt"),
            "influence": payload.get("a0"),
            "monetary_expand_rate": payload.get("rho"),
            "treasury_growth_rate": payload.get("tau"),
            "decentralisation": payload.get("decentralisation_param"),
            "extra_entropy": payload.get("extra_entropy"),
            "protocol_major": payload.get("protocol_major_ver"),
            "protocol_minor": payload.get("protocol_minor_ver"),
            "min_utxo_value": payload.get("min_utxo"),
            "min_pool_cost": payload.get("min_pool_cost"),
            "nonce": payload.get("nonce"),
            "cost_models": cost_models,
            "price_mem": payload.get("price_mem"),
            "price_step": payload.get("price_step"),
            "max_tx_ex_mem": payload.get("max_tx_ex_mem"),
            "max_tx_ex_steps": payload.get("max_tx_ex_steps"),
            "max_block_ex_mem": payload.get("max_block_ex_mem"),
            "max_block_ex_steps": payload.get("max_block_ex_steps"),
            "max_val_size": payload.get("max_val_size"),
            "collateral_percent": payload.get("collateral_percent"),
            "max_collateral_inputs": payload.get("max_collateral_inputs"),
            "coins_per_utxo_size": payload.get("coins_per_utxo_size"),
            "block_hash": None,
            "era": None,
        }
    ]


def koios_epoch_blocks_to_blockfrost(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Koios blocks payload")
    return [
        row.get("hash")
        for row in rows
        if isinstance(row, dict) and row.get("hash")
    ]


def blockfrost_epoch_blocks_to_koios(rows: Any, epoch_no: int) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Unexpected Blockfrost epoch blocks payload")
    return [
        {"hash": block_hash, "epoch_no": epoch_no}
        for block_hash in rows
        if isinstance(block_hash, str)
    ]
