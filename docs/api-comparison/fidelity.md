# Client fidelity notes

Light rules so Janus looks closer to a native Blockfrost (or Koios) face. This is not a claim of byte-identical responses.

## Error JSON

Public errors are face-shaped, not FastAPI `{"detail": ...}`.

| Face | Shape |
| --- | --- |
| Blockfrost | `{ "status_code", "error", "message" }` at the top level |
| Koios | `{ "message", "status_code" }` (simple; not full PostgREST) |

Upstream Blockfrost error bodies are unwrapped when already in that shape. Timeouts map to **504**.

## Empty / missing resources

| Case | Behavior |
| --- | --- |
| By-id miss (tx, block, pool, asset, script, datum, DRep, epoch row) | **404** face error (`NotFoundError`) |
| Address info with empty Koios payload | **200** zero-balance stub |
| Account info with empty Koios payload | **200** inactive stub |
| Empty list endpoints (rewards, history, addresses, pool relays) | **200** `[]` |

## Auth response headers

`auth.expose_janus_headers` defaults to **false**. When false, Janus does not set `X-Janus-Auth` / `X-Janus-Auth-Warning` (warnings still go to logs). `/health` still reports auth mapping previews for operators.

## Pagination (known Partial)

- Blockfrost face: `count` / `page` / `order` query params as usual.
- Koios face: `limit` / `offset` / `order`; **non-aligned** `offset` (not a multiple of `limit`) returns **400**.
- Account rewards / history / delegations from Koios still fetch the nested array then slice client-side (see [band2-partial.md](endpoints/band2-partial.md)).

## Tests

```bash
uv sync --group dev
uv run pytest
```
