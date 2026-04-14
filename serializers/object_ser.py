"""serializers/object_ser.py — Blender Object serializers.

Pure Python — no bpy import. Accepts bpy Object instances (or mocks with the
same attribute shape) passed in from the api/ layer.

serialize_object_summary → lightweight dict for list endpoints
serialize_object_detail  → full dict for single-resource endpoints
"""
from __future__ import annotations

from typing import Any

from serializers.common import vec3_to_dict


def serialize_object_summary(obj: Any) -> dict:
    """Return a lightweight representation suitable for collection responses."""
    linked = obj.library is not None
    library_path = obj.library.filepath if linked else None

    return {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "collections": [c.name for c in obj.users_collection],
        "visible": not obj.hide_viewport,
        "linked": linked,
        "library": library_path,
    }


def serialize_object_detail(obj: Any) -> dict:
    """Return a full representation including transforms, materials, and modifiers."""
    detail = serialize_object_summary(obj)

    detail["location"] = vec3_to_dict(obj.location)
    detail["rotation_mode"] = obj.rotation_mode
    detail["rotation_euler"] = vec3_to_dict(obj.rotation_euler)
    detail["rotation_quaternion"] = {
        "x": float(obj.rotation_quaternion.x),
        "y": float(obj.rotation_quaternion.y),
        "z": float(obj.rotation_quaternion.z),
        "w": float(obj.rotation_quaternion.w),
    }
    detail["scale"] = vec3_to_dict(obj.scale)
    detail["dimensions"] = vec3_to_dict(obj.dimensions)
    detail["data_name"] = obj.data.name if obj.data else None

    # Material slots — name or empty string if slot has no material
    detail["material_slots"] = [
        slot.material.name if slot.material else ""
        for slot in obj.material_slots
    ]

    # Modifiers — name, type, viewport visibility
    detail["modifiers"] = [
        {
            "name": mod.name,
            "type": mod.type,
            "show_viewport": mod.show_viewport,
        }
        for mod in obj.modifiers
    ]

    # Constraints — type strings only
    detail["constraints"] = [con.type for con in obj.constraints]

    # Custom properties (id_props) — scalar values only
    custom: dict[str, Any] = {}
    for key in obj.keys():
        val = getattr(obj, key, None)
        if isinstance(val, (int, float, bool, str)):
            custom[key] = val
    detail["custom_properties"] = custom

    return detail
