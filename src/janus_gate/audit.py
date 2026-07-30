"""Compatibility audit: record face traffic bound by client IP or public API key."""

from __future__ import annotations

import html
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.parse import quote

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse, Response

from janus_gate import __version__
from janus_gate.auth import extract_public_api_key, mask_api_key, request_app_path
from janus_gate.catalog import EndpointEntry, endpoints_for_face
from janus_gate.config import AppConfig, ProviderName, public_url

logger = logging.getLogger("janus_gate.audit")
access_logger = logging.getLogger("janus_gate.access")

# Magic sessionID value: bind the audit to the resolved client IP.
SESSION_ID_MY_IP = "myIP"

_SKIP_AUDIT_PATHS = frozenset(
    {
        "/health",
        "/endpoints",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/openapi.json",
        "/audit/start",
        "/audit/report",
    }
)

# Path segments that often carry privacy-sensitive identifiers.
_SENSITIVE_PREFIXES = (
    "stake1",
    "stake_test1",
    "addr1",
    "addr_test1",
    "pool1",
    "drep1",
    "asset1",
    "script1",
)

_HEX_RE = re.compile(r"^[0-9a-fA-F]{40,}$")
_BECH32_TAIL_RE = re.compile(r"^[0-9a-z]+$", re.IGNORECASE)


class AuditBindKind(StrEnum):
    IP = "ip"
    API_KEY = "api_key"


class AuditLabel(StrEnum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class AuditEvent:
    ts: float
    method: str
    path: str
    query: str
    status_code: int
    label: AuditLabel
    description: str
    catalog_path: str | None = None
    implemented: bool | None = None


@dataclass
class AuditSession:
    session_id: str
    bind_kind: AuditBindKind
    started_at: float
    expires_at: float
    events: list[AuditEvent] = field(default_factory=list)
    truncated: bool = False


class AuditStore:
    """In-process session store (one active session per bind key)."""

    def __init__(self, *, ttl_seconds: int, max_events: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_events = max_events
        self._lock = threading.Lock()
        self._sessions: dict[str, AuditSession] = {}

    def start(
        self,
        *,
        session_id: str,
        bind_kind: AuditBindKind,
    ) -> AuditSession:
        now = time.time()
        session = AuditSession(
            session_id=session_id,
            bind_kind=bind_kind,
            started_at=now,
            expires_at=now + self._ttl_seconds,
        )
        with self._lock:
            self._purge_locked(now)
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> AuditSession | None:
        now = time.time()
        with self._lock:
            self._purge_locked(now)
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.expires_at <= now:
                self._sessions.pop(session_id, None)
                return None
            return session

    def record_for_keys(self, keys: list[str], event: AuditEvent) -> None:
        if not keys:
            return
        now = time.time()
        with self._lock:
            self._purge_locked(now)
            for key in keys:
                session = self._sessions.get(key)
                if session is None or session.expires_at <= now:
                    continue
                if len(session.events) >= self._max_events:
                    session.truncated = True
                    continue
                session.events.append(event)

    def _purge_locked(self, now: float) -> None:
        expired = [sid for sid, s in self._sessions.items() if s.expires_at <= now]
        for sid in expired:
            self._sessions.pop(sid, None)


def client_ip_from_request(request: Request, *, trusted_proxy_hops: int) -> str:
    """Resolve client IP using X-Forwarded-For / X-Real-IP behind nginx.

    When trusted_proxy_hops >= 1, prefer X-Real-IP, then the leftmost
    X-Forwarded-For entry (nginx typically appends with $proxy_add_x_forwarded_for).
    Janus must not be exposed without the reverse proxy, or clients can spoof XFF.
    """
    if trusted_proxy_hops >= 1:
        real_ip = (request.headers.get("x-real-ip") or "").strip()
        if real_ip:
            return real_ip
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                return parts[0]

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def anonymize_path(path: str, *, keep: int = 5) -> str:
    """Truncate privacy-sensitive path segments (stake keys, addresses, hashes)."""
    if not path:
        return path
    parts = path.split("/")
    out: list[str] = []
    for part in parts:
        if not part:
            out.append(part)
            continue
        out.append(_anonymize_segment(part, keep=keep))
    return "/".join(out)


def anonymize_query(query: str, *, keep: int = 5) -> str:
    if not query:
        return ""
    pieces: list[str] = []
    for pair in query.split("&"):
        if "=" not in pair:
            pieces.append(_anonymize_segment(pair, keep=keep))
            continue
        key, value = pair.split("=", 1)
        pieces.append(f"{key}={_anonymize_segment(value, keep=keep)}")
    return "&".join(pieces)


def _anonymize_segment(segment: str, *, keep: int) -> str:
    if len(segment) <= keep:
        return segment
    lower = segment.lower()
    if any(lower.startswith(prefix) for prefix in _SENSITIVE_PREFIXES):
        return f"{segment[:keep]}..."
    if _HEX_RE.match(segment):
        return f"{segment[:keep]}..."
    if len(segment) >= 20 and _BECH32_TAIL_RE.match(segment):
        return f"{segment[:keep]}..."
    if len(segment) >= 48:
        return f"{segment[:keep]}..."
    return segment


def match_catalog_entry(
    method: str,
    path: str,
    face: ProviderName,
) -> EndpointEntry | None:
    method_u = method.upper()
    for entry in endpoints_for_face(face):
        if entry.method.upper() != method_u:
            continue
        if _path_matches(entry.path, path):
            return entry
    return None


def _path_matches(pattern: str, path: str) -> bool:
    """Match catalog paths like /txs/{hash} against a concrete request path."""
    pat_parts = [p for p in pattern.split("/") if p != ""]
    path_parts = [p for p in path.split("/") if p != ""]
    if len(pat_parts) != len(path_parts):
        return False
    for pat, got in zip(pat_parts, path_parts, strict=True):
        if pat.startswith("{") and pat.endswith("}"):
            continue
        if pat != got:
            return False
    return True


def label_event(
    *,
    status_code: int,
    entry: EndpointEntry | None,
) -> tuple[AuditLabel, str]:
    if entry is None:
        return (
            AuditLabel.UNKNOWN,
            "Path not in Janus face catalog",
        )
    if not entry.implemented:
        return (
            AuditLabel.FAIL,
            f"Known face route not implemented yet ({entry.summary})",
        )
    if 200 <= status_code < 300:
        return AuditLabel.OK, entry.summary
    if status_code == 404:
        return AuditLabel.OK, f"{entry.summary} (resource not found)"
    if 400 <= status_code < 500:
        return AuditLabel.WARN, f"{entry.summary} (client error {status_code})"
    if status_code >= 500:
        return AuditLabel.FAIL, f"{entry.summary} (server error {status_code})"
    return AuditLabel.UNKNOWN, entry.summary


def session_display_id(session: AuditSession) -> str:
    if session.bind_kind is AuditBindKind.API_KEY:
        return mask_api_key(session.session_id) or "(key)"
    return session.session_id


def wants_json(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept and "text/html" not in accept:
        return True
    fmt = (request.query_params.get("format") or "").lower()
    return fmt == "json"


class AuditMiddleware(BaseHTTPMiddleware):
    """Record audited face requests and emit access logs with XFF + anonymized paths."""

    def __init__(self, app: Any, config: AppConfig, store: AuditStore) -> None:
        super().__init__(app)
        self._config = config
        self._store = store

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Use scope path, not request.url.path (url includes ASGI root_path / base_path).
        path = request_app_path(request)
        client_ip = client_ip_from_request(
            request,
            trusted_proxy_hops=self._config.audit.trusted_proxy_hops,
        )
        xff = request.headers.get("x-forwarded-for") or "-"
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        safe_path = anonymize_path(path)
        safe_query = anonymize_query(request.url.query)
        # Log the public path when mounted under base_path (e.g. /janus/...).
        log_path = public_url(self._config.server.base_path, safe_path)
        display = log_path + (f"?{safe_query}" if safe_query else "")
        access_logger.info(
            '%s xff="%s" "%s %s" %s %.1fms',
            client_ip,
            xff,
            request.method,
            display,
            response.status_code,
            elapsed_ms,
        )

        if not self._config.audit.enabled:
            return response
        if path in _SKIP_AUDIT_PATHS or path.startswith("/docs"):
            return response

        entry = match_catalog_entry(
            request.method,
            path,
            self._config.public_face,
        )
        label, description = label_event(
            status_code=response.status_code,
            entry=entry,
        )
        event = AuditEvent(
            ts=time.time(),
            method=request.method.upper(),
            path=safe_path,
            query=safe_query,
            status_code=response.status_code,
            label=label,
            description=description,
            catalog_path=entry.path if entry else None,
            implemented=entry.implemented if entry else None,
        )

        keys: list[str] = []
        # IP-bound session uses the resolved client IP as session_id.
        keys.append(client_ip)
        public_key = extract_public_api_key(request, self._config.public_face)
        if public_key:
            keys.append(public_key)
        self._store.record_for_keys(keys, event)
        return response


def start_session_from_request(
    request: Request,
    config: AppConfig,
    store: AuditStore,
    *,
    session_id_param: str | None,
) -> tuple[AuditSession, str] | tuple[None, str]:
    """Start an audit. Returns (session, error_message)."""
    if not config.audit.enabled:
        return None, "Compatibility audit is disabled on this instance."

    raw = (session_id_param or "").strip()
    if not raw:
        return None, "Missing sessionID. Use myIP or a public API key."

    client_ip = client_ip_from_request(
        request,
        trusted_proxy_hops=config.audit.trusted_proxy_hops,
    )

    if raw == SESSION_ID_MY_IP:
        session = store.start(session_id=client_ip, bind_kind=AuditBindKind.IP)
        return session, ""

    session = store.start(session_id=raw, bind_kind=AuditBindKind.API_KEY)
    return session, ""


def resolve_report_session_id(
    request: Request,
    config: AppConfig,
    *,
    session_id_param: str | None,
) -> str:
    raw = (session_id_param or "").strip()
    if raw and raw != SESSION_ID_MY_IP:
        return raw
    return client_ip_from_request(
        request,
        trusted_proxy_hops=config.audit.trusted_proxy_hops,
    )


def session_to_dict(session: AuditSession) -> dict[str, Any]:
    counts = {label.value: 0 for label in AuditLabel}
    for event in session.events:
        counts[event.label.value] += 1
    return {
        "session_id_display": session_display_id(session),
        "bind_kind": session.bind_kind.value,
        "started_at": session.started_at,
        "expires_at": session.expires_at,
        "truncated": session.truncated,
        "counts": counts,
        "events": [
            {
                "ts": e.ts,
                "method": e.method,
                "path": e.path,
                "query": e.query,
                "status_code": e.status_code,
                "label": e.label.value,
                "description": e.description,
                "catalog_path": e.catalog_path,
                "implemented": e.implemented,
            }
            for e in session.events
        ],
    }


def render_audit_start_page(
    *,
    config: AppConfig,
    client_ip: str,
    started: AuditSession | None = None,
    error: str | None = None,
) -> str:
    base = config.server.base_path
    start_path = public_url(base, "/audit/start")
    report_path = public_url(base, "/audit/report")
    ip_start_href = f"{start_path}?sessionID={SESSION_ID_MY_IP}"
    key_label = (
        "Blockfrost project_id"
        if config.public_face is ProviderName.BLOCKFROST
        else "Koios Bearer token / public API key"
    )

    banner = ""
    if error:
        banner = f'<p class="banner err">{html.escape(error)}</p>'
    elif started is not None:
        report_href = (
            report_path
            if started.bind_kind is AuditBindKind.IP
            else f"{report_path}?sessionID={quote(started.session_id, safe='')}"
        )
        banner = (
            '<p class="banner ok">Audit session started '
            f"({html.escape(started.bind_kind.value)}: "
            f"<code>{html.escape(session_display_id(started))}</code>). "
            f'Open <a href="{html.escape(report_href)}">the report</a> when ready. '
            f"Expires in about {config.audit.session_ttl_minutes} minutes.</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Janus Gate compatibility audit</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --ink: #1c1917;
      --muted: #57534e;
      --line: #d6d3d1;
      --link: #1d4ed8;
      --ok: #166534;
      --ok-bg: #dcfce7;
      --err: #991b1b;
      --err-bg: #fee2e2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.45;
    }}
    main {{
      max-width: 720px;
      margin: 0 auto;
      padding: 2rem 1.25rem 3rem;
    }}
    h1 {{ font-size: 1.6rem; margin: 0 0 0.5rem; }}
    .meta {{ color: var(--muted); margin: 0 0 1.25rem; }}
    .meta a {{ color: var(--link); }}
    section {{
      background: #fff;
      border: 1px solid var(--line);
      padding: 1rem 1.1rem;
      margin: 0 0 1rem;
    }}
    h2 {{ font-size: 1.05rem; margin: 0 0 0.5rem; }}
    code {{
      font-family: ui-monospace, Consolas, monospace;
      font-size: 0.88em;
    }}
    a {{ color: var(--link); }}
    label {{ display: block; margin: 0.75rem 0 0.35rem; }}
    input[type="text"] {{
      width: 100%;
      padding: 0.45rem 0.55rem;
      border: 1px solid var(--line);
      font: inherit;
    }}
    button {{
      margin-top: 0.75rem;
      padding: 0.45rem 0.9rem;
      font: inherit;
      cursor: pointer;
    }}
    .banner {{
      padding: 0.75rem 1rem;
      margin: 0 0 1rem;
      border: 1px solid var(--line);
    }}
    .banner.ok {{ background: var(--ok-bg); color: var(--ok); }}
    .banner.err {{ background: var(--err-bg); color: var(--err); }}
    .note {{ color: var(--muted); font-size: 0.9rem; margin-top: 1.25rem; }}
  </style>
</head>
<body>
  <main>
    <h1>Compatibility audit</h1>
    <p class="meta">
      version {html.escape(__version__)}
      · public face <strong>{html.escape(config.public_face.value)}</strong>
      · backend <strong>{html.escape(config.backend.provider.value)}</strong>
    </p>
    {banner}
    <p>
      Run your existing client against this Janus instance. Janus records the
      requests that match your chosen bind key and labels each as
      ok / warn / fail / unknown. No client code changes are required.
    </p>
    <section>
      <h2>Option 1: bind to your client IP</h2>
      <p>
        Detected client IP: <code>{html.escape(client_ip)}</code>
        (from <code>X-Forwarded-For</code> / <code>X-Real-IP</code> when behind nginx).
      </p>
      <p>
        <a href="{html.escape(ip_start_href)}">Start audit for this IP</a>
        (<code>?sessionID={html.escape(SESSION_ID_MY_IP)}</code>)
      </p>
      <p class="meta">
        Later open <a href="{html.escape(report_path)}"><code>{html.escape(report_path)}</code></a>
        from the same IP.
      </p>
    </section>
    <section>
      <h2>Option 2: bind to your public API key</h2>
      <p>
        Use the same {html.escape(key_label)} your client sends on every request.
        Automation: <code>GET {html.escape(start_path)}?sessionID=&lt;your-key&gt;</code>
      </p>
      <form method="get" action="{html.escape(start_path)}">
        <label for="sessionID">{html.escape(key_label)}</label>
        <input id="sessionID" name="sessionID" type="text" autocomplete="off"
               placeholder="mainnet..." required>
        <button type="submit">Start audit for this key</button>
      </form>
      <p class="meta">
        Later open
        <code>{html.escape(report_path)}?sessionID=&lt;your-key&gt;</code>
      </p>
    </section>
    <p class="note">
      Sessions last {config.audit.session_ttl_minutes} minutes. Starting again with
      the same bind key replaces the previous session. Paths in reports and logs
      are anonymized (sensitive segments truncated). This page is Janus-native.
    </p>
  </main>
</body>
</html>
"""


def render_audit_report_page(
    *,
    config: AppConfig,
    session: AuditSession | None,
    lookup_display: str,
) -> str:
    base = config.server.base_path
    start_href = public_url(base, "/audit/start")
    endpoints_href = public_url(base, "/endpoints")

    if session is None:
        body = f"""
    <p class="banner err">
      No active audit session for <code>{html.escape(lookup_display)}</code>.
      <a href="{html.escape(start_href)}">Start an audit</a> first.
    </p>
"""
    else:
        counts = {label.value: 0 for label in AuditLabel}
        for event in session.events:
            counts[event.label.value] += 1
        rows = "\n".join(_report_row(e) for e in session.events) or (
            '<tr><td colspan="5">No face requests recorded yet.</td></tr>'
        )
        trunc = (
            '<p class="banner warn">Event cap reached; later requests were dropped.</p>'
            if session.truncated
            else ""
        )
        remaining = max(0, int(session.expires_at - time.time()))
        body = f"""
    {trunc}
    <p class="meta">
      bind <strong>{html.escape(session.bind_kind.value)}</strong>
      · id <code>{html.escape(session_display_id(session))}</code>
      · events {len(session.events)}
      · ok {counts["ok"]} · warn {counts["warn"]} · fail {counts["fail"]}
      · unknown {counts["unknown"]}
      · ~{remaining}s remaining
      · <a href="{html.escape(endpoints_href)}">endpoint catalog</a>
    </p>
    <table>
      <thead>
        <tr>
          <th>Label</th>
          <th>Status</th>
          <th>Method</th>
          <th>Path</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Janus Gate audit report</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --ink: #1c1917;
      --muted: #57534e;
      --line: #d6d3d1;
      --link: #1d4ed8;
      --ok: #166534;
      --ok-bg: #dcfce7;
      --warn: #92400e;
      --warn-bg: #fef3c7;
      --fail: #991b1b;
      --fail-bg: #fee2e2;
      --unk: #57534e;
      --unk-bg: #e7e5e4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.45;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 2rem 1.25rem 3rem;
    }}
    h1 {{ font-size: 1.6rem; margin: 0 0 0.5rem; }}
    .meta {{ color: var(--muted); margin: 0 0 1rem; }}
    .meta a {{ color: var(--link); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      background: #fff;
    }}
    th, td {{
      text-align: left;
      padding: 0.4rem 0.5rem;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{ color: var(--muted); }}
    code {{
      font-family: ui-monospace, Consolas, monospace;
      font-size: 0.88em;
    }}
    .badge {{
      display: inline-block;
      padding: 0.1rem 0.45rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .badge.ok {{ background: var(--ok-bg); color: var(--ok); }}
    .badge.warn {{ background: var(--warn-bg); color: var(--warn); }}
    .badge.fail {{ background: var(--fail-bg); color: var(--fail); }}
    .badge.unknown {{ background: var(--unk-bg); color: var(--unk); }}
    .banner {{
      padding: 0.75rem 1rem;
      margin: 0 0 1rem;
      border: 1px solid var(--line);
    }}
    .banner.err {{ background: var(--fail-bg); color: var(--fail); }}
    .banner.warn {{ background: var(--warn-bg); color: var(--warn); }}
  </style>
</head>
<body>
  <main>
    <h1>Audit report</h1>
    {body}
    <p class="meta"><a href="{html.escape(start_href)}">Back to audit start</a></p>
  </main>
</body>
</html>
"""


def _report_row(event: AuditEvent) -> str:
    path = event.path + (f"?{event.query}" if event.query else "")
    return (
        "<tr>"
        f'<td><span class="badge {html.escape(event.label.value)}">'
        f"{html.escape(event.label.value)}</span></td>"
        f"<td><code>{event.status_code}</code></td>"
        f"<td><code>{html.escape(event.method)}</code></td>"
        f"<td><code>{html.escape(path)}</code></td>"
        f"<td>{html.escape(event.description)}</td>"
        "</tr>"
    )


def audit_start_response(
    request: Request,
    config: AppConfig,
    store: AuditStore,
    *,
    session_id_param: str | None,
) -> Response:
    client_ip = client_ip_from_request(
        request,
        trusted_proxy_hops=config.audit.trusted_proxy_hops,
    )
    if not session_id_param:
        if wants_json(request):
            return JSONResponse(
                {
                    "message": (
                        "Pass sessionID=myIP to bind by client IP, "
                        "or sessionID=<public API key> to bind by key."
                    ),
                    "client_ip": client_ip,
                    "options": {
                        "ip": f"?sessionID={SESSION_ID_MY_IP}",
                        "api_key": "?sessionID=<public-api-key>",
                    },
                    "report": public_url(config.server.base_path, "/audit/report"),
                }
            )
        return HTMLResponse(
            render_audit_start_page(config=config, client_ip=client_ip)
        )

    session, err = start_session_from_request(
        request,
        config,
        store,
        session_id_param=session_id_param,
    )
    if session is None:
        if wants_json(request):
            return JSONResponse({"error": err}, status_code=400)
        return HTMLResponse(
            render_audit_start_page(
                config=config,
                client_ip=client_ip,
                error=err,
            ),
            status_code=400,
        )

    if wants_json(request):
        report = public_url(config.server.base_path, "/audit/report")
        if session.bind_kind is AuditBindKind.API_KEY:
            report = f"{report}?sessionID={quote(session.session_id, safe='')}"
        return JSONResponse(
            {
                "status": "started",
                "bind_kind": session.bind_kind.value,
                "session_id_display": session_display_id(session),
                "client_ip": client_ip,
                "expires_at": session.expires_at,
                "ttl_minutes": config.audit.session_ttl_minutes,
                "report_url": report,
            }
        )

    return HTMLResponse(
        render_audit_start_page(
            config=config,
            client_ip=client_ip,
            started=session,
        )
    )


def audit_report_response(
    request: Request,
    config: AppConfig,
    store: AuditStore,
    *,
    session_id_param: str | None,
) -> Response:
    lookup = resolve_report_session_id(
        request,
        config,
        session_id_param=session_id_param,
    )
    session = store.get(lookup)
    display = (
        mask_api_key(lookup) or lookup
        if session_id_param and session_id_param.strip() not in ("", SESSION_ID_MY_IP)
        else lookup
    )

    if wants_json(request):
        if session is None:
            return JSONResponse(
                {"error": "No active audit session", "lookup": display},
                status_code=404,
            )
        return JSONResponse(session_to_dict(session))

    status = 200 if session is not None else 404
    return HTMLResponse(
        render_audit_report_page(
            config=config,
            session=session,
            lookup_display=display,
        ),
        status_code=status,
    )
