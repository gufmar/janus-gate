"""Unit tests for face-shaped errors and NotFound mapping."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from janus_gate.app import create_app
from janus_gate.config import (
    AppConfig,
    AuthConfig,
    BackendConfig,
    ProviderName,
    ServerConfig,
)
from janus_gate.faces.errors import (
    NotFoundError,
    blockfrost_error_body,
    koios_error_body,
    provider_error_response,
)
from janus_gate.mappers.util import first_row
from janus_gate.providers.base import ProviderError


def _config(
    *,
    face: ProviderName = ProviderName.BLOCKFROST,
    expose_headers: bool = False,
) -> AppConfig:
    backend = (
        ProviderName.KOIOS
        if face is ProviderName.BLOCKFROST
        else ProviderName.BLOCKFROST
    )
    return AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080),
        public_face=face,
        backend=BackendConfig(
            provider=backend,
            base_url="https://example.invalid",
        ),
        auth=AuthConfig(expose_janus_headers=expose_headers),
    )


def test_blockfrost_error_body_shape() -> None:
    body = blockfrost_error_body(404, "missing")
    assert body == {
        "status_code": 404,
        "error": "Not Found",
        "message": "missing",
    }


def test_koios_error_body_shape() -> None:
    body = koios_error_body(400, "bad")
    assert body["message"] == "bad"
    assert body["status_code"] == 400


def test_provider_error_unwraps_blockfrost_body() -> None:
    exc = ProviderError(
        404,
        {
            "status_code": 404,
            "error": "Not Found",
            "message": "Transaction not found",
        },
    )
    response = provider_error_response(ProviderName.BLOCKFROST, exc)
    assert response.status_code == 404
    assert response.body  # type: ignore[truthy-function]
    import json

    payload = json.loads(response.body.decode())
    assert payload["message"] == "Transaction not found"
    assert "detail" not in payload


def test_first_row_empty_raises_not_found() -> None:
    with pytest.raises(NotFoundError):
        first_row([], "tx_info")


def test_bf_face_not_found_json_shape() -> None:
    app = create_app(_config())

    @app.get("/_test/missing")
    async def missing() -> None:
        raise NotFoundError("gone")

    with TestClient(app) as client:
        response = client.get("/_test/missing")
    assert response.status_code == 404
    assert response.json() == {
        "status_code": 404,
        "error": "Not Found",
        "message": "gone",
    }
    assert "detail" not in response.json()


def test_janus_auth_headers_hidden_by_default() -> None:
    app = create_app(_config(expose_headers=False))

    @app.get("/_test/ok")
    async def ok() -> dict[str, str]:
        return {"ok": "1"}

    with TestClient(app) as client:
        response = client.get("/_test/ok")
    assert response.status_code == 200
    assert "X-Janus-Auth" not in response.headers
    assert "X-Janus-Auth-Warning" not in response.headers


def test_janus_auth_headers_when_enabled() -> None:
    app = create_app(_config(expose_headers=True))

    @app.get("/_test/ok")
    async def ok() -> dict[str, str]:
        return {"ok": "1"}

    with TestClient(app) as client:
        response = client.get("/_test/ok")
    assert response.headers.get("X-Janus-Auth") == "fallback"
