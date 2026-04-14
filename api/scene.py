"""api/scene.py — scene list and detail handlers.

Routes:
  GET /api/v1/scenes           — list all scenes from bpy.data.scenes
  GET /api/v1/scenes/{scene}   — detail for a named scene

All handlers run on Blender's main thread (dispatched by ExecutionStrategy).
"""
from __future__ import annotations

from core.errors import NotFoundError


def handle_scenes_list(params: dict, query: dict) -> dict:
    """Return summary list of all scenes in bpy.data."""
    import bpy  # noqa: PLC0415

    return {
        "scenes": [
            {
                "name": s.name,
                "object_count": len(s.objects),
                "frame_start": s.frame_start,
                "frame_end": s.frame_end,
                "active_camera": s.camera.name if s.camera else None,
            }
            for s in bpy.data.scenes
        ]
    }


def handle_scene_detail(params: dict, query: dict) -> dict:
    """Return detail for a named scene."""
    import bpy  # noqa: PLC0415

    scene_name: str = params.get("scene", "")
    scene = bpy.data.scenes.get(scene_name)
    if scene is None:
        raise NotFoundError(f"Scene '{scene_name}' not found")

    return {
        "name": scene.name,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "frame_current": scene.frame_current,
        "fps": scene.render.fps,
        "active_camera": scene.camera.name if scene.camera else None,
        "object_count": len(scene.objects),
        "collection": scene.collection.name,
    }
