"""Blockfrost-compatible public face routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

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


def build_blockfrost_router() -> APIRouter:
    router = APIRouter(tags=["blockfrost-face"])

    @router.get("/blocks/latest")
    async def blocks_latest(request: Request):
        return await run_upstream(
            fetch_tip_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )

    @router.get("/blocks/{hash_or_number}")
    async def blocks_by_id(hash_or_number: str, request: Request):
        return await run_upstream(
            fetch_block_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                hash_or_number,
            )
        )

    @router.get("/genesis")
    async def genesis(request: Request):
        return await run_upstream(
            fetch_genesis_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )

    @router.get("/epochs/latest")
    async def epochs_latest(request: Request):
        return await run_upstream(
            fetch_epoch_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )

    @router.get("/epochs/latest/parameters")
    async def epochs_latest_parameters(request: Request):
        return await run_upstream(
            fetch_epoch_parameters_as(
                ProviderName.BLOCKFROST, request.app.state.backend
            )
        )

    @router.get("/epochs/{number}")
    async def epochs_by_number(number: int, request: Request):
        return await run_upstream(
            fetch_epoch_as(
                ProviderName.BLOCKFROST, request.app.state.backend, number
            )
        )

    @router.get("/epochs/{number}/parameters")
    async def epochs_parameters(number: int, request: Request):
        return await run_upstream(
            fetch_epoch_parameters_as(
                ProviderName.BLOCKFROST, request.app.state.backend, number
            )
        )

    @router.get("/addresses/{address}")
    async def address_info(address: str, request: Request):
        return await run_upstream(
            fetch_address_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
            )
        )

    @router.get("/addresses/{address}/utxos")
    async def address_utxos(
        address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_address_utxos_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
                **params,
            )
        )

    @router.get("/addresses/{address}/transactions")
    async def address_transactions(
        address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_address_transactions_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
                **params,
            )
        )

    @router.post("/tx/submit")
    async def tx_submit(request: Request):
        body = await request.body()
        if not body:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="Empty transaction body")
        result = await run_upstream(submit_tx_as(request.app.state.backend, body))
        # Blockfrost returns a JSON string (tx hash).
        if isinstance(result, str):
            return PlainTextResponse(f'"{result}"', media_type="application/json")
        return result

    return router
