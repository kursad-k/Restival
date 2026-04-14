"""api/traverse.py — GET /api/v1/data/{path} handler.

Traverses bpy.data using the path segments supplied in the URL.
Examples:
  GET /api/v1/data/scenes                         → list of scene summaries
  GET /api/v1/data/scenes/Scene                   → scene struct
  GET /api/v1/data/scenes/Scene/name              → "Scene" (string scalar)
  GET /api/v1/data/objects/Cube/location          → [x, y, z]
  GET /api/v1/data/images/MyTex/size              → [w, h]
  GET /api/v1/data/images/MyTex/pixels            → truncated stub (binary guard)

Runs on Blender's main thread (dispatched by ExecutionStrategy).
"""
from __future__ import annotations

from core.traversal import resolve_path
from serializers.rna_ser import serialize_value

# Attributes of bpy.data that are callable/internal and not useful to expose.
_DATA_SKIP = frozenset({
    "bl_rna", "rna_type", "batch_remove", "orphans_purge",
    "file_path_foreach", "file_path_map", "pack_linked_ids_hierarchy",
    "user_map", "temp_data", "colorspace",
})


def handle_data_root(params: dict, query: dict) -> dict:
    """Return a directory of available bpy.data collections and scalar properties."""
    import bpy  # noqa: PLC0415

    collections = []
    scalars = {}

    for name in dir(bpy.data):
        if name.startswith("_") or name in _DATA_SKIP:
            continue
        try:
            val = getattr(bpy.data, name)
        except Exception:  # noqa: BLE001
            continue
        if callable(val):
            continue
        if hasattr(val, "__iter__") and hasattr(val, "values"):
            length = len(val) if hasattr(val, "__len__") else None
            entry = {"n": name}
            if length is not None:
                entry["tot"] = length
            collections.append(entry)
        elif isinstance(val, (bool, int, float, str)):
            scalars[name] = val

    return {
        "path": "",
        "collections": collections,
        "properties": scalars,
    }


def handle_traverse(params: dict, query: dict) -> dict:
    """Traverse bpy.data at the given path and return a serialized response."""
    import bpy  # noqa: PLC0415

    path: str = params.get("path", "")
    value = resolve_path(bpy.data, path)
    serialized = serialize_value(value)

    return {
        "path": path,
        "t": type(value).__name__,
        "value": serialized,
    }
