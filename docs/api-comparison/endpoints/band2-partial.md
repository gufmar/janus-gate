# Band 2: accounts, pools, epoch blocks, governance, scripts

Partial mappings. Field-level fidelity varies; treat as compatibility shims, not byte-identical twins.

## Account extras

| Blockfrost | Koios |
| --- | --- |
| `GET /accounts/{stake}/rewards` | `POST /account_rewards` (nested `rewards[]` flattened) |
| `GET /accounts/{stake}/history` | `POST /account_history` |
| `GET /accounts/{stake}/addresses` | `POST /account_addresses` |
| `GET /accounts/{stake}/delegations` | Derived from `account_history` pool changes (`tx_hash` Gap) |

Pagination for rewards/history is applied client-side after Koios returns the nested arrays.

## Pool extras

| Blockfrost | Koios |
| --- | --- |
| `GET /pools/{id}/history` | `GET /pool_history?_pool_bech32=` |
| `GET /pools/{id}/metadata` | `POST /pool_metadata` |
| `GET /pools/{id}/delegators` | `GET /pool_delegators?_pool_bech32=` |
| `GET /pools/{id}/relays` | `GET /pool_relays` (filtered) or relays on `pool_info` |

## Epoch blocks

| Blockfrost | Koios |
| --- | --- |
| `GET /epochs/{number}/blocks` | `GET /blocks?epoch_no=eq.N` |

Returns a list of block hashes on the Blockfrost face. Epoch **stakes** remain Gap.

## Governance basics

| Blockfrost | Koios |
| --- | --- |
| `GET /governance/committee` | `GET /committee_info` |
| `GET /governance/dreps` | `GET /drep_list` |
| `GET /governance/dreps/{id}` | `POST /drep_info` |
| `GET /governance/proposals` | `GET /proposal_list` |

Shapes are Partial; proposal IDs and vote families are not fully mirrored.

## Scripts / datums

| Blockfrost | Koios |
| --- | --- |
| `GET /scripts/{hash}` | `POST /script_info` |
| `GET /scripts/datum/{hash}` | `POST /datum_info` |

Missing hashes may surface as upstream **404** (face-shaped) rather than invented stub objects.
