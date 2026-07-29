# Band 2.5: block txs, account txs, metadata labels

## Block transactions

| Blockfrost | Koios |
| --- | --- |
| `GET /blocks/{hash_or_number}/txs` | `POST /block_txs` |
| `GET /blocks/latest/txs` | tip hash + `block_txs` |

Blockfrost returns a list of tx hash strings. Koios returns `{block_hash, tx_hash, ...}` rows; Janus flattens to hashes on the BF face. Pagination is applied client-side after Koios returns the full block tx list.

## Account transactions

| Blockfrost | Koios |
| --- | --- |
| `GET /accounts/{stake}/transactions` | `GET /account_txs?_stake_address=` |

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `tx_hash` | `tx_hash` | Compatible |
| `block_height` / `block_time` | same | Compatible |
| `tx_index` | — | Gap (PoC `0`) |
| `address` (payment) | — | Gap (PoC repeats stake address) |

## Metadata labels

| Blockfrost | Koios |
| --- | --- |
| `GET /metadata/txs/labels` | `GET /tx_metalabels` |
| `GET /metadata/txs/labels/{label}` | `GET /tx_by_metalabel?_label=` |

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `label` | `key` | Rename |
| `cip10` / `count` | — | Gap (`null`) |
| `json_metadata` on label content | — | Gap (`null`; use `/txs/{hash}/metadata`) |

CBOR variants of metadata-by-label are not implemented yet.
