"""server/response.py — JSON response envelope writer.

HTTPResponseWriter implements the ResponseWriter protocol. Every response uses:
  {"data": ..., "meta": ..., "error": ...}

Headers always include:
  Content-Type: application/json; charset=utf-8
  X-Blender-Version: <version string or "unknown">
  X-Server-Name: Restival
"""
from __future__ import annotations

import json
from typing import Any

_CONTENT_TYPE = "application/json; charset=utf-8"


def _blender_version() -> str:
    try:
        import bpy  # noqa: F401 — optional at test time
        return bpy.app.version_string
    except (ImportError, AttributeError):
        return "unknown"


class HTTPResponseWriter:
    """Write Restival JSON envelopes to a BaseHTTPRequestHandler."""

    def _write(self, handler: Any, status: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", _CONTENT_TYPE)
        handler.send_header("Content-Length", str(len(raw)))
        handler.send_header("X-Blender-Version", _blender_version())
        handler.send_header("X-Server-Name", "Restival")
        handler.end_headers()
        handler.wfile.write(raw)

    def success(self, handler: Any, data: Any, meta: dict | None = None) -> None:
        body = {"data": data, "meta": meta or {}, "error": None}
        self._write(handler, 200, body)

    def error(
        self, handler: Any, code: str, message: str, status: int
    ) -> None:
        body = {
            "data": None,
            "meta": {},
            "error": {"code": code, "message": message},
        }
        self._write(handler, status, body)

    def paginated(
        self,
        handler: Any,
        data: Any,
        page: int,
        page_size: int,
        total: int,
        elapsed_ms: float,
    ) -> None:
        meta = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "elapsed_ms": elapsed_ms,
        }
        body = {"data": data, "meta": meta, "error": None}
        self._write(handler, 200, body)
