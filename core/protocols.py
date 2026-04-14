"""core/protocols.py — structural interfaces for the Restival server layers.

All four protocols are runtime-checkable so isinstance() can verify conformance
in unit tests without importing bpy.
"""
from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class ServerBackend(Protocol):
    """HTTP transport: bind socket, accept connections, shut down."""

    def start(self, host: str, port: int) -> None: ...
    def stop(self) -> None: ...

    @property
    def is_running(self) -> bool: ...


@runtime_checkable
class ExecutionStrategy(Protocol):
    """Dispatch a bpy callable to Blender's main thread and await its result."""

    def dispatch(self, bpy_fn: Callable[[], Any], timeout: float = 5.0) -> Any: ...
    def register(self) -> None: ...
    def unregister(self) -> None: ...


@runtime_checkable
class RequestRouter(Protocol):
    """Map URL patterns to handler callables."""

    def register(self, pattern: str, handler: Callable[..., Any]) -> None: ...
    def resolve(self, path: str) -> tuple[Callable[..., Any], dict[str, str]] | None: ...


@runtime_checkable
class ResponseWriter(Protocol):
    """Write JSON response envelopes to an HTTP handler."""

    def success(self, handler: Any, data: Any, meta: dict | None = None) -> None: ...
    def error(self, handler: Any, code: str, message: str, status: int) -> None: ...
    def paginated(
        self,
        handler: Any,
        data: Any,
        page: int,
        page_size: int,
        total: int,
        elapsed_ms: float,
    ) -> None: ...
