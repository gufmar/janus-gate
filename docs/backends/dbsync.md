# dbSync backend

Phase 2 adds `backend.provider: dbsync` so a Blockfrost face can read a local [cardano-db-sync](https://github.com/IntersectMBO/cardano-db-sync) PostgreSQL database (networks where public BF/Koios are unavailable or undesired).

## Config

```yaml
public_face: blockfrost
backend:
  provider: dbsync
  dsn: postgresql://user:pass@127.0.0.1:5432/cexplorer
```

Or set `JANUS_BACKEND_DSN`. See `config.dbsync.example.yaml`.

Assumes the **official** db-sync public schema (with `address` on `tx_out`, not the `use_address_table` variant).

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
