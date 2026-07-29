"""Shared provider HTTP client abstractions."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from janus_gate.auth import get_backend_api_key


class ProviderError(Exception):
    """Raised when an upstream provider call fails."""

    def __init__(self, status_code: int, detail: Any) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Upstream error {status_code}: {detail}")


class BackendProvider(Protocol):
    name: str

    async def get_tip(self) -> Any: ...

    async def get_genesis(self) -> Any: ...

    async def get_epoch(self, number: int | None = None) -> Any: ...

    async def get_epoch_parameters(self, number: int | None = None) -> Any: ...

    async def get_block(self, hash_or_number: str) -> Any: ...

    async def get_address_info(self, address: str) -> Any: ...

    async def get_address_utxos(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any: ...

    async def get_address_transactions(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any: ...

    async def submit_tx(self, cbor: bytes) -> Any: ...

    async def get_tx(self, tx_hash: str) -> Any: ...

    async def get_tx_utxos(self, tx_hash: str) -> Any: ...

    async def get_tx_metadata(self, tx_hash: str) -> Any: ...

    async def get_tx_cbor(self, tx_hash: str) -> Any: ...

    async def get_account_info(self, stake_address: str) -> Any: ...

    async def get_account_rewards(self, stake_address: str) -> Any: ...

    async def get_account_history(self, stake_address: str) -> Any: ...

    async def get_account_addresses(self, stake_address: str) -> Any: ...

    async def get_pools(
        self,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any: ...

    async def get_pools_extended(
        self,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any: ...

    async def get_pool(self, pool_id: str) -> Any: ...

    async def get_pool_history(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any: ...

    async def get_pool_metadata(self, pool_id: str) -> Any: ...

    async def get_pool_delegators(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any: ...

    async def get_pool_relays(self, pool_id: str) -> Any: ...

    async def get_epoch_blocks(
        self,
        number: int,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any: ...

    async def get_committee(self) -> Any: ...

    async def get_dreps(self, *, count: int = 100, page: int = 1) -> Any: ...

    async def get_drep(self, drep_id: str) -> Any: ...

    async def get_proposals(self, *, count: int = 100, page: int = 1) -> Any: ...

    async def get_script(self, script_hash: str) -> Any: ...

    async def get_datum(self, datum_hash: str) -> Any: ...

    async def get_asset(self, asset: str) -> Any: ...

    async def aclose(self) -> None: ...


class HttpProvider:
    """Thin async HTTP helper shared by concrete providers."""

    def __init__(
        self,
        base_url: str,
        *,
        headers: dict[str, str] | None = None,
        auth_header: str | None = None,
        auth_prefix: str = "",
    ) -> None:
        self._auth_header = auth_header
        self._auth_prefix = auth_prefix
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers or {},
            timeout=httpx.Timeout(60.0),
        )

    def _auth_headers(self) -> dict[str, str]:
        if not self._auth_header:
            return {}
        key = get_backend_api_key()
        if not key:
            return {}
        return {self._auth_header: f"{self._auth_prefix}{key}"}

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        merged_headers = self._auth_headers()
        if headers:
            merged_headers.update(headers)
        try:
            response = await self._client.request(
                method,
                path,
                json=json,
                params=params,
                content=content,
                headers=merged_headers or None,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(
                504, {"message": "Upstream timeout", "status_code": 504, "error": "Gateway Timeout"}
            ) from exc
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise ProviderError(response.status_code, detail)
        if response.status_code == 204 or not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        text = response.text.strip()
        if text.startswith("{") or text.startswith("["):
            return response.json()
        # Blockfrost submit returns a quoted tx hash string.
        if text.startswith('"') and text.endswith('"'):
            return json_loads_maybe(text)
        return text

    async def aclose(self) -> None:
        await self._client.aclose()


def json_loads_maybe(text: str) -> Any:
    import json

    return json.loads(text)


def page_to_offset(page: int, count: int) -> int:
    safe_page = max(page, 1)
    safe_count = max(count, 1)
    return (safe_page - 1) * safe_count
