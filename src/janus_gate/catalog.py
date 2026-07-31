"""Known public-face endpoints and which ones Janus currently implements."""

from __future__ import annotations

from dataclasses import dataclass

from janus_gate.config import ProviderName


@dataclass(frozen=True, slots=True)
class EndpointEntry:
    method: str
    path: str
    summary: str
    group: str
    implemented: bool = False
    # Optional concrete demo path for GET hrefs (path params replaced with placeholders).
    href: str | None = None


def _bf(
    method: str,
    path: str,
    summary: str,
    group: str,
    *,
    implemented: bool = False,
    href: str | None = None,
) -> EndpointEntry:
    return EndpointEntry(method, path, summary, group, implemented, href)


def _ko(
    method: str,
    path: str,
    summary: str,
    group: str,
    *,
    implemented: bool = False,
    href: str | None = None,
) -> EndpointEntry:
    return EndpointEntry(method, path, summary, group, implemented, href)


BLOCKFROST_ENDPOINTS: tuple[EndpointEntry, ...] = (
    # Network / ledger
    _bf("GET", "/blocks/latest", "Latest block / tip", "Network / blocks", implemented=True, href="/blocks/latest"),
    _bf("GET", "/genesis", "Blockchain genesis", "Network / blocks", implemented=True, href="/genesis"),
    _bf("GET", "/network", "Network information", "Network / blocks"),
    _bf("GET", "/network/eras", "Era summaries", "Network / blocks", implemented=True, href="/network/eras"),
    # Blocks
    _bf("GET", "/blocks/{hash_or_number}", "Specific block", "Network / blocks", implemented=True, href="/blocks/{hash_or_number}"),
    _bf("GET", "/blocks/{hash_or_number}/next", "Next blocks", "Network / blocks", implemented=True, href="/blocks/{hash_or_number}/next"),
    _bf("GET", "/blocks/{hash_or_number}/previous", "Previous blocks", "Network / blocks", implemented=True, href="/blocks/{hash_or_number}/previous"),
    _bf("GET", "/blocks/slot/{slot_number}", "Block by slot", "Network / blocks", implemented=True, href="/blocks/slot/{slot_number}"),
    _bf("GET", "/blocks/epoch/{epoch_number}/slot/{slot_number}", "Block by epoch slot", "Network / blocks", implemented=True, href="/blocks/epoch/{epoch_number}/slot/{slot_number}"),
    _bf("GET", "/blocks/latest/txs", "Latest block transactions", "Network / blocks", implemented=True, href="/blocks/latest/txs"),
    _bf("GET", "/blocks/{hash_or_number}/txs", "Block transactions", "Network / blocks", implemented=True, href="/blocks/{hash_or_number}/txs"),
    _bf("GET", "/blocks/{hash_or_number}/addresses", "Addresses in block", "Network / blocks"),
    # Epochs
    _bf("GET", "/epochs/latest", "Latest epoch", "Epochs", implemented=True, href="/epochs/latest"),
    _bf("GET", "/epochs/latest/parameters", "Latest epoch parameters", "Epochs", implemented=True, href="/epochs/latest/parameters"),
    _bf("GET", "/epochs/{number}", "Specific epoch", "Epochs", implemented=True, href="/epochs/{number}"),
    _bf("GET", "/epochs/{number}/parameters", "Epoch parameters", "Epochs", implemented=True, href="/epochs/{number}/parameters"),
    _bf("GET", "/epochs/{number}/next", "Next epochs", "Epochs", implemented=True, href="/epochs/{number}/next"),
    _bf("GET", "/epochs/{number}/previous", "Previous epochs", "Epochs", implemented=True, href="/epochs/{number}/previous"),
    _bf("GET", "/epochs/{number}/stakes", "Epoch stake distribution", "Epochs"),
    _bf("GET", "/epochs/{number}/blocks", "Epoch blocks", "Epochs", implemented=True, href="/epochs/{number}/blocks"),
    # Transactions
    _bf("GET", "/txs/{hash}", "Transaction", "Transactions", implemented=True, href="/txs/{hash}"),
    _bf("GET", "/txs/{hash}/utxos", "Transaction UTxOs", "Transactions", implemented=True, href="/txs/{hash}/utxos"),
    _bf("GET", "/txs/{hash}/metadata", "Transaction metadata", "Transactions", implemented=True, href="/txs/{hash}/metadata"),
    _bf("GET", "/txs/{hash}/cbor", "Transaction CBOR", "Transactions", implemented=True, href="/txs/{hash}/cbor"),
    _bf("POST", "/tx/submit", "Submit transaction", "Transactions", implemented=True),
    _bf("GET", "/metadata/txs/labels", "Metadata labels", "Transactions", implemented=True, href="/metadata/txs/labels"),
    _bf("GET", "/metadata/txs/labels/{label}", "Metadata by label", "Transactions", implemented=True, href="/metadata/txs/labels/{label}"),
    # Addresses
    _bf("GET", "/addresses/{address}", "Address info", "Addresses", implemented=True, href="/addresses/{address}"),
    _bf("GET", "/addresses/{address}/extended", "Address extended", "Addresses", implemented=True, href="/addresses/{address}/extended"),
    _bf("GET", "/addresses/{address}/total", "Address totals", "Addresses"),
    _bf("GET", "/addresses/{address}/utxos", "Address UTxOs", "Addresses", implemented=True, href="/addresses/{address}/utxos"),
    _bf("GET", "/addresses/{address}/transactions", "Address transactions", "Addresses", implemented=True, href="/addresses/{address}/transactions"),
    _bf("GET", "/addresses/{address}/txs", "Address txs (legacy)", "Addresses"),
    # Accounts
    _bf("GET", "/accounts/{stake_address}", "Account info", "Accounts", implemented=True, href="/accounts/{stake_address}"),
    _bf("GET", "/accounts/{stake_address}/rewards", "Account rewards", "Accounts", implemented=True, href="/accounts/{stake_address}/rewards"),
    _bf("GET", "/accounts/{stake_address}/history", "Account history", "Accounts", implemented=True, href="/accounts/{stake_address}/history"),
    _bf("GET", "/accounts/{stake_address}/delegations", "Account delegations", "Accounts", implemented=True, href="/accounts/{stake_address}/delegations"),
    _bf("GET", "/accounts/{stake_address}/addresses", "Account addresses", "Accounts", implemented=True, href="/accounts/{stake_address}/addresses"),
    _bf("GET", "/accounts/{stake_address}/utxos", "Account UTxOs", "Accounts"),
    _bf("GET", "/accounts/{stake_address}/transactions", "Account transactions", "Accounts", implemented=True, href="/accounts/{stake_address}/transactions"),
    # Pools
    _bf("GET", "/pools", "Pool list", "Pools", implemented=True, href="/pools"),
    _bf("GET", "/pools/extended", "Pool list extended", "Pools", implemented=True, href="/pools/extended"),
    _bf("GET", "/pools/{pool_id}", "Pool info", "Pools", implemented=True, href="/pools/{pool_id}"),
    _bf("GET", "/pools/{pool_id}/history", "Pool history", "Pools", implemented=True, href="/pools/{pool_id}/history"),
    _bf("GET", "/pools/{pool_id}/metadata", "Pool metadata", "Pools", implemented=True, href="/pools/{pool_id}/metadata"),
    _bf("GET", "/pools/{pool_id}/delegators", "Pool delegators", "Pools", implemented=True, href="/pools/{pool_id}/delegators"),
    _bf("GET", "/pools/{pool_id}/relays", "Pool relays", "Pools", implemented=True, href="/pools/{pool_id}/relays"),
    _bf("GET", "/pools/{pool_id}/blocks", "Pool blocks", "Pools", implemented=True, href="/pools/{pool_id}/blocks"),
    _bf("GET", "/pools/{pool_id}/updates", "Pool updates", "Pools", implemented=True, href="/pools/{pool_id}/updates"),
    _bf("GET", "/pools/{pool_id}/votes", "Pool votes", "Pools", implemented=True, href="/pools/{pool_id}/votes"),
    # Assets / scripts / governance (abbrev)
    _bf("GET", "/assets", "Assets", "Assets", implemented=True, href="/assets"),
    _bf("GET", "/assets/{asset}", "Asset info", "Assets", implemented=True, href="/assets/{asset}"),
    _bf("GET", "/assets/{asset}/history", "Asset history", "Assets", implemented=True, href="/assets/{asset}/history"),
    _bf("GET", "/assets/{asset}/transactions", "Asset transactions", "Assets", implemented=True, href="/assets/{asset}/transactions"),
    _bf("GET", "/assets/{asset}/addresses", "Asset addresses", "Assets", implemented=True, href="/assets/{asset}/addresses"),
    _bf("GET", "/scripts", "Scripts", "Scripts"),
    _bf("GET", "/scripts/datum/{datum_hash}", "Datum by hash", "Scripts", implemented=True, href="/scripts/datum/{datum_hash}"),
    _bf("GET", "/scripts/{script_hash}", "Script info", "Scripts", implemented=True, href="/scripts/{script_hash}"),
    _bf("GET", "/governance/dreps", "DReps", "Governance", implemented=True, href="/governance/dreps"),
    _bf("GET", "/governance/dreps/{drep_id}", "DRep info", "Governance", implemented=True, href="/governance/dreps/{drep_id}"),
    _bf("GET", "/governance/proposals", "Proposals", "Governance", implemented=True, href="/governance/proposals"),
    _bf("GET", "/governance/committee", "Committee", "Governance", implemented=True, href="/governance/committee"),
    _bf("GET", "/mempool", "Mempool", "Mempool / utils"),
    _bf("POST", "/utils/txs/evaluate", "Evaluate transaction", "Mempool / utils"),
)

KOIOS_ENDPOINTS: tuple[EndpointEntry, ...] = (
    _ko("GET", "/tip", "Chain tip", "Network", implemented=True, href="/tip"),
    _ko("GET", "/genesis", "Genesis", "Network", implemented=True, href="/genesis"),
    _ko("GET", "/era_summaries", "Era summaries", "Network", implemented=True, href="/era_summaries"),
    _ko("GET", "/totals", "Historical totals", "Network"),
    _ko("GET", "/param_updates", "Param updates", "Network"),
    _ko("GET", "/cli_protocol_params", "CLI protocol params", "Network"),
    _ko("GET", "/epoch_info", "Epoch information", "Epoch", implemented=True, href="/epoch_info"),
    _ko("GET", "/epoch_params", "Epoch parameters", "Epoch", implemented=True, href="/epoch_params"),
    _ko("GET", "/epoch_block_protocols", "Epoch block protocols", "Epoch"),
    _ko("GET", "/blocks", "Block list (filters)", "Block", implemented=True, href="/blocks?epoch_no=eq.{number}"),
    _ko("POST", "/block_info", "Block information", "Block", implemented=True),
    _ko("POST", "/block_txs", "Block transactions", "Block", implemented=True),
    _ko("POST", "/block_tx_info", "Block tx details", "Block"),
    _ko("POST", "/tx_info", "Transaction information", "Transactions", implemented=True),
    _ko("POST", "/tx_utxos", "Transaction UTxOs", "Transactions", implemented=True),
    _ko("POST", "/tx_metadata", "Transaction metadata", "Transactions", implemented=True),
    _ko("POST", "/tx_cbor", "Transaction CBOR", "Transactions", implemented=True),
    _ko("POST", "/submittx", "Submit transaction", "Transactions", implemented=True),
    _ko("GET", "/tx_metalabels", "Metadata labels", "Transactions", implemented=True, href="/tx_metalabels"),
    _ko("GET", "/tx_by_metalabel", "Txs by metadata label", "Transactions", implemented=True, href="/tx_by_metalabel?_label={label}"),
    _ko("POST", "/address_info", "Address information", "Address", implemented=True),
    _ko("POST", "/address_utxos", "Address UTxOs", "Address", implemented=True),
    _ko("POST", "/address_txs", "Address transactions", "Address", implemented=True),
    _ko("POST", "/address_assets", "Address assets", "Address", implemented=True),
    _ko("POST", "/account_info", "Account information", "Stake account", implemented=True),
    _ko("POST", "/account_rewards", "Account rewards", "Stake account", implemented=True),
    _ko("POST", "/account_history", "Account history", "Stake account", implemented=True),
    _ko("POST", "/account_addresses", "Account addresses", "Stake account", implemented=True),
    _ko("GET", "/account_txs", "Account transactions", "Stake account", implemented=True, href="/account_txs?_stake_address={stake}"),
    _ko("GET", "/pool_list", "Pool list", "Pool", implemented=True, href="/pool_list"),
    _ko("POST", "/pool_info", "Pool information", "Pool", implemented=True),
    _ko("GET", "/pool_history", "Pool history", "Pool", implemented=True, href="/pool_history?_pool_bech32={pool_id}"),
    _ko("POST", "/pool_metadata", "Pool metadata", "Pool", implemented=True),
    _ko("GET", "/pool_delegators", "Pool delegators", "Pool", implemented=True, href="/pool_delegators?_pool_bech32={pool_id}"),
    _ko("GET", "/pool_relays", "Pool relays", "Pool", implemented=True, href="/pool_relays?_pool_bech32={pool_id}"),
    _ko("GET", "/pool_blocks", "Pool blocks", "Pool", implemented=True, href="/pool_blocks?_pool_bech32={pool_id}"),
    _ko("GET", "/pool_updates", "Pool updates", "Pool", implemented=True, href="/pool_updates?_pool_bech32={pool_id}"),
    _ko("GET", "/pool_votes", "Pool votes", "Pool", implemented=True, href="/pool_votes?_pool_bech32={pool_id}"),
    _ko("GET", "/asset_list", "Asset list", "Asset", implemented=True, href="/asset_list"),
    _ko("POST", "/asset_info", "Asset information", "Asset", implemented=True),
    _ko("GET", "/asset_history", "Asset history", "Asset", implemented=True, href="/asset_history?_asset_policy={policy}&_asset_name={name}"),
    _ko("GET", "/asset_txs", "Asset transactions", "Asset", implemented=True, href="/asset_txs?_asset_policy={policy}&_asset_name={name}"),
    _ko("GET", "/asset_addresses", "Asset addresses", "Asset", implemented=True, href="/asset_addresses?_asset_policy={policy}&_asset_name={name}"),
    _ko("GET", "/drep_list", "DRep list", "Governance", implemented=True, href="/drep_list"),
    _ko("POST", "/drep_info", "DRep information", "Governance", implemented=True),
    _ko("GET", "/proposal_list", "Proposal list", "Governance", implemented=True, href="/proposal_list"),
    _ko("GET", "/committee_info", "Committee info", "Governance", implemented=True, href="/committee_info"),
    _ko("POST", "/script_info", "Script information", "Script", implemented=True),
    _ko("POST", "/datum_info", "Datum information", "Script", implemented=True),
)


def endpoints_for_face(face: ProviderName) -> tuple[EndpointEntry, ...]:
    if face is ProviderName.BLOCKFROST:
        return BLOCKFROST_ENDPOINTS
    if face is ProviderName.KOIOS:
        return KOIOS_ENDPOINTS
    raise ValueError(f"Unsupported public face: {face}")
