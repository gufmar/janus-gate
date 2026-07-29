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

                raise ProviderError(
                    404,
                    {
                        "status_code": 404,
                        "error": "Not Found",
                        "message": "Block not found",
                    },
                )
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

    async def _resolve_block_hash(self, hash_or_number: str) -> str:
        if not hash_or_number.isdigit():
            return hash_or_number
        rows = await self.request(
            "GET",
            "/blocks",
            params={"block_height": f"eq.{hash_or_number}", "limit": 1},
        )
        if not isinstance(rows, list) or not rows:
            from janus_gate.providers.base import ProviderError

            raise ProviderError(
                404,
                {
                    "status_code": 404,
                    "error": "Not Found",
                    "message": "Block not found",
                },
            )
        return rows[0]["hash"]

    async def get_block_transactions(
        self,
        hash_or_number: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        block_hash = await self._resolve_block_hash(hash_or_number)
        rows = await self.request(
            "POST",
            "/block_txs",
            json={"_block_hashes": [block_hash]},
        )
        # Koios returns the full set; apply BF-style page/order client-side.
        if not isinstance(rows, list):
            return rows
        ordered = rows if order != "desc" else list(reversed(rows))
        start = max(page - 1, 0) * max(count, 1)
        return ordered[start : start + max(count, 1)]

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

    async def get_tx(self, tx_hash: str) -> Any:
        return await self.request(
            "POST", "/tx_info", json={"_tx_hashes": [tx_hash]}
        )

    async def get_tx_utxos(self, tx_hash: str) -> Any:
        return await self.request(
            "POST", "/tx_utxos", json={"_tx_hashes": [tx_hash]}
        )

    async def get_tx_metadata(self, tx_hash: str) -> Any:
        return await self.request(
            "POST", "/tx_metadata", json={"_tx_hashes": [tx_hash]}
        )

    async def get_tx_cbor(self, tx_hash: str) -> Any:
        return await self.request(
            "POST", "/tx_cbor", json={"_tx_hashes": [tx_hash]}
        )

    async def get_account_info(self, stake_address: str) -> Any:
        return await self.request(
            "POST",
            "/account_info",
            json={"_stake_addresses": [stake_address]},
        )

    async def get_account_rewards(self, stake_address: str) -> Any:
        return await self.request(
            "POST",
            "/account_rewards",
            json={"_stake_addresses": [stake_address]},
        )

    async def get_account_history(self, stake_address: str) -> Any:
        return await self.request(
            "POST",
            "/account_history",
            json={"_stake_addresses": [stake_address]},
        )

    async def get_account_addresses(self, stake_address: str) -> Any:
        return await self.request(
            "POST",
            "/account_addresses",
            json={"_stake_addresses": [stake_address]},
        )

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
            "/account_txs",
            params={
                "_stake_address": stake_address,
                "limit": count,
                "offset": page_to_offset(page, count),
                "order": f"block_height.{'desc' if order == 'desc' else 'asc'}",
            },
        )

    async def get_pools(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.request(
            "GET",
            "/pool_list",
            params={"limit": count, "offset": page_to_offset(page, count)},
        )

    async def get_pools_extended(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.get_pools(count=count, page=page)

    async def get_pool(self, pool_id: str) -> Any:
        return await self.request(
            "POST",
            "/pool_info",
            json={"_pool_bech32_ids": [pool_id]},
        )

    async def get_pool_history(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        params: dict[str, Any] = {
            "_pool_bech32": pool_id,
            "limit": count,
            "offset": page_to_offset(page, count),
            "order": f"epoch_no.{'desc' if order == 'desc' else 'asc'}",
        }
        return await self.request("GET", "/pool_history", params=params)

    async def get_pool_metadata(self, pool_id: str) -> Any:
        return await self.request(
            "POST",
            "/pool_metadata",
            json={"_pool_bech32_ids": [pool_id]},
        )

    async def get_pool_delegators(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self.request(
            "GET",
            "/pool_delegators",
            params={
                "_pool_bech32": pool_id,
                "limit": count,
                "offset": page_to_offset(page, count),
            },
        )

    async def get_pool_relays(self, pool_id: str) -> Any:
        rows = await self.request(
            "GET",
            "/pool_relays",
            params={"pool_id_bech32": f"eq.{pool_id}"},
        )
        if isinstance(rows, list) and rows:
            return rows
        # Fallback: relays are also present on pool_info.
        info = await self.get_pool(pool_id)
        if isinstance(info, list) and info and isinstance(info[0], dict):
            return [
                {
                    "pool_id_bech32": info[0].get("pool_id_bech32") or pool_id,
                    "relays": info[0].get("relays") or [],
                }
            ]
        return []

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
            "/blocks",
            params={
                "epoch_no": f"eq.{number}",
                "limit": count,
                "offset": page_to_offset(page, count),
                "order": f"block_height.{'desc' if order == 'desc' else 'asc'}",
            },
        )

    async def get_committee(self) -> Any:
        return await self.request("GET", "/committee_info")

    async def get_dreps(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.request(
            "GET",
            "/drep_list",
            params={"limit": count, "offset": page_to_offset(page, count)},
        )

    async def get_drep(self, drep_id: str) -> Any:
        return await self.request(
            "POST",
            "/drep_info",
            json={"_drep_ids": [drep_id]},
        )

    async def get_proposals(self, *, count: int = 100, page: int = 1) -> Any:
        return await self.request(
            "GET",
            "/proposal_list",
            params={"limit": count, "offset": page_to_offset(page, count)},
        )

    async def get_script(self, script_hash: str) -> Any:
        return await self.request(
            "POST",
            "/script_info",
            json={"_script_hashes": [script_hash]},
        )

    async def get_datum(self, datum_hash: str) -> Any:
        return await self.request(
            "POST",
            "/datum_info",
            json={"_datum_hashes": [datum_hash]},
        )

    async def get_metadata_labels(
        self,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        return await self.request(
            "GET",
            "/tx_metalabels",
            params={
                "limit": count,
                "offset": page_to_offset(page, count),
                "order": f"key.{'desc' if order == 'desc' else 'asc'}",
            },
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
            "/tx_by_metalabel",
            params={
                "_label": label,
                "limit": count,
                "offset": page_to_offset(page, count),
                "order": f"block_height.{'desc' if order == 'desc' else 'asc'}",
            },
        )

    async def get_asset(self, asset: str) -> Any:
        if len(asset) < 56:
            from janus_gate.providers.base import ProviderError

            raise ProviderError(
                400,
                {
                    "status_code": 400,
                    "error": "Bad Request",
                    "message": "Invalid asset id",
                },
            )
        policy_id, asset_name = asset[:56], asset[56:]
        return await self.request(
            "POST",
            "/asset_info",
            json={"_asset_list": [[policy_id, asset_name]]},
        )
