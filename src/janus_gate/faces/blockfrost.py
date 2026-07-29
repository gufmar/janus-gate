"""Blockfrost-compatible public face routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from janus_gate.config import ProviderName
from janus_gate.mappers.registry import fetch_address_as, fetch_tip_as
from janus_gate.providers.base import ProviderError


def build_blockfrost_router() -> APIRouter:
    router = APIRouter(tags=["blockfrost-face"])

    @router.get("/blocks/latest")
    async def blocks_latest(request: Request):
        try:
            return await fetch_tip_as(ProviderName.BLOCKFROST, request.app.state.backend)
        except ProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @router.get("/addresses/{address}")
    async def address_info(address: str, request: Request):
        try:
            return await fetch_address_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
            )
        except ProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return router
