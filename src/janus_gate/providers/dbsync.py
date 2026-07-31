"""cardano-db-sync PostgreSQL backend (Phase 2 MVP)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import asyncpg

from janus_gate.config import SshTunnelConfig
from janus_gate.providers.base import ProviderError
from janus_gate.providers.ssh_tunnel import start_ssh_tunnel, stop_ssh_tunnel

logger = logging.getLogger("janus_gate.dbsync")

_BLOCK_SELECT = """
SELECT
  encode(b.hash, 'hex') AS hash,
  b.block_no,
  b.epoch_no,
  b.slot_no,
  b.epoch_slot_no,
  EXTRACT(EPOCH FROM b.time)::bigint AS block_time,
  b.size,
  b.tx_count,
  b.vrf_key,
  encode(b.op_cert, 'hex') AS op_cert,
  b.op_cert_counter,
  encode(prev.hash, 'hex') AS previous_hash,
  encode(nxt.hash, 'hex') AS next_hash,
  COALESCE(ph.view, encode(sl.hash, 'hex')) AS slot_leader,
  COALESCE(
    (SELECT MAX(block_no) FROM block WHERE block_no IS NOT NULL) - b.block_no,
    0
  ) AS confirmations,
  (
    SELECT COALESCE(SUM(t.out_sum), 0) FROM tx t WHERE t.block_id = b.id
  ) AS out_sum,
  (
    SELECT COALESCE(SUM(t.fee), 0) FROM tx t WHERE t.block_id = b.id
  ) AS fees
FROM block b
LEFT JOIN block prev ON prev.id = b.previous_id
LEFT JOIN block nxt ON nxt.previous_id = b.id
LEFT JOIN slot_leader sl ON sl.id = b.slot_leader_id
LEFT JOIN pool_hash ph ON ph.id = sl.pool_hash_id
"""


def _row_to_dict(row: asyncpg.Record | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _not_found(message: str = "The requested component has not been found.") -> ProviderError:
    return ProviderError(404, message)


def _nyi(op: str) -> ProviderError:
    return ProviderError(
        501,
        f"dbsync backend does not implement {op} yet",
    )


def _safe_dsn_endpoint(dsn: str) -> tuple[str, int | None]:
    """Host/port for logs (never includes credentials)."""
    try:
        parsed = urlparse(dsn)
        return parsed.hostname or "unknown", parsed.port
    except Exception:  # noqa: BLE001
        return "unparseable", None


class DbSyncProvider:
    """BackendProvider backed by an official cardano-db-sync schema."""

    name = "dbsync"

    def __init__(
        self,
        dsn: str,
        *,
        ssh_tunnel: SshTunnelConfig | None = None,
    ) -> None:
        self._dsn = dsn
        self._ssh_tunnel_cfg = ssh_tunnel
        self._tunnel: Any | None = None
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        connect_dsn = self._dsn
        cfg = self._ssh_tunnel_cfg
        dsn_host, _ = _safe_dsn_endpoint(self._dsn)
        logger.info(
            "dbsync connecting (dsn_host=%s ssh_tunnel=%s)",
            dsn_host,
            "enabled" if cfg is not None and cfg.enabled else "disabled",
        )
        if cfg is not None and cfg.enabled:
            logger.info(
                "dbsync opening SSH tunnel to %s@%s:%s (key=%s passphrase=%s)",
                cfg.user,
                cfg.host,
                cfg.port,
                cfg.private_key_path or ("inline" if cfg.private_key else "none"),
                "set" if cfg.passphrase else "missing",
            )
            self._tunnel, connect_dsn = await asyncio.to_thread(
                start_ssh_tunnel, dsn=self._dsn, cfg=cfg
            )
        try:
            self._pool = await asyncpg.create_pool(
                connect_dsn, min_size=1, max_size=5
            )
            await self._probe_connection()
        except Exception:
            if self._tunnel is not None:
                await asyncio.to_thread(stop_ssh_tunnel, self._tunnel)
                self._tunnel = None
            raise

    async def _probe_connection(self) -> None:
        """Run a lightweight startup check and log tip height when available."""
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            tip_height = await conn.fetchval(
                "SELECT MAX(block_no) FROM block WHERE block_no IS NOT NULL"
            )
            network = await conn.fetchval(
                "SELECT network_name FROM meta ORDER BY id LIMIT 1"
            )
        logger.info(
            "dbsync connection ok (network=%s tip_height=%s ssh_tunnel=%s)",
            network or "unknown",
            tip_height if tip_height is not None else "empty",
            "up" if self._tunnel is not None else "unused",
        )

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        if self._tunnel is not None:
            await asyncio.to_thread(stop_ssh_tunnel, self._tunnel)
            self._tunnel = None

    async def _pool_or_raise(self) -> asyncpg.Pool:
        if self._pool is None:
            await self.connect()
        assert self._pool is not None
        return self._pool

    async def _fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        pool = await self._pool_or_raise()
        async with pool.acquire() as conn:
            return _row_to_dict(await conn.fetchrow(query, *args))

    async def _fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        pool = await self._pool_or_raise()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]

    async def get_tip(self) -> Any:
        row = await self._fetchrow(
            _BLOCK_SELECT
            + """
            WHERE b.block_no = (SELECT MAX(block_no) FROM block WHERE block_no IS NOT NULL)
            """
        )
        if not row:
            raise _not_found("No blocks found in db-sync")
        return row

    async def get_block(self, hash_or_number: str) -> Any:
        if hash_or_number.isdigit():
            row = await self._fetchrow(
                _BLOCK_SELECT + " WHERE b.block_no = $1::integer",
                int(hash_or_number),
            )
        else:
            row = await self._fetchrow(
                _BLOCK_SELECT + " WHERE encode(b.hash, 'hex') = lower($1)",
                hash_or_number,
            )
        if not row:
            raise _not_found("The requested component has not been found.")
        return row

    async def get_genesis(self) -> Any:
        row = await self._fetchrow(
            """
            SELECT
              network_name,
              EXTRACT(EPOCH FROM start_time)::bigint AS system_start
            FROM meta
            ORDER BY id
            LIMIT 1
            """
        )
        return row

    async def get_epoch(self, number: int | None = None) -> Any:
        if number is None:
            row = await self._fetchrow(
                """
                SELECT
                  e.no AS epoch_no,
                  EXTRACT(EPOCH FROM e.start_time)::bigint AS start_time,
                  EXTRACT(EPOCH FROM e.end_time)::bigint AS end_time,
                  e.blk_count,
                  e.tx_count,
                  e.out_sum,
                  e.fees,
                  EXTRACT(EPOCH FROM (
                    SELECT MIN(b.time) FROM block b WHERE b.epoch_no = e.no
                  ))::bigint AS first_block_time,
                  EXTRACT(EPOCH FROM (
                    SELECT MAX(b.time) FROM block b WHERE b.epoch_no = e.no
                  ))::bigint AS last_block_time,
                  (
                    SELECT SUM(es.amount)
                    FROM epoch_stake es
                    WHERE es.epoch_no = e.no
                  ) AS active_stake
                FROM epoch e
                ORDER BY e.no DESC
                LIMIT 1
                """
            )
        else:
            row = await self._fetchrow(
                """
                SELECT
                  e.no AS epoch_no,
                  EXTRACT(EPOCH FROM e.start_time)::bigint AS start_time,
                  EXTRACT(EPOCH FROM e.end_time)::bigint AS end_time,
                  e.blk_count,
                  e.tx_count,
                  e.out_sum,
                  e.fees,
                  EXTRACT(EPOCH FROM (
                    SELECT MIN(b.time) FROM block b WHERE b.epoch_no = e.no
                  ))::bigint AS first_block_time,
                  EXTRACT(EPOCH FROM (
                    SELECT MAX(b.time) FROM block b WHERE b.epoch_no = e.no
                  ))::bigint AS last_block_time,
                  (
                    SELECT SUM(es.amount)
                    FROM epoch_stake es
                    WHERE es.epoch_no = e.no
                  ) AS active_stake
                FROM epoch e
                WHERE e.no = $1
                """,
                number,
            )
        if not row:
            raise _not_found("The requested component has not been found.")
        return row

    async def get_epochs_next(
        self,
        number: int,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self._epochs_adjacent(number, direction=1, count=count, page=page)

    async def get_epochs_previous(
        self,
        number: int,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        return await self._epochs_adjacent(number, direction=-1, count=count, page=page)

    async def _epochs_adjacent(
        self,
        number: int,
        *,
        direction: int,
        count: int,
        page: int,
    ) -> list[dict[str, Any]]:
        tip = await self.get_tip()
        tip_epoch = int(tip["epoch_no"])
        start = number + direction * (1 + (page - 1) * count)
        out: list[dict[str, Any]] = []
        for i in range(count):
            epoch_no = start + direction * i
            if epoch_no < 0 or epoch_no > tip_epoch:
                break
            try:
                row = await self.get_epoch(epoch_no)
            except ProviderError as exc:
                if exc.status_code == 404:
                    break
                raise
            if not isinstance(row, dict):
                break
            out.append(row)
        if direction < 0:
            out.reverse()
        return out

    async def get_epoch_parameters(self, number: int | None = None) -> Any:
        if number is None:
            row = await self._fetchrow(
                """
                SELECT
                  ep.epoch_no,
                  ep.min_fee_a,
                  ep.min_fee_b,
                  ep.max_block_size,
                  ep.max_tx_size,
                  ep.max_bh_size,
                  ep.key_deposit,
                  ep.pool_deposit,
                  ep.max_epoch,
                  ep.optimal_pool_count,
                  ep.influence,
                  ep.monetary_expand_rate,
                  ep.treasury_growth_rate,
                  ep.decentralisation,
                  encode(ep.extra_entropy, 'hex') AS extra_entropy,
                  ep.protocol_major,
                  ep.protocol_minor,
                  ep.min_utxo_value,
                  ep.min_pool_cost,
                  encode(ep.nonce, 'hex') AS nonce,
                  ep.coins_per_utxo_size,
                  ep.price_mem,
                  ep.price_step,
                  ep.max_tx_ex_mem,
                  ep.max_tx_ex_steps,
                  ep.max_block_ex_mem,
                  ep.max_block_ex_steps,
                  ep.max_val_size,
                  ep.collateral_percent,
                  ep.max_collateral_inputs,
                  cm.costs AS cost_models
                FROM epoch_param ep
                LEFT JOIN cost_model cm ON cm.id = ep.cost_model_id
                ORDER BY ep.epoch_no DESC
                LIMIT 1
                """
            )
        else:
            row = await self._fetchrow(
                """
                SELECT
                  ep.epoch_no,
                  ep.min_fee_a,
                  ep.min_fee_b,
                  ep.max_block_size,
                  ep.max_tx_size,
                  ep.max_bh_size,
                  ep.key_deposit,
                  ep.pool_deposit,
                  ep.max_epoch,
                  ep.optimal_pool_count,
                  ep.influence,
                  ep.monetary_expand_rate,
                  ep.treasury_growth_rate,
                  ep.decentralisation,
                  encode(ep.extra_entropy, 'hex') AS extra_entropy,
                  ep.protocol_major,
                  ep.protocol_minor,
                  ep.min_utxo_value,
                  ep.min_pool_cost,
                  encode(ep.nonce, 'hex') AS nonce,
                  ep.coins_per_utxo_size,
                  ep.price_mem,
                  ep.price_step,
                  ep.max_tx_ex_mem,
                  ep.max_tx_ex_steps,
                  ep.max_block_ex_mem,
                  ep.max_block_ex_steps,
                  ep.max_val_size,
                  ep.collateral_percent,
                  ep.max_collateral_inputs,
                  cm.costs AS cost_models
                FROM epoch_param ep
                LEFT JOIN cost_model cm ON cm.id = ep.cost_model_id
                WHERE ep.epoch_no = $1
                """,
                number,
            )
        if not row:
            raise _not_found("The requested component has not been found.")
        return row

    async def _address_amounts(self, address: str) -> tuple[list[dict[str, str]], bool, str | None]:
        lovelace_row = await self._fetchrow(
            """
            SELECT
              COALESCE(SUM(o.value), 0) AS lovelace,
              BOOL_OR(o.address_has_script) AS script,
              MAX(sa.view) AS stake_address
            FROM tx_out o
            JOIN tx ON tx.id = o.tx_id
            LEFT JOIN tx_in i
              ON i.tx_out_id = tx.id AND i.tx_out_index = o.index
            LEFT JOIN stake_address sa ON sa.id = o.stake_address_id
            WHERE o.address = $1 AND i.id IS NULL
            """,
            address,
        )
        assets = await self._fetch(
            """
            SELECT
              encode(ma.policy, 'hex') AS policy_id,
              encode(ma.name, 'hex') AS asset_name,
              SUM(mto.quantity) AS quantity
            FROM tx_out o
            JOIN tx ON tx.id = o.tx_id
            LEFT JOIN tx_in i
              ON i.tx_out_id = tx.id AND i.tx_out_index = o.index
            JOIN ma_tx_out mto ON mto.tx_out_id = o.id
            JOIN multi_asset ma ON ma.id = mto.ident
            WHERE o.address = $1 AND i.id IS NULL
            GROUP BY ma.policy, ma.name
            """,
            address,
        )
        amounts: list[dict[str, str]] = [
            {
                "unit": "lovelace",
                "quantity": str(int((lovelace_row or {}).get("lovelace") or 0)),
            }
        ]
        for asset in assets:
            unit = f"{asset['policy_id']}{asset['asset_name']}"
            amounts.append({"unit": unit, "quantity": str(int(asset["quantity"]))})
        script = bool((lovelace_row or {}).get("script"))
        stake = (lovelace_row or {}).get("stake_address")
        return amounts, script, stake

    async def get_address_info(self, address: str) -> Any:
        amounts, script, stake = await self._address_amounts(address)
        return {
            "address": address,
            "amount": amounts,
            "lovelace": amounts[0]["quantity"] if amounts else "0",
            "stake_address": stake,
            "script": script,
        }

    async def get_address_utxos(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        offset = max(page - 1, 0) * max(count, 1)
        order_sql = "ASC" if order != "desc" else "DESC"
        rows = await self._fetch(
            f"""
            SELECT
              o.address,
              encode(tx.hash, 'hex') AS tx_hash,
              o.index AS tx_index,
              o.value,
              encode(b.hash, 'hex') AS block_hash,
              encode(o.data_hash, 'hex') AS data_hash,
              o.id AS tx_out_id
            FROM tx_out o
            JOIN tx ON tx.id = o.tx_id
            JOIN block b ON b.id = tx.block_id
            LEFT JOIN tx_in i
              ON i.tx_out_id = tx.id AND i.tx_out_index = o.index
            WHERE o.address = $1 AND i.id IS NULL
            ORDER BY b.block_no {order_sql}, tx.block_index {order_sql}, o.index {order_sql}
            LIMIT $2 OFFSET $3
            """,
            address,
            count,
            offset,
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            assets = await self._fetch(
                """
                SELECT
                  encode(ma.policy, 'hex') AS policy_id,
                  encode(ma.name, 'hex') AS asset_name,
                  mto.quantity
                FROM ma_tx_out mto
                JOIN multi_asset ma ON ma.id = mto.ident
                WHERE mto.tx_out_id = $1
                """,
                row["tx_out_id"],
            )
            amount = [{"unit": "lovelace", "quantity": str(int(row["value"]))}]
            for asset in assets:
                amount.append(
                    {
                        "unit": f"{asset['policy_id']}{asset['asset_name']}",
                        "quantity": str(int(asset["quantity"])),
                    }
                )
            result.append({**row, "amount": amount})
        return result

    async def get_account_info(self, stake_address: str) -> Any:
        row = await self._fetchrow(
            """
            SELECT
              sa.view AS stake_address,
              sa.id AS stake_id,
              (
                SELECT sr.epoch_no
                FROM stake_registration sr
                WHERE sr.addr_id = sa.id
                ORDER BY sr.id DESC
                LIMIT 1
              ) AS active_epoch,
              EXISTS (
                SELECT 1 FROM stake_registration sr WHERE sr.addr_id = sa.id
              )
              AND NOT EXISTS (
                SELECT 1
                FROM stake_deregistration sd
                WHERE sd.addr_id = sa.id
                  AND sd.id > COALESCE(
                    (SELECT MAX(sr2.id) FROM stake_registration sr2 WHERE sr2.addr_id = sa.id),
                    0
                  )
              ) AS active,
              (
                SELECT COALESCE(SUM(o.value), 0)
                FROM tx_out o
                JOIN tx ON tx.id = o.tx_id
                LEFT JOIN tx_in i
                  ON i.tx_out_id = tx.id AND i.tx_out_index = o.index
                WHERE o.stake_address_id = sa.id AND i.id IS NULL
              ) AS controlled_amount,
              (
                SELECT COALESCE(SUM(r.amount), 0)
                FROM reward r
                WHERE r.addr_id = sa.id
              ) AS rewards_sum,
              (
                SELECT COALESCE(SUM(w.amount), 0)
                FROM withdrawal w
                WHERE w.addr_id = sa.id
              ) AS withdrawals_sum,
              (
                SELECT ph.view
                FROM delegation d
                JOIN pool_hash ph ON ph.id = d.pool_hash_id
                WHERE d.addr_id = sa.id
                ORDER BY d.id DESC
                LIMIT 1
              ) AS pool_id
            FROM stake_address sa
            WHERE sa.view = $1
            """,
            stake_address,
        )
        if not row:
            return None
        rewards = int(row.get("rewards_sum") or 0)
        withdrawals = int(row.get("withdrawals_sum") or 0)
        withdrawable = max(rewards - withdrawals, 0)
        return {
            **row,
            "reserves_sum": 0,
            "treasury_sum": 0,
            "withdrawable_amount": withdrawable,
        }

    async def get_tx(self, tx_hash: str) -> Any:
        row = await self._fetchrow(
            """
            SELECT
              encode(tx.hash, 'hex') AS tx_hash,
              encode(b.hash, 'hex') AS block_hash,
              b.block_no AS block_height,
              EXTRACT(EPOCH FROM b.time)::bigint AS block_time,
              b.slot_no,
              tx.block_index,
              tx.out_sum,
              tx.fee,
              tx.deposit,
              tx.size,
              tx.invalid_before,
              tx.invalid_hereafter,
              tx.valid_contract,
              (
                SELECT COUNT(*) FROM tx_in WHERE tx_in_id = tx.id
              ) + (
                SELECT COUNT(*) FROM tx_out WHERE tx_id = tx.id
              ) AS utxo_count,
              (
                SELECT COUNT(*) FROM withdrawal WHERE tx_id = tx.id
              ) AS withdrawal_count
            FROM tx
            JOIN block b ON b.id = tx.block_id
            WHERE encode(tx.hash, 'hex') = lower($1)
            """,
            tx_hash,
        )
        if not row:
            raise _not_found("The requested component has not been found.")
        return row

    # --- MVP Gaps / later ---

    async def get_block_transactions(
        self,
        hash_or_number: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        raise _nyi("get_block_transactions")

    async def get_address_transactions(
        self,
        address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        raise _nyi("get_address_transactions")

    async def submit_tx(self, cbor: bytes) -> Any:
        raise _nyi("submit_tx")

    async def get_tx_utxos(self, tx_hash: str) -> Any:
        raise _nyi("get_tx_utxos")

    async def get_tx_metadata(self, tx_hash: str) -> Any:
        raise _nyi("get_tx_metadata")

    async def get_tx_cbor(self, tx_hash: str) -> Any:
        raise _nyi("get_tx_cbor")

    async def get_account_rewards(self, stake_address: str) -> Any:
        raise _nyi("get_account_rewards")

    async def get_account_history(self, stake_address: str) -> Any:
        raise _nyi("get_account_history")

    async def get_account_addresses(self, stake_address: str) -> Any:
        raise _nyi("get_account_addresses")

    async def get_account_transactions(
        self,
        stake_address: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        raise _nyi("get_account_transactions")

    async def get_pools(self, *, count: int = 100, page: int = 1) -> Any:
        raise _nyi("get_pools")

    async def get_pools_extended(self, *, count: int = 100, page: int = 1) -> Any:
        raise _nyi("get_pools_extended")

    async def get_pool(self, pool_id: str) -> Any:
        raise _nyi("get_pool")

    async def get_pool_history(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        raise _nyi("get_pool_history")

    async def get_pool_metadata(self, pool_id: str) -> Any:
        raise _nyi("get_pool_metadata")

    async def get_pool_delegators(
        self,
        pool_id: str,
        *,
        count: int = 100,
        page: int = 1,
    ) -> Any:
        raise _nyi("get_pool_delegators")

    async def get_pool_relays(self, pool_id: str) -> Any:
        raise _nyi("get_pool_relays")

    async def get_epoch_blocks(
        self,
        number: int,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        raise _nyi("get_epoch_blocks")

    async def get_committee(self) -> Any:
        raise _nyi("get_committee")

    async def get_dreps(self, *, count: int = 100, page: int = 1) -> Any:
        raise _nyi("get_dreps")

    async def get_drep(self, drep_id: str) -> Any:
        raise _nyi("get_drep")

    async def get_proposals(self, *, count: int = 100, page: int = 1) -> Any:
        raise _nyi("get_proposals")

    async def get_script(self, script_hash: str) -> Any:
        raise _nyi("get_script")

    async def get_datum(self, datum_hash: str) -> Any:
        raise _nyi("get_datum")

    async def get_metadata_labels(
        self,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        raise _nyi("get_metadata_labels")

    async def get_metadata_by_label(
        self,
        label: str,
        *,
        count: int = 100,
        page: int = 1,
        order: str = "asc",
    ) -> Any:
        raise _nyi("get_metadata_by_label")

    async def get_asset(self, asset: str) -> Any:
        raise _nyi("get_asset")
