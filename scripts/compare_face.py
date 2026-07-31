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


def _tip_epoch_no(client: httpx.Client, base: str, headers: dict[str, str]) -> int:
    tip = _json_get(client, base, "/tip", headers=headers)
    row = tip[0] if isinstance(tip, list) and tip else tip
    if not isinstance(row, dict) or "epoch_no" not in row:
        raise ValueError(f"Unexpected tip payload from {base}")
    return int(row["epoch_no"])


def _resolve_compare_epoch(
    client: httpx.Client,
    *,
    face: str,
    native_base: str,
    native_headers: dict[str, str],
    pinned: int | None,
) -> int | None:
    """Pick a stable epoch for apple-to-apple compares.

    Prefer COMPARE_EPOCH. Otherwise for Koios use tip.epoch_no - 2 so
    pool_history (reward lag) and completed epoch_info both have data.
    """
    if pinned is not None:
        return pinned
    if face != "koios":
        return None
    tip_epoch = _tip_epoch_no(client, native_base, native_headers)
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
                | frozenset({"epoch", "epoch_no", "block_no"})
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

        return CaseResult(name, False, f"unknown case {name!r}")
    except httpx.HTTPError as exc:
        return CaseResult(name, False, f"HTTP error: {exc}")
    except Exception as exc:  # noqa: BLE001
        return CaseResult(name, False, f"error: {exc}")


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
        default="tip,genesis,epoch_info,pool_list,pool_history",
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
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        # Resolve a stable completed epoch once for epoch_info + pool_history.
        if compare_epoch is None and face == "koios":
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
