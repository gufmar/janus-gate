"""Koios-compatible public face routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from janus_gate.config import ProviderName
from janus_gate.mappers.registry import fetch_address_as, fetch_tip_as
from janus_gate.providers.base import ProviderError


class AddressInfoRequest(BaseModel):
    addresses: list[str] = Field(alias="_addresses")

    model_config = {"populate_by_name": True}


def build_koios_router() -> APIRouter:
    router = APIRouter(tags=["koios-face"])

    @router.get("/tip")
    async def tip(request: Request) -> Any:
        try:
            return await fetch_tip_as(ProviderName.KOIOS, request.app.state.backend)
        except ProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @router.post("/address_info")
    async def address_info(body: AddressInfoRequest, request: Request) -> Any:
        if not body.addresses:
            raise HTTPException(status_code=400, detail="_addresses must not be empty")
        # PoC: translate the first address (Koios accepts batches; clients often send one).
        address = body.addresses[0]
        try:
            return await fetch_address_as(
                ProviderName.KOIOS,
                request.app.state.backend,
                address,
            )
        except ProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return router
