# API comparison overview

This folder compares Blockfrost and Koios endpoints so Janus Gate can grow coverage deliberately.

## Compatibility classes

| Class | Meaning |
| --- | --- |
| **Compatible** | Same meaning and usable shape with little or no change |
| **Rename** | Same data, different field names |
| **Convert** | Needs transformation (units, nesting, HTTP method, array wrapping) |
| **Gap** | Not available on one side, or not safely mappable yet |

## Full coverage map

For every published route on both providers, including **BF-only** / **Koios-only** gaps and suggested Janus priority bands, see [endpoint-catalog.md](endpoint-catalog.md).

## PoC matrix

| Concept | Blockfrost | Koios | Dominant classes | Notes |
| --- | --- | --- | --- | --- |
| Network tip | `GET /blocks/latest` | `GET /tip` | Rename, Convert, Gap | See [network-tip.md](endpoints/network-tip.md) |
| Address info | `GET /addresses/{address}` | `POST /address_info` | Rename, Convert, Gap | See [address-info.md](endpoints/address-info.md) |

## Auth headers

| Provider | Typical auth |
| --- | --- |
| Blockfrost | `project_id: <api_key>` request header |
| Koios | Optional `Authorization: Bearer <token>` (tier-dependent) |

## How to add an endpoint

1. Capture request/response examples from both official OpenAPI specs.
2. Fill a field table using the four classes above.
3. Implement mappers and face routes.
4. Link the new doc from this overview matrix.

## Sources

- Blockfrost OpenAPI: https://github.com/blockfrost/openapi
- Koios OpenAPI artifacts: https://github.com/cardano-community/koios-artifacts
