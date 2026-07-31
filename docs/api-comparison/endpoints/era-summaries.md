# Era summaries

## Endpoints

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/network/eras` |
| Koios | `GET` | `/era_summaries` |

## Mapping notes

Shapes differ enough that Janus treats this as **Partial**:

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `start.epoch` / `start.time` | `epoch_no` / `first_block_time` | Convert |
| `end.*`, `parameters.*` | — | Gap when sourced from Koios |
| — | `era`, `protocol_major/minor`, `first_block_hash`, notes | Gap when sourced from Blockfrost |

Same-provider passthrough is faithful. Cross-provider responses keep the face schema with nulls for missing fields.

## dbsync

`get_era_summaries` is not implemented (501) until a SQL/MVP source is added.
