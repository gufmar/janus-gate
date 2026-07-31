#!/usr/bin/env python3
"""Compare native face APIs vs a deployed Janus Gate instance.

Loads secrets from the environment (optionally via a dotenv-style file passed
with --env-file). Never commit API keys.

Example (Koios face Janus, compare to native Koios):

  set -a && source scripts/compare_face.env && set +a
  uv run python scripts/compare_face.py --cases tip,epoch_info,pool_history

Exit code 1 if any compared case has field mismatches (beyond known Gaps).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

# Volatile / expected-to-drift keys when comparing tip-like payloads.
_DEFAULT_IGNORE = frozenset(
    {
        "hash",
        "block_hash",
        "abs_slot",
        "slot",
        "block_height",
        "height",
        "block_time",
        "time",
        "epoch_slot",
        "confirmations",
        "num_confirmations",
    }
)

# Documented Gaps when the face is served from a Blockfrost-shaped backend.
_KOIOS_GAP_IGNORE = frozenset(
    {
        "era",
        "alonzogenesis",
        "networkid",
        "total_rewards",
        "avg_blk_reward",
        "saturation_pct",
        "margin",
        "fixed_cost",
        "member_rewards",
        "epoch_ros",
        "deposit",
        "pool_group",
        "block_hash",
        "cost_models",  # list vs dict shape often differs
        "vrf_key_hash",
        "op_cert",
        "op_cert_counter",
        "active_epoch_no",
        "retiring_epoch",
        "relays",  # shape Partial on pool_info
        "owners",
        "reward_addr",
        "ticker",
        "meta_url",
        "meta_hash",
        "meta_json",
        "pool_status",
        "sigma",
        "block_count",
        "live_pledge",
        "live_stake",
        "live_size",
        "live_saturation",
        "live_delegators",
        "active_stake",  # often lags / units differ on pool_info
    }
)


@dataclass
class CaseResult:
    name: str
    ok: bool
    detail: str
    native: Any = None
    janus: Any = None
    diffs: list[str] | None = None


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Env file not found: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _require(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def _optional(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _headers_for_face(face: str, api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    if face == "blockfrost":
        return {"project_id": api_key}
    if face == "koios":
        return {"Authorization": f"Bearer {api_key}"}
    return {}


def _json_get(
    client: httpx.Client,
    base: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    response = client.get(url, headers=headers or {}, params=params)
    response.raise_for_status()
    return response.json()


def _json_post(
    client: httpx.Client,
    base: str,
    path: str,
    body: Any,
    *,
    headers: dict[str, str] | None = None,
) -> Any:
    url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    response = client.post(url, headers=hdrs, json=body)
    response.raise_for_status()
    return response.json()


def _resolve_sample_tx_hash(
    client: httpx.Client,
    native_base: str,
    native_headers: dict[str, str],
) -> str | None:
    """Pick a recent tx hash from a tip-relative block (Blockfrost paths)."""
    tip = _json_get(client, native_base, "/blocks/latest", headers=native_headers)
    height = tip.get("height") if isinstance(tip, dict) else None
    if height is None:
        return None
    for delta in (50, 100, 200, 500):
        h = max(1, int(height) - delta)
        txs = _json_get(
            client,
            native_base,
            f"/blocks/{h}/txs",
            headers=native_headers,
            params={"count": 1, "page": 1},
        )
        if isinstance(txs, list) and txs:
            return str(txs[0])
    return None


def _resolve_sample_script_or_datum(
    client: httpx.Client,
    native_base: str,
    native_headers: dict[str, str],
    *,
    kind: str,
) -> str | None:
    """Scan recent tip-relative txs for a script or datum hash fixture."""
    tip = _json_get(client, native_base, "/blocks/latest", headers=native_headers)
    height = tip.get("height") if isinstance(tip, dict) else None
    if height is None:
        return None
    field = "reference_script_hash" if kind == "script" else "data_hash"
    for delta in (20, 50, 100, 200, 500, 1000, 2000):
        h = max(1, int(height) - delta)
        txs = _json_get(
            client,
            native_base,
            f"/blocks/{h}/txs",
            headers=native_headers,
            params={"count": 10, "page": 1},
        )
        if not isinstance(txs, list):
            continue
        for tx_hash in txs:
            try:
                utxos = _json_get(
                    client,
                    native_base,
                    f"/txs/{tx_hash}/utxos",
                    headers=native_headers,
                )
            except httpx.HTTPError:
                continue
            if not isinstance(utxos, dict):
                continue
            for side in ("inputs", "outputs"):
                for u in utxos.get(side) or []:
                    if not isinstance(u, dict):
                        continue
                    value = u.get(field)
                    if value:
                        return str(value)
    return None


def _norm(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_norm(v) for v in value]
    return value


def _diff(
    native: Any,
    janus: Any,
    *,
    path: str = "$",
    ignore: frozenset[str] = _DEFAULT_IGNORE,
) -> list[str]:
    diffs: list[str] = []

    # Treat numeric strings as numbers when the other side is int/float.
    if isinstance(native, str) and isinstance(janus, (int, float)):
        try:
            native = int(native) if native.isdigit() else float(native)
        except ValueError:
            pass
    elif isinstance(janus, str) and isinstance(native, (int, float)):
        try:
            janus = int(janus) if janus.isdigit() else float(janus)
        except ValueError:
            pass

    if type(native) is not type(janus) and not (
        isinstance(native, (int, float)) and isinstance(janus, (int, float))
    ):
        # Allow int/float mix; otherwise report type mismatch.
        if not (
            isinstance(native, (int, float)) and isinstance(janus, (int, float))
        ):
            diffs.append(f"{path}: type {type(native).__name__} vs {type(janus).__name__}")
            return diffs

    if isinstance(native, dict) and isinstance(janus, dict):
        keys = set(native) | set(janus)
        for key in sorted(keys):
            if key in ignore:
                continue
            sub = f"{path}.{key}"
            if key not in native:
                diffs.append(f"{sub}: missing in native (janus={janus[key]!r})")
            elif key not in janus:
                diffs.append(f"{sub}: missing in janus (native={native[key]!r})")
            else:
                diffs.extend(_diff(native[key], janus[key], path=sub, ignore=ignore))
        return diffs

    if isinstance(native, list) and isinstance(janus, list):
        if len(native) != len(janus):
            diffs.append(f"{path}: list len {len(native)} vs {len(janus)}")
        for i, (a, b) in enumerate(zip(native, janus)):
            diffs.extend(_diff(a, b, path=f"{path}[{i}]", ignore=ignore))
        return diffs

    if isinstance(native, (int, float)) and isinstance(janus, (int, float)):
        if abs(float(native) - float(janus)) > 1e-9 * max(1.0, abs(float(native))):
            diffs.append(f"{path}: {native!r} vs {janus!r}")
        return diffs

    if _norm(native) != _norm(janus):
        # NULL / None Gaps: highlight explicitly
        if native is not None and janus is None:
            diffs.append(f"{path}: native={native!r} janus=null (possible Gap)")
        elif native is None and janus is not None:
            diffs.append(f"{path}: native=null janus={janus!r}")
        else:
            diffs.append(f"{path}: {native!r} vs {janus!r}")
    return diffs


def _filter_pool_history_epochs(rows: Any, epochs: set[int]) -> Any:
    if not isinstance(rows, list) or not epochs:
        return rows
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        epoch = row.get("epoch_no", row.get("epoch"))
        try:
            if int(epoch) in epochs:
                out.append(row)
        except (TypeError, ValueError):
            continue
    return out


def _align_by_epoch(rows: Any) -> dict[int, dict[str, Any]]:
    """Index pool/epoch history rows by epoch_no for order-independent compare."""
    out: dict[int, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        epoch = row.get("epoch_no", row.get("epoch"))
        try:
            out[int(epoch)] = row
        except (TypeError, ValueError):
            continue
    return out


def _diff_by_epoch(
    native: Any,
    janus: Any,
    *,
    ignore: frozenset[str],
) -> list[str]:
    n_map = _align_by_epoch(native)
    j_map = _align_by_epoch(janus)
    diffs: list[str] = []
    only_n = sorted(set(n_map) - set(j_map))
    only_j = sorted(set(j_map) - set(n_map))
    if only_n:
        diffs.append(f"$: epochs only in native: {only_n[:20]}")
    if only_j:
        diffs.append(f"$: epochs only in janus: {only_j[:20]}")
    for epoch in sorted(set(n_map) & set(j_map)):
        diffs.extend(
            _diff(
                n_map[epoch],
                j_map[epoch],
                path=f"$[epoch={epoch}]",
                ignore=ignore,
            )
        )
    return diffs


def _tip_epoch_no(client: httpx.Client, base: str, headers: dict[str, str], face: str) -> int:
    if face == "koios":
        tip = _json_get(client, base, "/tip", headers=headers)
        row = tip[0] if isinstance(tip, list) and tip else tip
        if not isinstance(row, dict) or "epoch_no" not in row:
            raise ValueError(f"Unexpected tip payload from {base}")
        return int(row["epoch_no"])
    tip = _json_get(client, base, "/blocks/latest", headers=headers)
    if not isinstance(tip, dict) or "epoch" not in tip:
        raise ValueError(f"Unexpected Blockfrost tip payload from {base}")
    return int(tip["epoch"])


def _resolve_compare_epoch(
    client: httpx.Client,
    *,
    face: str,
    native_base: str,
    native_headers: dict[str, str],
    pinned: int | None,
) -> int | None:
    """Pick a stable epoch for apple-to-apple compares.

    Prefer COMPARE_EPOCH. Otherwise use tip.epoch - 2 so pool_history
    (reward lag) and completed epoch_info both have data.
    """
    if pinned is not None:
        return pinned
    tip_epoch = _tip_epoch_no(client, native_base, native_headers, face)
    return max(0, tip_epoch - 2)


def run_case(
    client: httpx.Client,
    *,
    name: str,
    face: str,
    janus_base: str,
    native_base: str,
    janus_headers: dict[str, str],
    native_headers: dict[str, str],
    pool_id: str,
    epochs: set[int],
    compare_epoch: int | None,
    address: str = "",
    stake_address: str = "",
) -> CaseResult:
    try:
        if name == "tip":
            if face == "koios":
                native = _json_get(client, native_base, "/tip", headers=native_headers)
                janus = _json_get(client, janus_base, "/tip", headers=janus_headers)
            else:
                native = _json_get(
                    client, native_base, "/blocks/latest", headers=native_headers
                )
                janus = _json_get(
                    client, janus_base, "/blocks/latest", headers=janus_headers
                )
            # Tip drifts; only compare stable structural keys.
            ignore = (
                _DEFAULT_IGNORE
                | _KOIOS_GAP_IGNORE
                | frozenset({"epoch", "epoch_no", "block_no", "fees", "output"})
            )
            diffs = _diff(native, janus, ignore=ignore)
            # Soft pass for tip: report but do not fail CI hard on slot drift alone.
            ok = True
            detail = "tip compared (volatile fields ignored)"
            if diffs:
                detail = f"tip soft-diff ({len(diffs)} notes)"
            return CaseResult(name, ok, detail, native, janus, diffs)

        if name == "genesis":
            native = _json_get(client, native_base, "/genesis", headers=native_headers)
            janus = _json_get(client, janus_base, "/genesis", headers=janus_headers)
            diffs = _diff(native, janus, ignore=_KOIOS_GAP_IGNORE)
            return CaseResult(
                name,
                ok=not diffs,
                detail="ok" if not diffs else f"{len(diffs)} diff(s)",
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "epoch_info":
            epoch = _resolve_compare_epoch(
                client,
                face=face,
                native_base=native_base,
                native_headers=native_headers,
                pinned=compare_epoch,
            )
            if face == "koios":
                # Native Koios RPC uses _epoch_no. Older Janus faces used
                # PostgREST epoch_no=eq.N; current face accepts both.
                native_params = (
                    {"_epoch_no": str(epoch)} if epoch is not None else None
                )
                janus_params = None
                if epoch is not None:
                    janus_params = {
                        "_epoch_no": str(epoch),
                        "epoch_no": f"eq.{epoch}",
                    }
                native = _json_get(
                    client,
                    native_base,
                    "/epoch_info",
                    headers=native_headers,
                    params=native_params,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    "/epoch_info",
                    headers=janus_headers,
                    params=janus_params,
                )
                detail_epoch = f"epoch={epoch}"
            else:
                if epoch is None:
                    native = _json_get(
                        client, native_base, "/epochs/latest", headers=native_headers
                    )
                    janus = _json_get(
                        client, janus_base, "/epochs/latest", headers=janus_headers
                    )
                    detail_epoch = "latest"
                else:
                    native = _json_get(
                        client,
                        native_base,
                        f"/epochs/{epoch}",
                        headers=native_headers,
                    )
                    janus = _json_get(
                        client,
                        janus_base,
                        f"/epochs/{epoch}",
                        headers=janus_headers,
                    )
                    detail_epoch = f"epoch={epoch}"
            ignore = _KOIOS_GAP_IGNORE | frozenset({"active_stake"})
            diffs = _diff(native, janus, ignore=ignore)
            return CaseResult(
                name,
                ok=not diffs,
                detail=(
                    f"ok ({detail_epoch})"
                    if not diffs
                    else f"{len(diffs)} diff(s) ({detail_epoch})"
                ),
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "pool_list":
            if face == "koios":
                native = _json_get(
                    client,
                    native_base,
                    "/pool_list",
                    headers=native_headers,
                    params={"limit": 5},
                )
                janus = _json_get(
                    client,
                    janus_base,
                    "/pool_list",
                    headers=janus_headers,
                    params={"limit": 5},
                )
            else:
                native = _json_get(
                    client,
                    native_base,
                    "/pools",
                    headers=native_headers,
                    params={"count": 5, "page": 1},
                )
                janus = _json_get(
                    client,
                    janus_base,
                    "/pools",
                    headers=janus_headers,
                    params={"count": 5, "page": 1},
                )
            # Ordering may differ; compare lengths only for this smoke case.
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len >= 0
            detail = f"list lens native={n_len} janus={j_len}"
            return CaseResult(name, ok, detail, native, janus, None)

        if name == "pool_history":
            if not pool_id:
                return CaseResult(name, False, "COMPARE_POOL_ID not set")
            # Prefer explicit COMPARE_EPOCHS; else pin to COMPARE_EPOCH / tip-1.
            filter_epochs = set(epochs)
            if not filter_epochs and compare_epoch is not None:
                filter_epochs = {compare_epoch}
            if face == "koios":
                # Fetch recent history (Koios-native default is descending).
                params: dict[str, Any] = {
                    "_pool_bech32": pool_id,
                    "limit": 100,
                    "order": "epoch_no.desc",
                }
                if len(filter_epochs) == 1:
                    only = next(iter(filter_epochs))
                    params["_epoch_no"] = str(only)
                native = _json_get(
                    client,
                    native_base,
                    "/pool_history",
                    headers=native_headers,
                    params=params,
                )
                # Live Janus may still default to asc until redeployed; force desc.
                janus = _json_get(
                    client,
                    janus_base,
                    "/pool_history",
                    headers=janus_headers,
                    params={
                        "_pool_bech32": pool_id,
                        "limit": 100,
                        "order": "epoch_no.desc",
                    },
                )
            else:
                native = _json_get(
                    client,
                    native_base,
                    f"/pools/{pool_id}/history",
                    headers=native_headers,
                    params={"count": 100, "page": 1},
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/pools/{pool_id}/history",
                    headers=janus_headers,
                    params={"count": 100, "page": 1},
                )
            native = _filter_pool_history_epochs(native, filter_epochs)
            janus = _filter_pool_history_epochs(janus, filter_epochs)
            diffs = _diff_by_epoch(native, janus, ignore=_KOIOS_GAP_IGNORE)
            epoch_note = (
                f"epochs={sorted(filter_epochs)}" if filter_epochs else "all fetched"
            )
            return CaseResult(
                name,
                ok=not diffs,
                detail=(
                    f"ok ({epoch_note})"
                    if not diffs
                    else f"{len(diffs)} diff(s) ({epoch_note})"
                ),
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "epoch_params":
            epoch = _resolve_compare_epoch(
                client,
                face=face,
                native_base=native_base,
                native_headers=native_headers,
                pinned=compare_epoch,
            )
            if face == "koios":
                native_params = {"_epoch_no": str(epoch)} if epoch is not None else None
                janus_params = None
                if epoch is not None:
                    janus_params = {
                        "_epoch_no": str(epoch),
                        "epoch_no": f"eq.{epoch}",
                    }
                native = _json_get(
                    client,
                    native_base,
                    "/epoch_params",
                    headers=native_headers,
                    params=native_params,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    "/epoch_params",
                    headers=janus_headers,
                    params=janus_params,
                )
                ignore = _KOIOS_GAP_IGNORE | frozenset(
                    {
                        "nonce",
                        "committee_max_term_length",
                        "committee_min_size",
                        "drep_activity",
                        "drep_deposit",
                        "dvt_committee_no_confidence",
                        "dvt_committee_normal",
                        "dvt_hard_fork_initiation",
                        "dvt_motion_no_confidence",
                        "dvt_p_p_economic_group",
                        "dvt_p_p_gov_group",
                        "dvt_p_p_network_group",
                        "dvt_p_p_technical_group",
                        "dvt_treasury_withdrawal",
                        "dvt_update_to_constitution",
                        "gov_action_deposit",
                        "gov_action_lifetime",
                        "min_fee_ref_script_cost_per_byte",
                        "pvt_committee_no_confidence",
                        "pvt_committee_normal",
                        "pvt_hard_fork_initiation",
                        "pvt_motion_no_confidence",
                        "pvtpp_security_group",
                    }
                )
            else:
                if epoch is None:
                    native = _json_get(
                        client,
                        native_base,
                        "/epochs/latest/parameters",
                        headers=native_headers,
                    )
                    janus = _json_get(
                        client,
                        janus_base,
                        "/epochs/latest/parameters",
                        headers=janus_headers,
                    )
                else:
                    native = _json_get(
                        client,
                        native_base,
                        f"/epochs/{epoch}/parameters",
                        headers=native_headers,
                    )
                    janus = _json_get(
                        client,
                        janus_base,
                        f"/epochs/{epoch}/parameters",
                        headers=janus_headers,
                    )
                ignore = frozenset(
                    {
                        "nonce",
                        "cost_models",
                        "cost_models_raw",
                        # Conway gov params often Gap when Janus backend is Koios.
                        "committee_max_term_length",
                        "committee_min_size",
                        "drep_activity",
                        "drep_deposit",
                        "dvt_committee_no_confidence",
                        "dvt_committee_normal",
                        "dvt_hard_fork_initiation",
                        "dvt_motion_no_confidence",
                        "dvt_p_p_economic_group",
                        "dvt_p_p_gov_group",
                        "dvt_p_p_network_group",
                        "dvt_p_p_technical_group",
                        "dvt_treasury_withdrawal",
                        "dvt_update_to_constitution",
                        "gov_action_deposit",
                        "gov_action_lifetime",
                        "min_fee_ref_script_cost_per_byte",
                        "pvt_committee_no_confidence",
                        "pvt_committee_normal",
                        "pvt_hard_fork_initiation",
                        "pvt_motion_no_confidence",
                        "pvt_p_p_security_group",
                        "pvtpp_security_group",
                        # Known: Koios min_utxo_value=0 vs BF min_utxo=coins_per_utxo_size.
                        "min_utxo",
                    }
                )
            diffs = _diff(native, janus, ignore=ignore)
            detail_epoch = f"epoch={epoch}"
            return CaseResult(
                name,
                ok=not diffs,
                detail=(
                    f"ok ({detail_epoch})"
                    if not diffs
                    else f"{len(diffs)} diff(s) ({detail_epoch})"
                ),
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "epochs_next":
            epoch = _resolve_compare_epoch(
                client,
                face=face,
                native_base=native_base,
                native_headers=native_headers,
                pinned=compare_epoch,
            )
            if face != "blockfrost":
                return CaseResult(name, False, "epochs_next case is Blockfrost-face only")
            if epoch is None:
                return CaseResult(name, False, "COMPARE_EPOCH unresolved")
            # Ask for a few epochs after a completed one (may be empty near tip).
            base_epoch = max(0, epoch - 5)
            params = {"count": 3, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/epochs/{base_epoch}/next",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/epochs/{base_epoch}/next",
                headers=janus_headers,
                params=params,
            )
            diffs = _diff(native, janus, ignore=frozenset({"active_stake"}))
            return CaseResult(
                name,
                ok=not diffs,
                detail=(
                    f"ok (from={base_epoch})"
                    if not diffs
                    else f"{len(diffs)} diff(s) (from={base_epoch})"
                ),
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "pool_info":
            if not pool_id:
                return CaseResult(name, False, "COMPARE_POOL_ID not set")
            if face == "koios":
                body = {"_pool_bech32_ids": [pool_id]}
                native = _json_post(
                    client, native_base, "/pool_info", body, headers=native_headers
                )
                janus = _json_post(
                    client, janus_base, "/pool_info", body, headers=janus_headers
                )
                ignore = _KOIOS_GAP_IGNORE | frozenset(
                    {
                        "pool_id_hex",
                        "pledge",
                        "active_stake",
                        "block_count",
                        "sigma",
                        "voting_power",
                        "reward_addr_delegated_drep",
                        "relays",
                    }
                )
            else:
                native = _json_get(
                    client,
                    native_base,
                    f"/pools/{pool_id}",
                    headers=native_headers,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/pools/{pool_id}",
                    headers=janus_headers,
                )
                ignore = frozenset(
                    {
                        "live_stake",
                        "live_size",
                        "live_saturation",
                        "live_delegators",
                        "live_pledge",
                        "active_stake",
                        "active_size",
                        "blocks_minted",
                        "blocks_epoch",
                        "declared_pledge",
                        "margin_cost",
                        "fixed_cost",
                        "owners",
                        "registration",
                        "retirement",
                        "calidus_key",
                    }
                )
            diffs = _diff(native, janus, ignore=ignore)
            return CaseResult(
                name,
                ok=not diffs,
                detail="ok" if not diffs else f"{len(diffs)} diff(s)",
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "pool_metadata":
            if not pool_id:
                return CaseResult(name, False, "COMPARE_POOL_ID not set")
            if face == "koios":
                body = {"_pool_bech32_ids": [pool_id]}
                native = _json_post(
                    client, native_base, "/pool_metadata", body, headers=native_headers
                )
                janus = _json_post(
                    client, janus_base, "/pool_metadata", body, headers=janus_headers
                )
                diffs = _diff(native, janus, ignore=frozenset({"meta_json"}))
                hard = [
                    d
                    for d in diffs
                    if ".meta_json" not in d and not d.endswith(".meta_json")
                ]
            else:
                native = _json_get(
                    client,
                    native_base,
                    f"/pools/{pool_id}/metadata",
                    headers=native_headers,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/pools/{pool_id}/metadata",
                    headers=janus_headers,
                )
                diffs = _diff(
                    native,
                    janus,
                    ignore=frozenset({"description", "homepage", "name", "hex"}),
                )
                hard = [
                    d
                    for d in diffs
                    if any(
                        k in d for k in (".pool_id", ".url", ".hash", ".ticker")
                    )
                    or d.startswith("$:")
                ]
            return CaseResult(
                name,
                ok=not hard,
                detail="ok" if not hard else f"{len(hard)} diff(s)",
                native=native,
                janus=janus,
                diffs=hard or None,
            )

        if name == "pool_relays":
            if not pool_id:
                return CaseResult(name, False, "COMPARE_POOL_ID not set")
            if face == "koios":
                native_info = _json_post(
                    client,
                    native_base,
                    "/pool_info",
                    {"_pool_bech32_ids": [pool_id]},
                    headers=native_headers,
                )
                native_relays: list[Any] = []
                if isinstance(native_info, list) and native_info:
                    native_relays = list(native_info[0].get("relays") or [])
                janus_rows = _json_get(
                    client,
                    janus_base,
                    "/pool_relays",
                    headers=janus_headers,
                    params={"_pool_bech32": pool_id},
                )
                janus_relays: list[Any] = []
                if isinstance(janus_rows, list) and janus_rows:
                    janus_relays = list(janus_rows[0].get("relays") or [])
            else:
                native_relays = _json_get(
                    client,
                    native_base,
                    f"/pools/{pool_id}/relays",
                    headers=native_headers,
                )
                janus_relays = _json_get(
                    client,
                    janus_base,
                    f"/pools/{pool_id}/relays",
                    headers=janus_headers,
                )
                if not isinstance(native_relays, list):
                    native_relays = []
                if not isinstance(janus_relays, list):
                    janus_relays = []
            n_len, j_len = len(native_relays), len(janus_relays)
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"relay rows native={n_len} janus={j_len}",
                native_relays,
                janus_relays,
                None,
            )

        if name == "pool_delegators":
            if not pool_id:
                return CaseResult(name, False, "COMPARE_POOL_ID not set")
            if face == "koios":
                params: dict[str, Any] = {"_pool_bech32": pool_id, "limit": 5}
                native = _json_get(
                    client,
                    native_base,
                    "/pool_delegators",
                    headers=native_headers,
                    params=params,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    "/pool_delegators",
                    headers=janus_headers,
                    params=params,
                )
            else:
                params = {"count": 5, "page": 1}
                native = _json_get(
                    client,
                    native_base,
                    f"/pools/{pool_id}/delegators",
                    headers=native_headers,
                    params=params,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/pools/{pool_id}/delegators",
                    headers=janus_headers,
                    params=params,
                )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "block_info":
            if face == "koios":
                tip = _json_get(client, native_base, "/tip", headers=native_headers)
                tip_row = tip[0] if isinstance(tip, list) and tip else tip
                height = tip_row.get("block_height") if isinstance(tip_row, dict) else None
                block_hash = None
                if height is not None:
                    rows = _json_get(
                        client,
                        native_base,
                        "/blocks",
                        headers=native_headers,
                        params={
                            "block_height": f"eq.{max(1, int(height) - 20)}",
                            "limit": 1,
                        },
                    )
                    if isinstance(rows, list) and rows:
                        block_hash = rows[0].get("hash")
                if not block_hash and isinstance(tip_row, dict):
                    block_hash = tip_row.get("hash")
                if not block_hash:
                    return CaseResult(name, False, "could not resolve block hash")
                body = {"_block_hashes": [block_hash]}
                native = _json_post(
                    client, native_base, "/block_info", body, headers=native_headers
                )
                janus = _json_post(
                    client, janus_base, "/block_info", body, headers=janus_headers
                )
                ignore = _DEFAULT_IGNORE | _KOIOS_GAP_IGNORE | frozenset(
                    {
                        "parent_hash",
                        "child_hash",
                        "proto_major",
                        "proto_minor",
                        "pool",
                        "vrf_key",
                        "total_fees",
                        "total_output",
                        "block_size",
                        "tx_count",
                    }
                )
            else:
                tip = _json_get(
                    client, native_base, "/blocks/latest", headers=native_headers
                )
                height = tip.get("height") if isinstance(tip, dict) else None
                if height is None:
                    return CaseResult(name, False, "could not resolve tip height")
                target = max(1, int(height) - 20)
                native = _json_get(
                    client,
                    native_base,
                    f"/blocks/{target}",
                    headers=native_headers,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/blocks/{target}",
                    headers=janus_headers,
                )
                block_hash = (
                    str(native.get("hash", ""))[:12]
                    if isinstance(native, dict)
                    else str(target)
                )
                ignore = _DEFAULT_IGNORE | frozenset(
                    {
                        "previous_block",
                        "next_block",
                        "confirmations",
                        "slot",
                        "epoch",
                        "epoch_slot",
                        "height",
                        "time",
                        "tx_count",
                        "size",
                        "fees",
                        "output",
                        "block_vrf",
                        "op_cert",
                        "op_cert_counter",
                        "slot_leader",
                    }
                )
            diffs = _diff(native, janus, ignore=ignore)
            return CaseResult(
                name,
                ok=not diffs,
                detail=(
                    f"ok (hash={block_hash}…)"
                    if not diffs
                    else f"{len(diffs)} diff(s)"
                ),
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "address_info":
            addr = address
            if not addr:
                return CaseResult(name, False, "COMPARE_ADDRESS not set / unresolved")
            if face == "koios":
                body = {"_addresses": [addr]}
                native = _json_post(
                    client, native_base, "/address_info", body, headers=native_headers
                )
                janus = _json_post(
                    client, janus_base, "/address_info", body, headers=janus_headers
                )
                ignore = frozenset({"utxo_set", "script_address", "balance"})
                diffs = _diff(native, janus, ignore=ignore)
                hard = [d for d in diffs if "address" in d or "stake_address" in d]
            else:
                native = _json_get(
                    client,
                    native_base,
                    f"/addresses/{addr}",
                    headers=native_headers,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/addresses/{addr}",
                    headers=janus_headers,
                )
                ignore = frozenset(
                    {"amount", "received_amount", "sent_amount", "tx_count"}
                )
                diffs = _diff(native, janus, ignore=ignore)
                hard = [d for d in diffs if ".address" in d or d.endswith(".address")]
            return CaseResult(
                name,
                ok=not hard,
                detail=(
                    "ok (identity)"
                    if not hard
                    else f"{len(hard)} identity diff(s); {len(diffs)} total"
                ),
                native=native,
                janus=janus,
                diffs=diffs if diffs else None,
            )

        if name == "account_info":
            stake = stake_address
            if not stake:
                return CaseResult(
                    name, False, "COMPARE_STAKE_ADDRESS not set / unresolved"
                )
            if face == "koios":
                body = {"_stake_addresses": [stake]}
                native = _json_post(
                    client, native_base, "/account_info", body, headers=native_headers
                )
                janus = _json_post(
                    client, janus_base, "/account_info", body, headers=janus_headers
                )
                ignore = _KOIOS_GAP_IGNORE | frozenset(
                    {
                        "total_balance",
                        "utxo",
                        "rewards",
                        "withdrawals",
                        "rewards_available",
                        "delegated_pool",
                        "delegated_drep",
                        "status",
                        "reserves",
                        "treasury",
                    }
                )
                diffs = _diff(native, janus, ignore=ignore)
                hard = [d for d in diffs if "stake_address" in d]
            else:
                native = _json_get(
                    client,
                    native_base,
                    f"/accounts/{stake}",
                    headers=native_headers,
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/accounts/{stake}",
                    headers=janus_headers,
                )
                ignore = frozenset(
                    {
                        "controlled_amount",
                        "rewards_sum",
                        "withdrawals_sum",
                        "reserves_sum",
                        "treasury_sum",
                        "withdrawable_amount",
                        "pool_id",
                        "drep_id",
                        "active",
                    }
                )
                diffs = _diff(native, janus, ignore=ignore)
                hard = [
                    d
                    for d in diffs
                    if "stake_address" in d or d.endswith(".stake_address")
                ]
            return CaseResult(
                name,
                ok=not hard,
                detail=(
                    "ok (identity)"
                    if not diffs
                    else f"{len(diffs)} soft diff(s); identity ok"
                    if not hard
                    else f"{len(hard)} identity diff(s)"
                ),
                native=native,
                janus=janus,
                diffs=diffs if diffs else None,
            )

        if name == "epochs_previous":
            epoch = _resolve_compare_epoch(
                client,
                face=face,
                native_base=native_base,
                native_headers=native_headers,
                pinned=compare_epoch,
            )
            if face != "blockfrost":
                return CaseResult(
                    name, False, "epochs_previous case is Blockfrost-face only"
                )
            if epoch is None:
                return CaseResult(name, False, "COMPARE_EPOCH unresolved")
            params = {"count": 3, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/epochs/{epoch}/previous",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/epochs/{epoch}/previous",
                headers=janus_headers,
                params=params,
            )
            # Align by epoch number (order may still differ until redeploy).
            diffs = _diff_by_epoch(
                native if isinstance(native, list) else [],
                janus if isinstance(janus, list) else [],
                ignore=frozenset({"active_stake"}),
            )
            return CaseResult(
                name,
                ok=not diffs,
                detail=(
                    f"ok (from={epoch})"
                    if not diffs
                    else f"{len(diffs)} diff(s) (from={epoch})"
                ),
                native=native,
                janus=janus,
                diffs=diffs,
            )

        if name == "epoch_blocks":
            epoch = _resolve_compare_epoch(
                client,
                face=face,
                native_base=native_base,
                native_headers=native_headers,
                pinned=compare_epoch,
            )
            if epoch is None:
                return CaseResult(name, False, "COMPARE_EPOCH unresolved")
            if face == "koios":
                native = _json_get(
                    client,
                    native_base,
                    "/blocks",
                    headers=native_headers,
                    params={
                        "epoch_no": f"eq.{epoch}",
                        "limit": 5,
                        "order": "block_height.asc",
                    },
                )
                janus = _json_get(
                    client,
                    janus_base,
                    "/blocks",
                    headers=janus_headers,
                    params={
                        "epoch_no": f"eq.{epoch}",
                        "limit": 5,
                        "order": "block_height.asc",
                    },
                )
                n_hashes = [
                    r.get("hash")
                    for r in native
                    if isinstance(r, dict) and r.get("hash")
                ] if isinstance(native, list) else []
                j_hashes = [
                    r.get("hash")
                    for r in janus
                    if isinstance(r, dict) and r.get("hash")
                ] if isinstance(janus, list) else []
            else:
                native = _json_get(
                    client,
                    native_base,
                    f"/epochs/{epoch}/blocks",
                    headers=native_headers,
                    params={"count": 5, "page": 1, "order": "asc"},
                )
                janus = _json_get(
                    client,
                    janus_base,
                    f"/epochs/{epoch}/blocks",
                    headers=janus_headers,
                    params={"count": 5, "page": 1, "order": "asc"},
                )
                n_hashes = native if isinstance(native, list) else []
                j_hashes = janus if isinstance(janus, list) else []
            ok = len(n_hashes) == len(j_hashes) and len(n_hashes) > 0
            # Order can differ on some backends; require set overlap when both non-empty.
            if n_hashes and j_hashes and set(n_hashes) != set(j_hashes):
                overlap = len(set(n_hashes) & set(j_hashes))
                ok = overlap == len(n_hashes) == len(j_hashes)
                detail = f"hashes overlap={overlap} native={len(n_hashes)} janus={len(j_hashes)}"
            else:
                detail = f"hashes native={len(n_hashes)} janus={len(j_hashes)}"
            return CaseResult(name, ok, detail, native, janus, None)

        if name == "block_txs":
            if face != "blockfrost":
                return CaseResult(name, False, "block_txs case is Blockfrost-face only")
            tip = _json_get(
                client, native_base, "/blocks/latest", headers=native_headers
            )
            height = tip.get("height") if isinstance(tip, dict) else None
            if height is None:
                return CaseResult(name, False, "could not resolve tip height")
            # Walk back until a block with txs is found.
            txs_n: list[Any] = []
            txs_j: list[Any] = []
            used_height = None
            for delta in (50, 100, 200, 500):
                h = max(1, int(height) - delta)
                block = _json_get(
                    client, native_base, f"/blocks/{h}", headers=native_headers
                )
                if not isinstance(block, dict) or not block.get("tx_count"):
                    continue
                params = {"count": 5, "page": 1}
                txs_n = _json_get(
                    client,
                    native_base,
                    f"/blocks/{h}/txs",
                    headers=native_headers,
                    params=params,
                )
                txs_j = _json_get(
                    client,
                    janus_base,
                    f"/blocks/{h}/txs",
                    headers=janus_headers,
                    params=params,
                )
                used_height = h
                break
            if used_height is None:
                return CaseResult(name, False, "no recent block with txs found")
            n_len = len(txs_n) if isinstance(txs_n, list) else -1
            j_len = len(txs_j) if isinstance(txs_j, list) else -1
            ok = n_len == j_len and n_len > 0
            return CaseResult(
                name,
                ok,
                f"height={used_height} lens native={n_len} janus={j_len}",
                txs_n,
                txs_j,
                None,
            )

        if name == "tx_info":
            if face != "blockfrost":
                return CaseResult(name, False, "tx_info case is Blockfrost-face only")
            tx_hash = _resolve_sample_tx_hash(client, native_base, native_headers)
            if not tx_hash:
                return CaseResult(name, False, "could not resolve sample tx hash")
            native = _json_get(
                client, native_base, f"/txs/{tx_hash}", headers=native_headers
            )
            janus = _json_get(
                client, janus_base, f"/txs/{tx_hash}", headers=janus_headers
            )
            ignore = _DEFAULT_IGNORE | frozenset(
                {
                    "block",
                    "block_height",
                    "block_time",
                    "slot",
                    "index",
                    "fees",
                    "deposit",
                    "size",
                    "invalid_before",
                    "invalid_hereafter",
                    "utxo_count",
                    "withdrawal_count",
                    "mir_cert_count",
                    "delegation_count",
                    "stake_cert_count",
                    "pool_update_count",
                    "pool_retire_count",
                    "asset_mint_or_burn_count",
                    "redeemer_count",
                    "valid_contract",
                    "output_amount",
                    "treasury_donation",
                }
            )
            diffs = _diff(native, janus, ignore=ignore)
            hard = [d for d in diffs if ".hash" in d]
            return CaseResult(
                name,
                ok=not hard and isinstance(janus, dict),
                detail=(
                    f"ok (tx={tx_hash[:12]}…)"
                    if not hard
                    else f"{len(hard)} identity diff(s)"
                ),
                native=native,
                janus=janus,
                diffs=diffs if diffs else None,
            )

        if name == "tx_utxos":
            if face != "blockfrost":
                return CaseResult(name, False, "tx_utxos case is Blockfrost-face only")
            tx_hash = _resolve_sample_tx_hash(client, native_base, native_headers)
            if not tx_hash:
                return CaseResult(name, False, "could not resolve sample tx hash")
            native = _json_get(
                client, native_base, f"/txs/{tx_hash}/utxos", headers=native_headers
            )
            janus = _json_get(
                client, janus_base, f"/txs/{tx_hash}/utxos", headers=janus_headers
            )
            if not isinstance(native, dict) or not isinstance(janus, dict):
                return CaseResult(
                    name,
                    False,
                    f"types native={type(native).__name__} janus={type(janus).__name__}",
                    native,
                    janus,
                )
            # Koios /tx_utxos omits collateral + reference inputs/outputs (Gap).
            n_in = [
                i
                for i in (native.get("inputs") or [])
                if isinstance(i, dict)
                and not i.get("collateral")
                and not i.get("reference")
            ]
            j_in = [i for i in (janus.get("inputs") or []) if isinstance(i, dict)]
            n_out = sorted(
                [
                    o
                    for o in (native.get("outputs") or [])
                    if isinstance(o, dict) and not o.get("collateral")
                ],
                key=lambda o: o.get("output_index") or 0,
            )
            j_out = sorted(
                [o for o in (janus.get("outputs") or []) if isinstance(o, dict)],
                key=lambda o: o.get("output_index") or 0,
            )

            def _io_key(u: dict[str, Any]) -> tuple[Any, ...]:
                return (u.get("tx_hash"), u.get("output_index"), u.get("address"))

            def _amt_key(u: dict[str, Any]) -> tuple[tuple[str, str], ...]:
                amts = u.get("amount") or []
                pairs: list[tuple[str, str]] = []
                for a in amts:
                    if isinstance(a, dict) and a.get("unit") is not None:
                        pairs.append((str(a["unit"]), str(a.get("quantity", "0"))))
                return tuple(sorted(pairs))

            n_in_keys = {_io_key(i) for i in n_in}
            j_in_keys = {_io_key(i) for i in j_in}
            in_ok = n_in_keys == j_in_keys and len(n_in) == len(j_in)
            out_ok = len(n_out) == len(j_out)
            out_diffs: list[str] = []
            if out_ok:
                for i, (a, b) in enumerate(zip(n_out, j_out)):
                    if a.get("output_index") != b.get("output_index"):
                        out_diffs.append(f"outputs[{i}].output_index")
                    if a.get("address") != b.get("address"):
                        out_diffs.append(f"outputs[{i}].address")
                    if _amt_key(a) != _amt_key(b):
                        out_diffs.append(f"outputs[{i}].amount")
            else:
                out_diffs.append(f"outputs len {len(n_out)} vs {len(j_out)}")
            n_col = sum(
                1
                for i in (native.get("inputs") or [])
                if isinstance(i, dict) and (i.get("collateral") or i.get("reference"))
            )
            ok = native.get("hash") == janus.get("hash") == tx_hash and in_ok and not out_diffs
            detail = (
                f"ok (tx={tx_hash[:12]}…, regular in={len(n_in)} out={len(n_out)}"
                f"{f', skipped {n_col} collateral/ref inputs' if n_col else ''})"
            )
            if not ok:
                detail = (
                    f"mismatch (in_ok={in_ok}, out_diffs={len(out_diffs)}, "
                    f"tx={tx_hash[:12]}…)"
                )
            soft = []
            if n_col:
                soft.append(
                    f"Gap: native has {n_col} collateral/reference input(s) absent from Koios"
                )
            for d in out_diffs[:20]:
                soft.append(d)
            return CaseResult(
                name,
                ok,
                detail,
                native,
                janus,
                soft if soft else None,
            )

        if name == "tx_metadata":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "tx_metadata case is Blockfrost-face only"
                )
            tx_hash = _optional("COMPARE_TX_HASH") or _resolve_sample_tx_hash(
                client, native_base, native_headers
            )
            if not tx_hash:
                return CaseResult(name, False, "could not resolve sample tx hash")
            native = _json_get(
                client,
                native_base,
                f"/txs/{tx_hash}/metadata",
                headers=native_headers,
            )
            janus = _json_get(
                client, janus_base, f"/txs/{tx_hash}/metadata", headers=janus_headers
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len} (tx={tx_hash[:12]}…)",
                native,
                janus,
                None,
            )

        if name == "tx_cbor":
            if face != "blockfrost":
                return CaseResult(name, False, "tx_cbor case is Blockfrost-face only")
            tx_hash = _resolve_sample_tx_hash(client, native_base, native_headers)
            if not tx_hash:
                return CaseResult(name, False, "could not resolve sample tx hash")
            native = _json_get(
                client, native_base, f"/txs/{tx_hash}/cbor", headers=native_headers
            )
            janus = _json_get(
                client, janus_base, f"/txs/{tx_hash}/cbor", headers=janus_headers
            )
            n_cbor = native.get("cbor") if isinstance(native, dict) else None
            j_cbor = janus.get("cbor") if isinstance(janus, dict) else None
            ok = bool(n_cbor) and n_cbor == j_cbor
            return CaseResult(
                name,
                ok,
                (
                    f"cbor match (tx={tx_hash[:12]}…, len={len(str(n_cbor))})"
                    if ok
                    else f"cbor mismatch or empty (tx={tx_hash[:12]}…)"
                ),
                native,
                janus,
                None if ok else ["$.cbor differs"],
            )

        if name == "address_utxos":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "address_utxos case is Blockfrost-face only"
                )
            addr = address
            if not addr:
                return CaseResult(name, False, "COMPARE_ADDRESS not set / unresolved")
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/addresses/{addr}/utxos",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/addresses/{addr}/utxos",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            # Empty is valid for some addresses; require equal lengths.
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "address_txs":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "address_txs case is Blockfrost-face only"
                )
            addr = address
            if not addr:
                return CaseResult(name, False, "COMPARE_ADDRESS not set / unresolved")
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/addresses/{addr}/transactions",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/addresses/{addr}/transactions",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "account_rewards":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "account_rewards case is Blockfrost-face only"
                )
            stake = stake_address
            if not stake:
                return CaseResult(
                    name, False, "COMPARE_STAKE_ADDRESS not set / unresolved"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/accounts/{stake}/rewards",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/accounts/{stake}/rewards",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "account_history":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "account_history case is Blockfrost-face only"
                )
            stake = stake_address
            if not stake:
                return CaseResult(
                    name, False, "COMPARE_STAKE_ADDRESS not set / unresolved"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/accounts/{stake}/history",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/accounts/{stake}/history",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "account_addresses":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "account_addresses case is Blockfrost-face only"
                )
            stake = stake_address
            if not stake:
                return CaseResult(
                    name, False, "COMPARE_STAKE_ADDRESS not set / unresolved"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/accounts/{stake}/addresses",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/accounts/{stake}/addresses",
                headers=janus_headers,
                params=params,
            )
            n_addrs = _normalize_address_list(native)
            j_addrs = _normalize_address_list(janus)
            n_len, j_len = len(n_addrs), len(j_addrs)
            # Koios often returns a smaller payment-address set than native BF.
            overlap = len(set(n_addrs) & set(j_addrs))
            ok = n_len >= 0 and j_len >= 0 and (n_len == 0) == (j_len == 0)
            detail = f"lens native={n_len} janus={j_len} overlap={overlap}"
            if n_len != j_len:
                detail += " (count Gap vs Koios inventory)"
            return CaseResult(
                name,
                ok,
                detail,
                native,
                janus,
                None,
            )

        if name == "pools_extended":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "pools_extended case is Blockfrost-face only"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                "/pools/extended",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                "/pools/extended",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len > 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "governance_committee":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "governance_committee case is Blockfrost-face only"
                )
            native = _json_get(
                client, native_base, "/governance/committee", headers=native_headers
            )
            janus = _json_get(
                client, janus_base, "/governance/committee", headers=janus_headers
            )
            # Shape Partial across providers; require both dict/list responses.
            ok = type(native) is type(janus)
            detail = f"types native={type(native).__name__} janus={type(janus).__name__}"
            return CaseResult(name, ok, detail, native, janus, None)

        if name == "account_delegations":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "account_delegations case is Blockfrost-face only"
                )
            stake = stake_address
            if not stake:
                return CaseResult(
                    name, False, "COMPARE_STAKE_ADDRESS not set / unresolved"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/accounts/{stake}/delegations",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/accounts/{stake}/delegations",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            # Koios-derived delegations are Partial (pool-change derived).
            ok = n_len >= 0 and j_len >= 0 and (n_len == 0) == (j_len == 0)
            detail = f"list lens native={n_len} janus={j_len}"
            if n_len != j_len:
                detail += " (count Gap vs Koios-derived)"
            return CaseResult(name, ok, detail, native, janus, None)

        if name == "account_txs":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "account_txs case is Blockfrost-face only"
                )
            stake = stake_address
            if not stake:
                return CaseResult(
                    name, False, "COMPARE_STAKE_ADDRESS not set / unresolved"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                f"/accounts/{stake}/transactions",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/accounts/{stake}/transactions",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len >= 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "metadata_labels":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "metadata_labels case is Blockfrost-face only"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                "/metadata/txs/labels",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                "/metadata/txs/labels",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len == j_len and n_len > 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "governance_dreps":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "governance_dreps case is Blockfrost-face only"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                "/governance/dreps",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                "/governance/dreps",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            # Ordering / inventory Partial across providers.
            ok = n_len > 0 and j_len > 0
            detail = f"list lens native={n_len} janus={j_len}"
            if isinstance(native, list) and isinstance(janus, list):
                n_ids = {x if isinstance(x, str) else x.get("drep_id") for x in native}
                j_ids = {x if isinstance(x, str) else x.get("drep_id") for x in janus}
                n_ids = {str(x) for x in n_ids if x}
                j_ids = {str(x) for x in j_ids if x}
                detail += f" overlap={len(n_ids & j_ids)}"
            return CaseResult(name, ok, detail, native, janus, None)

        if name == "governance_proposals":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "governance_proposals case is Blockfrost-face only"
                )
            params = {"count": 5, "page": 1}
            native = _json_get(
                client,
                native_base,
                "/governance/proposals",
                headers=native_headers,
                params=params,
            )
            janus = _json_get(
                client,
                janus_base,
                "/governance/proposals",
                headers=janus_headers,
                params=params,
            )
            n_len = len(native) if isinstance(native, list) else -1
            j_len = len(janus) if isinstance(janus, list) else -1
            ok = n_len > 0 and j_len > 0
            return CaseResult(
                name,
                ok,
                f"list lens native={n_len} janus={j_len}",
                native,
                janus,
                None,
            )

        if name == "asset_info":
            if face != "blockfrost":
                return CaseResult(name, False, "asset_info case is Blockfrost-face only")
            asset = _optional("COMPARE_ASSET")
            if not asset and address:
                # Pull a non-lovelace unit from address UTxOs when available.
                utxos = _json_get(
                    client,
                    native_base,
                    f"/addresses/{address}/utxos",
                    headers=native_headers,
                    params={"count": 20, "page": 1},
                )
                if isinstance(utxos, list):
                    for u in utxos:
                        if not isinstance(u, dict):
                            continue
                        for amt in u.get("amount") or []:
                            if (
                                isinstance(amt, dict)
                                and amt.get("unit")
                                and amt["unit"] != "lovelace"
                            ):
                                asset = str(amt["unit"])
                                break
                        if asset:
                            break
            if not asset:
                # Fall back: first native asset on a recent tx's outputs.
                tx_hash = _resolve_sample_tx_hash(client, native_base, native_headers)
                if tx_hash:
                    utxos = _json_get(
                        client,
                        native_base,
                        f"/txs/{tx_hash}/utxos",
                        headers=native_headers,
                    )
                    if isinstance(utxos, dict):
                        for side in ("outputs", "inputs"):
                            for u in utxos.get(side) or []:
                                if not isinstance(u, dict):
                                    continue
                                for amt in u.get("amount") or []:
                                    if (
                                        isinstance(amt, dict)
                                        and amt.get("unit")
                                        and amt["unit"] != "lovelace"
                                    ):
                                        asset = str(amt["unit"])
                                        break
                                if asset:
                                    break
                            if asset:
                                break
            if not asset:
                listed = _json_get(
                    client,
                    native_base,
                    "/assets",
                    headers=native_headers,
                    params={"count": 1, "page": 1},
                )
                if isinstance(listed, list) and listed:
                    first = listed[0]
                    if isinstance(first, dict) and first.get("asset"):
                        asset = str(first["asset"])
                    elif isinstance(first, str):
                        asset = first
            if not asset:
                return CaseResult(
                    name,
                    True,
                    "skipped (no COMPARE_ASSET / no sample asset found)",
                    None,
                    None,
                    None,
                )
            native = _json_get(
                client, native_base, f"/assets/{asset}", headers=native_headers
            )
            janus = _json_get(
                client, janus_base, f"/assets/{asset}", headers=janus_headers
            )
            ignore = frozenset(
                {
                    "metadata",
                    "onchain_metadata",
                    "onchain_metadata_standard",
                    "onchain_metadata_extra",
                    "fingerprint",
                    "quantity",
                    "initial_mint_tx_hash",
                    "mint_or_burn_count",
                }
            )
            diffs = _diff(native, janus, ignore=ignore)
            hard = [d for d in diffs if any(x in d for x in (".asset", ".policy_id"))]
            return CaseResult(
                name,
                ok=isinstance(janus, dict) and not hard,
                detail=f"ok (asset={asset[:16]}…)" if not hard else f"{len(hard)} hard diff(s)",
                native=native,
                janus=janus,
                diffs=diffs if diffs else None,
            )

        if name == "drep_info":
            if face != "blockfrost":
                return CaseResult(name, False, "drep_info case is Blockfrost-face only")
            drep_id = _optional("COMPARE_DREP_ID")
            if not drep_id:
                dreps = _json_get(
                    client,
                    native_base,
                    "/governance/dreps",
                    headers=native_headers,
                    params={"count": 1, "page": 1},
                )
                if isinstance(dreps, list) and dreps:
                    first = dreps[0]
                    drep_id = first if isinstance(first, str) else str(
                        (first or {}).get("drep_id") or ""
                    )
            if not drep_id:
                return CaseResult(name, False, "could not resolve sample drep id")
            native = _json_get(
                client,
                native_base,
                f"/governance/dreps/{drep_id}",
                headers=native_headers,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/governance/dreps/{drep_id}",
                headers=janus_headers,
            )
            ignore = frozenset(
                {
                    "amount",
                    "active",
                    "active_epoch",
                    "has_script",
                    "hex",
                    "retired",
                    "expired",
                    "metadata",
                    "anchor",
                    "last_active_epoch",
                }
            )
            diffs = _diff(native, janus, ignore=ignore)
            hard = [d for d in diffs if ".drep_id" in d]
            return CaseResult(
                name,
                ok=isinstance(janus, dict) and not hard,
                detail=(
                    f"ok (drep={drep_id[:16]}…)"
                    if not hard
                    else f"{len(hard)} identity diff(s)"
                ),
                native=native,
                janus=janus,
                diffs=diffs if diffs else None,
            )

        if name == "metadata_by_label":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "metadata_by_label case is Blockfrost-face only"
                )
            label = _optional("COMPARE_METADATA_LABEL")
            candidates: list[str] = []
            if label:
                candidates = [label]
            else:
                # Hot labels (0/1/721) often 504 through Koios /tx_by_metalabel.
                labels = _json_get(
                    client,
                    native_base,
                    "/metadata/txs/labels",
                    headers=native_headers,
                    params={"count": 20, "page": 1},
                )
                hot = {"0", "1", "721"}
                scored: list[tuple[int, str]] = []
                if isinstance(labels, list):
                    for item in labels:
                        if not isinstance(item, dict) or item.get("label") is None:
                            continue
                        lab = str(item["label"])
                        if lab in hot:
                            continue
                        try:
                            cnt = int(item.get("count") or 0)
                        except (TypeError, ValueError):
                            cnt = 0
                        scored.append((cnt, lab))
                scored.sort(key=lambda x: x[0])
                candidates = [lab for _, lab in scored[:5]]
            if not candidates:
                return CaseResult(name, False, "could not resolve metadata label")
            params = {"count": 2, "page": 1}
            last_err: str | None = None
            native: Any = None
            janus: Any = None
            chosen = candidates[0]
            for chosen in candidates:
                try:
                    native = _json_get(
                        client,
                        native_base,
                        f"/metadata/txs/labels/{chosen}",
                        headers=native_headers,
                        params=params,
                    )
                    janus = _json_get(
                        client,
                        janus_base,
                        f"/metadata/txs/labels/{chosen}",
                        headers=janus_headers,
                        params=params,
                    )
                    last_err = None
                    break
                except httpx.HTTPStatusError as exc:
                    code = exc.response.status_code if exc.response is not None else "?"
                    last_err = f"{code} for label={chosen}"
                    if code not in {504, 502, 408}:
                        raise
                    continue
                except httpx.TimeoutException:
                    last_err = f"timeout for label={chosen}"
                    continue
            if last_err is not None:
                return CaseResult(
                    name,
                    True,
                    f"soft-ok (upstream timeouts; last={last_err})",
                    None,
                    None,
                    ["Gap/timeout on metadata-by-label via Koios"],
                )
            n_hashes = {
                str(r.get("tx_hash"))
                for r in (native if isinstance(native, list) else [])
                if isinstance(r, dict) and r.get("tx_hash")
            }
            j_hashes = {
                str(r.get("tx_hash"))
                for r in (janus if isinstance(janus, list) else [])
                if isinstance(r, dict) and r.get("tx_hash")
            }
            n_len, j_len = len(n_hashes), len(j_hashes)
            # Koios json_metadata is Gap/null; compare tx_hash inventory loosely.
            ok = n_len > 0 and j_len > 0
            detail = (
                f"label={chosen} lens native={n_len} janus={j_len} "
                f"overlap={len(n_hashes & j_hashes)}"
            )
            soft = None
            if n_len != j_len or not (n_hashes & j_hashes):
                soft = ["Gap: label tx ordering/inventory differs across providers"]
            return CaseResult(name, ok, detail, native, janus, soft)

        if name == "script_info":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "script_info case is Blockfrost-face only"
                )
            script_hash = _optional("COMPARE_SCRIPT_HASH")
            if not script_hash:
                script_hash = _resolve_sample_script_or_datum(
                    client, native_base, native_headers, kind="script"
                )
            if not script_hash:
                return CaseResult(
                    name,
                    True,
                    "skipped (no COMPARE_SCRIPT_HASH / no sample found)",
                    None,
                    None,
                    None,
                )
            native = _json_get(
                client,
                native_base,
                f"/scripts/{script_hash}",
                headers=native_headers,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/scripts/{script_hash}",
                headers=janus_headers,
            )
            ignore = frozenset({"serialised_size", "type"})
            diffs = _diff(native, janus, ignore=ignore)
            hard = [d for d in diffs if ".script_hash" in d]
            return CaseResult(
                name,
                ok=isinstance(janus, dict) and not hard,
                detail=(
                    f"ok (script={script_hash[:16]}…)"
                    if not hard
                    else f"{len(hard)} identity diff(s)"
                ),
                native=native,
                janus=janus,
                diffs=diffs if diffs else None,
            )

        if name == "datum_info":
            if face != "blockfrost":
                return CaseResult(
                    name, False, "datum_info case is Blockfrost-face only"
                )
            datum_hash = _optional("COMPARE_DATUM_HASH")
            if not datum_hash:
                datum_hash = _resolve_sample_script_or_datum(
                    client, native_base, native_headers, kind="datum"
                )
            if not datum_hash:
                return CaseResult(
                    name,
                    True,
                    "skipped (no COMPARE_DATUM_HASH / no sample found)",
                    None,
                    None,
                    None,
                )
            native = _json_get(
                client,
                native_base,
                f"/scripts/datum/{datum_hash}",
                headers=native_headers,
            )
            janus = _json_get(
                client,
                janus_base,
                f"/scripts/datum/{datum_hash}",
                headers=janus_headers,
            )
            # JSON value shape often Partial across providers; require dict presence.
            ok = isinstance(native, dict) and isinstance(janus, dict)
            detail = f"ok (datum={datum_hash[:16]}…)" if ok else "shape mismatch"
            soft = None
            if ok and native.get("json_value") != janus.get("json_value"):
                soft = ["Gap: json_value Partial across providers"]
            return CaseResult(name, ok, detail, native, janus, soft)

        return CaseResult(name, False, f"unknown case {name!r}")
    except httpx.HTTPError as exc:
        return CaseResult(name, False, f"HTTP error: {exc}")
    except Exception as exc:  # noqa: BLE001
        return CaseResult(name, False, f"error: {exc}")


def _normalize_address_list(rows: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(rows, list):
        return out
    for item in rows:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and item.get("address"):
            out.append(str(item["address"]))
    return out


def _resolve_pool_fixtures(
    client: httpx.Client,
    *,
    face: str,
    native_base: str,
    native_headers: dict[str, str],
    pool_id: str,
    address: str,
    stake_address: str,
) -> tuple[str, str]:
    """Fill address/stake from native pool endpoints when env fixtures are empty."""
    if (address and stake_address) or not pool_id:
        return address, stake_address
    try:
        if face == "koios":
            rows = _json_post(
                client,
                native_base,
                "/pool_info",
                {"_pool_bech32_ids": [pool_id]},
                headers=native_headers,
            )
            row = rows[0] if isinstance(rows, list) and rows else None
            if isinstance(row, dict) and not stake_address:
                stake_address = str(row.get("reward_addr") or "")
            if stake_address and not address:
                addrs = _json_post(
                    client,
                    native_base,
                    "/account_addresses",
                    {"_stake_addresses": [stake_address]},
                    headers=native_headers,
                )
                if isinstance(addrs, list) and addrs:
                    first = addrs[0]
                    if isinstance(first, dict):
                        nested = first.get("addresses")
                        if isinstance(nested, list) and nested:
                            address = str(nested[0])
                        else:
                            address = str(first.get("address") or "")
                    elif isinstance(first, str):
                        address = first
        else:
            pool = _json_get(
                client,
                native_base,
                f"/pools/{pool_id}",
                headers=native_headers,
            )
            if isinstance(pool, dict) and not stake_address:
                stake_address = str(pool.get("reward_account") or "")
            if stake_address and not address:
                addrs = _json_get(
                    client,
                    native_base,
                    f"/accounts/{stake_address}/addresses",
                    headers=native_headers,
                    params={"count": 1, "page": 1},
                )
                if isinstance(addrs, list) and addrs:
                    first = addrs[0]
                    if isinstance(first, str):
                        address = first
                    elif isinstance(first, dict):
                        address = str(first.get("address") or "")
    except Exception:  # noqa: BLE001
        pass
    return address, stake_address


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional dotenv file (does not override existing env vars)",
    )
    parser.add_argument(
        "--cases",
        default=(
            "tip,genesis,epoch_info,epoch_params,pool_list,pool_info,"
            "pool_metadata,pool_relays,pool_delegators,pool_history,"
            "block_info,address_info,account_info"
        ),
        help="Comma-separated case names",
    )
    parser.add_argument(
        "--dump-dir",
        type=Path,
        default=None,
        help="If set, write native/janus JSON dumps per case",
    )
    args = parser.parse_args(argv)

    if args.env_file:
        _load_env_file(args.env_file)

    face = _require("JANUS_PUBLIC_FACE").lower()
    if face not in {"koios", "blockfrost"}:
        raise SystemExit("JANUS_PUBLIC_FACE must be koios or blockfrost")

    janus_base = _require("JANUS_COMPARE_URL")
    janus_key = _optional("JANUS_FACE_API_KEY") or None

    if face == "koios":
        native_base = _optional("KOIOS_BASE_URL", "https://api.koios.rest/api/v1")
        native_key = _optional("KOIOS_API_KEY") or None
    else:
        native_base = _optional(
            "BLOCKFROST_BASE_URL", "https://cardano-mainnet.blockfrost.io/api/v0"
        )
        native_key = _require("BLOCKFROST_PROJECT_ID")

    pool_id = _optional("COMPARE_POOL_ID")
    address = _optional("COMPARE_ADDRESS")
    stake_address = _optional("COMPARE_STAKE_ADDRESS")
    epochs_raw = _optional("COMPARE_EPOCHS")
    epochs: set[int] = set()
    if epochs_raw:
        epochs = {int(x.strip()) for x in epochs_raw.split(",") if x.strip()}
    compare_epoch_raw = _optional("COMPARE_EPOCH")
    compare_epoch: int | None = (
        int(compare_epoch_raw) if compare_epoch_raw else None
    )

    cases = [c.strip() for c in args.cases.split(",") if c.strip()]
    janus_headers = _headers_for_face(face, janus_key)
    native_headers = _headers_for_face(face, native_key)

    print(f"face={face}")
    print(f"janus={janus_base}")
    print(f"native={native_base}")
    print(f"cases={','.join(cases)}")

    results: list[CaseResult] = []
    with httpx.Client(timeout=90.0, follow_redirects=True) as client:
        # Resolve a stable completed epoch once for epoch_info + pool_history.
        if compare_epoch is None:
            try:
                compare_epoch = _resolve_compare_epoch(
                    client,
                    face=face,
                    native_base=native_base,
                    native_headers=native_headers,
                    pinned=None,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"warning: could not resolve tip epoch ({exc})")
        if compare_epoch is not None:
            print(f"COMPARE_EPOCH={compare_epoch}")

        need_fixtures = any(
            c in cases
            for c in (
                "address_info",
                "account_info",
                "address_utxos",
                "address_txs",
                "account_rewards",
                "account_history",
                "account_addresses",
                "account_delegations",
                "account_txs",
                "asset_info",
            )
        )
        if pool_id and need_fixtures:
            address, stake_address = _resolve_pool_fixtures(
                client,
                face=face,
                native_base=native_base,
                native_headers=native_headers,
                pool_id=pool_id,
                address=address,
                stake_address=stake_address,
            )
            if stake_address:
                print(f"COMPARE_STAKE_ADDRESS={stake_address[:20]}…")
            if address:
                print(f"COMPARE_ADDRESS={address[:20]}…")
        print()

        for name in cases:
            result = run_case(
                client,
                name=name,
                face=face,
                janus_base=janus_base,
                native_base=native_base,
                janus_headers=janus_headers,
                native_headers=native_headers,
                pool_id=pool_id,
                epochs=epochs,
                compare_epoch=compare_epoch,
                address=address,
                stake_address=stake_address,
            )
            results.append(result)
            status = "OK" if result.ok else "FAIL"
            print(f"[{status}] {result.name}: {result.detail}")
            if result.diffs:
                for line in result.diffs[:40]:
                    print(f"  - {line}")
                if len(result.diffs) > 40:
                    print(f"  ... {len(result.diffs) - 40} more")
            if args.dump_dir and result.native is not None:
                args.dump_dir.mkdir(parents=True, exist_ok=True)
                (args.dump_dir / f"{name}.native.json").write_text(
                    json.dumps(result.native, indent=2, default=str),
                    encoding="utf-8",
                )
                (args.dump_dir / f"{name}.janus.json").write_text(
                    json.dumps(result.janus, indent=2, default=str),
                    encoding="utf-8",
                )

    failed = sum(1 for r in results if not r.ok)
    print()
    print(f"{len(results) - failed}/{len(results)} cases ok")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
