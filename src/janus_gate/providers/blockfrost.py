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

    async def get_epochs_next(
        self,
        number: int,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self.request(
            "GET",
            f"/epochs/{number}/next",
            params={"count": count, "page": page},
        )

    async def get_epochs_previous(
        self,
        number: int,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self.request(
            "GET",
            f"/epochs/{number}/previous",
            params={"count": count, "page": page},
        )

    async def get_era_summaries(self) -> Any:
        return await self.request("GET", "/network/eras")

    async def get_block(self, hash_or_number: str) -> Any:
        return await self.request("GET", f"/blocks/{hash_or_number}")

    async def get_blocks_next(
        self,
        hash_or_number: str,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self.request(
            "GET",
            f"/blocks/{hash_or_number}/next",
            params={"count": count, "page": page},
        )

    async def get_blocks_previous(
        self,
        hash_or_number: str,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self.request(
            "GET",
            f"/blocks/{hash_or_number}/previous",
            params={"count": count, "page": page},
        )

    async def get_block_by_slot(self, slot: int) -> Any:
        return await self.request("GET", f"/blocks/slot/{slot}")

    async def get_block_by_epoch_slot(self, epoch: int, slot: int) -> Any:
        return await self.request("GET", f"/blocks/epoch/{epoch}/slot/{slot}")

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

    async def get_address_extended(self, address: str) -> Any:
        return await self.request("GET", f"/addresses/{address}/extended")

    async def get_address_assets(self, address: str) -> Any:
        # Blockfrost has no dedicated address-assets route; reuse summary amounts.
        return await self.get_address_info(address)

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

    async def get_pool_blocks(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/pools/{pool_id}/blocks",
            params={"count": count, "page": page, "order": order},
        )

    async def get_pool_updates(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/pools/{pool_id}/updates",
            params={"count": count, "page": page, "order": order},
        )

    async def get_pool_votes(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        from janus_gate.providers.base import ProviderError

        try:
            return await self.request(
                "GET",
                f"/pools/{pool_id}/votes",
                params={"count": count, "page": page, "order": order},
            )
        except ProviderError as exc:
            # Blockfrost often 404s when a pool has no indexed votes.
            if exc.status_code == 404:
                return []
            raise

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

    async def get_assets(
        self,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            "/assets",
            params={"count": count, "page": page, "order": order},
        )

    async def get_asset(self, asset: str) -> Any:
        return await self.request("GET", f"/assets/{asset}")

    async def get_asset_history(
        self,
        asset: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/assets/{asset}/history",
            params={"count": count, "page": page, "order": order},
        )

    async def get_asset_transactions(
        self,
        asset: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/assets/{asset}/transactions",
            params={"count": count, "page": page, "order": order},
        )

    async def get_asset_addresses(
        self,
        asset: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            f"/assets/{asset}/addresses",
            params={"count": count, "page": page, "order": order},
        )
