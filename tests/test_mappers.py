"""Mapper golden / behavior tests."""

from __future__ import annotations

import pytest

from janus_gate.faces.errors import BadRequestError, NotFoundError
from janus_gate.faces.koios import _koios_page
from janus_gate.mappers import account as account_mapper
from janus_gate.mappers import block as block_mapper
from janus_gate.mappers import pool as pool_mapper
from janus_gate.mappers import script as script_mapper


def test_koios_page_aligned() -> None:
    assert _koios_page(100, 0, "asc") == (100, 1, "asc")
    assert _koios_page(100, 200, "epoch_no.desc") == (100, 3, "desc")


def test_koios_page_rejects_non_aligned_offset() -> None:
    with pytest.raises(BadRequestError):
        _koios_page(100, 50, "asc")


def test_account_rewards_flatten_and_paginate() -> None:
    rows = [
        {
            "stake_address": "stake1test",
            "rewards": [
                {
                    "earned_epoch": 1,
                    "amount": "10",
                    "pool_id": "pool1a",
                    "type": "member",
                },
                {
                    "earned_epoch": 2,
                    "amount": "20",
                    "pool_id": "pool1a",
                    "type": "member",
                },
                {
                    "earned_epoch": 3,
                    "amount": "30",
                    "pool_id": "pool1a",
                    "type": "member",
                },
            ],
        }
    ]
    page = account_mapper.koios_account_rewards_to_blockfrost(
        rows, count=2, page=1, order="asc"
    )
    assert len(page) == 2
    assert page[0]["epoch"] == 1
    assert page[1]["amount"] == "20"
    page2 = account_mapper.koios_account_rewards_to_blockfrost(
        rows, count=2, page=2, order="asc"
    )
    assert len(page2) == 1
    assert page2[0]["epoch"] == 3


def test_pool_history_mapping() -> None:
    rows = [
        {
            "epoch_no": 210,
            "block_cnt": 2,
            "active_stake": 1000,
            "active_stake_pct": 0.1,
            "delegator_cnt": 5,
            "deleg_rewards": 50,
            "pool_fees": 10,
        }
    ]
    mapped = pool_mapper.koios_pool_history_to_blockfrost(rows)
    assert mapped[0]["epoch"] == 210
    assert mapped[0]["blocks"] == 2
    assert mapped[0]["active_stake"] == "1000"
    assert mapped[0]["fees"] == "10"


def test_tip_mapping_basic() -> None:
    tip = [{"epoch_no": 500, "block_height": 1, "hash": "abc", "abs_slot": 9}]
    mapped = block_mapper.koios_tip_to_blockfrost(tip, None)
    assert mapped["epoch"] == 500
    assert mapped["height"] == 1
    assert mapped["hash"] == "abc"


def test_script_missing_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        script_mapper.koios_script_info_to_blockfrost([], "deadbeef")


def test_datum_missing_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        script_mapper.koios_datum_to_blockfrost([], "deadbeef")
