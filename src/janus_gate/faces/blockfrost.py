"""Blockfrost-compatible public face routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from janus_gate.config import ProviderName
from janus_gate.faces.common import pagination_params, run_upstream
from janus_gate.faces.errors import BadRequestError
from janus_gate.mappers.registry import (
    fetch_account_addresses_as,
    fetch_account_as,
    fetch_account_delegations_as,
    fetch_account_history_as,
    fetch_account_rewards_as,
    fetch_account_transactions_as,
    fetch_address_as,
    fetch_address_extended_as,
    fetch_address_transactions_as,
    fetch_address_utxos_as,
    fetch_asset_addresses_as,
    fetch_asset_as,
    fetch_asset_history_as,
    fetch_asset_transactions_as,
    fetch_assets_as,
    fetch_block_as,
    fetch_block_by_epoch_slot_as,
    fetch_block_by_slot_as,
    fetch_block_transactions_as,
    fetch_blocks_next_as,
    fetch_blocks_previous_as,
    fetch_committee_as,
    fetch_datum_as,
    fetch_drep_as,
    fetch_dreps_as,
    fetch_epoch_as,
    fetch_epoch_blocks_as,
    fetch_epoch_parameters_as,
    fetch_epochs_next_as,
    fetch_epochs_previous_as,
    fetch_era_summaries_as,
    fetch_genesis_as,
    fetch_metadata_by_label_as,
    fetch_metadata_labels_as,
    fetch_pool_as,
    fetch_pool_blocks_as,
    fetch_pool_delegators_as,
    fetch_pool_history_as,
    fetch_pool_metadata_as,
    fetch_pool_relays_as,
    fetch_pool_updates_as,
    fetch_pool_votes_as,
    fetch_pools_as,
    fetch_proposals_as,
    fetch_script_as,
    fetch_tip_as,
    fetch_tx_as,
    fetch_tx_cbor_as,
    fetch_tx_metadata_as,
    fetch_tx_utxos_as,
    submit_tx_as,
)


def build_blockfrost_router() -> APIRouter:
    router = APIRouter(tags=["blockfrost-face"])

    @router.get("/blocks/latest")
    async def blocks_latest(request: Request):
        return await run_upstream(
            fetch_tip_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )

    @router.get("/blocks/latest/txs")
    async def blocks_latest_txs(
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        tip = await run_upstream(
            fetch_tip_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )
        block_id = tip.get("hash") or tip.get("height")
        if block_id is None:
            from janus_gate.faces.errors import NotFoundError

            raise NotFoundError("The requested block has not been found.")
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_block_transactions_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                str(block_id),
                **params,
            )
        )

    @router.get("/blocks/slot/{slot_number}")
    async def blocks_by_slot(slot_number: int, request: Request):
        return await run_upstream(
            fetch_block_by_slot_as(
                ProviderName.BLOCKFROST, request.app.state.backend, slot_number
            )
        )

    @router.get("/blocks/epoch/{epoch_number}/slot/{slot_number}")
    async def blocks_by_epoch_slot(
        epoch_number: int, slot_number: int, request: Request
    ):
        return await run_upstream(
            fetch_block_by_epoch_slot_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                epoch_number,
                slot_number,
            )
        )

    @router.get("/blocks/{hash_or_number}/txs")
    async def blocks_txs(
        hash_or_number: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_block_transactions_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                hash_or_number,
                **params,
            )
        )

    @router.get("/blocks/{hash_or_number}/next")
    async def blocks_next(
        hash_or_number: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_blocks_next_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                hash_or_number,
                count=count,
                page=page,
            )
        )

    @router.get("/blocks/{hash_or_number}/previous")
    async def blocks_previous(
        hash_or_number: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_blocks_previous_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                hash_or_number,
                count=count,
                page=page,
            )
        )

    @router.get("/blocks/{hash_or_number}")
    async def blocks_by_id(hash_or_number: str, request: Request):
        return await run_upstream(
            fetch_block_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                hash_or_number,
            )
        )

    @router.get("/network/eras")
    async def network_eras(request: Request):
        return await run_upstream(
            fetch_era_summaries_as(
                ProviderName.BLOCKFROST, request.app.state.backend
            )
        )

    @router.get("/genesis")
    async def genesis(request: Request):
        return await run_upstream(
            fetch_genesis_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )

    @router.get("/epochs/latest")
    async def epochs_latest(request: Request):
        return await run_upstream(
            fetch_epoch_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )

    @router.get("/epochs/latest/parameters")
    async def epochs_latest_parameters(request: Request):
        return await run_upstream(
            fetch_epoch_parameters_as(
                ProviderName.BLOCKFROST, request.app.state.backend
            )
        )

    @router.get("/epochs/{number}")
    async def epochs_by_number(number: int, request: Request):
        return await run_upstream(
            fetch_epoch_as(
                ProviderName.BLOCKFROST, request.app.state.backend, number
            )
        )

    @router.get("/epochs/{number}/parameters")
    async def epochs_parameters(number: int, request: Request):
        return await run_upstream(
            fetch_epoch_parameters_as(
                ProviderName.BLOCKFROST, request.app.state.backend, number
            )
        )

    @router.get("/epochs/{number}/next")
    async def epochs_next(
        number: int,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_epochs_next_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                number,
                count=count,
                page=page,
            )
        )

    @router.get("/epochs/{number}/previous")
    async def epochs_previous(
        number: int,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_epochs_previous_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                number,
                count=count,
                page=page,
            )
        )

    @router.get("/epochs/{number}/blocks")
    async def epochs_blocks(
        number: int,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_epoch_blocks_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                number,
                **params,
            )
        )

    @router.get("/txs/{tx_hash}")
    async def tx_by_hash(tx_hash: str, request: Request):
        return await run_upstream(
            fetch_tx_as(ProviderName.BLOCKFROST, request.app.state.backend, tx_hash)
        )

    @router.get("/txs/{tx_hash}/utxos")
    async def tx_utxos(tx_hash: str, request: Request):
        return await run_upstream(
            fetch_tx_utxos_as(
                ProviderName.BLOCKFROST, request.app.state.backend, tx_hash
            )
        )

    @router.get("/txs/{tx_hash}/metadata")
    async def tx_metadata(tx_hash: str, request: Request):
        return await run_upstream(
            fetch_tx_metadata_as(
                ProviderName.BLOCKFROST, request.app.state.backend, tx_hash
            )
        )

    @router.get("/txs/{tx_hash}/cbor")
    async def tx_cbor(tx_hash: str, request: Request):
        return await run_upstream(
            fetch_tx_cbor_as(
                ProviderName.BLOCKFROST, request.app.state.backend, tx_hash
            )
        )

    @router.get("/metadata/txs/labels")
    async def metadata_labels(
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_metadata_labels_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                **params,
            )
        )

    @router.get("/metadata/txs/labels/{label}")
    async def metadata_by_label(
        label: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_metadata_by_label_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                label,
                **params,
            )
        )

    @router.get("/addresses/{address}")
    async def address_info(address: str, request: Request):
        return await run_upstream(
            fetch_address_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
            )
        )

    @router.get("/addresses/{address}/extended")
    async def address_extended(address: str, request: Request):
        return await run_upstream(
            fetch_address_extended_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
            )
        )

    @router.get("/addresses/{address}/utxos")
    async def address_utxos(
        address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_address_utxos_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
                **params,
            )
        )

    @router.get("/addresses/{address}/transactions")
    async def address_transactions(
        address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_address_transactions_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                address,
                **params,
            )
        )

    @router.get("/accounts/{stake_address}")
    async def account_info(stake_address: str, request: Request):
        return await run_upstream(
            fetch_account_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                stake_address,
            )
        )

    @router.get("/accounts/{stake_address}/rewards")
    async def account_rewards(
        stake_address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_account_rewards_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                stake_address,
                **params,
            )
        )

    @router.get("/accounts/{stake_address}/history")
    async def account_history(
        stake_address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_account_history_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                stake_address,
                **params,
            )
        )

    @router.get("/accounts/{stake_address}/delegations")
    async def account_delegations(
        stake_address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_account_delegations_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                stake_address,
                **params,
            )
        )

    @router.get("/accounts/{stake_address}/addresses")
    async def account_addresses(
        stake_address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_account_addresses_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                stake_address,
                count=count,
                page=page,
            )
        )

    @router.get("/accounts/{stake_address}/transactions")
    async def account_transactions(
        stake_address: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_account_transactions_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                stake_address,
                **params,
            )
        )

    @router.get("/pools")
    async def pools(
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_pools_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                count=count,
                page=page,
                extended=False,
            )
        )

    @router.get("/pools/extended")
    async def pools_extended(
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_pools_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                count=count,
                page=page,
                extended=True,
            )
        )

    @router.get("/pools/{pool_id}")
    async def pool_by_id(pool_id: str, request: Request):
        return await run_upstream(
            fetch_pool_as(
                ProviderName.BLOCKFROST, request.app.state.backend, pool_id
            )
        )

    @router.get("/pools/{pool_id}/history")
    async def pool_history(
        pool_id: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_pool_history_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                pool_id,
                **params,
            )
        )

    @router.get("/pools/{pool_id}/metadata")
    async def pool_metadata(pool_id: str, request: Request):
        return await run_upstream(
            fetch_pool_metadata_as(
                ProviderName.BLOCKFROST, request.app.state.backend, pool_id
            )
        )

    @router.get("/pools/{pool_id}/delegators")
    async def pool_delegators(
        pool_id: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_pool_delegators_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                pool_id,
                count=count,
                page=page,
            )
        )

    @router.get("/pools/{pool_id}/relays")
    async def pool_relays(pool_id: str, request: Request):
        return await run_upstream(
            fetch_pool_relays_as(
                ProviderName.BLOCKFROST, request.app.state.backend, pool_id
            )
        )

    @router.get("/pools/{pool_id}/blocks")
    async def pool_blocks(
        pool_id: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_pool_blocks_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                pool_id,
                **params,
            )
        )

    @router.get("/pools/{pool_id}/updates")
    async def pool_updates(
        pool_id: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_pool_updates_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                pool_id,
                **params,
            )
        )

    @router.get("/pools/{pool_id}/votes")
    async def pool_votes(
        pool_id: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_pool_votes_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                pool_id,
                **params,
            )
        )

    @router.get("/assets")
    async def assets(
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_assets_as(
                ProviderName.BLOCKFROST, request.app.state.backend, **params
            )
        )

    @router.get("/assets/{asset}")
    async def asset_by_id(asset: str, request: Request):
        return await run_upstream(
            fetch_asset_as(
                ProviderName.BLOCKFROST, request.app.state.backend, asset
            )
        )

    @router.get("/assets/{asset}/history")
    async def asset_history(
        asset: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_asset_history_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                asset,
                **params,
            )
        )

    @router.get("/assets/{asset}/transactions")
    async def asset_transactions(
        asset: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_asset_transactions_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                asset,
                **params,
            )
        )

    @router.get("/assets/{asset}/addresses")
    async def asset_addresses(
        asset: str,
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
        order: str = Query(default="asc"),
    ):
        params = pagination_params(count, page, order)
        return await run_upstream(
            fetch_asset_addresses_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                asset,
                **params,
            )
        )

    @router.get("/scripts/datum/{datum_hash}")
    async def datum_by_hash(datum_hash: str, request: Request):
        return await run_upstream(
            fetch_datum_as(
                ProviderName.BLOCKFROST, request.app.state.backend, datum_hash
            )
        )

    @router.get("/scripts/{script_hash}")
    async def script_by_hash(script_hash: str, request: Request):
        return await run_upstream(
            fetch_script_as(
                ProviderName.BLOCKFROST, request.app.state.backend, script_hash
            )
        )

    @router.get("/governance/committee")
    async def governance_committee(request: Request):
        return await run_upstream(
            fetch_committee_as(ProviderName.BLOCKFROST, request.app.state.backend)
        )

    @router.get("/governance/dreps")
    async def governance_dreps(
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_dreps_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                count=count,
                page=page,
            )
        )

    @router.get("/governance/dreps/{drep_id}")
    async def governance_drep(drep_id: str, request: Request):
        return await run_upstream(
            fetch_drep_as(
                ProviderName.BLOCKFROST, request.app.state.backend, drep_id
            )
        )

    @router.get("/governance/proposals")
    async def governance_proposals(
        request: Request,
        count: int = Query(default=100, ge=1, le=100),
        page: int = Query(default=1, ge=1),
    ):
        return await run_upstream(
            fetch_proposals_as(
                ProviderName.BLOCKFROST,
                request.app.state.backend,
                count=count,
                page=page,
            )
        )

    @router.post("/tx/submit")
    async def tx_submit(request: Request):
        body = await request.body()
        if not body:
            raise BadRequestError("Empty transaction body")
        result = await run_upstream(submit_tx_as(request.app.state.backend, body))
        if isinstance(result, str):
            return PlainTextResponse(f'"{result}"', media_type="application/json")
        return result

    return router
