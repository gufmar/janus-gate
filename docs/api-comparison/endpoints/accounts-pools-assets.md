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
| `GET /pools/{pool_id}/blocks` | `GET /pool_blocks` |
| `GET /pools/{pool_id}/updates` | `GET /pool_updates` |
| `GET /pools/{pool_id}/votes` | `GET /pool_votes` (Koios deprecated) |

Pool detail maps live/active stake, pledge, margin, owners, VRF, block_count→blocks_minted. Registration history arrays are Gap (empty) when sourced from Koios `pool_info`.

Pool blocks: BF returns hash strings; Koios returns objects (`block_hash` plus epoch/slot/height/time Gaps when sourced from BF).

Pool updates: `update_type` ↔ `action` (`registered` / `deregistered`). Extra Koios registration fields are Gap when facing BF.

Pool votes: `proposal_tx_hash`/`proposal_index` ↔ `tx_hash`/`cert_index`; vote normalized to yes/no/abstain.

## Assets

| Blockfrost | Koios |
| --- | --- |
| `GET /assets` | `GET /asset_list` |
| `GET /assets/{asset}` | `POST /asset_info` with `[policy_id, asset_name]` |
| `GET /assets/{asset}/history` | `GET /asset_history` |
| `GET /assets/{asset}/transactions` | `GET /asset_txs` |
| `GET /assets/{asset}/addresses` | `GET /asset_addresses` |

Blockfrost asset id is `policy_id` (56 hex) + `asset_name` hex. Quantity←`total_supply`, `mint_or_burn_count`←`mint_cnt+burn_cnt`.

Asset history flattens Koios nested `minting_txs` into BF `{tx_hash, amount, action}` rows (`minted` / `burned`).

## Address extended / assets

| Blockfrost | Koios |
| --- | --- |
| `GET /addresses/{address}/extended` | Derived from `POST /address_info` |
| (amount native tokens) | `POST /address_assets` |

Extended pads `decimals=null` and `has_nft_onchain_metadata=false` (Partial/Gap). Address assets maps BF `amount[]` units into Koios `{policy_id, asset_name, quantity}` lists (lovelace omitted).
