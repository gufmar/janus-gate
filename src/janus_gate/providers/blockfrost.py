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

    async def get_address_info(self, address: str) -> Any:
        return await self.request("GET", f"/addresses/{address}")
