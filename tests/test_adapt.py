"""Tests for adapt_to_face dispatch."""

from __future__ import annotations

import pytest

from janus_gate.config import FaceName
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


def test_unknown_pair_raises_mapping_error() -> None:
    with pytest.raises(MappingError, match="No face adapter"):
        adapt_to_face(FaceName.BLOCKFROST, "dbsync", TIP, {"x": 1})
