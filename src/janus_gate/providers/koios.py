"""Koios backend client."""

from __future__ import annotations

from typing import Any

from janus_gate.providers.base import HttpProvider


class KoiosProvider(HttpProvider):
    name = "koios"

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        super().__init__(base_url, headers=headers)

    async def get_tip(self) -> Any:
        return await self.request("GET", "/tip")

    async def get_address_info(self, address: str) -> Any:
        return await self.request(
            "POST",
            "/address_info",
            json={"_addresses": [address]},
        )

    async def get_block_by_height(self, height: int) -> Any:
        """Fetch a single block row for richer tip mapping when available."""
        rows = await self.request(
            "GET",
            "/blocks",
            params={"block_height": f"eq.{height}", "limit": 1},
        )
        if isinstance(rows, list) and rows:
            return rows[0]
        return None
