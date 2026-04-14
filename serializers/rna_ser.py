"""serializers/rna_ser.py — generic RNA value serializer.

Converts arbitrary bpy RNA objects to JSON-safe Python primitives.

Safety layers (in order applied):
  1. bytes / bytearray        → metadata stub, no data emitted
  2. Sequence length cap       → arrays > MAX_ARRAY_LENGTH get truncated stub
  3. Callable                  → skipped
  4. mathutils types           → list of floats
  5. bpy_prop_collection       → list of summaries (name + type)
  6. bpy_struct                → dict of scalar/simple properties
  7. Scalars                   → as-is
"""
from __future__ import annotations

from typing import Any

# Maximum number of elements emitted from a numeric array or collection.
MAX_ARRAY_LENGTH = 500

# Property types considered safe to inline as scalars.
_SCALAR_TYPES = (bool, int, float, str)

# Names of known mathutils vector/matrix types (checked via type name string
# to avoid importing mathutils outside of Blender).
_MATHUTILS_TYPES = frozenset(
    {
        "Vector",
        "Euler",
        "Quaternion",
        "Matrix",
        "Color",
    }
)


def serialize_value(value: Any, *, depth: int = 0) -> Any:
    """Recursively serialize *value* to a JSON-safe primitive.

    *depth* prevents infinite recursion on circular RNA structures.
    At depth >= 2 only scalars and stubs are returned.
    """
    # --- binary data ---
    if isinstance(value, (bytes, bytearray)):
        return {
            "t": "binary",
            "size": len(value),
            "note": "Binary data is not serialized. Use a dedicated file export instead.",
        }

    # --- scalars (fast path) ---
    if isinstance(value, _SCALAR_TYPES):
        return value

    # --- None ---
    if value is None:
        return None

    # --- mathutils types (Vector, Matrix, Color, …) ---
    type_name = type(value).__name__
    if type_name in _MATHUTILS_TYPES:
        return _serialize_mathutils(value)

    # --- numeric sequences (e.g. image.pixels, mesh attribute arrays) ---
    if _is_numeric_sequence(value):
        length = len(value)
        if length > MAX_ARRAY_LENGTH:
            return {
                "t": "array",
                "len": length,
                "trunc": True,
                "note": (
                    f"Array has {length} elements (max {MAX_ARRAY_LENGTH} shown). "
                    "Use dedicated mesh endpoints or export the data directly."
                ),
            }
        return list(value)

    # Depth guard — avoid deeply nested struct expansion
    if depth >= 2:
        return _scalar_stub(value)

    # --- bpy_prop_collection ---
    if _is_bpy_collection(value):
        return _serialize_collection(value, depth=depth)

    # --- bpy_struct (any other RNA struct) ---
    if _is_bpy_struct(value):
        return _serialize_struct(value, depth=depth)

    # --- fallback ---
    return _scalar_stub(value)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _serialize_mathutils(value: Any) -> list[float]:
    """Flatten a mathutils type to a list of floats."""
    try:
        # Matrix: flatten row by row
        if type(value).__name__ == "Matrix":
            return [float(x) for row in value for x in row]
        return [float(x) for x in value]
    except (TypeError, AttributeError):
        return str(value)


def _is_numeric_sequence(value: Any) -> bool:
    """Return True if *value* is a sized, indexable sequence of numbers.

    Excludes str/bytes (handled separately) and dicts.
    """
    if isinstance(value, (str, bytes, bytearray, dict)):
        return False
    if not hasattr(value, "__len__") or not hasattr(value, "__getitem__"):
        return False
    # Sample the first element to confirm numeric content
    try:
        if len(value) == 0:
            return True  # empty numeric sequence is fine
        return isinstance(value[0], (int, float, bool))
    except (IndexError, TypeError):
        return False


def _is_bpy_collection(value: Any) -> bool:
    """Return True if *value* looks like a bpy_prop_collection.

    bpy_struct objects (MeshVertex, Object, etc.) also have .items()/.values()
    from RNA property access, but they are NOT iterable. Requiring __iter__
    correctly excludes structs and accepts only real collections.
    """
    return (
        hasattr(value, "items")
        and hasattr(value, "values")
        and hasattr(value, "__iter__")
        and not isinstance(value, dict)
    )


def _is_bpy_struct(value: Any) -> bool:
    """Return True if *value* looks like a bpy_struct (has bl_rna or rna_type)."""
    return hasattr(value, "bl_rna") or hasattr(value, "rna_type")


def _serialize_collection(collection: Any, *, depth: int) -> dict:
    """Serialize a bpy_prop_collection as {total, items} with per-item indices."""
    total = len(collection) if hasattr(collection, "__len__") else None
    items = []
    truncated = False
    for i, item in enumerate(collection):
        if i >= MAX_ARRAY_LENGTH:
            truncated = True
            break
        items.append(_item_summary(item, index=i))

    result: dict[str, Any] = {
        "tot": total if total is not None else len(items),
        "items": items,
    }
    if truncated:
        result["trunc"] = True
        result["note"] = f"Collection truncated at {MAX_ARRAY_LENGTH} items. Use index path to access individual items."
    return result


def _item_summary(item: Any, index: int = 0) -> dict:
    """Compact summary for a collection member: i=index, t=type, n=name if available."""
    summary: dict[str, Any] = {"i": index, "t": type(item).__name__}
    for attr in ("name", "type", "bl_idname"):
        if hasattr(item, attr):
            v = getattr(item, attr)
            if isinstance(v, str):
                summary["n" if attr == "name" else attr] = v
    return summary


def _serialize_struct(struct: Any, *, depth: int) -> dict:
    """Serialize a bpy_struct as a dict of its scalar/simple properties."""
    result: dict[str, Any] = {"t": type(struct).__name__}

    try:
        rna = struct.bl_rna
        props = rna.properties
    except AttributeError:
        return result

    for prop in props:
        name = prop.identifier
        if name.startswith("_") or name in ("bl_rna", "rna_type"):
            continue
        try:
            raw = getattr(struct, name)
        except Exception:  # noqa: BLE001
            continue

        if callable(raw) and not _is_bpy_collection(raw):
            continue

        result[name] = serialize_value(raw, depth=depth + 1)

    return result


def _scalar_stub(value: Any) -> dict:
    """Return a type-only stub for values we cannot safely serialize."""
    return {"t": type(value).__name__, "note": "Value not serializable as JSON."}
