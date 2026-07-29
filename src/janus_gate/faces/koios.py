"""Koios-compatible public face routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from janus_gate.config import ProviderName
from janus_gate.faces.common import run_upstream
from janus_gate.faces.errors import BadRequestError
from janus_gate.mappers.registry import (
    fetch_account_addresses_as,
    fetch_account_as,
    fetch_account_history_as,
    fetch_account_rewards_as,
    fetch_account_transactions_as,
    fetch_address_as,
    fetch_address_transactions_as,
    fetch_address_utxos_as,
    fetch_asset_as,
    fetch_block_as,
    fetch_block_transactions_as,
    fetch_committee_as,
    fetch_datum_as,
    fetch_drep_as,
    fetch_dreps_as,
    fetch_epoch_as,
    fetch_epoch_blocks_as,
    fetch_epoch_parameters_as,
    fetch_genesis_as,
    fetch_metadata_by_label_as,
    fetch_metadata_labels_as,
    fetch_pool_as,
    fetch_pool_delegators_as,
    fetch_pool_history_as,
    fetch_pool_metadata_as,
    fetch_pool_relays_as,
    fetch_pools_as,
    fetch_proposals_as,
    fetch_script_as,
    fetch_tip_as,
    fetch_tx_as,
    fetch_tx_cbor_as,
    fetch_tx_metadata_as,
    fetch_tx_utxos_as,
    submit_tx_as,
)


class AddressInfoRequest(BaseModel):
    addresses: list[str] = Field(alias="_addresses")
    model_config = {"populate_by_name": True}


class AddressListRequest(BaseModel):
    addresses: list[str] = Field(alias="_addresses")
    model_config = {"populate_by_name": True}


class BlockInfoRequest(BaseModel):
    block_hashes: list[str] = Field(alias="_block_hashes")
    model_config = {"populate_by_name": True}


class TxHashesRequest(BaseModel):
    tx_hashes: list[str] = Field(alias="_tx_hashes")
    model_config = {"populate_by_name": True}


class StakeAddressesRequest(BaseModel):
    stake_addresses: list[str] = Field(alias="_stake_addresses")
    model_config = {"populate_by_name": True}


class PoolIdsRequest(BaseModel):
    pool_bech32_ids: list[str] = Field(alias="_pool_bech32_ids")
    model_config = {"populate_by_name": True}


class AssetListRequest(BaseModel):
    asset_list: list[Any] = Field(alias="_asset_list")
    model_config = {"populate_by_name": True}


class DrepIdsRequest(BaseModel):
    drep_ids: list[str] = Field(alias="_drep_ids")
    model_config = {"populate_by_name": True}


class ScriptHashesRequest(BaseModel):
    script_hashes: list[str] = Field(alias="_script_hashes")
    model_config = {"populate_by_name": True}


class DatumHashesRequest(BaseModel):
    datum_hashes: list[str] = Field(alias="_datum_hashes")
    model_config = {"populate_by_name": True}


def build_koios_router() -> APIRouter:
    router = APIRouter(tags=["koios-face"])

    @router.get("/tip")
    async def tip(request: Request) -> Any:
        return await run_upstream(
            fetch_tip_as(ProviderName.KOIOS, request.app.state.backend)
        )

    @router.get("/genesis")
    async def genesis(request: Request) -> Any:
        return await run_upstream(
            fetch_genesis_as(ProviderName.KOIOS, request.app.state.backend)
        )

    @router.get("/epoch_info")
    async def epoch_info(
        request: Request,
        epoch_no: str | None = Query(default=None),
    ) -> Any:
        return await run_upstream(
            fetch_epoch_as(
                ProviderName.KOIOS, request.app.state.backend, _parse_eq_int(epoch_no)
            )
        )

    @router.get("/epoch_params")
    async def epoch_params(
        request: Request,
        epoch_no: str | None = Query(default=None),
    ) -> Any:
        return await run_upstream(
            fetch_epoch_parameters_as(
                ProviderName.KOIOS, request.app.state.backend, _parse_eq_int(epoch_no)
            )
        )

    @router.get("/blocks")
    async def blocks(
        request: Request,
        epoch_no: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="block_height.asc"),
    ) -> Any:
        number = _parse_eq_int(epoch_no)
        if number is None:
            raise BadRequestError(
                "Janus PoC requires epoch_no=eq.N for GET /blocks"
            )
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_epoch_blocks_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                number,
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.post("/block_info")
    async def block_info(body: BlockInfoRequest, request: Request) -> Any:
        if not body.block_hashes:
            raise BadRequestError("_block_hashes must not be empty")
        return await run_upstream(
            fetch_block_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                body.block_hashes[0],
            )
        )

    @router.post("/block_txs")
    async def block_txs(
        body: BlockInfoRequest,
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="asc"),
    ) -> Any:
        if not body.block_hashes:
            raise BadRequestError("_block_hashes must not be empty")
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_block_transactions_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                body.block_hashes[0],
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.post("/tx_info")
    async def tx_info(body: TxHashesRequest, request: Request) -> Any:
        tx_hash = _first(body.tx_hashes, "_tx_hashes")
        return await run_upstream(
            fetch_tx_as(ProviderName.KOIOS, request.app.state.backend, tx_hash)
        )

    @router.post("/tx_utxos")
    async def tx_utxos(body: TxHashesRequest, request: Request) -> Any:
        tx_hash = _first(body.tx_hashes, "_tx_hashes")
        return await run_upstream(
            fetch_tx_utxos_as(ProviderName.KOIOS, request.app.state.backend, tx_hash)
        )

    @router.post("/tx_metadata")
    async def tx_metadata(body: TxHashesRequest, request: Request) -> Any:
        tx_hash = _first(body.tx_hashes, "_tx_hashes")
        return await run_upstream(
            fetch_tx_metadata_as(
                ProviderName.KOIOS, request.app.state.backend, tx_hash
            )
        )

    @router.post("/tx_cbor")
    async def tx_cbor(body: TxHashesRequest, request: Request) -> Any:
        tx_hash = _first(body.tx_hashes, "_tx_hashes")
        return await run_upstream(
            fetch_tx_cbor_as(ProviderName.KOIOS, request.app.state.backend, tx_hash)
        )

    @router.get("/tx_metalabels")
    async def tx_metalabels(
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="key.asc"),
    ) -> Any:
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_metadata_labels_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.get("/tx_by_metalabel")
    async def tx_by_metalabel(
        request: Request,
        _label: str = Query(...),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="block_height.asc"),
    ) -> Any:
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_metadata_by_label_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                _label,
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.post("/address_info")
    async def address_info(body: AddressInfoRequest, request: Request) -> Any:
        address = _first(body.addresses, "_addresses")
        return await run_upstream(
            fetch_address_as(
                ProviderName.KOIOS, request.app.state.backend, address
            )
        )

    @router.post("/address_utxos")
    async def address_utxos(
        body: AddressListRequest,
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="block_height.asc"),
    ) -> Any:
        address = _first(body.addresses, "_addresses")
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_address_utxos_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                address,
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.post("/address_txs")
    async def address_txs(
        body: AddressListRequest,
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="block_height.asc"),
    ) -> Any:
        address = _first(body.addresses, "_addresses")
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_address_transactions_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                address,
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.post("/account_info")
    async def account_info(body: StakeAddressesRequest, request: Request) -> Any:
        stake = _first(body.stake_addresses, "_stake_addresses")
        return await run_upstream(
            fetch_account_as(ProviderName.KOIOS, request.app.state.backend, stake)
        )

    @router.post("/account_rewards")
    async def account_rewards(body: StakeAddressesRequest, request: Request) -> Any:
        stake = _first(body.stake_addresses, "_stake_addresses")
        return await run_upstream(
            fetch_account_rewards_as(
                ProviderName.KOIOS, request.app.state.backend, stake
            )
        )

    @router.post("/account_history")
    async def account_history(body: StakeAddressesRequest, request: Request) -> Any:
        stake = _first(body.stake_addresses, "_stake_addresses")
        return await run_upstream(
            fetch_account_history_as(
                ProviderName.KOIOS, request.app.state.backend, stake
            )
        )

    @router.post("/account_addresses")
    async def account_addresses(body: StakeAddressesRequest, request: Request) -> Any:
        stake = _first(body.stake_addresses, "_stake_addresses")
        return await run_upstream(
            fetch_account_addresses_as(
                ProviderName.KOIOS, request.app.state.backend, stake
            )
        )

    @router.get("/account_txs")
    async def account_txs(
        request: Request,
        _stake_address: str = Query(...),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="block_height.asc"),
    ) -> Any:
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_account_transactions_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                _stake_address,
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.get("/pool_list")
    async def pool_list(
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> Any:
        count, page, _ = _koios_page(limit, offset, "asc")
        return await run_upstream(
            fetch_pools_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                count=count,
                page=page,
                extended=False,
            )
        )

    @router.post("/pool_info")
    async def pool_info(body: PoolIdsRequest, request: Request) -> Any:
        pool_id = _first(body.pool_bech32_ids, "_pool_bech32_ids")
        return await run_upstream(
            fetch_pool_as(ProviderName.KOIOS, request.app.state.backend, pool_id)
        )

    @router.get("/pool_history")
    async def pool_history(
        request: Request,
        _pool_bech32: str = Query(...),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        order: str = Query(default="epoch_no.asc"),
    ) -> Any:
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_pool_history_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                _pool_bech32,
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.post("/pool_metadata")
    async def pool_metadata(body: PoolIdsRequest, request: Request) -> Any:
        pool_id = _first(body.pool_bech32_ids, "_pool_bech32_ids")
        return await run_upstream(
            fetch_pool_metadata_as(
                ProviderName.KOIOS, request.app.state.backend, pool_id
            )
        )

    @router.get("/pool_delegators")
    async def pool_delegators(
        request: Request,
        _pool_bech32: str = Query(...),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> Any:
        count, page, _ = _koios_page(limit, offset, "asc")
        return await run_upstream(
            fetch_pool_delegators_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                _pool_bech32,
                count=count,
                page=page,
            )
        )

    @router.get("/pool_relays")
    async def pool_relays(
        request: Request,
        _pool_bech32: str | None = Query(default=None),
        pool_id_bech32: str | None = Query(default=None),
    ) -> Any:
        pool_id = _pool_bech32
        if pool_id is None and pool_id_bech32:
            pool_id = (
                pool_id_bech32[3:]
                if pool_id_bech32.startswith("eq.")
                else pool_id_bech32
            )
        if not pool_id:
            raise BadRequestError(
                "Janus PoC requires _pool_bech32 for GET /pool_relays"
            )
        return await run_upstream(
            fetch_pool_relays_as(
                ProviderName.KOIOS, request.app.state.backend, pool_id
            )
        )

    @router.post("/asset_info")
    async def asset_info(body: AssetListRequest, request: Request) -> Any:
        if not body.asset_list:
            raise BadRequestError("_asset_list must not be empty")
        first = body.asset_list[0]
        if isinstance(first, list) and len(first) >= 2:
            asset = f"{first[0]}{first[1] or ''}"
        elif isinstance(first, str):
            asset = first
        else:
            raise BadRequestError("Unsupported _asset_list item")
        return await run_upstream(
            fetch_asset_as(ProviderName.KOIOS, request.app.state.backend, asset)
        )

    @router.get("/committee_info")
    async def committee_info(request: Request) -> Any:
        return await run_upstream(
            fetch_committee_as(ProviderName.KOIOS, request.app.state.backend)
        )

    @router.get("/drep_list")
    async def drep_list(
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> Any:
        count, page, _ = _koios_page(limit, offset, "asc")
        return await run_upstream(
            fetch_dreps_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                count=count,
                page=page,
            )
        )

    @router.post("/drep_info")
    async def drep_info(body: DrepIdsRequest, request: Request) -> Any:
        drep_id = _first(body.drep_ids, "_drep_ids")
        return await run_upstream(
            fetch_drep_as(ProviderName.KOIOS, request.app.state.backend, drep_id)
        )

    @router.get("/proposal_list")
    async def proposal_list(
        request: Request,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> Any:
        count, page, _ = _koios_page(limit, offset, "asc")
        return await run_upstream(
            fetch_proposals_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                count=count,
                page=page,
            )
        )

    @router.post("/script_info")
    async def script_info(body: ScriptHashesRequest, request: Request) -> Any:
        script_hash = _first(body.script_hashes, "_script_hashes")
        return await run_upstream(
            fetch_script_as(
                ProviderName.KOIOS, request.app.state.backend, script_hash
            )
        )

    @router.post("/datum_info")
    async def datum_info(body: DatumHashesRequest, request: Request) -> Any:
        datum_hash = _first(body.datum_hashes, "_datum_hashes")
        return await run_upstream(
            fetch_datum_as(
                ProviderName.KOIOS, request.app.state.backend, datum_hash
            )
        )

    @router.post("/submittx")
    async def submittx(request: Request) -> Any:
        body = await request.body()
        if not body:
            raise BadRequestError("Empty transaction body")
        result = await run_upstream(submit_tx_as(request.app.state.backend, body))
        if isinstance(result, str):
            return PlainTextResponse(result, media_type="text/plain")
        return result

    return router


def _first(values: list[str], field: str) -> str:
    if not values:
        raise BadRequestError(f"{field} must not be empty")
    return values[0]


def _parse_eq_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    if value.startswith("eq."):
        value = value[3:]
    return int(value)


def _koios_page(limit: int, offset: int, order: str) -> tuple[int, int, str]:
    count = max(limit, 1)
    if offset % count != 0:
        raise BadRequestError(
            f"offset ({offset}) must be a multiple of limit ({count})"
        )
    page = (offset // count) + 1
    bf_order = "desc" if order.endswith(".desc") or order == "desc" else "asc"
    return count, page, bf_order
