"""Tip / latest-block response mappers (thin re-export of block mappers)."""

from janus_gate.mappers.block import (
    blockfrost_latest_to_koios_tip,
    koios_tip_to_blockfrost,
)

__all__ = ["blockfrost_latest_to_koios_tip", "koios_tip_to_blockfrost"]
