"""server/http_server.py — stdlib HTTP backend.

StdlibHTTPBackend implements ServerBackend (core.protocols).
Uses socketserver.ThreadingMixIn + http.server.HTTPServer.

Concurrency cap: threading.Semaphore(10) — acquired in setup(), released in
finish(). Requests beyond the cap block until a slot frees; they won't pile up
unboundedly because the HTTP server's accept() loop is the outer gate.

Error handling in do_GET:
  - ServerBusyError  → 503 Service Unavailable
  - TimeoutError     → 503 Service Unavailable + Retry-After: 5
  - NotFoundError    → 404 Not Found
  - BadRequestError  → 400 Bad Request
  - Unmatched route  → 404 Not Found
  - Any other error  → 500 Internal Server Error
"""
from __future__ import annotations

import http.server
import json
import socketserver
import threading
import time
import urllib.parse
from typing import Any

from server.response import HTTPResponseWriter

_writer = HTTPResponseWriter()
_connection_semaphore = threading.Semaphore(10)


class BlenderAPIHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler — one instance per request."""

    # Injected by StdlibHTTPBackend.start()
    router: Any = None
    execution_strategy: Any = None

    def setup(self) -> None:
        _connection_semaphore.acquire()
        super().setup()

    def finish(self) -> None:
        try:
            super().finish()
        finally:
            _connection_semaphore.release()

    def _handle_request(self, method: str) -> None:
        """Common request handling logic for GET and POST."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = dict(urllib.parse.parse_qsl(parsed.query))
        body = None

        # Parse JSON body for POST requests
        if method == "POST":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                try:
                    raw_body = self.rfile.read(content_length)
                    body = json.loads(raw_body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    _writer.error(self, "BAD_REQUEST", f"Invalid JSON: {exc}", 400)
                    return
            else:
                body = {}

        if self.router is None:
            _writer.error(self, "INTERNAL_ERROR", "Router not configured", 500)
            return

        match = self.router.resolve(path, method)
        if match is None:
            _writer.error(self, "NOT_FOUND", f"No route for {method} {path}", 404)
            return

        handler_fn, params = match

        # Inject the client-facing host so handlers can build absolute URLs.
        query["_host"] = self.headers.get("Host", "localhost")

        # Lazily import error types to avoid circular imports at module load.
        from core.errors import NotFoundError, BadRequestError  # noqa: PLC0415
        from execution.timer_strategy import ServerBusyError  # noqa: PLC0415

        t0 = time.monotonic()

        try:
            if body is not None:
                data = self.execution_strategy.dispatch(
                    lambda: handler_fn(params=params, query=query, body=body),
                    timeout=5.0,
                )
            else:
                data = self.execution_strategy.dispatch(
                    lambda: handler_fn(params=params, query=query),
                    timeout=5.0,
                )
        except ServerBusyError:
            _writer.error(self, "SERVICE_UNAVAILABLE", "Server is busy", 503)
            return
        except TimeoutError:
            self.send_response(503)
            self.send_header("Retry-After", "5")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            body_response = json.dumps({
                "data": None,
                "meta": {},
                "error": {"code": "TIMEOUT", "message": "Request timed out"},
            }).encode("utf-8")
            self.wfile.write(body_response)
            return
        except NotFoundError as exc:
            _writer.error(self, "NOT_FOUND", str(exc), 404)
            return
        except BadRequestError as exc:
            _writer.error(self, "BAD_REQUEST", str(exc), 400)
            return
        except Exception as exc:  # noqa: BLE001
            _writer.error(self, "INTERNAL_ERROR", str(exc), 500)
            return

        elapsed_ms = (time.monotonic() - t0) * 1000.0

        # Handlers return a dict; if it already has pagination meta, use paginated writer.
        if isinstance(data, dict) and "_paginated" in data:
            _writer.paginated(
                self,
                data=data["data"],
                page=data["page"],
                page_size=data["page_size"],
                total=data["total"],
                elapsed_ms=elapsed_ms,
            )
        else:
            status_code = 201 if method == "POST" else 200
            _writer.success(self, data=data, meta={"elapsed_ms": elapsed_ms}, status=status_code)

    def do_GET(self) -> None:  # noqa: N802
        self._handle_request("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle_request("POST")

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: N802
        print(f"[Restival] {self.address_string()} - {fmt % args}")


class _ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class StdlibHTTPBackend:
    """Bind and serve HTTP requests using Python's stdlib server."""

    def __init__(
        self,
        router: Any,
        execution_strategy: Any,
    ) -> None:
        self._router = router
        self._execution_strategy = execution_strategy
        self._server: _ThreadedHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._server is not None

    def start(self, host: str, port: int) -> None:
        """Bind and start serving in a daemon thread."""
        # Inject router + strategy into handler class via a subclass to avoid
        # BaseHTTPRequestHandler's class-level state being shared across instances.
        router = self._router
        strategy = self._execution_strategy

        class _Handler(BlenderAPIHandler):
            pass

        _Handler.router = router
        _Handler.execution_strategy = strategy

        self._server = _ThreadedHTTPServer((host, port), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="restival-http",
        )
        self._thread.start()
        print(f"[Restival] Server started on http://{host}:{port}/api/v1")

    def stop(self) -> None:
        """Shut down the server and join the thread."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        print("[Restival] Server stopped")
