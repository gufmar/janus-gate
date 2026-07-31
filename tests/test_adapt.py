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
