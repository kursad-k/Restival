"""api/mesh.py — mesh data handlers.

Routes:
  GET /api/v1/scenes/{scene}/objects/{name}/mesh
  GET /api/v1/scenes/{scene}/objects/{name}/mesh/verts
  GET /api/v1/scenes/{scene}/objects/{name}/mesh/edges
  GET /api/v1/scenes/{scene}/objects/{name}/mesh/faces
  GET /api/v1/scenes/{scene}/objects/{name}/mesh/uvs

All handlers run on Blender's main thread (dispatched by ExecutionStrategy).
Returns plain dicts/lists — JSON encoding happens on the worker thread.

Mesh is always evaluated (modifiers applied) via depsgraph.
Query params:
  normals=true  — include vertex normals on /mesh and /mesh/verts (opt-in)
"""
from __future__ import annotations

from core.errors import BadRequestError, NotFoundError
from serializers.common import paginate
from serializers.mesh_ser import (
    serialize_verts,
    serialize_edges,
    serialize_faces,
    serialize_uvs,
    serialize_mesh_full,
    SCHEMA_NO_NORMALS,
    SCHEMA_WITH_NORMALS,
)


def _get_evaluated_mesh(scene_name: str, name: str):
    """Resolve object from scene and return evaluated mesh.

    Raises NotFoundError if scene or object is not found.
    Raises BadRequestError if the object is not a MESH type.
    """
    import bpy  # noqa: PLC0415

    scene = bpy.data.scenes.get(scene_name)
    if scene is None:
        raise NotFoundError(f"Scene '{scene_name}' not found")

    obj = scene.objects.get(name)
    if obj is None:
        raise NotFoundError(f"Object '{name}' not found in scene '{scene_name}'")
    if obj.type != "MESH":
        raise BadRequestError(
            f"Object '{name}' is type '{obj.type}', not MESH"
        )

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    return mesh


def _parse_normals_flag(query: dict) -> bool:
    return query.get("normals", "").lower() == "true"


_MESH_MAX_PAGE_SIZE = 10_000


def _pagination_requested(query: dict) -> bool:
    return "page" in query or "page_size" in query


def _parse_pagination(query: dict) -> tuple[int, int]:
    try:
        page = int(query.get("page", 1))
        page_size = int(query.get("page_size", _MESH_MAX_PAGE_SIZE))
    except ValueError as exc:
        raise BadRequestError(f"Invalid pagination parameter: {exc}") from exc
    return page, page_size


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle_mesh_full(params: dict, query: dict) -> dict:
    """Return a single coherent mesh data block — all components combined."""
    mesh = _get_evaluated_mesh(params.get("scene", ""), params.get("name", ""))
    return serialize_mesh_full(mesh, include_normals=_parse_normals_flag(query))


def handle_mesh_verts(params: dict, query: dict) -> dict:
    """Return vertex array. Full by default; paginated if page/page_size supplied.

    Each entry: [x, y, z] or [x, y, z, nx, ny, nz] with ?normals=true
    Array position = vertex index (0-based).
    """
    include_normals = _parse_normals_flag(query)
    schema = SCHEMA_WITH_NORMALS["verts"] if include_normals else SCHEMA_NO_NORMALS["verts"]

    mesh = _get_evaluated_mesh(params.get("scene", ""), params.get("name", ""))
    verts = serialize_verts(mesh, include_normals=include_normals)

    if not _pagination_requested(query):
        return {"schema": schema, "data": verts, "total": len(verts)}

    page, page_size = _parse_pagination(query)
    try:
        sliced, total = paginate(verts, page, page_size, max_page_size=_MESH_MAX_PAGE_SIZE)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    return {
        "_paginated": True,
        "schema": schema,
        "data": sliced,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def handle_mesh_edges(params: dict, query: dict) -> dict:
    """Return edge array. Full by default; paginated if page/page_size supplied.

    Each entry: [v0, v1] — vertex indices (0-based).
    Array position = edge index (0-based).
    """
    mesh = _get_evaluated_mesh(params.get("scene", ""), params.get("name", ""))
    edges = serialize_edges(mesh)

    if not _pagination_requested(query):
        return {"schema": SCHEMA_NO_NORMALS["edges"], "data": edges, "total": len(edges)}

    page, page_size = _parse_pagination(query)
    try:
        sliced, total = paginate(edges, page, page_size, max_page_size=_MESH_MAX_PAGE_SIZE)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    return {
        "_paginated": True,
        "schema": SCHEMA_NO_NORMALS["edges"],
        "data": sliced,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def handle_mesh_faces(params: dict, query: dict) -> dict:
    """Return face array. Full by default; paginated if page/page_size supplied.

    Each entry: [loop_start, loop_total, mat_idx, nx, ny, nz, use_smooth]
    Array position = face index (0-based).
    """
    mesh = _get_evaluated_mesh(params.get("scene", ""), params.get("name", ""))
    faces = serialize_faces(mesh)

    if not _pagination_requested(query):
        return {"schema": SCHEMA_NO_NORMALS["faces"], "data": faces, "total": len(faces)}

    page, page_size = _parse_pagination(query)
    try:
        sliced, total = paginate(faces, page, page_size, max_page_size=_MESH_MAX_PAGE_SIZE)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    return {
        "_paginated": True,
        "schema": SCHEMA_NO_NORMALS["faces"],
        "data": sliced,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def handle_mesh_uvs(params: dict, query: dict) -> dict:
    """Return UV array. Full by default; paginated if page/page_size supplied.

    Each entry: [u, v], indexed by loop index (0-based).
    Returns empty data if no active UV layer exists.
    Cross-reference with face loop_start/loop_total to map UVs to vertices.
    """
    mesh = _get_evaluated_mesh(params.get("scene", ""), params.get("name", ""))
    uvs = serialize_uvs(mesh)

    if not _pagination_requested(query):
        return {"schema": SCHEMA_NO_NORMALS["uvs"], "data": uvs, "total": len(uvs)}

    page, page_size = _parse_pagination(query)
    try:
        sliced, total = paginate(uvs, page, page_size, max_page_size=_MESH_MAX_PAGE_SIZE)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    return {
        "_paginated": True,
        "schema": SCHEMA_NO_NORMALS["uvs"],
        "data": sliced,
        "page": page,
        "page_size": page_size,
        "total": total,
    }
