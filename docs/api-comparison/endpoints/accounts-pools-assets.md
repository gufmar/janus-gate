# Accounts, pools, assets

## Account info

| Blockfrost | Koios |
| --- | --- |
| `GET /accounts/{stake_address}` | `POST /account_info` |

| Blockfrost | Koios | Class |
| --- | --- | --- |
| `stake_address` | `stake_address` | Compatible |
| `active` | `status` (`registered`) | Convert |
| `controlled_amount` | `total_balance` | Rename |
| `rewards_sum` | `rewards` | Rename |
| `withdrawals_sum` | `withdrawals` | Rename |
| `withdrawable_amount` | `rewards_available` | Rename |
| `reserves_sum` / `treasury_sum` | `reserves` / `treasury` | Rename |
| `pool_id` | `delegated_pool` | Rename |
| `active_epoch` | — | Gap |

## Pools

| Blockfrost | Koios |
| --- | --- |
| `GET /pools` | `GET /pool_list` (IDs only on BF) |
| `GET /pools/extended` | `GET /pool_list` (enriched) |
| `GET /pools/{pool_id}` | `POST /pool_info` |

Pool detail maps live/active stake, pledge, margin, owners, VRF, block_count→blocks_minted. Registration history arrays are Gap (empty) when sourced from Koios `pool_info`.

## Assets

| Blockfrost | Koios |
| --- | --- |
| `GET /assets/{asset}` | `POST /asset_info` with `[policy_id, asset_name]` |

Blockfrost asset id is `policy_id` (56 hex) + `asset_name` hex. Quantity←`total_supply`, `mint_or_burn_count`←`mint_cnt+burn_cnt`.
