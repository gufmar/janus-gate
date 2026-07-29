"""Koios-compatible public face routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from janus_gate.config import ProviderName
from janus_gate.faces.common import pagination_params, run_upstream
from janus_gate.mappers.registry import (
    fetch_address_as,
    fetch_address_transactions_as,
    fetch_address_utxos_as,
    fetch_block_as,
    fetch_epoch_as,
    fetch_epoch_parameters_as,
    fetch_genesis_as,
    fetch_tip_as,
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
        number = _parse_eq_int(epoch_no)
        return await run_upstream(
            fetch_epoch_as(ProviderName.KOIOS, request.app.state.backend, number)
        )

    @router.get("/epoch_params")
    async def epoch_params(
        request: Request,
        epoch_no: str | None = Query(default=None),
    ) -> Any:
        number = _parse_eq_int(epoch_no)
        return await run_upstream(
            fetch_epoch_parameters_as(
                ProviderName.KOIOS, request.app.state.backend, number
            )
        )

    @router.post("/block_info")
    async def block_info(body: BlockInfoRequest, request: Request) -> Any:
        if not body.block_hashes:
            raise HTTPException(status_code=400, detail="_block_hashes must not be empty")
        # PoC: first hash only (Koios accepts batches).
        return await run_upstream(
            fetch_block_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                body.block_hashes[0],
            )
        )

    @router.post("/address_info")
    async def address_info(body: AddressInfoRequest, request: Request) -> Any:
        if not body.addresses:
            raise HTTPException(status_code=400, detail="_addresses must not be empty")
        address = body.addresses[0]
        return await run_upstream(
            fetch_address_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                address,
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
        if not body.addresses:
            raise HTTPException(status_code=400, detail="_addresses must not be empty")
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_address_utxos_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                body.addresses[0],
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
        if not body.addresses:
            raise HTTPException(status_code=400, detail="_addresses must not be empty")
        count, page, bf_order = _koios_page(limit, offset, order)
        return await run_upstream(
            fetch_address_transactions_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                body.addresses[0],
                count=count,
                page=page,
                order=bf_order,
            )
        )

    @router.post("/submittx")
    async def submittx(request: Request) -> Any:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty transaction body")
        result = await run_upstream(submit_tx_as(request.app.state.backend, body))
        if isinstance(result, str):
            return PlainTextResponse(result, media_type="text/plain")
        return result

    return router


def _parse_eq_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    if value.startswith("eq."):
        value = value[3:]
    return int(value)


def _koios_page(limit: int, offset: int, order: str) -> tuple[int, int, str]:
    count = max(limit, 1)
    page = (offset // count) + 1
    bf_order = "desc" if order.endswith(".desc") or order == "desc" else "asc"
    return count, page, bf_order
