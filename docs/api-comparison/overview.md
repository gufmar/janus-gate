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
| Network tip | `GET /blocks/latest` | `GET /tip` | Rename, Convert, Gap | [network-tip.md](endpoints/network-tip.md) |
| Block by id | `GET /blocks/{hash_or_number}` | `POST /block_info` | Rename, Convert | [block-info.md](endpoints/block-info.md) |
| Genesis | `GET /genesis` | `GET /genesis` | Rename, Convert | [genesis.md](endpoints/genesis.md) |
| Epoch info / params | `/epochs/...` | `/epoch_info`, `/epoch_params` | Rename, Convert | [epochs.md](endpoints/epochs.md) |
| Address info | `GET /addresses/{address}` | `POST /address_info` | Rename, Convert, Gap | [address-info.md](endpoints/address-info.md) |
| Address UTxOs / txs | `/addresses/.../utxos`, `/transactions` | `/address_utxos`, `/address_txs` | Convert, Gap | [address-utxos-txs.md](endpoints/address-utxos-txs.md) |
| Submit tx | `POST /tx/submit` | `POST /submittx` | Compatible (passthrough) | [address-utxos-txs.md](endpoints/address-utxos-txs.md) |

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
