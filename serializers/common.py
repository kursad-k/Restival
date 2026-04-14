"""serializers/common.py — pure Python data transformation helpers.

No bpy imports. Accepts bpy-style objects (with .x/.y/.z, .r/.g/.b/.a
attributes) or plain tuples. Safe to test without Blender.
"""
from __future__ import annotations

from typing import Any


def vec3_to_dict(v: Any) -> dict[str, float]:
    """Convert a mathutils.Vector-like or 3-tuple to {"x":…,"y":…,"z":…}."""
    if isinstance(v, (list, tuple)):
        return {"x": float(v[0]), "y": float(v[1]), "z": float(v[2])}
    return {"x": float(v.x), "y": float(v.y), "z": float(v.z)}


def color_to_list(c: Any) -> list[float]:
    """Convert a mathutils.Color-like or tuple to [r, g, b, a].

    3-element tuples get alpha=1.0; 4-element tuples are used as-is.
    """
    if isinstance(c, (list, tuple)):
        if len(c) == 4:
            return [float(c[0]), float(c[1]), float(c[2]), float(c[3])]
        return [float(c[0]), float(c[1]), float(c[2]), 1.0]
    r = float(c.r)
    g = float(c.g)
    b = float(c.b)
    a = float(c.a) if hasattr(c, "a") else 1.0
    return [r, g, b, a]


def paginate(
    items: list[Any], page: int, page_size: int, max_page_size: int = 200
) -> tuple[list[Any], int]:
    """Slice *items* for the requested page.

    Returns (sliced_items, total_count).
    Raises ValueError if page_size is outside 1–max_page_size.
    """
    if page_size < 1 or page_size > max_page_size:
        raise ValueError(f"page_size must be 1\u2013{max_page_size}, got {page_size}")
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total
