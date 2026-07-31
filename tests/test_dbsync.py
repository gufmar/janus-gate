"""dbSync mapper and provider MVP tests (no live Postgres)."""

from __future__ import annotations

import pytest

from janus_gate.config import FaceName
from janus_gate.faces.errors import MappingError, NotFoundError
from janus_gate.mapping.adapt import BLOCK, GENESIS, TIP, TX, adapt_to_face
from janus_gate.mappers import dbsync as dbsync_mapper
from janus_gate.providers.base import ProviderError
from janus_gate.providers.dbsync import DbSyncProvider


def test_dbsync_block_to_blockfrost() -> None:
    row = {
        "hash": "abc",
        "block_no": 10,
        "epoch_no": 2,
        "slot_no": 100,
        "epoch_slot_no": 5,
        "block_time": 1700000000,
        "size": 1000,
        "tx_count": 3,
        "vrf_key": "vrf",
        "op_cert": None,
        "op_cert_counter": 1,
        "previous_hash": "prev",
        "next_hash": None,
        "slot_leader": "pool1abc",
        "confirmations": 0,
        "out_sum": 50,
        "fees": 2,
    }
    mapped = dbsync_mapper.dbsync_block_to_blockfrost(row)
    assert mapped["hash"] == "abc"
    assert mapped["height"] == 10
    assert mapped["epoch"] == 2
    assert mapped["fees"] == "2"
    assert mapped["slot_leader"] == "pool1abc"


def test_dbsync_genesis_uses_network_defaults() -> None:
    mapped = dbsync_mapper.dbsync_genesis_to_blockfrost(
        {"network_name": "preview", "system_start": 1666656000}
    )
    assert mapped["network_magic"] == 2
    assert mapped["epoch_length"] == 86400
    assert mapped["system_start"] == 1666656000


def test_adapt_dbsync_tip_and_tx() -> None:
    tip = adapt_to_face(
        FaceName.BLOCKFROST,
        "dbsync",
        TIP,
        {
            "hash": "h1",
            "block_no": 1,
            "epoch_no": 0,
            "slot_no": 0,
            "epoch_slot_no": 0,
            "block_time": 1,
            "size": 1,
            "tx_count": 0,
            "confirmations": 0,
            "out_sum": 0,
            "fees": 0,
            "slot_leader": None,
            "previous_hash": None,
            "next_hash": None,
            "vrf_key": None,
            "op_cert": None,
            "op_cert_counter": None,
        },
    )
    assert tip["height"] == 1

    tx = adapt_to_face(
        FaceName.BLOCKFROST,
        "dbsync",
        TX,
        {
            "tx_hash": "deadbeef",
            "block_hash": "b",
            "block_height": 9,
            "block_time": 2,
            "slot_no": 3,
            "block_index": 0,
            "out_sum": 100,
            "fee": 1,
            "deposit": 0,
            "size": 200,
            "invalid_before": None,
            "invalid_hereafter": None,
            "valid_contract": True,
            "utxo_count": 2,
            "withdrawal_count": 0,
        },
    )
    assert tx["hash"] == "deadbeef"
    assert tx["fees"] == "1"


def test_adapt_unknown_dbsync_koios_pair() -> None:
    # Unknown concept for koios+dbsync still errors; tip is registered.
    with pytest.raises(MappingError, match="No face adapter"):
        adapt_to_face(FaceName.KOIOS, "dbsync", "pools", {"x": 1})


def test_adapt_dbsync_tip_to_koios() -> None:
    tip = adapt_to_face(
        FaceName.KOIOS,
        "dbsync",
        TIP,
        {
            "hash": "h1",
            "block_no": 1,
            "epoch_no": 0,
            "slot_no": 0,
            "epoch_slot_no": 0,
            "block_time": 1,
            "size": 1,
            "tx_count": 0,
            "confirmations": 0,
            "out_sum": 0,
            "fees": 0,
            "slot_leader": None,
            "previous_hash": None,
            "next_hash": None,
            "vrf_key": None,
            "op_cert": None,
            "op_cert_counter": None,
        },
    )
    assert isinstance(tip, list)
    assert tip[0]["hash"] == "h1"
    assert tip[0]["block_height"] == 1


def test_dbsync_block_missing_raises() -> None:
    with pytest.raises(NotFoundError):
        dbsync_mapper.dbsync_block_to_blockfrost(None)


def test_dbsync_unimplemented_ops() -> None:
    import asyncio

    provider = DbSyncProvider("postgresql://unused")

    async def _run() -> None:
        with pytest.raises(ProviderError) as exc:
            await provider.submit_tx(b"\x00")
        assert exc.value.status_code == 501

    asyncio.run(_run())


def test_adapt_block_concept() -> None:
    mapped = adapt_to_face(
        FaceName.BLOCKFROST,
        "dbsync",
        BLOCK,
        {
            "hash": "x",
            "block_no": 5,
            "epoch_no": 1,
            "slot_no": 10,
            "epoch_slot_no": 1,
            "block_time": 99,
            "size": 10,
            "tx_count": 1,
            "confirmations": 2,
            "out_sum": 1,
            "fees": 0,
            "slot_leader": "pool1",
            "previous_hash": None,
            "next_hash": None,
            "vrf_key": None,
            "op_cert": None,
            "op_cert_counter": None,
        },
    )
    assert mapped["confirmations"] == 2
