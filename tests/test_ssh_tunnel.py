"""SSH tunnel DSN helpers and config validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from janus_gate.config import (
    AppConfig,
    BackendConfig,
    BackendSource,
    FaceName,
    ServerConfig,
    SshTunnelConfig,
)
from janus_gate.providers import create_backend
from janus_gate.providers.ssh_tunnel import (
    dsn_via_local_tunnel,
    parse_postgres_dsn_host_port,
    start_ssh_tunnel,
)


def test_parse_postgres_dsn_host_port() -> None:
    assert parse_postgres_dsn_host_port(
        "postgresql://u:p@10.0.0.5:5432/cexplorer"
    ) == ("10.0.0.5", 5432)
    assert parse_postgres_dsn_host_port("postgres://u@db.internal/cexplorer") == (
        "db.internal",
        5432,
    )


def test_dsn_via_local_tunnel_preserves_credentials() -> None:
    rewritten = dsn_via_local_tunnel(
        "postgresql://user:s%3Becret@10.0.0.5:5432/cexplorer",
        "127.0.0.1",
        15432,
    )
    assert rewritten.startswith("postgresql://user:s%3Becret@127.0.0.1:15432/")
    assert rewritten.endswith("/cexplorer")


def test_ssh_tunnel_config_requires_credentials() -> None:
    with pytest.raises(ValidationError, match="private_key"):
        SshTunnelConfig(host="bastion", user="deploy")


def test_ssh_tunnel_only_for_dbsync() -> None:
    with pytest.raises(ValidationError, match="only supported"):
        AppConfig(
            server=ServerConfig(host="127.0.0.1", port=8080),
            public_face=FaceName.BLOCKFROST,
            backend=BackendConfig(
                provider=BackendSource.KOIOS,
                base_url="https://example.invalid",
                ssh_tunnel=SshTunnelConfig(
                    host="bastion",
                    user="deploy",
                    private_key_path="/tmp/id_ed25519",
                ),
            ),
        )


def test_create_backend_passes_ssh_tunnel() -> None:
    cfg = AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8080),
        public_face=FaceName.BLOCKFROST,
        backend=BackendConfig(
            provider=BackendSource.DBSYNC,
            dsn="postgresql://u:p@10.0.0.5:5432/cexplorer",
            ssh_tunnel=SshTunnelConfig(
                host="bastion.example.com",
                user="deploy",
                private_key_path="/tmp/id_ed25519",
            ),
        ),
    )
    backend = create_backend(cfg)
    assert backend.name == "dbsync"
    assert backend._ssh_tunnel_cfg is not None  # type: ignore[attr-defined]
    assert backend._ssh_tunnel_cfg.host == "bastion.example.com"  # type: ignore[attr-defined]


def test_start_ssh_tunnel_rewrites_dsn() -> None:
    cfg = SshTunnelConfig(
        host="bastion",
        user="deploy",
        password="secret",
        local_bind_host="127.0.0.1",
        local_bind_port=0,
    )
    fake_tunnel = MagicMock()
    fake_tunnel.local_bind_port = 23456

    with patch(
        "sshtunnel.SSHTunnelForwarder", return_value=fake_tunnel
    ) as forwarder_cls:
        tunnel, rewritten = start_ssh_tunnel(
            dsn="postgresql://dbuser:dbpass@10.1.2.3:5432/cexplorer",
            cfg=cfg,
        )

    assert tunnel is fake_tunnel
    fake_tunnel.start.assert_called_once()
    assert rewritten == "postgresql://dbuser:dbpass@127.0.0.1:23456/cexplorer"
    kwargs = forwarder_cls.call_args.kwargs
    assert kwargs["ssh_address_or_host"] == ("bastion", 22)
    assert kwargs["remote_bind_address"] == ("10.1.2.3", 5432)
    assert kwargs["ssh_password"] == "secret"


def test_encrypted_key_without_passphrase_is_clear() -> None:
    from janus_gate.providers.ssh_tunnel import _load_pkey
    from paramiko.ssh_exception import PasswordRequiredException

    cfg = SshTunnelConfig(
        host="bastion",
        user="deploy",
        private_key_path="/tmp/encrypted_key",
    )

    with patch(
        "paramiko.Ed25519Key.from_private_key_file",
        side_effect=PasswordRequiredException("private key file is encrypted"),
    ):
        with pytest.raises(ValueError, match="encrypted") as exc:
            _load_pkey(cfg)
    assert "JANUS_SSH_PASSPHRASE" in str(exc.value)
