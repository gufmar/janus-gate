# Network tip / latest block

## Endpoints

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/blocks/latest` |
| Koios | `GET` | `/tip` |

Blockfrost returns a single block object. Koios returns a one-element array of tip objects.

Optional enrichment: Koios `GET /blocks?block_height=eq.{n}` can supply fields such as `pool`, `tx_count`, and `vrf_key` that tip alone does not always expose fully.

## Field mapping

| Blockfrost field | Koios field | Class | Notes |
| --- | --- | --- | --- |
| `hash` | `hash` | Compatible | Block hash |
| `height` | `block_height` (prefer) / `block_no` (deprecated) | Rename | Integer height |
| `slot` | `abs_slot` | Rename | Absolute slot |
| `epoch` | `epoch_no` | Rename | Epoch number |
| `epoch_slot` | `epoch_slot` | Compatible | Slot within epoch |
| `time` | `block_time` | Rename | UNIX seconds |
| `slot_leader` | `pool` (from `/blocks`) | Rename / Gap | Null if block detail unavailable |
| `tx_count` | `tx_count` (from `/blocks`) | Compatible / Gap | Default `0` when tip-only |
| `block_vrf` | `vrf_key` (from `/blocks`) | Rename / Gap | Naming differs |
| `op_cert_counter` | `op_cert_counter` (from `/blocks`) | Convert | Blockfrost string vs Koios number |
| `size` | — | Gap | Not on tip; omit / null in PoC |
| `output` | — | Gap | Not on tip |
| `fees` | — | Gap | Not on tip |
| `op_cert` | — | Gap | Not routinely on tip |
| `previous_block` | — | Gap | Needs neighboring block query |
| `next_block` | — | Gap | Null at tip |
| `confirmations` | — | Convert | PoC sets `0` for tip |

## Envelope conversion

| Direction | Conversion |
| --- | --- |
| Koios -> Blockfrost | Unwrap first tip row; build single object |
| Blockfrost -> Koios | Wrap object in a one-element array; emit both `block_height` and deprecated `block_no` |

## Janus PoC behavior

- Blockfrost face: calls Koios `/tip`, optionally `/blocks` by height, returns Blockfrost-shaped JSON (nulls for gaps).
- Koios face: calls Blockfrost `/blocks/latest`, returns Koios tip array shape.
