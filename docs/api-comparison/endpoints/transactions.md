# Transactions (info, UTxOs, metadata, CBOR)

## Endpoints

| Concept | Blockfrost | Koios |
| --- | --- | --- |
| Tx summary | `GET /txs/{hash}` | `POST /tx_info` |
| Tx UTxOs | `GET /txs/{hash}/utxos` | `POST /tx_utxos` |
| Metadata | `GET /txs/{hash}/metadata` | `POST /tx_metadata` |
| CBOR | `GET /txs/{hash}/cbor` | `POST /tx_cbor` |

## Notable mapping notes

- Koios returns arrays; Janus unwraps the first hash (batch PoC: first item only on Koios face).
- Summary: Rename for hash/block/slot/fees/size; cert-count fields on Blockfrost are often Gap/zero when sourced from Koios tip-level `tx_info`.
- UTxOs: Convert `payment_addr.bech32` → `address`, `value`+`asset_list` → `amount[]`.
- Metadata: Convert Koios object map → Blockfrost `[{label, json_metadata}]`.
- CBOR: Compatible `cbor` field inside different envelopes.
