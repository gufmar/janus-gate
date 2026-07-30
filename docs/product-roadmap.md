# Product roadmap

Janus Gate is evolving from a Blockfrost↔Koios translator into a **Cardano API face over pluggable backends**, with optional redundancy.

## Phases

### Phase 0 – Reverse face validation

Run Koios face + Blockfrost backend (`config.koios-face.example.yaml`). Confirm bidirectional claim for core routes. Inventory Gaps specific to that direction.

**Status:** started / in progress with operators.

### Phase 1 – Canonical foundation (this work)

- Separate **API faces** from **backend sources**.
- Keep `BackendProvider` methods as canonical operations.
- Centralize **face adaptation** (`adapt_to_face`) so new sources register mappers instead of growing registry if-chains.
- Config rules for passthrough and future `dbsync` (DSN), without implementing SQL yet.

**Status:** done.

### Phase 2 – dbSync / PostgreSQL backend

Expose a basic Blockfrost face by reading local cardano-db-sync. MVP: tip, block, genesis/epoch (+ params), address (+ utxos), account basics, tx by hash. Submit tx and the rest of the catalog return 501 until extended. See [backends/dbsync.md](backends/dbsync.md).

**Status:** MVP implemented (Blockfrost face).

### Phase 3 – Master / slave dual backends

One face, primary + secondary sources. Policies: failover, prefer-fresher tip, shadow compare/log.

### Phase 4 – Consensus backend

Call two sources, normalize, compare selected fields, return face-mapped result only on agreement (or configurable prefer/503).

### Phase 5 – Ogmios / Yaci-Store

Additional `BackendProvider` adapters once the adaptation table and multi-backend router exist. Left last to avoid exploding pairwise face↔face matrices.

## Non-goals (near term)

- Full OpenAPI parity with commercial Blockfrost/Koios
- Inventing CDN response headers to mimic Cloudflare
- Byte-identical JSON across all sources
