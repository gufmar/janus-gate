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
    _bf("GET", "/network/eras", "Era summaries", "Network / blocks"),
    # Blocks
    _bf("GET", "/blocks/{hash_or_number}", "Specific block", "Network / blocks", implemented=True, href="/blocks/{hash_or_number}"),
    _bf("GET", "/blocks/{hash_or_number}/next", "Next blocks", "Network / blocks"),
    _bf("GET", "/blocks/{hash_or_number}/previous", "Previous blocks", "Network / blocks"),
    _bf("GET", "/blocks/slot/{slot_number}", "Block by slot", "Network / blocks"),
    _bf("GET", "/blocks/epoch/{epoch_number}/slot/{slot_number}", "Block by epoch slot", "Network / blocks"),
    _bf("GET", "/blocks/latest/txs", "Latest block transactions", "Network / blocks"),
    _bf("GET", "/blocks/{hash_or_number}/txs", "Block transactions", "Network / blocks"),
    _bf("GET", "/blocks/{hash_or_number}/addresses", "Addresses in block", "Network / blocks"),
    # Epochs
    _bf("GET", "/epochs/latest", "Latest epoch", "Epochs", implemented=True, href="/epochs/latest"),
    _bf("GET", "/epochs/latest/parameters", "Latest epoch parameters", "Epochs", implemented=True, href="/epochs/latest/parameters"),
    _bf("GET", "/epochs/{number}", "Specific epoch", "Epochs", implemented=True, href="/epochs/{number}"),
    _bf("GET", "/epochs/{number}/parameters", "Epoch parameters", "Epochs", implemented=True, href="/epochs/{number}/parameters"),
    _bf("GET", "/epochs/{number}/next", "Next epochs", "Epochs"),
    _bf("GET", "/epochs/{number}/previous", "Previous epochs", "Epochs"),
    _bf("GET", "/epochs/{number}/stakes", "Epoch stake distribution", "Epochs"),
    _bf("GET", "/epochs/{number}/blocks", "Epoch blocks", "Epochs"),
    # Transactions
    _bf("GET", "/txs/{hash}", "Transaction", "Transactions"),
    _bf("GET", "/txs/{hash}/utxos", "Transaction UTxOs", "Transactions"),
    _bf("GET", "/txs/{hash}/metadata", "Transaction metadata", "Transactions"),
    _bf("GET", "/txs/{hash}/cbor", "Transaction CBOR", "Transactions"),
    _bf("POST", "/tx/submit", "Submit transaction", "Transactions", implemented=True),
    _bf("GET", "/metadata/txs/labels", "Metadata labels", "Transactions"),
    # Addresses
    _bf("GET", "/addresses/{address}", "Address info", "Addresses", implemented=True, href="/addresses/{address}"),
    _bf("GET", "/addresses/{address}/extended", "Address extended", "Addresses"),
    _bf("GET", "/addresses/{address}/total", "Address totals", "Addresses"),
    _bf("GET", "/addresses/{address}/utxos", "Address UTxOs", "Addresses", implemented=True, href="/addresses/{address}/utxos"),
    _bf("GET", "/addresses/{address}/transactions", "Address transactions", "Addresses", implemented=True, href="/addresses/{address}/transactions"),
    _bf("GET", "/addresses/{address}/txs", "Address txs (legacy)", "Addresses"),
    # Accounts
    _bf("GET", "/accounts/{stake_address}", "Account info", "Accounts"),
    _bf("GET", "/accounts/{stake_address}/rewards", "Account rewards", "Accounts"),
    _bf("GET", "/accounts/{stake_address}/history", "Account history", "Accounts"),
    _bf("GET", "/accounts/{stake_address}/delegations", "Account delegations", "Accounts"),
    _bf("GET", "/accounts/{stake_address}/addresses", "Account addresses", "Accounts"),
    _bf("GET", "/accounts/{stake_address}/utxos", "Account UTxOs", "Accounts"),
    _bf("GET", "/accounts/{stake_address}/transactions", "Account transactions", "Accounts"),
    # Pools
    _bf("GET", "/pools", "Pool list", "Pools"),
    _bf("GET", "/pools/extended", "Pool list extended", "Pools"),
    _bf("GET", "/pools/{pool_id}", "Pool info", "Pools"),
    _bf("GET", "/pools/{pool_id}/history", "Pool history", "Pools"),
    _bf("GET", "/pools/{pool_id}/metadata", "Pool metadata", "Pools"),
    _bf("GET", "/pools/{pool_id}/delegators", "Pool delegators", "Pools"),
    # Assets / scripts / governance (abbrev)
    _bf("GET", "/assets", "Assets", "Assets"),
    _bf("GET", "/assets/{asset}", "Asset info", "Assets"),
    _bf("GET", "/scripts", "Scripts", "Scripts"),
    _bf("GET", "/scripts/{script_hash}", "Script info", "Scripts"),
    _bf("GET", "/governance/dreps", "DReps", "Governance"),
    _bf("GET", "/governance/proposals", "Proposals", "Governance"),
    _bf("GET", "/governance/committee", "Committee", "Governance"),
    _bf("GET", "/mempool", "Mempool", "Mempool / utils"),
    _bf("POST", "/utils/txs/evaluate", "Evaluate transaction", "Mempool / utils"),
)

KOIOS_ENDPOINTS: tuple[EndpointEntry, ...] = (
    _ko("GET", "/tip", "Chain tip", "Network", implemented=True, href="/tip"),
    _ko("GET", "/genesis", "Genesis", "Network", implemented=True, href="/genesis"),
    _ko("GET", "/era_summaries", "Era summaries", "Network"),
    _ko("GET", "/totals", "Historical totals", "Network"),
    _ko("GET", "/param_updates", "Param updates", "Network"),
    _ko("GET", "/cli_protocol_params", "CLI protocol params", "Network"),
    _ko("GET", "/epoch_info", "Epoch information", "Epoch", implemented=True, href="/epoch_info"),
    _ko("GET", "/epoch_params", "Epoch parameters", "Epoch", implemented=True, href="/epoch_params"),
    _ko("GET", "/epoch_block_protocols", "Epoch block protocols", "Epoch"),
    _ko("GET", "/blocks", "Block list", "Block"),
    _ko("POST", "/block_info", "Block information", "Block", implemented=True),
    _ko("POST", "/block_txs", "Block transactions", "Block"),
    _ko("POST", "/block_tx_info", "Block tx details", "Block"),
    _ko("POST", "/tx_info", "Transaction information", "Transactions"),
    _ko("POST", "/tx_utxos", "Transaction UTxOs", "Transactions"),
    _ko("POST", "/tx_metadata", "Transaction metadata", "Transactions"),
    _ko("POST", "/tx_cbor", "Transaction CBOR", "Transactions"),
    _ko("POST", "/submittx", "Submit transaction", "Transactions", implemented=True),
    _ko("GET", "/tx_metalabels", "Metadata labels", "Transactions"),
    _ko("POST", "/address_info", "Address information", "Address", implemented=True),
    _ko("POST", "/address_utxos", "Address UTxOs", "Address", implemented=True),
    _ko("POST", "/address_txs", "Address transactions", "Address", implemented=True),
    _ko("POST", "/address_assets", "Address assets", "Address"),
    _ko("POST", "/account_info", "Account information", "Stake account"),
    _ko("POST", "/account_rewards", "Account rewards", "Stake account"),
    _ko("POST", "/account_addresses", "Account addresses", "Stake account"),
    _ko("GET", "/pool_list", "Pool list", "Pool"),
    _ko("POST", "/pool_info", "Pool information", "Pool"),
    _ko("GET", "/asset_list", "Asset list", "Asset"),
    _ko("POST", "/asset_info", "Asset information", "Asset"),
    _ko("GET", "/drep_list", "DRep list", "Governance"),
    _ko("GET", "/proposal_list", "Proposal list", "Governance"),
    _ko("GET", "/committee_info", "Committee info", "Governance"),
    _ko("POST", "/script_info", "Script information", "Script"),
    _ko("POST", "/datum_info", "Datum information", "Script"),
)


def endpoints_for_face(face: ProviderName) -> tuple[EndpointEntry, ...]:
    if face is ProviderName.BLOCKFROST:
        return BLOCKFROST_ENDPOINTS
    if face is ProviderName.KOIOS:
        return KOIOS_ENDPOINTS
    raise ValueError(f"Unsupported public face: {face}")
