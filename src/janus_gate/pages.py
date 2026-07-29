"""HTML overview pages (Janus-native, not part of provider faces)."""

from __future__ import annotations

import html
from collections import defaultdict

from janus_gate import __version__
from janus_gate.catalog import EndpointEntry, endpoints_for_face
from janus_gate.config import ProviderName, public_url


def render_endpoints_html(
    *,
    public_face: ProviderName,
    backend: ProviderName,
    base_path: str = "",
) -> str:
    entries = endpoints_for_face(public_face)
    implemented = sum(1 for e in entries if e.implemented)
    groups: dict[str, list[EndpointEntry]] = defaultdict(list)
    for entry in entries:
        groups[entry.group].append(entry)

    sections: list[str] = []
    for group, items in groups.items():
        rows = "\n".join(_row(item, base_path) for item in items)
        sections.append(
            f"""
      <section>
        <h2>{html.escape(group)}</h2>
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Method</th>
              <th>Path</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
      </section>
"""
        )

    health_href = public_url(base_path, "/health")
    docs_href = public_url(base_path, "/docs")
    base_note = html.escape(base_path or "/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Janus Gate endpoints</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --ink: #1c1917;
      --muted: #57534e;
      --ok: #166534;
      --ok-bg: #dcfce7;
      --todo: #78716c;
      --todo-bg: #e7e5e4;
      --line: #d6d3d1;
      --link: #1d4ed8;
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
      max-width: 960px;
      margin: 0 auto;
      padding: 2rem 1.25rem 3rem;
    }}
    h1 {{
      font-size: 1.75rem;
      margin: 0 0 0.35rem;
    }}
    .meta {{
      color: var(--muted);
      margin: 0 0 1.5rem;
    }}
    .meta a {{ color: var(--link); }}
    h2 {{
      font-size: 1.1rem;
      margin: 1.75rem 0 0.6rem;
      padding-bottom: 0.25rem;
      border-bottom: 1px solid var(--line);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.45rem 0.5rem;
      vertical-align: top;
      border-bottom: 1px solid var(--line);
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    code {{
      font-family: ui-monospace, Consolas, monospace;
      font-size: 0.88em;
    }}
    a {{ color: var(--link); }}
    .badge {{
      display: inline-block;
      padding: 0.1rem 0.45rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge.ok {{ background: var(--ok-bg); color: var(--ok); }}
    .badge.todo {{ background: var(--todo-bg); color: var(--todo); }}
    .note {{
      margin-top: 2rem;
      padding: 0.85rem 1rem;
      background: #fff;
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Janus Gate endpoints</h1>
    <p class="meta">
      version {html.escape(__version__)}
      · public face <strong>{html.escape(public_face.value)}</strong>
      · backend <strong>{html.escape(backend.value)}</strong>
      · base path <strong>{base_note}</strong>
      · {implemented}/{len(entries)} implemented
      · <a href="{html.escape(health_href)}">{html.escape(health_href)}</a>
      · <a href="{html.escape(docs_href)}">{html.escape(docs_href)}</a>
    </p>
    <p class="meta">
      Implemented <strong>GET</strong> routes are linked with the configured
      <code>server.base_path</code> (path parameters may still need values).
      <strong>POST</strong> routes are marked implemented but not clickable.
      Grey rows are known face routes not wired yet.
    </p>
    {"".join(sections)}
    <p class="note">
      This page is Janus-native. Full provider comparison lives in the repo under
      <code>docs/api-comparison/</code>.
    </p>
  </main>
</body>
</html>
"""


def _row(entry: EndpointEntry, base_path: str) -> str:
    status = (
        '<span class="badge ok">implemented</span>'
        if entry.implemented
        else '<span class="badge todo">planned</span>'
    )
    path_html = html.escape(entry.path)
    if entry.implemented and entry.method == "GET" and entry.href:
        href = public_url(base_path, entry.href)
        path_cell = f'<a href="{html.escape(href)}"><code>{path_html}</code></a>'
    else:
        path_cell = f"<code>{path_html}</code>"
    return (
        "<tr>"
        f"<td>{status}</td>"
        f"<td><code>{html.escape(entry.method)}</code></td>"
        f"<td>{path_cell}</td>"
        f"<td>{html.escape(entry.summary)}</td>"
        "</tr>"
    )
