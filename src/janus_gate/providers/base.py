"""Shared provider HTTP client abstractions."""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class ProviderError(Exception):
    """Raised when an upstream provider call fails."""

    def __init__(self, status_code: int, detail: Any) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Upstream error {status_code}: {detail}")


class BackendProvider(Protocol):
    name: str

    async def get_tip(self) -> Any: ...

    async def get_address_info(self, address: str) -> Any: ...

    async def aclose(self) -> None: ...


class HttpProvider:
    """Thin async HTTP helper shared by concrete providers."""

    def __init__(self, base_url: str, headers: dict[str, str] | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers or {},
            timeout=httpx.Timeout(30.0),
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._client.request(method, path, json=json, params=params)
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise ProviderError(response.status_code, detail)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()
