"""Health payload, auth debug logging, and IP allowlist."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from janus_gate.access import ip_is_allowed
from janus_gate.app import create_app
from janus_gate.auth import auth_health_payload, mask_api_key
from janus_gate.config import (
    AccessConfig,
    AccessDenyMode,
    AppConfig,
    AuthConfig,
    BackendConfig,
    BackendSource,
    FaceName,
    KeyMapping,
    ServerConfig,
)


def _config(
    *,
    access: AccessConfig | None = None,
    auth: AuthConfig | None = None,
) -> AppConfig:
    return AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080),
        public_face=FaceName.BLOCKFROST,
        backend=BackendConfig(
            provider=BackendSource.KOIOS,
            base_url="https://example.invalid",
        ),
        auth=auth
        or AuthConfig(
            key_map=[
                KeyMapping(
                    label="tenant-a",
                    public_key="public-key-abcdefghij",
                    backend_key="backend-key-klmnopqrst",
                )
            ],
            fallback_backend_key="fallback-key-uvwxyz0123",
        ),
        access=access or AccessConfig(),
    )


def test_auth_health_payload_has_no_key_material() -> None:
    payload = auth_health_payload(_config().auth)
    assert payload == {
        "key_map_count": 1,
        "has_fallback_backend_key": True,
        "expose_janus_headers": False,
        "debug_log_keys": False,
    }
    blob = str(payload)
    assert "public-key" not in blob
    assert "backend-key" not in blob
    assert "fallback-key" not in blob
    assert "preview" not in blob


def test_health_endpoint_omits_key_previews() -> None:
    with TestClient(create_app(_config())) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    auth = resp.json()["auth"]
    assert auth["key_map_count"] == 1
    assert auth["has_fallback_backend_key"] is True
    assert "mappings" not in auth
    assert "fallback_backend_key_preview" not in auth
    assert "public_key_preview" not in str(resp.json())


def test_debug_log_keys_emits_masked_line(caplog: pytest.LogCaptureFixture) -> None:
    cfg = _config(auth=AuthConfig(debug_log_keys=True, key_map=[]))
    app = create_app(cfg)

    @app.get("/_test/ok")
    async def ok() -> dict[str, str]:
        return {"ok": "1"}

    with caplog.at_level(logging.INFO, logger="janus_gate.auth"):
        with TestClient(app) as client:
            client.get("/_test/ok", headers={"project_id": "public-key-abcdefghij"})

    assert any("auth keys" in record.message for record in caplog.records)
    joined = " ".join(r.message for r in caplog.records)
    assert "public-key-abcdefghij" not in joined
    assert mask_api_key("public-key-abcdefghij") in joined


def test_ip_is_allowed_exact_and_cidr() -> None:
    assert ip_is_allowed("203.0.113.10", ["203.0.113.10"])
    assert not ip_is_allowed("203.0.113.11", ["203.0.113.10"])
    assert ip_is_allowed("10.1.2.3", ["10.0.0.0/8"])
    assert not ip_is_allowed("11.0.0.1", ["10.0.0.0/8"])
    assert ip_is_allowed("any", []) is True


def test_access_endpoints_mode_blocks_face_keeps_home_health() -> None:
    cfg = _config(
        access=AccessConfig(
            allowed_ips=["203.0.113.10"],
            deny=AccessDenyMode.ENDPOINTS,
            trusted_proxy_hops=1,
        )
    )
    app = create_app(cfg)

    @app.get("/_test/face")
    async def face_probe() -> dict[str, str]:
        return {"ok": "1"}

    with TestClient(app) as client:
        denied = client.get(
            "/_test/face", headers={"X-Real-IP": "198.51.100.1"}
        )
        assert denied.status_code == 403
        assert denied.json()["error"] == "Forbidden"

        home = client.get("/", headers={"X-Real-IP": "198.51.100.1"})
        assert home.status_code == 200

        health = client.get("/health", headers={"X-Real-IP": "198.51.100.1"})
        assert health.status_code == 200

        endpoints = client.get("/endpoints", headers={"X-Real-IP": "198.51.100.1"})
        assert endpoints.status_code == 200

        openapi = client.get(
            "/openapi.json", headers={"X-Real-IP": "198.51.100.1"}
        )
        assert openapi.status_code == 200

        audit = client.get(
            "/audit/start", headers={"X-Real-IP": "198.51.100.1"}
        )
        assert audit.status_code == 403

        allowed = client.get(
            "/_test/face", headers={"X-Real-IP": "203.0.113.10"}
        )
        assert allowed.status_code == 200


def test_access_strict_mode_blocks_home_and_health() -> None:
    cfg = _config(
        access=AccessConfig(
            allowed_ips=["203.0.113.10"],
            deny=AccessDenyMode.STRICT,
            trusted_proxy_hops=1,
        )
    )
    with TestClient(create_app(cfg)) as client:
        assert (
            client.get("/", headers={"X-Real-IP": "198.51.100.1"}).status_code
            == 403
        )
        assert (
            client.get("/health", headers={"X-Real-IP": "198.51.100.1"}).status_code
            == 403
        )
        assert (
            client.get("/", headers={"X-Real-IP": "203.0.113.10"}).status_code
            == 200
        )


def test_access_empty_allowlist_is_noop() -> None:
    cfg = _config(access=AccessConfig(allowed_ips=[], deny=AccessDenyMode.STRICT))
    with TestClient(create_app(cfg)) as client:
        assert client.get("/health").status_code == 200
