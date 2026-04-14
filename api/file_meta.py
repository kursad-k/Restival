"""api/file_meta.py — GET /api/v1/file handler.

Returns .blend file metadata: path, save state, scene list,
unit system, unit scale, and Blender version.
"""
from __future__ import annotations


def handle_file(params: dict, query: dict) -> dict:
    """Return metadata about the open .blend file.

    Called on Blender's main thread by TimerExecutionStrategy.
    """
    import bpy  # noqa: PLC0415

    filepath = bpy.data.filepath
    is_saved = bool(filepath)
    unit = bpy.context.scene.unit_settings

    return {
        "filepath": filepath,
        "is_saved": is_saved,
        "blender_version": bpy.app.version_string,
        "active_scene": bpy.context.scene.name,
        "scenes": [s.name for s in bpy.data.scenes],
        "unit_system": unit.system,
        "unit_scale": unit.scale_length,
    }
