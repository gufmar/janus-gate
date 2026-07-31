# Endpoint catalog: Blockfrost vs Koios

Source OpenAPI snapshots (checked into local `scripts/` for regen):

- Blockfrost `openapi.yaml` v0.1.91 (~128 operations)
- Koios `koiosapi-mainnet.yaml` v1.4.2 (~102 operations)

Regenerate the raw dump with:

```bash
uv run python scripts/dump_endpoints.py
```

This document is a **coverage map for Janus Gate**, not a field-level mapping. Per-endpoint field detail lives under [`endpoints/`](endpoints/) as we implement each pair.

## Verdict legend

| Verdict | Meaning for Janus |
| --- | --- |
| **Likely** | Clear semantic twin; mostly Rename/Convert work |
| **Partial** | Same domain, but shape/method/pagination differ enough that mapping is lossy or multi-call |
| **Hard** | Related data exists, but not as a drop-in twin (compose several calls, or accept Gaps) |
| **BF-only** | Blockfrost exposes it; Koios has no easy equivalent |
| **Koios-only** | Koios exposes it; Blockfrost has no easy equivalent |
| **Platform** | Provider product feature (not Cardano chain data parity) |

HTTP style note: Blockfrost is mostly `GET` with path params. Koios is often `POST` with JSON body (`_addresses`, `_tx_hashes`, …) plus PostgREST filters on `GET` lists.

---

## Network / ledger

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Chain tip / latest block | `GET /blocks/latest` | `GET /tip` | **Likely** (PoC done; Gaps for full block fields) |
| Genesis | `GET /genesis` | `GET /genesis` | **Likely** (field renames) |
| Era summaries | `GET /network/eras` | `GET /era_summaries` | **Likely** |
| Network summary | `GET /network` | — (derive from tip/totals) | **Partial** / **Hard** |
| Historical supply / totals | — | `GET /totals` | **Koios-only** |
| Param update proposals | — | `GET /param_updates` | **Koios-only** (BF has epoch params, not this history view) |
| CLI protocol params blob | — | `GET /cli_protocol_params` | **Koios-only** |
| Reserve withdrawals | — | `GET /reserve_withdrawals` | **Koios-only** |
| Treasury withdrawals | — | `GET /treasury_withdrawals` | **Koios-only** (related BF gov proposal withdrawals are narrower) |

---

## Epochs

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Epoch info (latest / by number) | `GET /epochs/latest`, `GET /epochs/{number}` | `GET /epoch_info` | **Likely** / **Partial** (Koios list+filter vs BF path) |
| Epoch protocol parameters | `GET /epochs/latest/parameters`, `GET /epochs/{number}/parameters` | `GET /epoch_params` | **Likely** |
| Next / previous epochs | `GET /epochs/{number}/next`, `.../previous` | filter `epoch_info` | **Likely** (BF face walks consecutive epochs) |
| Stake distribution by epoch | `GET /epochs/{number}/stakes`, `.../stakes/{pool_id}` | pool/account history style | **Hard** |
| Blocks in epoch | `GET /epochs/{number}/blocks`, `.../blocks/{pool_id}` | `GET /blocks?epoch_no=eq.N` | **Partial** |
| Block protocols in epoch | — | `GET /epoch_block_protocols` | **Koios-only** |

---

## Blocks

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Block by hash/height | `GET /blocks/{hash_or_number}` | `POST /block_info` | **Likely** |
| Block list / paging | next/previous around a block | `GET /blocks` (+ filters) | **Partial** |
| Block by slot | `GET /blocks/slot/{slot}` | filter blocks by `abs_slot` | **Partial** |
| Block by epoch+slot | `GET /blocks/epoch/{e}/slot/{s}` | filter `epoch_no` + `epoch_slot` | **Partial** |
| Txs in block | `GET /blocks/.../txs`, `.../txs/cbor`, latest variants | `POST /block_txs`, `/block_tx_cbor`, `/block_tx_info` | **Likely** / **Partial** |
| Addresses touched in block | `GET /blocks/{id}/addresses` | compose from tx outs | **Hard** |

---

## Transactions

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Tx summary | `GET /txs/{hash}` | `POST /tx_info` | **Likely** / **Partial** (Koios is richer/bulk) |
| Tx UTxOs | `GET /txs/{hash}/utxos` | `POST /tx_utxos` | **Likely** |
| Tx CBOR | `GET /txs/{hash}/cbor` | `POST /tx_cbor` | **Likely** |
| Tx metadata | `GET /txs/{hash}/metadata`, `.../cbor` | `POST /tx_metadata` | **Likely** |
| Tx redeemers | `GET /txs/{hash}/redeemers` | inside `tx_info` / script redeemers | **Partial** |
| Tx required signers | `GET /txs/{hash}/required_signers` | inside `tx_info` | **Partial** |
| Split cert endpoints (stakes, delegations, withdrawals, MIRs, pool updates/retires) | `GET /txs/{hash}/stakes` etc. | fields inside `tx_info` | **Partial** (BF splits; Koios aggregates) |
| Submit tx | `POST /tx/submit` | `POST /submittx` | **Likely** |
| Tx confirmation status | — | `POST /tx_status` | **Koios-only** |
| UTxO info by refs | — | `POST /utxo_info` | **Koios-only** (BF reaches via address/tx UTxO routes) |
| Outputs by epoch | — | `GET /tx_outs_epoch` | **Koios-only** |
| Metadata label catalog | `GET /metadata/txs/labels` | `GET /tx_metalabels` | **Likely** |
| Txs by metadata label | `GET /metadata/txs/labels/{label}` (+ cbor) | `GET /tx_by_metalabel` | **Likely** / **Partial** |

---

## Addresses (payment)

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Address summary | `GET /addresses/{address}` | `POST /address_info` | **Likely** (PoC done) |
| Extended address | `GET /addresses/{address}/extended` | richer `address_info` | **Partial** (done; decimals/NFT Gaps) |
| Address totals | `GET /addresses/{address}/total` | derive from info/assets | **Partial** |
| Address UTxOs | `GET /addresses/{address}/utxos` (+ by asset) | `POST /address_utxos` | **Likely** |
| Address txs | `GET /addresses/{address}/txs`, `.../transactions` | `POST /address_txs` | **Likely** |
| Address assets | (via extended/amount) | `POST /address_assets` | **Partial** (done; BF via amount[]) |
| Address outputs history | — | `POST /address_outputs` | **Koios-only** |
| Payment credential UTxOs/txs | — | `POST /credential_utxos`, `/credential_txs` | **Koios-only** |
| Global address list | — | `GET /address_list` | **Koios-only** |

---

## Accounts (stake)

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Account summary | `GET /accounts/{stake_address}` | `POST /account_info` (+ cached) | **Likely** |
| Rewards | `GET /accounts/.../rewards` | `POST /account_rewards`, `/account_reward_history` | **Likely** / **Partial** |
| History / stake history | `GET /accounts/.../history` | `POST /account_history`, `/account_stake_history` | **Likely** / **Partial** |
| Delegations | `GET /accounts/.../delegations` | account history / updates | **Partial** |
| Registrations | `GET /accounts/.../registrations` | `POST /account_updates`, `/account_update_history` | **Partial** |
| Withdrawals | `GET /accounts/.../withdrawals` | from rewards/history style | **Partial** |
| MIR history | `GET /accounts/.../mirs` | limited / historical | **Hard** |
| Associated addresses | `GET /accounts/.../addresses` | `POST /account_addresses` | **Likely** |
| Account assets | `GET /accounts/.../addresses/assets` | `POST /account_assets` | **Likely** |
| Address totals under account | `GET /accounts/.../addresses/total` | compose | **Partial** |
| Account UTxOs | `GET /accounts/.../utxos` | `POST /account_utxos` | **Likely** |
| Account txs | `GET /accounts/.../transactions` | `GET /account_txs` | **Likely** / **Partial** |
| Global account list | — | `GET /account_list` | **Koios-only** |

---

## Pools

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Pool list | `GET /pools`, `/pools/extended` | `GET /pool_list` | **Likely** / **Partial** |
| Retired / retiring lists | `GET /pools/retired`, `/pools/retiring` | `GET /pool_retirements` (+ registrations) | **Partial** |
| Pool detail | `GET /pools/{pool_id}` | `POST /pool_info` | **Likely** |
| Pool history | `GET /pools/{id}/history` | `GET /pool_history` | **Likely** |
| Metadata | `GET /pools/{id}/metadata` | `POST /pool_metadata` | **Likely** |
| Relays | `GET /pools/{id}/relays` | `GET /pool_relays` | **Likely** |
| Delegators | `GET /pools/{id}/delegators` | `GET /pool_delegators` (+ history, invalid) | **Likely** / **Partial** |
| Pool blocks | `GET /pools/{id}/blocks` | `GET /pool_blocks` | **Likely** (done) |
| Pool updates | `GET /pools/{id}/updates` | `GET /pool_updates` | **Likely** (done) |
| Pool votes | `GET /pools/{id}/votes` | `GET /pool_votes` | **Likely** (done; Koios deprecated) |
| Stake snapshot | — | `GET /pool_stake_snapshot` | **Koios-only** |
| Owner history | — | `POST /pool_owner_history` | **Koios-only** |
| Pool groups | — | `GET /pool_groups` | **Koios-only** |
| Calidus keys | — | `GET /pool_calidus_keys` | **Koios-only** |
| Registrations list | — | `GET /pool_registrations` | **Koios-only** (BF via updates/tx certs) |

---

## Assets

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Asset list | `GET /assets` | `GET /asset_list` | **Likely** / **Partial** (done) |
| Asset by id | `GET /assets/{asset}` | `POST /asset_info` | **Likely** |
| Policy assets | `GET /assets/policy/{policy_id}` | `GET /policy_asset_list`, `/policy_asset_info`, `/policy_asset_mints` | **Partial** (Koios richer) |
| History / txs / addresses / UTxOs | BF `/assets/{asset}/...` | Koios `asset_history`, `asset_txs`, `asset_addresses`, `asset_utxos` | **Likely** (history/txs/addresses done; UTxOs still open) |
| NFT current address | — | `GET /asset_nft_address` | **Koios-only** |
| Policy asset addresses | — | `GET /policy_asset_addresses` | **Koios-only** (BF: per-asset addresses) |
| Token registry | — | `GET /asset_token_registry` | **Koios-only** |
| Asset summary | — | `GET /asset_summary` | **Koios-only** |

---

## Scripts / datums

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Script list | `GET /scripts` | `GET /native_script_list`, `/plutus_script_list` | **Partial** |
| Script detail / JSON / CBOR | `GET /scripts/{hash}`, `.../json`, `.../cbor` | `POST /script_info` | **Partial** |
| Redeemers | `GET /scripts/{hash}/redeemers` | `GET /script_redeemers` | **Likely** / **Partial** |
| Reference script UTxOs | `GET /scripts/{hash}/utxos` | `POST /reference_script_utxos`, `GET /script_utxos` | **Likely** / **Partial** |
| Datum by hash | `GET /scripts/datum/{hash}`, `.../cbor` | `POST /datum_info` | **Likely** |

---

## Governance (Conway)

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Committee | `GET /governance/committee` | `GET /committee_info` | **Likely** |
| Committee votes | `GET /governance/committee/votes`, `.../{cc_id}/votes` | `GET /committee_votes` | **Likely** / **Partial** |
| DRep list / detail | `GET /governance/dreps`, `.../{drep_id}` | `GET /drep_list`, `POST /drep_info` | **Likely** |
| DRep delegators / metadata / updates / votes | BF under `/governance/dreps/{id}/...` | Koios `drep_*` family | **Likely** / **Partial** |
| Proposals + votes + metadata | BF `/governance/proposals...` (incl. gov_action_id variants) | `proposal_list`, `proposal_votes`, `proposal_voting_summary`, … | **Partial** (ID schemes differ) |
| DRep epoch summary / voting power history | — | `drep_epoch_summary`, `drep_history`, `drep_voting_power_history` | **Koios-only** / **Hard** on BF |
| Vote list / voter proposals | — | `vote_list`, `voter_proposal_list` | **Koios-only** |
| Pool voting power history | — | `pool_voting_power_history` | **Koios-only** |

---

## Mempool, utilities, platform

| Concept | Blockfrost | Koios | Verdict |
| --- | --- | --- | --- |
| Mempool contents | `GET /mempool`, `.../{hash}`, `.../addresses/{address}` | — | **BF-only** |
| Evaluate tx / ex-units | `POST /utils/txs/evaluate`, `.../evaluate/utxos` | via `POST /ogmios` (not REST-equivalent) | **BF-only** / **Hard** |
| Derive address from xpub | `GET /utils/addresses/xpub/...` | — | **BF-only** |
| Health / clock | `GET /health`, `/health/clock` | — | **Platform** (Janus has own `/health`) |
| Usage metrics | `GET /metrics`, `/metrics/endpoints` | — | **Platform** / **BF-only** |
| IPFS add/pin/gateway | `/ipfs/...` | — | **Platform** / **BF-only** |
| Nut.link oracles | `/nutlink/...` | — | **Platform** / **BF-only** |
| Ogmios proxy | — | `POST /ogmios` | **Platform** / **Koios-only** |

---

## One-sided highlights (hard to fake)

### Blockfrost offers, Koios does not easily

1. **Mempool APIs** – live mempool inspection by hash/address.
2. **Tx evaluation utilities** – `utils/txs/evaluate` without standing up Ogmios yourself.
3. **xpub address derivation** – wallet utility, not chain index data.
4. **IPFS + metrics + nut.link** – Blockfrost product surface, not Koios scope.
5. **Fine-grained BF path variants** such as `/blocks/{id}/addresses` and split `/txs/{hash}/mirs` style slices – often recoverable from Koios `tx_info` / joins, but not 1:1 routes.

### Koios offers, Blockfrost does not easily

1. **Bulk POST query style** – many `_addresses` / `_tx_hashes` batch endpoints (BF is mostly one resource per request).
2. **Payment credential queries** – `credential_utxos`, `credential_txs`.
3. **Global enumeration** – `address_list`, `account_list` (BF paginates domain lists differently; no full address census).
4. **Network economics history** – `totals`, `reserve_withdrawals`, `treasury_withdrawals`, `param_updates`.
5. **CLI protocol params** – `cli_protocol_params`.
6. **Tx status / UTxO-by-ref / epoch outputs** – `tx_status`, `utxo_info`, `tx_outs_epoch`.
7. **Asset registry / NFT address / policy-wide address & mint views**.
8. **Pool extras** – stake snapshot, owner history, groups, calidus keys.
9. **Broader governance analytics** – voting power histories, vote lists, voter proposal lists.
10. **Ogmios gateway** – `POST /ogmios`.

---

## Practical Janus priority bands

Suggested expansion order after the PoC tip + address pair:

1. **High likelihood, high client value:** genesis, epochs (+ params), block_info, tx_info/utxos/metadata/cbor, address utxos/txs, account_info, pool_info/list, asset_info, submit tx. **(implemented in Janus)**
2. **Partial but doable:** epoch blocks, governance committee/drep/proposal basics, script/datum routes, pool history/delegators/metadata/relays, account rewards/history/addresses/delegations. **(implemented in Janus; epoch stakes still Gap)**
2.5. **High-value follow-ons:** block txs, account txs, metadata labels (+ by label). **(implemented in Janus)**
3. **Defer / document as Gaps:** mempool, BF evaluate utilities, IPFS/metrics/nutlink, Koios-only analytics (totals, credential_*, global lists), Ogmios proxy, full epoch stake distributions.

---

## Counts (rough)

| Scope | Blockfrost ops | Koios ops |
| --- | --- | --- |
| Full OpenAPI | 128 | 102 |
| Cardano-ish (exclude IPFS/metrics/nutlink/health/ogmios) | ~112 | ~101 |
| Clear **Likely** twins (concept-level) | ~45–55 pairs | same |
| Distinct one-sided product/analytics surfaces | see BF-only / Koios-only lists above | |

Exact “pair count” will move as we write field-level docs; use this file as the living triage board.
