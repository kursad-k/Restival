"""api/objects.py — object list and detail handlers.

Routes:
  GET /api/v1/scenes/{scene}/objects        — objects linked to a specific scene
  GET /api/v1/scenes/{scene}/objects/{name} — object detail within scene context
  GET /api/v1/objects                       — all objects in bpy.data (scene-independent)
  GET /api/v1/objects/{name}                — object from bpy.data by name

All handlers run on Blender's main thread (dispatched by ExecutionStrategy).
"""
from __future__ import annotations

from core.errors import BadRequestError, NotFoundError
from serializers.common import paginate
from serializers.object_ser import serialize_object_summary, serialize_object_detail


def _get_scene(scene_name: str):
    """Resolve scene by name from bpy.data. Raises NotFoundError if missing."""
    import bpy  # noqa: PLC0415

    scene = bpy.data.scenes.get(scene_name)
    if scene is None:
        raise NotFoundError(f"Scene '{scene_name}' not found")
    return scene


def _apply_type_filter(objects, query: dict) -> list:
    type_filter: str | None = query.get("type")
    if type_filter:
        return [o for o in objects if o.type == type_filter]
    return list(objects)


def _paginate_objects(objects: list, query: dict) -> dict:
    try:
        page = int(query.get("page", 1))
        page_size = int(query.get("page_size", 50))
    except ValueError as exc:
        raise BadRequestError(f"Invalid pagination parameter: {exc}") from exc

    try:
        sliced, total = paginate(objects, page, page_size)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    return {
        "_paginated": True,
        "data": [serialize_object_summary(o) for o in sliced],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Scene-scoped handlers
# ---------------------------------------------------------------------------

def handle_scene_objects_list(params: dict, query: dict) -> dict:
    """Return objects linked to a specific scene.

    Query params:
        type      — filter by object type (MESH, LIGHT, CAMERA, …)
        page      — 1-based page number (default 1)
        page_size — items per page, 1–200 (default 50)
    """
    scene = _get_scene(params.get("scene", ""))
    objects = _apply_type_filter(scene.objects, query)
    return _paginate_objects(objects, query)


def handle_scene_object_detail(params: dict, query: dict) -> dict:
    """Return full detail for an object within a specific scene."""
    scene = _get_scene(params.get("scene", ""))
    name: str = params.get("name", "")
    obj = scene.objects.get(name)
    if obj is None:
        raise NotFoundError(f"Object '{name}' not found in scene '{scene.name}'")
    return serialize_object_detail(obj)


# ---------------------------------------------------------------------------
# Global handlers (bpy.data — scene-independent)
# ---------------------------------------------------------------------------

def handle_objects_list(params: dict, query: dict) -> dict:
    """Return all objects in bpy.data regardless of scene membership.

    Query params:
        type      — filter by object type (MESH, LIGHT, CAMERA, …)
        page      — 1-based page number (default 1)
        page_size — items per page, 1–200 (default 50)
    """
    import bpy  # noqa: PLC0415

    objects = _apply_type_filter(bpy.data.objects, query)
    return _paginate_objects(objects, query)


def handle_object_detail(params: dict, query: dict) -> dict:
    """Return full detail for an object from bpy.data by name."""
    import bpy  # noqa: PLC0415

    name: str = params.get("name", "")
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise NotFoundError(f"Object '{name}' not found in bpy.data")
    return serialize_object_detail(obj)
