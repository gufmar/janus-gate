"""Koios backend client."""

from __future__ import annotations

from typing import Any

from janus_gate.providers.base import HttpProvider, page_to_offset


class KoiosProvider(HttpProvider):
    name = "koios"

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        # api_key kept for call-site compatibility; per-request auth uses context.
        del api_key
        super().__init__(
            base_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            auth_header="Authorization",
            auth_prefix="Bearer ",
        )

    async def get_tip(self) -> Any:
        return await self.request("GET", "/tip")

    async def get_genesis(self) -> Any:
        return await self.request("GET", "/genesis")

    async def get_epoch(self, number: int | None = None) -> Any:
        params: dict[str, Any] = {"limit": 1}
        if number is None:
            tip = await self.get_tip()
            tip_row = tip[0] if isinstance(tip, list) and tip else tip
            number = int(tip_row["epoch_no"])
        params["epoch_no"] = f"eq.{number}"
        return await self.request("GET", "/epoch_info", params=params)

    async def get_epoch_parameters(self, number: int | None = None) -> Any:
        params: dict[str, Any] = {"limit": 1}
        if number is None:
            tip = await self.get_tip()
            tip_row = tip[0] if isinstance(tip, list) and tip else tip
            number = int(tip_row["epoch_no"])
        params["epoch_no"] = f"eq.{number}"
        return await self.request("GET", "/epoch_params", params=params)

    async def get_block(self, hash_or_number: str) -> Any:
        block_hash = hash_or_number
        if hash_or_number.isdigit():
            rows = await self.request(
                "GET",
                "/blocks",
                params={"block_height": f"eq.{hash_or_number}", "limit": 1},
            )
            if not isinstance(rows, list) or not rows:
                from janus_gate.providers.base import ProviderError

                raise ProviderError(404, {"message": "Block not found", "status_code": 404})
            block_hash = rows[0]["hash"]
        return await self.request(
            "POST",
            "/block_info",
            json={"_block_hashes": [block_hash]},
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

    async def get_address_info(self, address: str) -> Any:
        return await self.request(
            "POST",
            "/address_info",
            json={"_addresses": [address]},
        )

    async def get_address_utxos(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        params = {
            "limit": count,
            "offset": page_to_offset(page, count),
            "order": f"block_height.{'desc' if order == 'desc' else 'asc'}",
        }
        return await self.request(
            "POST",
            "/address_utxos",
            json={"_addresses": [address]},
            params=params,
        )

    async def get_address_transactions(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        params = {
            "limit": count,
            "offset": page_to_offset(page, count),
            "order": f"block_height.{'desc' if order == 'desc' else 'asc'}",
        }
        return await self.request(
            "POST",
            "/address_txs",
            json={"_addresses": [address]},
            params=params,
        )

    async def submit_tx(self, cbor: bytes) -> Any:
        return await self.request(
            "POST",
            "/submittx",
            content=cbor,
            headers={"Content-Type": "application/cbor"},
        )
