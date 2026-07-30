"""Tests for compatibility audit binding, anonymization, and reports."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from janus_gate.app import create_app
from janus_gate.audit import (
    AuditBindKind,
    AuditLabel,
    AuditStore,
    anonymize_path,
    anonymize_query,
    client_ip_from_request,
    label_event,
    match_catalog_entry,
)
from janus_gate.catalog import EndpointEntry
from janus_gate.config import (
    AppConfig,
    AuditConfig,
    AuthConfig,
    BackendConfig,
    ProviderName,
    ServerConfig,
)


def _config(*, base_path: str = "", **audit_kwargs: object) -> AppConfig:
    return AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080, base_path=base_path),
        public_face=ProviderName.BLOCKFROST,
        backend=BackendConfig(
            provider=ProviderName.KOIOS,
            base_url="https://example.invalid",
        ),
        auth=AuthConfig(),
        audit=AuditConfig(**audit_kwargs),  # type: ignore[arg-type]
    )


def test_anonymize_stake_and_address_segments() -> None:
    path = (
        "/accounts/stake1u9ylzsgxaa6x6m4kfx7p8zqexampletoolongtoleak/"
        "rewards"
    )
    out = anonymize_path(path)
    assert "stake1..." in out or out.startswith("/accounts/stake")
    assert "sgxaa6x6m4kfx7p8zqexampletoolongtoleak" not in out
    assert out.endswith("/rewards")


def test_anonymize_hex_hash() -> None:
    tx = "a" * 64
    out = anonymize_path(f"/txs/{tx}")
    assert out == f"/txs/{tx[:5]}..."


def test_anonymize_query_values() -> None:
    stake = "stake1u9ylzsgxaa6x6m4kfx7p8zqexampletoolong"
    out = anonymize_query(f"_stake_address={stake}&limit=10")
    assert "limit=10" in out
    assert stake not in out
    assert "_stake_address=stake" in out


def test_client_ip_prefers_x_real_ip() -> None:
    request = MagicMock()
    request.headers = {
        "x-real-ip": "203.0.113.10",
        "x-forwarded-for": "198.51.100.1, 203.0.113.10",
    }
    request.client = MagicMock(host="127.0.0.1")
    assert client_ip_from_request(request, trusted_proxy_hops=1) == "203.0.113.10"


def test_client_ip_uses_leftmost_xff() -> None:
    request = MagicMock()
    request.headers = {"x-forwarded-for": "198.51.100.7, 10.0.0.1"}
    request.client = MagicMock(host="127.0.0.1")
    assert client_ip_from_request(request, trusted_proxy_hops=1) == "198.51.100.7"


def test_client_ip_ignores_xff_when_hops_zero() -> None:
    request = MagicMock()
    request.headers = {"x-forwarded-for": "198.51.100.7"}
    request.client = MagicMock(host="127.0.0.1")
    assert client_ip_from_request(request, trusted_proxy_hops=0) == "127.0.0.1"


def test_match_catalog_and_labels() -> None:
    entry = match_catalog_entry("GET", "/blocks/latest", ProviderName.BLOCKFROST)
    assert entry is not None
    assert entry.implemented is True
    label, _ = label_event(status_code=200, entry=entry)
    assert label is AuditLabel.OK

    planned = EndpointEntry(
        "GET",
        "/network",
        "Network information",
        "Network / blocks",
        implemented=False,
    )
    label, desc = label_event(status_code=404, entry=planned)
    assert label is AuditLabel.FAIL
    assert "not implemented" in desc.lower()

    label, _ = label_event(status_code=404, entry=None)
    assert label is AuditLabel.UNKNOWN


def test_audit_start_page_and_ip_session() -> None:
    with TestClient(create_app(_config())) as client:
        page = client.get("/audit/start")
        assert page.status_code == 200
        assert "Compatibility audit" in page.text
        assert "myIP" in page.text

        started = client.get(
            "/audit/start",
            params={"sessionID": "myIP", "format": "json"},
            headers={"X-Forwarded-For": "203.0.113.50"},
        )
        assert started.status_code == 200
        body = started.json()
        assert body["bind_kind"] == AuditBindKind.IP.value
        assert body["session_id_display"] == "203.0.113.50"

        # Face 404 for unimplemented catalog route should be recorded as fail.
        hit = client.get(
            "/network",
            headers={"X-Forwarded-For": "203.0.113.50"},
        )
        assert hit.status_code == 404

        report = client.get(
            "/audit/report",
            params={"format": "json"},
            headers={"X-Forwarded-For": "203.0.113.50"},
        )
        assert report.status_code == 200
        payload = report.json()
        assert payload["counts"]["fail"] >= 1
        assert any(e["path"] == "/network" for e in payload["events"])


def test_audit_bind_by_api_key() -> None:
    with TestClient(create_app(_config())) as client:
        key = "mainnetTestProjectKeyForAudit"
        started = client.get(
            "/audit/start",
            params={"sessionID": key, "format": "json"},
        )
        assert started.status_code == 200
        assert started.json()["bind_kind"] == AuditBindKind.API_KEY.value

        # Unimplemented catalog path: still recorded against the key bind.
        client.get("/network", headers={"project_id": key})
        # Different key must not land in this session.
        client.get("/network", headers={"project_id": "otherKey"})

        report = client.get(
            "/audit/report",
            params={"sessionID": key, "format": "json"},
        )
        assert report.status_code == 200
        events = report.json()["events"]
        assert len(events) == 1
        assert events[0]["path"] == "/network"
        assert events[0]["label"] == AuditLabel.FAIL.value


def test_audit_skips_health_and_audit_paths() -> None:
    with TestClient(create_app(_config())) as client:
        client.get(
            "/audit/start",
            params={"sessionID": "myIP", "format": "json"},
            headers={"X-Real-IP": "198.51.100.9"},
        )
        client.get("/health", headers={"X-Real-IP": "198.51.100.9"})
        client.get("/audit/report", headers={"X-Real-IP": "198.51.100.9"})
        report = client.get(
            "/audit/report",
            params={"format": "json"},
            headers={"X-Real-IP": "198.51.100.9"},
        )
        assert report.status_code == 200
        assert report.json()["events"] == []


def test_audit_disabled() -> None:
    with TestClient(create_app(_config(enabled=False))) as client:
        resp = client.get(
            "/audit/start",
            params={"sessionID": "myIP", "format": "json"},
        )
        assert resp.status_code == 400
        assert "disabled" in resp.json()["error"].lower()


def test_audit_store_replaces_session() -> None:
    store = AuditStore(ttl_seconds=3600, max_events=10)
    first = store.start(session_id="1.2.3.4", bind_kind=AuditBindKind.IP)
    second = store.start(session_id="1.2.3.4", bind_kind=AuditBindKind.IP)
    assert store.get("1.2.3.4") is second
    assert first is not second


def test_audit_matches_catalog_with_base_path() -> None:
    """request.url.path includes root_path; catalog matching must use scope path."""
    with TestClient(create_app(_config(base_path="/janus"))) as client:
        started = client.get(
            "/audit/start",
            params={"sessionID": "myIP", "format": "json"},
            headers={"X-Real-IP": "203.0.113.77"},
        )
        assert started.status_code == 200
        # url.path may be /janus/... while the route is still /network
        assert client.get(
            "/network",
            headers={"X-Real-IP": "203.0.113.77"},
        ).status_code == 404

        report = client.get(
            "/audit/report",
            params={"format": "json"},
            headers={"X-Real-IP": "203.0.113.77"},
        )
        assert report.status_code == 200
        events = report.json()["events"]
        assert len(events) == 1
        assert events[0]["path"] == "/network"
        assert events[0]["label"] == AuditLabel.FAIL.value
        assert "not implemented" in events[0]["description"].lower()
        assert not any(e["path"].startswith("/janus") for e in events)
        assert not any("/audit/" in e["path"] for e in events)
