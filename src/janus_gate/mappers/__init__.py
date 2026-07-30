"""Response mappers between Cardano API providers."""

from __future__ import annotations

from typing import Any

__all__ = [
    "fetch_account_as",
    "fetch_address_as",
    "fetch_address_transactions_as",
    "fetch_address_utxos_as",
    "fetch_asset_as",
    "fetch_block_as",
    "fetch_epoch_as",
    "fetch_epoch_parameters_as",
    "fetch_genesis_as",
    "fetch_pool_as",
    "fetch_pools_as",
    "fetch_tip_as",
    "fetch_tx_as",
    "fetch_tx_cbor_as",
    "fetch_tx_metadata_as",
    "fetch_tx_utxos_as",
    "submit_tx_as",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from janus_gate.mappers import registry as _registry

        return getattr(_registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
