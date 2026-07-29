# Address UTxOs and transactions

## Address UTxOs

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/addresses/{address}/utxos` |
| Koios | `POST` | `/address_utxos` |

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `address` | `address` | Compatible |
| `tx_hash` | `tx_hash` | Compatible |
| `tx_index` / `output_index` | `tx_index` | Compatible / Rename |
| `amount[]` | `value` + `asset_list` | Convert |
| `block` (hash) | — (height/time only) | Gap |
| `data_hash` | `datum_hash` | Rename |
| `inline_datum` | `inline_datum` | Compatible / Partial |
| `reference_script_hash` | `reference_script.hash` | Convert |

Pagination: BF `count`/`page`/`order` ↔ Koios `limit`/`offset`/`order=block_height.asc|desc`.

## Address transactions

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/addresses/{address}/transactions` |
| Koios | `POST` | `/address_txs` |

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `tx_hash` | `tx_hash` | Compatible |
| `tx_index` | — | Gap (PoC sets `0`) |
| `block_height` | `block_height` | Compatible |
| `block_time` | `block_time` | Compatible |
| — | `epoch_no` | Gap on BF face |

## Tx submit

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `POST` | `/tx/submit` |
| Koios | `POST` | `/submittx` |

Raw CBOR body, `Content-Type: application/cbor`. Passthrough to the configured backend; response formatting stays close to each provider (`application/json` string on BF face).
