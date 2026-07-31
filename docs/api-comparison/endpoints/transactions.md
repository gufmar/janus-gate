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
- UTxOs: Convert `payment_addr.bech32` → `address`, `value`+`asset_list` → `amount[]`; sort by `tx_index` / `output_index`.
- UTxOs Gaps (Koios `/tx_utxos`): no collateral or reference inputs/outputs; `consumed_by_tx` usually absent; datum / ref-script fields often null vs Blockfrost.
- Metadata: Convert Koios object map → Blockfrost `[{label, json_metadata}]`.
- Metadata-by-label: Koios `/tx_by_metalabel` is Partial (`json_metadata` null) and hot labels (0/1/721) often time out upstream.
- CBOR: Compatible `cbor` field inside different envelopes.
