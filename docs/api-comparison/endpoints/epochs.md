# Epoch info and parameters

## Epoch info

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/epochs/latest`, `/epochs/{number}` |
| Koios | `GET` | `/epoch_info?_epoch_no={n}` (also accepts `epoch_no=eq.{n}`) |

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `epoch` | `epoch_no` | Rename |
| `start_time` / `end_time` | same names | Compatible |
| `first_block_time` / `last_block_time` | same | Compatible |
| `block_count` | `blk_count` | Rename |
| `tx_count` | `tx_count` | Compatible |
| `output` | `out_sum` | Rename |
| `fees` | `fees` | Compatible |
| `active_stake` | `active_stake` | Compatible |
| — | `era`, `total_rewards`, `avg_blk_reward` | Gap on BF face |

Latest epoch on Koios backend: resolve current `epoch_no` from `/tip`, then query `epoch_info`.

## Epoch parameters

| Side | Method | Path |
| --- | --- | --- |
| Blockfrost | `GET` | `/epochs/latest/parameters`, `/epochs/{number}/parameters` |
| Koios | `GET` | `/epoch_params?_epoch_no={n}` (also accepts `epoch_no=eq.{n}`) |

Notable renames: `max_bh_size`↔`max_block_header_size`, `max_epoch`↔`e_max`, `optimal_pool_count`↔`n_opt`, `influence`↔`a0`, `monetary_expand_rate`↔`rho`, `treasury_growth_rate`↔`tau`, `decentralisation`↔`decentralisation_param`, `protocol_major`↔`protocol_major_ver`, `protocol_minor`↔`protocol_minor_ver`, `min_utxo_value`↔`min_utxo`.

Cost models: Koios list-form maps to Blockfrost `cost_models_raw`; named `cost_models` left `null` when only list form is available (Convert / Gap).
