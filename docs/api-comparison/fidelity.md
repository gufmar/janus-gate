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

## Deferred: HTTP response headers (low priority)

Janus currently speaks plain Uvicorn/FastAPI at the HTTP layer. Clients can still spot that; for example the response often includes:

```http
Server: uvicorn
```

Native Blockfrost (and often Koios) sit behind a CDN/proxy and expose a different header set (`Server`, rate-limit headers, cache/CDN headers, etc.). Exact lists change over time.

**Later step (not in the light fidelity pass):**

1. Capture a real Blockfrost (and optionally Koios) response to a simple GET (e.g. `/blocks/latest` / `/tip`), including status line and all response headers.
2. Diff against a Janus face response for the same conceptual route.
3. Decide what to imitate in-app (e.g. suppress or rewrite `Server`) vs what nginx/CDN should own in front of Janus.
4. Prefer not inventing fake CDN headers unless a concrete client depends on them.

Until then, treat header mimicry as a known Gap below error-body / 404 fidelity.

## Tests

```bash
uv sync --group dev
uv run pytest
```
