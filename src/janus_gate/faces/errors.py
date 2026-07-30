"""Face-aware error types and JSON response builders."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from janus_gate.config import ProviderName
from janus_gate.providers.base import ProviderError

_BF_ERROR_NAMES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    418: "I'm a teapot",
    425: "Too Early",
    429: "Too Many Requests",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}


class NotFoundError(Exception):
    """Resource missing on the upstream / after mapping."""

    def __init__(self, message: str = "The requested component has not been found.") -> None:
        self.message = message
        super().__init__(message)


class BadRequestError(Exception):
    """Client-facing 400 without FastAPI detail wrapping."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class MappingError(Exception):
    """Mapper / shape failure that should surface as 502."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def blockfrost_error_body(
    status_code: int,
    message: str,
    *,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "status_code": status_code,
        "error": error or _BF_ERROR_NAMES.get(status_code, "Error"),
        "message": message,
    }


def blockfrost_error(
    status_code: int,
    message: str,
    *,
    error: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=blockfrost_error_body(status_code, message, error=error),
    )


def koios_error_body(status_code: int, message: str) -> dict[str, Any]:
    return {"message": message, "status_code": status_code}


def koios_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=koios_error_body(status_code, message),
    )


def face_error(
    face: ProviderName,
    status_code: int,
    message: str,
    *,
    error: str | None = None,
) -> JSONResponse:
    if face is ProviderName.BLOCKFROST:
        return blockfrost_error(status_code, message, error=error)
    return koios_error(status_code, message)


def _message_from_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        for key in ("message", "msg", "error", "detail"):
            value = detail.get(key)
            if isinstance(value, str) and value:
                return value
        return str(detail)
    if isinstance(detail, list):
        return str(detail)
    return str(detail) if detail is not None else "Error"


def _looks_like_blockfrost_body(detail: Any) -> bool:
    return (
        isinstance(detail, dict)
        and "status_code" in detail
        and "message" in detail
        and ("error" in detail or "status_code" in detail)
    )


def provider_error_response(face: ProviderName, exc: ProviderError) -> JSONResponse:
    detail = exc.detail
    if face is ProviderName.BLOCKFROST:
        if _looks_like_blockfrost_body(detail):
            body = dict(detail)
            body.setdefault("status_code", exc.status_code)
            body.setdefault("error", _BF_ERROR_NAMES.get(exc.status_code, "Error"))
            body.setdefault("message", _message_from_detail(detail))
            return JSONResponse(status_code=exc.status_code, content=body)
        return blockfrost_error(exc.status_code, _message_from_detail(detail))
    if isinstance(detail, dict):
        body = dict(detail)
        body.setdefault("status_code", exc.status_code)
        body.setdefault("message", _message_from_detail(detail))
        return JSONResponse(status_code=exc.status_code, content=body)
    return koios_error(exc.status_code, _message_from_detail(detail))


def register_face_exception_handlers(app: FastAPI, face: ProviderName) -> None:
    @app.exception_handler(ProviderError)
    async def _provider_error(_request: Request, exc: ProviderError) -> JSONResponse:
        return provider_error_response(face, exc)

    @app.exception_handler(NotFoundError)
    async def _not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
        return face_error(face, 404, exc.message)

    @app.exception_handler(BadRequestError)
    async def _bad_request(_request: Request, exc: BadRequestError) -> JSONResponse:
        return face_error(face, 400, exc.message)

    @app.exception_handler(MappingError)
    async def _mapping(_request: Request, exc: MappingError) -> JSONResponse:
        return face_error(face, 502, exc.message)

    @app.exception_handler(HTTPException)
    async def _http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        return face_error(face, exc.status_code, _message_from_detail(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return face_error(face, 422, _message_from_detail(exc.errors()))

    @app.exception_handler(ValueError)
    async def _value_error(_request: Request, exc: ValueError) -> JSONResponse:
        return face_error(face, 502, str(exc))
