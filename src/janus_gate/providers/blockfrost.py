"""Blockfrost backend client."""

from __future__ import annotations

from typing import Any

from janus_gate.providers.base import HttpProvider


class BlockfrostProvider(HttpProvider):
    name = "blockfrost"

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        # api_key kept for call-site compatibility; per-request auth uses context.
        del api_key
        super().__init__(
            base_url,
            headers={"Accept": "application/json"},
            auth_header="project_id",
            auth_prefix="",
        )

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

    async def get_block_transactions(
        self,
        hash_or_number: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/blocks/{hash_or_number}/txs",
            params={"count": count, "page": page, "order": order},
        )

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

    async def get_tx(self, tx_hash: str) -> Any:
        return await self.request("GET", f"/txs/{tx_hash}")

    async def get_tx_utxos(self, tx_hash: str) -> Any:
        return await self.request("GET", f"/txs/{tx_hash}/utxos")

    async def get_tx_metadata(self, tx_hash: str) -> Any:
        return await self.request("GET", f"/txs/{tx_hash}/metadata")

    async def get_tx_cbor(self, tx_hash: str) -> Any:
        return await self.request("GET", f"/txs/{tx_hash}/cbor")

    async def get_account_info(self, stake_address: str) -> Any:
        return await self.request("GET", f"/accounts/{stake_address}")

    async def get_account_rewards(self, stake_address: str) -> Any:
        return await self.request("GET", f"/accounts/{stake_address}/rewards")

    async def get_account_history(self, stake_address: str) -> Any:
        return await self.request("GET", f"/accounts/{stake_address}/history")

    async def get_account_addresses(self, stake_address: str) -> Any:
        return await self.request("GET", f"/accounts/{stake_address}/addresses")

    async def get_account_transactions(
        self,
        stake_address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/accounts/{stake_address}/transactions",
            params={"count": count, "page": page, "order": order},
        )

    async def get_pools(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.request(
            "GET", "/pools", params={"count": count, "page": page}
        )

    async def get_pools_extended(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.request(
            "GET", "/pools/extended", params={"count": count, "page": page}
        )

    async def get_pool(self, pool_id: str) -> Any:
        return await self.request("GET", f"/pools/{pool_id}")

    async def get_pool_history(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/pools/{pool_id}/history",
            params={"count": count, "page": page, "order": order},
        )

    async def get_pool_metadata(self, pool_id: str) -> Any:
        return await self.request("GET", f"/pools/{pool_id}/metadata")

    async def get_pool_delegators(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self.request(
            "GET",
            f"/pools/{pool_id}/delegators",
            params={"count": count, "page": page},
        )

    async def get_pool_relays(self, pool_id: str) -> Any:
        return await self.request("GET", f"/pools/{pool_id}/relays")

    async def get_epoch_blocks(
        self,
        number: int,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/epochs/{number}/blocks",
            params={"count": count, "page": page, "order": order},
        )

    async def get_committee(self) -> Any:
        return await self.request("GET", "/governance/committee")

    async def get_dreps(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.request(
            "GET", "/governance/dreps", params={"count": count, "page": page}
        )

    async def get_drep(self, drep_id: str) -> Any:
        return await self.request("GET", f"/governance/dreps/{drep_id}")

    async def get_proposals(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.request(
            "GET", "/governance/proposals", params={"count": count, "page": page}
        )

    async def get_script(self, script_hash: str) -> Any:
        return await self.request("GET", f"/scripts/{script_hash}")

    async def get_datum(self, datum_hash: str) -> Any:
        return await self.request("GET", f"/scripts/datum/{datum_hash}")

    async def get_metadata_labels(
        self,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            "/metadata/txs/labels",
            params={"count": count, "page": page, "order": order},
        )

    async def get_metadata_by_label(
        self,
        label: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/metadata/txs/labels/{label}",
            params={"count": count, "page": page, "order": order},
        )

    async def get_asset(self, asset: str) -> Any:
        return await self.request("GET", f"/assets/{asset}")
