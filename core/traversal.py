"""core/traversal.py — RNA-aware path traverser for bpy.data.

Walks a slash-separated path string against a root object using three
resolution strategies per segment, in order:

  1. getattr(current, segment)         — struct properties, e.g. "name"
  2. current[segment]                  — collection lookup by string key
  3. current[int(segment)]             — collection lookup by integer index

Raises:
  BadRequestError  — path is empty, exceeds MAX_SEGMENTS, or a segment name
                     is in the blocklist.
  NotFoundError    — a segment cannot be resolved on the current object.
"""
from __future__ import annotations

from core.errors import BadRequestError, NotFoundError

MAX_SEGMENTS = 10

# Names that are internal, callable, or potentially dangerous to expose.
_BLOCKLIST: frozenset[str] = frozenset(
    {
        "bl_rna",
        "rna_type",
    }
)


def _is_blocked(segment: str) -> bool:
    return segment.startswith("_") or segment in _BLOCKLIST


def resolve_path(root: object, path: str) -> object:
    """Traverse *path* starting from *root*.

    *path* is a slash-separated string, e.g. ``"images/MyTex/name"``.
    Returns the resolved object at the end of the path.
    """
    if not path:
        raise BadRequestError("Path must not be empty")

    segments = [s for s in path.split("/") if s]

    if len(segments) > MAX_SEGMENTS:
        raise BadRequestError(
            f"Path too deep: {len(segments)} segments (max {MAX_SEGMENTS})"
        )

    current = root
    traversed: list[str] = []

    for segment in segments:
        if _is_blocked(segment):
            raise BadRequestError(
                f"Segment '{segment}' is not accessible"
            )

        resolved = _resolve_segment(current, segment, traversed)
        traversed.append(segment)
        current = resolved

    return current


def _resolve_segment(current: object, segment: str, traversed: list[str]) -> object:
    """Try getattr → string key → integer index for *segment* on *current*."""
    location = "/" + "/".join(traversed) if traversed else "(root)"

    # 1. Attribute access
    if hasattr(current, segment):
        value = getattr(current, segment)
        if callable(value) and not _is_bpy_collection(value):
            raise BadRequestError(
                f"Segment '{segment}' at {location} is callable and not accessible"
            )
        return value

    # 2. String key lookup
    try:
        return current[segment]  # type: ignore[index]
    except (KeyError, TypeError):
        pass

    # 3. Integer index lookup
    try:
        idx = int(segment)
        return current[idx]  # type: ignore[index]
    except (ValueError, IndexError, TypeError):
        pass

    raise NotFoundError(
        f"Segment '{segment}' not found at {location}"
    )


def _is_bpy_collection(obj: object) -> bool:
    """Return True if *obj* looks like a bpy_prop_collection.

    bpy_struct objects also have .items()/.values() but are not iterable.
    Requiring __iter__ correctly excludes structs.
    """
    return hasattr(obj, "items") and hasattr(obj, "values") and hasattr(obj, "__iter__")
