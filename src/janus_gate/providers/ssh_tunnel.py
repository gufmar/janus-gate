"""Optional SSH local port-forward helpers for dbsync Postgres access."""

from __future__ import annotations

import io
import logging
from typing import Any
from urllib.parse import quote, unquote, urlparse, urlunparse

from janus_gate.config import SshTunnelConfig

logger = logging.getLogger("janus_gate.ssh_tunnel")


def parse_postgres_dsn_host_port(dsn: str) -> tuple[str, int]:
    """Return (host, port) from a postgresql:// DSN."""
    parsed = urlparse(dsn)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError(
            f"Unsupported dbsync DSN scheme {parsed.scheme!r}; "
            "expected postgresql:// or postgres://"
        )
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    return host, port


def dsn_via_local_tunnel(dsn: str, local_host: str, local_port: int) -> str:
    """Rewrite DSN host/port to the local SSH tunnel bind address."""
    parsed = urlparse(dsn)
    username = parsed.username
    password = parsed.password
    userinfo = ""
    if username is not None:
        userinfo = quote(unquote(username), safe="")
        if password is not None:
            userinfo = f"{userinfo}:{quote(unquote(password), safe='')}@"
        else:
            userinfo = f"{userinfo}@"
    netloc = f"{userinfo}{local_host}:{local_port}"
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def _load_pkey(cfg: SshTunnelConfig) -> Any | None:
    """Load a Paramiko key object from path or inline PEM, if configured."""
    if not cfg.private_key_path and not cfg.private_key:
        return None

    # Import lazily so API-mirror deployments need not load Paramiko until used.
    import paramiko

    passphrase = cfg.passphrase
    loaders = (
        paramiko.Ed25519Key,
        paramiko.RSAKey,
        paramiko.ECDSAKey,
    )

    def _from_file(path: str) -> Any:
        last_exc: Exception | None = None
        for cls in loaders:
            try:
                return cls.from_private_key_file(path, password=passphrase)
            except Exception as exc:  # noqa: BLE001 - try next key type
                last_exc = exc
        raise ValueError(f"Could not load SSH private key from {path}") from last_exc

    def _from_pem(pem: str) -> Any:
        last_exc: Exception | None = None
        for cls in loaders:
            try:
                return cls.from_private_key(io.StringIO(pem), password=passphrase)
            except Exception as exc:  # noqa: BLE001 - try next key type
                last_exc = exc
        raise ValueError("Could not load SSH private key from private_key PEM") from last_exc

    if cfg.private_key_path:
        return _from_file(cfg.private_key_path)
    assert cfg.private_key is not None
    return _from_pem(cfg.private_key)


def start_ssh_tunnel(
    *,
    dsn: str,
    cfg: SshTunnelConfig,
) -> tuple[Any, str]:
    """Start an SSH local forward and return (tunnel, rewritten_dsn).

    The returned tunnel object must be stopped by the caller (``tunnel.stop()``).
    """
    from sshtunnel import SSHTunnelForwarder

    dsn_host, dsn_port = parse_postgres_dsn_host_port(dsn)
    remote_host = cfg.remote_bind_host or dsn_host
    remote_port = cfg.remote_bind_port or dsn_port
    pkey = _load_pkey(cfg)

    kwargs: dict[str, Any] = {
        "ssh_address_or_host": (cfg.host, cfg.port),
        "ssh_username": cfg.user,
        "remote_bind_address": (remote_host, remote_port),
        "local_bind_address": (cfg.local_bind_host, cfg.local_bind_port),
    }
    if pkey is not None:
        kwargs["ssh_pkey"] = pkey
    if cfg.password:
        kwargs["ssh_password"] = cfg.password

    tunnel = SSHTunnelForwarder(**kwargs)
    tunnel.start()
    local_port = tunnel.local_bind_port
    local_host = cfg.local_bind_host
    rewritten = dsn_via_local_tunnel(dsn, local_host, local_port)
    logger.info(
        "SSH tunnel up: %s@%s:%s -> %s:%s via %s:%s",
        cfg.user,
        cfg.host,
        cfg.port,
        remote_host,
        remote_port,
        local_host,
        local_port,
    )
    return tunnel, rewritten


def stop_ssh_tunnel(tunnel: Any) -> None:
    if tunnel is None:
        return
    try:
        tunnel.stop()
    except Exception:  # noqa: BLE001 - best-effort shutdown
        logger.exception("Error while stopping SSH tunnel")
