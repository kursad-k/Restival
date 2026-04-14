"""serializers/mesh_ser.py — Blender Mesh serializers.

Pure Python — no bpy import. Accepts a bpy.types.Mesh (evaluated, modifiers
applied) passed in from the api/ layer.

All arrays are 0-indexed, matching Blender's native Python API conventions.

Tuple layouts (also emitted in the schema dict):
  verts          [x, y, z]
  verts+normals  [x, y, z, nx, ny, nz]
  edges          [v0, v1]
  faces          [loop_start, loop_total, mat_idx, nx, ny, nz, use_smooth]
  uvs            [u, v]
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Schema descriptor — emitted once in the /mesh full-block response
# ---------------------------------------------------------------------------

SCHEMA_NO_NORMALS = {
    "verts": ["x", "y", "z"],
    "edges": ["v0", "v1"],
    "faces": ["loop_start", "loop_total", "mat_idx", "nx", "ny", "nz", "use_smooth"],
    "uvs": ["u", "v"],
    "indexing": "0-based",
}

SCHEMA_WITH_NORMALS = {
    "verts": ["x", "y", "z", "nx", "ny", "nz"],
    "edges": ["v0", "v1"],
    "faces": ["loop_start", "loop_total", "mat_idx", "nx", "ny", "nz", "use_smooth"],
    "uvs": ["u", "v"],
    "indexing": "0-based",
}


# ---------------------------------------------------------------------------
# Component serializers
# ---------------------------------------------------------------------------

def serialize_verts(mesh: Any, include_normals: bool = False) -> list:
    """Return vertices as flat tuples.

    Without normals: [x, y, z]
    With normals:    [x, y, z, nx, ny, nz]
    """
    if include_normals:
        return [
            [
                round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6),
                round(v.normal.x, 6), round(v.normal.y, 6), round(v.normal.z, 6),
            ]
            for v in mesh.vertices
        ]
    return [
        [round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6)]
        for v in mesh.vertices
    ]


def serialize_edges(mesh: Any) -> list:
    """Return edges as flat tuples: [v0, v1].

    Additional flags (use_seam, use_sharp, is_loose) omitted for token economy;
    can be added as opt-in query params later.
    """
    return [
        [e.vertices[0], e.vertices[1]]
        for e in mesh.edges
    ]


def serialize_faces(mesh: Any) -> list:
    """Return polygons as flat tuples.

    Layout: [loop_start, loop_total, mat_idx, nx, ny, nz, use_smooth]
    Face normals always included — they are pre-computed and cheap.
    use_smooth encoded as 1/0 (int) to avoid JSON bool token overhead.
    """
    return [
        [
            p.loop_start,
            p.loop_total,
            p.material_index,
            round(p.normal.x, 6),
            round(p.normal.y, 6),
            round(p.normal.z, 6),
            1 if p.use_smooth else 0,
        ]
        for p in mesh.polygons
    ]


def serialize_uvs(mesh: Any) -> list:
    """Return UVs as flat tuples: [u, v], indexed by loop index (0-based).

    Returns [] if no active UV layer exists.
    Array position = loop index — cross-reference via face loop_start/loop_total.
    """
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return []
    return [
        [round(ld.uv.x, 6), round(ld.uv.y, 6)]
        for ld in uv_layer.data
    ]


def serialize_mesh_full(mesh: Any, include_normals: bool = False) -> dict:
    """Return a single coherent mesh data block.

    Includes a schema descriptor so consumers know each tuple's field layout.
    """
    verts = serialize_verts(mesh, include_normals=include_normals)
    edges = serialize_edges(mesh)
    faces = serialize_faces(mesh)
    uvs = serialize_uvs(mesh)

    schema = SCHEMA_WITH_NORMALS if include_normals else SCHEMA_NO_NORMALS

    return {
        "schema": schema,
        "vertex_count": len(verts),
        "edge_count": len(edges),
        "face_count": len(faces),
        "loop_count": len(mesh.loops),
        "uv_count": len(uvs),
        "verts": verts,
        "edges": edges,
        "faces": faces,
        "uvs": uvs,
    }
