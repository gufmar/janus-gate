"""Blockfrost backend client."""

from __future__ import annotations

from typing import Any

from janus_gate.providers.base import HttpProvider


class BlockfrostProvider(HttpProvider):
    name = "blockfrost"

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["project_id"] = api_key
        super().__init__(base_url, headers=headers)

    async def get_tip(self) -> Any:
        return await self.request("GET", "/blocks/latest")

    async def get_genesis(self) -> Any:
        return await self.request("GET", "/genesis")

    async def get_epoch(self, number: int | None = None) -> Any:
        path = "/epochs/latest" if number is None else f"/epochs/{number}"
        return await self.request("GET", path)

    async def get_epoch_parameters(self, number: int | None = None) -> Any:
        path = (
            "/epochs/latest/parameters"
            if number is None
            else f"/epochs/{number}/parameters"
        )
        return await self.request("GET", path)

    async def get_block(self, hash_or_number: str) -> Any:
        return await self.request("GET", f"/blocks/{hash_or_number}")

    async def get_address_info(self, address: str) -> Any:
        return await self.request("GET", f"/addresses/{address}")

    async def get_address_utxos(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/addresses/{address}/utxos",
            params={"count": count, "page": page, "order": order},
        )

    async def get_address_transactions(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/addresses/{address}/transactions",
            params={"count": count, "page": page, "order": order},
        )

    async def submit_tx(self, cbor: bytes) -> Any:
        return await self.request(
            "POST",
            "/tx/submit",
            content=cbor,
            headers={"Content-Type": "application/cbor"},
        )
