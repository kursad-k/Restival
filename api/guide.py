"""api/guide.py — GET /api/v1 agent guide handler.

Parses Help.md on the fly into structured JSON using stdlib only.
No bpy access needed — runs on the worker thread directly.
"""
from __future__ import annotations

from pathlib import Path

_HELP_FILE = Path(__file__).parent.parent / "Help.md"


# ---------------------------------------------------------------------------
# Markdown → dict parser
# ---------------------------------------------------------------------------

def _parse_table(rows: list) -> list:
    """Parse markdown table rows (with header + separator) into list of dicts."""
    if len(rows) < 3:
        return []
    headers = [h.strip() for h in rows[0].strip("|").split("|")]
    result = []
    for row in rows[2:]:  # rows[1] is the --- separator
        cells = [c.strip() for c in row.strip("|").split("|")]
        result.append({headers[j]: cells[j] if j < len(cells) else "" for j in range(len(headers))})
    return result


def _parse_help_md(text: str) -> dict:
    lines = text.splitlines()
    n = len(lines)
    i = 0

    out: dict = {
        "title": "",
        "description": "",
        "quick_start": [],
        "families": [],
        "common_params": {},
        "endpoints": [],
        "compact_keys": {},
        "notes": [],
    }

    # ------------------------------------------------------------------
    # Helpers (closures over i, n, lines)
    # ------------------------------------------------------------------

    def read_code_block(opening_line: str):
        """Consume lines until closing fence. Returns (lang, code_str)."""
        nonlocal i
        lang = opening_line[3:].strip()
        i += 1  # skip opening fence
        buf = []
        while i < n and not lines[i].startswith("```"):
            buf.append(lines[i])
            i += 1
        if i < n:
            i += 1  # skip closing fence
        return lang, "\n".join(buf).strip()

    def read_table():
        """Consume consecutive table rows."""
        nonlocal i
        rows = []
        while i < n and lines[i].startswith("|"):
            rows.append(lines[i])
            i += 1
        return rows

    def read_endpoint_body() -> dict:
        """Consume lines belonging to one endpoint until the next heading or ---."""
        nonlocal i
        body: dict = {"description": "", "returns": "", "examples": []}
        parts = []
        while i < n:
            ln = lines[i]
            if ln.startswith("#") or ln == "---":
                break
            if ln.startswith("```"):
                lang, code = read_code_block(ln)
                if lang == "bash":
                    body["examples"].extend(l.strip() for l in code.splitlines() if l.strip())
                continue
            if ln.startswith("|"):
                read_table()  # discard inline tables
                continue
            if ln.startswith("Returns:"):
                body["returns"] = ln[8:].strip()
                i += 1
                continue
            if ln.strip():
                parts.append(ln.strip())
            i += 1
        body["description"] = " ".join(parts)
        return body

    # ------------------------------------------------------------------
    # Parse title (first # heading)
    # ------------------------------------------------------------------
    while i < n:
        if lines[i].startswith("# "):
            out["title"] = lines[i][2:].strip()
            i += 1
            break
        i += 1

    # ------------------------------------------------------------------
    # Parse body by section
    # ------------------------------------------------------------------
    current_section: str | None = None
    current_endpoint: dict | None = None

    while i < n:
        line = lines[i]

        # Skip blank lines and horizontal rules
        if not line.strip() or line == "---":
            i += 1
            continue

        # Top-level section heading (## but not ###)
        if line.startswith("## "):
            if current_endpoint is not None:
                out["endpoints"].append(current_endpoint)
                current_endpoint = None
            current_section = line[3:].strip()
            i += 1
            continue

        # Description text before the first ##
        if current_section is None:
            out["description"] += (" " if out["description"] else "") + line.strip()
            i += 1
            continue

        # ── Quick start ─────────────────────────────────────────────────
        if current_section == "Quick start":
            if line.startswith("```"):
                lang, code = read_code_block(line)
                if lang == "bash":
                    out["quick_start"].extend(l.strip() for l in code.splitlines() if l.strip())
            else:
                i += 1
            continue

        # ── Route families ───────────────────────────────────────────────
        if current_section == "Route families":
            if line.startswith("|"):
                for row in _parse_table(read_table()):
                    name = row.get("Family", "").strip("*").strip()
                    if name:
                        out["families"].append({
                            "name": name,
                            "prefix": row.get("Prefix", ""),
                            "use_when": row.get("Use when", ""),
                        })
            else:
                i += 1
            continue

        # ── Common query parameters ──────────────────────────────────────
        if current_section == "Common query parameters":
            if line.startswith("### "):
                i += 1
                continue
            if line.startswith("|"):
                for row in _parse_table(read_table()):
                    param = row.get("Param", "").strip("`")
                    if param:
                        out["common_params"][param] = {
                            k.lower(): v for k, v in row.items() if k != "Param"
                        }
            else:
                i += 1
            continue

        # ── Compact key legend ───────────────────────────────────────────
        if current_section.startswith("Compact key legend"):
            if line.startswith("|"):
                for row in _parse_table(read_table()):
                    key = row.get("Key", "").strip("`")
                    if key:
                        out["compact_keys"][key] = row.get("Meaning", "")
            else:
                i += 1
            continue

        # ── Notes ────────────────────────────────────────────────────────
        if current_section == "Notes":
            if line.startswith("- "):
                out["notes"].append(line[2:].strip())
            i += 1
            continue

        # ── Endpoints ────────────────────────────────────────────────────
        if current_section == "Endpoints":

            # ### heading — either a real endpoint (contains GET) or a grouping label
            if line.startswith("### "):
                if current_endpoint is not None:
                    out["endpoints"].append(current_endpoint)
                    current_endpoint = None
                title = line[4:].strip().strip("`")
                i += 1
                if "GET " in title:
                    body = read_endpoint_body()
                    current_endpoint = {"path": title, "sub": [], **body}
                # else: grouping heading like "Mesh endpoints" — no body to parse
                continue

            # #### sub-endpoint
            if line.startswith("#### "):
                title = line[5:].strip().strip("`")
                i += 1
                body = read_endpoint_body()
                sub_ep = {"path": title, **body}
                if current_endpoint is not None:
                    current_endpoint["sub"].append(sub_ep)
                else:
                    out["endpoints"].append(sub_ep)
                continue

            i += 1
            continue

        # All other sections (Response envelope etc.) — skip
        i += 1

    if current_endpoint is not None:
        out["endpoints"].append(current_endpoint)

    return out


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handle_guide(params: dict, query: dict) -> dict:  # noqa: ARG001
    """Parse Help.md and return structured JSON."""
    return _parse_help_md(_HELP_FILE.read_text(encoding="utf-8"))
