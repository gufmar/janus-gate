# Product roadmap

Janus Gate is evolving from a Blockfrost↔Koios translator into a **Cardano API face over pluggable backends**, with optional redundancy.

## Phases

### Phase 0 – Reverse face validation

Run Koios face + Blockfrost backend (`config.koios-face.example.yaml`) and Blockfrost face + Koios backend. Confirm bidirectional claim for core routes. Inventory Gaps specific to each direction.

**Status:** operator-validated for core routes; ongoing fidelity work via `scripts/compare_face.py`.

### Phase 1 – Canonical foundation

- Separate **API faces** from **backend sources**.
- Keep `BackendProvider` methods as canonical operations.
- Centralize **face adaptation** (`adapt_to_face`) so new sources register mappers instead of growing registry if-chains.
- Config rules for passthrough and future `dbsync` (DSN), without implementing SQL yet.

**Status:** done.

### Phase 2a – Ops hardening

- `/health` no longer exposes API key previews.
- `auth.debug_log_keys` for masked per-request key logging.
- Optional `access.allowed_ips` with `deny: endpoints | strict`.

**Status:** done.

### Phase 2 – dbSync / PostgreSQL backend

Expose Blockfrost or Koios face by reading cardano-db-sync. MVP: tip, block, genesis/epoch (+ params), address (+ utxos), account basics, tx by hash. Optional SSH tunnel for private Postgres. Submit tx and the rest of the catalog return 501 until extended. See [backends/dbsync.md](backends/dbsync.md).

**Status:** MVP live (both faces); fidelity pass and endpoint expansion in progress.

### Phase 2.5 – Face fidelity (current focus)

Use `scripts/compare_face.py` against native Koios/Blockfrost and a deployed Janus instance. Fix field scale, NULL Gaps, and shape drift **one endpoint at a time** before multi-backend work.

### Phase 3 – Master / slave dual backends

One face, primary + secondary sources. Policies: failover, prefer-fresher tip, shadow compare/log.

### Phase 4 – Consensus backend

Call two sources, normalize, compare selected fields, return face-mapped result only on agreement (or configurable prefer/503).

### Phase 5 – Ogmios / Yaci-Store

Additional `BackendProvider` adapters once the adaptation table and multi-backend router exist. Left last to avoid exploding pairwise face↔face matrices. Also the natural path for submit-tx.

## Non-goals (near term)

- Full OpenAPI parity with commercial Blockfrost/Koios
- Inventing CDN response headers to mimic Cloudflare
- Byte-identical JSON across all sources
