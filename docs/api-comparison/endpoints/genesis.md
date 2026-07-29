# Genesis

## Endpoints

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/genesis` |
| Koios | `GET` | `/genesis` |

Koios returns a one-element array; Blockfrost returns a single object.

## Field mapping

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `active_slots_coefficient` (float) | `activeslotcoeff` (string) | Rename + Convert |
| `update_quorum` (int) | `updatequorum` (string) | Rename + Convert |
| `max_lovelace_supply` | `maxlovelacesupply` | Rename |
| `network_magic` (int) | `networkmagic` (string) | Rename + Convert |
| `epoch_length` | `epochlength` | Rename + Convert |
| `system_start` | `systemstart` | Rename |
| `slots_per_kes_period` | `slotsperkesperiod` | Rename + Convert |
| `slot_length` | `slotlength` | Rename + Convert |
| `max_kes_evolutions` | `maxkesrevolutions` | Rename + Convert |
| `security_param` | `securityparam` | Rename + Convert |
| — | `networkid`, `alonzogenesis` | Gap on BF face |

## Janus behavior

Bidirectional mapping with type coercion. Koios-only fields are dropped on the Blockfrost face; BF->Koios sets `networkid` to `"Mainnet"` and `alonzogenesis` to `null`.
