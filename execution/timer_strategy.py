"""execution/timer_strategy.py — bpy.app.timers-based execution strategy.

TimerExecutionStrategy implements ExecutionStrategy (core.protocols).

Architecture:
- Worker threads (HTTP handler threads) call dispatch(bpy_fn) which
  puts work onto a bounded queue and blocks waiting for the result.
- Blender's main thread runs _drain_once() via bpy.app.timers:
    - returns 0.0 when work was processed (re-register immediately)
    - returns 0.05 when queue empty (idle interval, prevents hot loop)
- Queue is bounded (maxsize=5). When full, dispatch raises ServerBusyError.
- dispatch times out after `timeout` seconds, raising TimeoutError.
"""
from __future__ import annotations

import queue
import threading
from typing import Any, Callable


class ServerBusyError(Exception):
    """Raised when the work queue is full (too many concurrent requests)."""


class TimerExecutionStrategy:
    """Dispatch bpy callables to Blender's main thread via a bounded queue."""

    _IDLE_INTERVAL = 0.05  # seconds to sleep when queue is empty

    def __init__(self) -> None:
        self._work_queue: queue.Queue[
            tuple[Callable[[], Any], threading.Event, dict]
        ] = queue.Queue(maxsize=5)
        self._drain_fn: Callable[[], float] | None = None

    # ------------------------------------------------------------------
    # ExecutionStrategy protocol
    # ------------------------------------------------------------------

    def dispatch(self, bpy_fn: Callable[[], Any], timeout: float = 5.0) -> Any:
        """Put *bpy_fn* on the queue and wait for the main thread to execute it.

        Raises:
            ServerBusyError: queue is full
            TimeoutError: main thread did not respond within *timeout* seconds
        """
        event = threading.Event()
        result_box: dict[str, Any] = {}
        try:
            self._work_queue.put_nowait((bpy_fn, event, result_box))
        except queue.Full as exc:
            raise ServerBusyError("Work queue full — server is busy") from exc

        if not event.wait(timeout):
            raise TimeoutError(
                f"bpy callable did not complete within {timeout}s"
            )

        if "error" in result_box:
            raise result_box["error"]
        return result_box.get("data")

    def register(self) -> None:
        """Register the drain loop with bpy.app.timers."""
        import bpy  # noqa: PLC0415 — imported at call time to allow unit testing

        def _drain_loop() -> float:
            return self._drain_once()

        self._drain_fn = _drain_loop
        bpy.app.timers.register(_drain_loop, first_interval=0.0)

    def unregister(self) -> None:
        """Unregister the drain loop if it is still registered."""
        import bpy  # noqa: PLC0415

        if self._drain_fn is not None and bpy.app.timers.is_registered(
            self._drain_fn
        ):
            bpy.app.timers.unregister(self._drain_fn)

    # ------------------------------------------------------------------
    # Internal — called by the timer; also callable directly in tests
    # ------------------------------------------------------------------

    def _drain_once(self) -> float:
        """Drain one item from the queue.  Called on the main thread.

        Returns:
            0.0  — work was processed, re-register immediately
            0.05 — queue was empty, check again after idle interval
        """
        try:
            bpy_fn, event, result_box = self._work_queue.get_nowait()
        except queue.Empty:
            return self._IDLE_INTERVAL

        try:
            result_box["data"] = bpy_fn()
        except Exception as exc:  # noqa: BLE001
            result_box["error"] = exc
        finally:
            event.set()

        return 0.0
