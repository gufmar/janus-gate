# Architecture

## Role

Janus Gate sits between Cardano API clients and one or more data sources. Clients see a familiar public **face** (Blockfrost or Koios HTTP API). Janus fulfills requests through a **backend source** (today: Koios or Blockfrost HTTP; later: cardano-db-sync, Ogmios, Yaci-Store), then adapts payloads into the public face contract.

TLS and edge HTTP concerns belong to nginx (or similar) in front of Janus. The service listens on plain HTTP.

## Layers

```text
Client -> nginx (TLS) -> Face router (BF or Koios paths)
                      -> Registry (canonical BackendProvider ops)
                      -> adapt_to_face (source-shaped JSON -> face JSON)
                      -> BackendProvider (koios | blockfrost | dbsync | ...)
```

1. **Face** – only Blockfrost or Koios routes are mounted (`public_face`).
2. **Canonical operations** – `BackendProvider` methods (`get_tip`, `get_block`, `get_account_info`, …) are the shared vocabulary every source must implement.
3. **Adaptation** – [`mapping/adapt.py`](../src/janus_gate/mapping/adapt.py) dispatches `(face, source, concept)` to mapper functions. Same face and source is identity (passthrough).
4. **Backend** – HTTP clients today; SQL/indexer adapters later. Sources return **source-native** JSON; they do not need to speak the face dialect.

## Configuration

| Field | Role |
| --- | --- |
| `public_face` | API face only: `blockfrost` \| `koios` |
| `backend.provider` | Source: `blockfrost` \| `koios` \| `dbsync` (reserved) \| … |
| `backend.passthrough` | Allow face == API source (explicit same-provider proxy) |
| `backend.base_url` | Required for HTTP API mirrors |
| `backend.dsn` | Required for `dbsync` (Phase 2; factory not implemented yet) |

Rules:

- Two different API mirrors (e.g. BF face + Koios backend) is the usual translate mode.
- Face equals API source only when `passthrough: true`.
- A data source such as `dbsync` may back either face; implementation lands in Phase 2.

Secrets should come from the environment (`JANUS_BACKEND_API_KEY`), not from committed YAML.

## Extending coverage

1. Document the endpoint under `docs/api-comparison/endpoints/`.
2. Classify fields as Compatible, Rename, Convert, or Gap.
3. Implement `BackendProvider` method(s) on each source that should support the op.
4. Register face adapters in `mapping/adapt.py` for each `(face, source, concept)`.
5. Expose the path on the matching face router; wire `fetch_*_as` in `mappers/registry.py`.

## Multi-backend (future)

Phase 3+ will add a `BackendProvider` wrapper (failover / shadow / consensus) in front of two sources. Faces and `adapt_to_face` stay unchanged; only the registry’s backend object becomes a policy router. Compare consensus on **normalized fields**, then adapt to the face once.

## Health and audit

- `GET /` and `GET /health` are Janus-native.
- `GET /endpoints` lists face coverage.
- `GET /audit/start` and `GET /audit/report` bind sessions by client IP or public API key and label traffic against the catalog.

Product phases: [product-roadmap.md](product-roadmap.md).
