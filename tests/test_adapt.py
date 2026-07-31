"""Tests for adapt_to_face dispatch."""

from __future__ import annotations

import pytest

from janus_gate.config import FaceName, ProviderName
from janus_gate.faces.errors import MappingError
from janus_gate.mapping.adapt import GENESIS, TIP, adapt_to_face


def test_identity_passthrough_when_face_equals_source() -> None:
    raw = {"height": 1, "hash": "abc"}
    assert adapt_to_face(FaceName.BLOCKFROST, "blockfrost", TIP, raw) is raw
    assert adapt_to_face("koios", "koios", GENESIS, [{"networkmagic": 1}]) == [
        {"networkmagic": 1}
    ]


def test_koios_tip_to_blockfrost() -> None:
    tip = [{"epoch_no": 500, "block_height": 1, "hash": "abc", "abs_slot": 9}]
    mapped = adapt_to_face(FaceName.BLOCKFROST, "koios", TIP, tip)
    assert mapped["epoch"] == 500
    assert mapped["height"] == 1
    assert mapped["hash"] == "abc"


def test_koios_genesis_to_blockfrost() -> None:
    rows = [
        {
            "networkmagic": 764824073,
            "networkid": "Mainnet",
            "epochlength": 432000,
            "slotlength": 1,
            "maxlovelacesupply": 45000000000000000,
            "systemstart": 1506203091,
            "activeslotcoeff": 0.05,
            "securityparam": 2160,
            "updatequorum": 5,
            "maxkesrevolutions": 62,
        }
    ]
    mapped = adapt_to_face(FaceName.BLOCKFROST, "koios", GENESIS, rows)
    assert mapped["network_magic"] == 764824073
    assert mapped["epoch_length"] == 432000


def test_adapt_epoch_list_koios_to_blockfrost() -> None:
    from janus_gate.mappers.registry import _adapt_epoch_list

    rows = [
        {
            "epoch_no": 226,
            "start_time": 1,
            "end_time": 2,
            "blk_count": 10,
            "tx_count": 20,
            "out_sum": "100",
            "fees": "5",
            "active_stake": "50",
        },
        {
            "epoch_no": 227,
            "start_time": 3,
            "end_time": 4,
            "blk_count": 11,
            "tx_count": 21,
            "out_sum": "101",
            "fees": "6",
            "active_stake": "51",
        },
    ]
    mapped = _adapt_epoch_list(ProviderName.BLOCKFROST, "koios", rows)
    assert len(mapped) == 2
    assert mapped[0]["epoch"] == 226
    assert mapped[0]["block_count"] == 10
    assert mapped[1]["epoch"] == 227


def test_adapt_epoch_list_blockfrost_passthrough() -> None:
    from janus_gate.mappers.registry import _adapt_epoch_list

    raw = [{"epoch": 1}, {"epoch": 2}]
    assert _adapt_epoch_list(ProviderName.BLOCKFROST, "blockfrost", raw) is raw


def test_adapt_block_list_koios_to_blockfrost() -> None:
    from janus_gate.mappers.registry import _adapt_block_list

    rows = [
        {
            "hash": "abc",
            "block_height": 10,
            "block_time": 1,
            "abs_slot": 100,
            "epoch_no": 2,
            "epoch_slot": 3,
            "pool": "pool1",
            "tx_count": 1,
        }
    ]
    mapped = _adapt_block_list(ProviderName.BLOCKFROST, "koios", rows)
    assert len(mapped) == 1
    assert mapped[0]["hash"] == "abc"
    assert mapped[0]["height"] == 10


def test_adapt_block_list_passthrough() -> None:
    from janus_gate.mappers.registry import _adapt_block_list

    raw = [{"hash": "x", "height": 1}]
    assert _adapt_block_list(ProviderName.BLOCKFROST, "blockfrost", raw) is raw


def test_era_summaries_round_trip_partial() -> None:
    from janus_gate.mapping.adapt import adapt_to_face
    from janus_gate.mappers import era as era_mapper

    koios = [
        {
            "era": 7,
            "epoch_no": 400,
            "first_block_time": 123,
            "first_block_hash": "h",
            "protocol_major": 9,
            "protocol_minor": 0,
        }
    ]
    bf = era_mapper.koios_era_summaries_to_blockfrost(koios)
    assert bf[0]["start"]["epoch"] == 400
    assert bf[0]["start"]["time"] == 123
    assert bf[0]["parameters"]["epoch_length"] is None

    back = era_mapper.blockfrost_eras_to_koios(bf)
    assert back[0]["epoch_no"] == 400
    assert back[0]["first_block_time"] == 123

    adapted = adapt_to_face("blockfrost", "koios", "era_summaries", koios)
    assert adapted[0]["start"]["epoch"] == 400
