"""Homepage and Janus-native HTML pages."""

from __future__ import annotations

from fastapi.testclient import TestClient

from janus_gate.app import create_app
from janus_gate.config import (
    AppConfig,
    AuthConfig,
    BackendConfig,
    ProviderName,
    ServerConfig,
)


def _config(*, base_path: str = "") -> AppConfig:
    return AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080, base_path=base_path),
        public_face=ProviderName.BLOCKFROST,
        backend=BackendConfig(
            provider=ProviderName.KOIOS,
            base_url="https://example.invalid",
        ),
        auth=AuthConfig(),
    )


def test_home_page_links() -> None:
    with TestClient(create_app(_config())) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Janus Gate" in resp.text
    assert 'href="/endpoints"' in resp.text
    assert 'href="/audit/start"' in resp.text
    assert 'href="/health"' in resp.text


def test_home_page_respects_base_path() -> None:
    with TestClient(create_app(_config(base_path="/janus"))) as client:
        resp = client.get("/janus/")
    assert resp.status_code == 200
    assert 'href="/janus/endpoints"' in resp.text
    assert 'href="/janus/audit/start"' in resp.text
    assert 'href="/janus/health"' in resp.text
