"""Mapper golden / behavior tests."""

from __future__ import annotations

import pytest

from janus_gate.faces.errors import BadRequestError, NotFoundError
from janus_gate.faces.koios import _koios_page, _resolve_epoch_no
from janus_gate.mappers import account as account_mapper
from janus_gate.mappers import block as block_mapper
from janus_gate.mappers import pool as pool_mapper
from janus_gate.mappers import script as script_mapper


def test_koios_page_aligned() -> None:
    assert _koios_page(100, 0, "asc") == (100, 1, "asc")
    assert _koios_page(100, 200, "epoch_no.desc") == (100, 3, "desc")


def test_resolve_epoch_no_prefers_underscore_param() -> None:
    assert _resolve_epoch_no("640", None) == 640
    assert _resolve_epoch_no(None, "eq.639") == 639
    assert _resolve_epoch_no("640", "eq.1") == 640
    assert _resolve_epoch_no(None, None) is None


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
            "active_stake_pct": 0.27302943272682884,
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
    assert mapped[0]["rewards"] == "60"  # deleg_rewards + pool_fees
    assert mapped[0]["active_size"] == pytest.approx(0.0027302943272682884)


def test_pool_history_active_size_scale_roundtrip() -> None:
    bf_rows = [
        {
            "epoch": 210,
            "blocks": 2,
            "active_stake": "1000",
            "active_size": 0.0027302943272682884,
            "delegators_count": 5,
            "rewards": "60",
            "fees": "10",
        }
    ]
    koios = pool_mapper.blockfrost_pool_history_to_koios(bf_rows)
    assert koios[0]["active_stake_pct"] == pytest.approx(0.27302943272682884)
    assert koios[0]["deleg_rewards"] == "50"
    assert koios[0]["pool_fees"] == "10"
    back = pool_mapper.koios_pool_history_to_blockfrost(koios)
    assert back[0]["active_size"] == pytest.approx(0.0027302943272682884)
    assert back[0]["rewards"] == "60"


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


def test_block_txs_to_hashes() -> None:
    rows = [
        {"block_hash": "b", "tx_hash": "aaa"},
        {"block_hash": "b", "tx_hash": "bbb"},
    ]
    assert block_mapper.koios_block_txs_to_blockfrost(rows) == ["aaa", "bbb"]


def test_account_txs_partial_address() -> None:
    rows = [{"tx_hash": "t1", "block_height": 1, "block_time": 2}]
    mapped = account_mapper.koios_account_txs_to_blockfrost(rows, "stake1abc")
    assert mapped[0]["address"] == "stake1abc"
    assert mapped[0]["tx_index"] == 0
    assert mapped[0]["tx_hash"] == "t1"


def test_metalabels_mapping() -> None:
    from janus_gate.mappers import metadata as metadata_mapper

    labels = metadata_mapper.koios_metalabels_to_blockfrost([{"key": "721"}])
    assert labels == [{"label": "721", "cip10": None, "count": None}]
    by_label = metadata_mapper.koios_tx_by_metalabel_to_blockfrost(
        [{"tx_hash": "abc", "block_height": 1}]
    )
    assert by_label == [{"tx_hash": "abc", "json_metadata": None}]


def test_pool_blocks_and_updates_mapping() -> None:
    blocks = pool_mapper.koios_pool_blocks_to_blockfrost(
        [{"block_hash": "abc", "block_height": 1}]
    )
    assert blocks == ["abc"]
    back = pool_mapper.blockfrost_pool_blocks_to_koios(blocks)
    assert back[0]["block_hash"] == "abc"
    assert back[0]["block_height"] is None

    updates = pool_mapper.koios_pool_updates_to_blockfrost(
        [{"tx_hash": "t1", "update_type": "registration", "cert_index": 2}]
    )
    assert updates == [{"tx_hash": "t1", "cert_index": 2, "action": "registered"}]
    votes = pool_mapper.koios_pool_votes_to_blockfrost(
        [{"proposal_tx_hash": "p1", "proposal_index": 0, "vote": "Yes"}]
    )
    assert votes[0]["vote"] == "yes"
    assert votes[0]["tx_hash"] == "p1"


def test_asset_list_and_history_mapping() -> None:
    from janus_gate.mappers import asset as asset_mapper

    listed = asset_mapper.koios_asset_list_to_blockfrost(
        [{"policy_id": "p" * 56, "asset_name": "aa", "quantity": "3"}]
    )
    assert listed[0]["asset"] == ("p" * 56) + "aa"
    assert listed[0]["quantity"] == "3"

    history = asset_mapper.koios_asset_history_to_blockfrost(
        [
            {
                "minting_txs": [
                    {"tx_hash": "m1", "quantity": "5"},
                    {"tx_hash": "b1", "quantity": "-2"},
                ]
            }
        ]
    )
    assert history[0]["action"] == "minted"
    assert history[1]["action"] == "burned"
    assert history[1]["amount"] == "2"


def test_address_extended_and_assets_mapping() -> None:
    from janus_gate.mappers import address as address_mapper

    koios_rows = [
        {
            "address": "addr1test",
            "balance": "100",
            "stake_address": "stake1x",
            "script_address": False,
            "utxo_set": [],
        }
    ]
    extended = address_mapper.koios_address_to_blockfrost_extended(
        koios_rows, "addr1test"
    )
    assert extended["amount"][0]["decimals"] is None
    assert extended["amount"][0]["unit"] == "lovelace"

    assets = address_mapper.blockfrost_amounts_to_koios_address_assets(
        {
            "address": "addr1test",
            "amount": [
                {"unit": "lovelace", "quantity": "1"},
                {"unit": ("a" * 56) + "bb", "quantity": "9"},
            ],
        },
        "addr1test",
    )
    assert len(assets) == 1
    assert assets[0]["policy_id"] == "a" * 56
    assert assets[0]["asset_name"] == "bb"
    assert assets[0]["address"] == "addr1test"
