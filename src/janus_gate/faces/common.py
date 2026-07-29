"""Shared FastAPI helpers for public faces."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar

from fastapi import HTTPException

from janus_gate.providers.base import ProviderError

T = TypeVar("T")


async def run_upstream(coro: Awaitable[T]) -> T:
    try:
        return await coro
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def pagination_params(
    count: int | None = None,
    page: int | None = None,
    order: str | None = None,
) -> dict[str, Any]:
    return {
        "count": count if count is not None else 100,
        "page": page if page is not None else 1,
        "order": order if order in {"asc", "desc"} else "asc",
    }
