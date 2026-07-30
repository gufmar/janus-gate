# dbSync backend

Phase 2 adds `backend.provider: dbsync` so a Blockfrost face can read a local [cardano-db-sync](https://github.com/IntersectMBO/cardano-db-sync) PostgreSQL database (networks where public BF/Koios are unavailable or undesired).

## Config

```yaml
public_face: blockfrost
backend:
  provider: dbsync
  dsn: postgresql://user:pass@10.0.0.5:5432/cexplorer
```

Or set `JANUS_BACKEND_DSN`. See `config.dbsync.example.yaml`.

Assumes the **official** db-sync public schema (with `address` on `tx_out`, not the `use_address_table` variant).

### Optional SSH tunnel

When Postgres is only reachable through a jump host, configure `backend.ssh_tunnel`. Janus opens a local port-forward before creating the asyncpg pool, and closes it on shutdown.

```yaml
backend:
  provider: dbsync
  # Host/port here are as seen *from the SSH jump host* (often a private IP).
  dsn: postgresql://dbsync_user:SECRET@10.0.0.5:5432/cexplorer
  ssh_tunnel:
    enabled: true
    host: bastion.example.com
    port: 22
    user: deploy
    private_key_path: /path/to/id_ed25519
    # passphrase: optional key passphrase
    # password: optional SSH password (prefer keys)
    # remote_bind_host / remote_bind_port: override DSN target if needed
    # local_bind_port: 0   # 0 = ephemeral
```

Environment overrides (optional): `JANUS_SSH_TUNNEL`, `JANUS_SSH_HOST`, `JANUS_SSH_PORT`, `JANUS_SSH_USER`, `JANUS_SSH_PRIVATE_KEY_PATH`, `JANUS_SSH_PRIVATE_KEY` (PEM contents), `JANUS_SSH_PASSWORD`, `JANUS_SSH_PASSPHRASE`, `JANUS_SSH_REMOTE_BIND_HOST`, `JANUS_SSH_REMOTE_BIND_PORT`.

If the private key is encrypted (OpenSSH asks for a passphrase), you **must** set `ssh_tunnel.passphrase` or `JANUS_SSH_PASSPHRASE`. Startup fails with a clear error otherwise.

On successful startup Janus logs `dbsync connection ok` with `network` (from `meta`) and `tip_height` (from `block`). Prefer an unencrypted deploy-only key when you do not want a passphrase in config/env.

Do not commit private keys or passwords. An OS-level or infra SSH tunnel remains valid; leave `ssh_tunnel` unset and point `dsn` at `127.0.0.1` in that case.

## MVP coverage (Blockfrost face)

| Concept | Route | Status |
| --- | --- | --- |
| Tip | `GET /blocks/latest` | Implemented |
| Block | `GET /blocks/{hash_or_number}` | Implemented |
| Genesis | `GET /genesis` | Partial (meta + network defaults) |
| Epoch | `GET /epochs/latest`, `/epochs/{n}` | Implemented |
| Epoch params | `GET /epochs/.../parameters` | Implemented |
| Address | `GET /addresses/{address}` | Implemented |
| Address UTxOs | `GET /addresses/{address}/utxos` | Implemented |
| Account | `GET /accounts/{stake}` | Implemented (basic) |
| Transaction | `GET /txs/{hash}` | Implemented (core fields) |
| Submit tx | `POST /tx/submit` | Gap (501) |
| Other catalog routes | pools, governance, … | Gap (501) |

Unimplemented ops return HTTP **501** with a clear message. Koios-face adapters for dbsync are not registered yet.

## Notes

- Genesis fills protocol constants from `meta.network_name` (mainnet / preprod / preview) plus `meta.start_time`.
- UTxO “unspent” uses `LEFT JOIN tx_in` (works when `consumed_by_tx_id` is not populated).
- Submit remains a Gap until a node/Ogmios path exists.
