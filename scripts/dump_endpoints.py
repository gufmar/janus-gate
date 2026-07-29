"""Extract Blockfrost and Koios OpenAPI endpoint catalogs without full YAML load."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BF = ROOT / "scripts" / "_bf_openapi.yaml"
KO = ROOT / "scripts" / "_ko_openapi.yaml"
OUT = ROOT / "docs" / "api-comparison" / "_endpoint_dump.txt"


def extract_ops(text: str) -> list[dict]:
    """Parse OpenAPI path ops via indentation-aware line scan."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^paths:\s*$", line):
            start = i + 1
            break
    if start is None:
        raise RuntimeError("paths: section not found")

    ops: list[dict] = []
    current_path: str | None = None
    i = start
    while i < len(lines):
        line = lines[i]
        if line and not line[0].isspace():
            break

        path_match = re.match(
            r"""^  ['"]?(/[^'"#:]+)['"]?:\s*(?:#.*)?$""",
            line,
        )
        if path_match:
            current_path = path_match.group(1)
            i += 1
            continue

        method_match = re.match(
            r"^    (get|post|put|patch|delete):\s*(?:#.*)?$",
            line,
            re.I,
        )
        if method_match and current_path:
            method = method_match.group(1).upper()
            summary = ""
            op_id = ""
            tags: list[str] = []
            j = i + 1
            while j < len(lines):
                inner = lines[j]
                if re.match(r"^    (get|post|put|patch|delete):\s*", inner, re.I):
                    break
                if re.match(r"""^  ['"]?/""", inner):
                    break
                if inner and not inner[0].isspace():
                    break
                sm = re.match(r'^      summary:\s*[\'"]?(.*?)[\'"]?\s*$', inner)
                if sm:
                    summary = sm.group(1).rstrip("'\"").strip()
                om = re.match(r'^      operationId:\s*[\'"]?(.*?)[\'"]?\s*$', inner)
                if om:
                    op_id = om.group(1).rstrip("'\"").strip()
                if re.match(r"^      tags:\s*$", inner):
                    k = j + 1
                    while k < len(lines):
                        tag_m = re.match(
                            r"""^        - \s*['"]?(.*?)['"]?\s*$""",
                            lines[k],
                        )
                        if tag_m:
                            tags.append(tag_m.group(1).strip())
                            k += 1
                            continue
                        break
                j += 1
            ops.append(
                {
                    "path": current_path,
                    "method": method,
                    "summary": summary or op_id,
                    "op": op_id,
                    "tags": tags,
                }
            )
        i += 1
    return ops


def main() -> None:
    bf_ops = extract_ops(BF.read_text(encoding="utf-8"))
    ko_ops = extract_ops(KO.read_text(encoding="utf-8"))
    lines: list[str] = [
        f"BF {len(bf_ops)}",
        f"KO {len(ko_ops)}",
        "---BF PATHS---",
    ]
    for o in bf_ops:
        tag = o["tags"][0] if o["tags"] else ""
        lines.append(f"{o['method']:6} {o['path']} | {tag} | {o['summary']}")
    lines.append("---KO PATHS---")
    for o in ko_ops:
        tag = o["tags"][0] if o["tags"] else ""
        lines.append(f"{o['method']:6} {o['path']} | {tag} | {o['summary']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} BF={len(bf_ops)} KO={len(ko_ops)}")


if __name__ == "__main__":
    main()
