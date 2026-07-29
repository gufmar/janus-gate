# Block by hash or height

## Endpoints

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/blocks/{hash_or_number}` |
| Koios | `POST` | `/block_info` body `{"_block_hashes":["..."]}` |

Height on Koios backend: look up hash via `GET /blocks?block_height=eq.N`, then `POST /block_info`.

## Field mapping

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `hash` | `hash` | Compatible |
| `height` | `block_height` | Rename |
| `time` | `block_time` | Rename |
| `slot` | `abs_slot` | Rename |
| `epoch` | `epoch_no` | Rename |
| `epoch_slot` | `epoch_slot` | Compatible |
| `slot_leader` | `pool` | Rename |
| `size` | `block_size` | Rename |
| `tx_count` | `tx_count` | Compatible |
| `output` | `total_output` | Rename |
| `fees` | `total_fees` | Rename |
| `block_vrf` | `vrf_key` | Rename |
| `op_cert` | `op_cert` | Compatible |
| `op_cert_counter` (string) | `op_cert_counter` (number) | Convert |
| `previous_block` | `parent_hash` | Rename |
| `next_block` | `child_hash` | Rename |
| `confirmations` | `num_confirmations` | Rename |

## Janus behavior

PoC translates a single block. Koios batch `_block_hashes` uses the first hash only when Janus is the Koios face.
