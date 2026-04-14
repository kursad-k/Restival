"""api/health.py — GET /api/v1/health handler.

Returns server liveness, Blender version, uptime, and active scene name.
All bpy access happens on the main thread (called via ExecutionStrategy.dispatch).
"""
from __future__ import annotations

import time

_start_time: float = time.monotonic()


def handle_health(params: dict, query: dict) -> dict:
    """Return server health information.

    Called on Blender's main thread by TimerExecutionStrategy.
    Returns a plain dict — JSON encoding happens on the worker thread.
    """
    import bpy  # noqa: PLC0415 — imported at call time (main thread only)

    uptime = time.monotonic() - _start_time
    filepath = bpy.data.filepath
    is_saved = bool(filepath)

    return {
        "status": "ok",
        "blender_version": bpy.app.version_string,
        "uptime_seconds": round(uptime, 3),
        "is_saved": is_saved,
        "active_scene": bpy.context.scene.name,
    }
