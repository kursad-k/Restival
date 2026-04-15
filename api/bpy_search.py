"""api/bpy_search.py — GET /api/v1/search/<term> and /api/v1/search/<term>/<id>

Parses bundled bpy_stubs/ .pyi files with ast, builds a lazy in-memory index.
No bpy access — runs on the worker thread directly.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

_STUBS_DIR = Path(__file__).parent.parent / "bpy_stubs"
_INDEX: list[dict] | None = None


# ---------------------------------------------------------------------------
# Path → module id
# ---------------------------------------------------------------------------

def _path_to_module_id(pyi_path: Path) -> str:
    """Convert e.g. bpy_stubs/gpu-stubs/types/__init__.pyi → gpu.types"""
    rel = pyi_path.relative_to(_STUBS_DIR)
    parts = list(rel.parts[:-1])  # drop __init__.pyi
    parts[0] = parts[0].replace("-stubs", "")
    return ".".join(parts)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _unparse(node: ast.expr | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _extract_params(func: ast.FunctionDef) -> list[dict]:
    params = []
    args = func.args
    n_args = len(args.args)
    n_defaults = len(args.defaults)

    for i, arg in enumerate(args.args):
        if arg.arg in ("self", "cls"):
            continue
        p: dict[str, Any] = {"name": arg.arg}
        if arg.annotation:
            p["type"] = _unparse(arg.annotation)
        default_idx = i - (n_args - n_defaults)
        if default_idx >= 0:
            p["default"] = _unparse(args.defaults[default_idx])
        params.append(p)

    for arg in args.kwonlyargs:
        p = {"name": arg.arg, "kw_only": True}
        if arg.annotation:
            p["type"] = _unparse(arg.annotation)
        params.append(p)

    return params


def _parse_class(node: ast.ClassDef, module_id: str) -> dict:
    doc = ast.get_docstring(node) or ""
    brief = doc.splitlines()[0].strip() if doc else ""

    methods = []
    props = []

    for item in ast.iter_child_nodes(node):
        if isinstance(item, ast.FunctionDef):
            m_doc = ast.get_docstring(item) or ""
            methods.append({
                "name": item.name,
                "brief": m_doc.splitlines()[0].strip() if m_doc else "",
                "doc": m_doc,
                "params": _extract_params(item),
                "returns": _unparse(item.returns),
            })
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            props.append({
                "name": item.target.id,
                "type": _unparse(item.annotation),
            })

    return {
        "id": f"{module_id}.{node.name}",
        "kind": "class",
        "module": module_id,
        "brief": brief,
        "_doc": doc,
        "_methods": methods,
        "_props": props,
    }


def _parse_function(node: ast.FunctionDef, module_id: str) -> dict:
    doc = ast.get_docstring(node) or ""
    brief = doc.splitlines()[0].strip() if doc else ""
    return {
        "id": f"{module_id}.{node.name}",
        "kind": "function",
        "module": module_id,
        "brief": brief,
        "_doc": doc,
        "_params": _extract_params(node),
        "_returns": _unparse(node.returns),
    }


def _parse_pyi(pyi_path: Path) -> list[dict]:
    module_id = _path_to_module_id(pyi_path)
    try:
        tree = ast.parse(pyi_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    entries = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            entries.append(_parse_class(node, module_id))
        elif isinstance(node, ast.FunctionDef):
            entries.append(_parse_function(node, module_id))
    return entries


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

def _build_index() -> list[dict]:
    index = []
    for pyi_path in sorted(_STUBS_DIR.rglob("__init__.pyi")):
        index.extend(_parse_pyi(pyi_path))
    return index


def _get_index() -> list[dict]:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle_bpy_search(params: dict, query: dict) -> dict:
    term = params.get("term", "").lower()
    index = _get_index()

    results = []
    for entry in index:
        if term in entry["id"].lower() or term in entry["brief"].lower() or term in entry.get("_doc", "").lower():
            results.append({
                "id": entry["id"],
                "kind": entry["kind"],
                "module": entry["module"],
                "brief": entry["brief"],
                "detail_url": f"/api/v1/search/{params['term']}/{entry['id']}",
            })
        if len(results) >= 50:
            break

    return {
        "term": params.get("term", ""),
        "count": len(results),
        "results": results,
    }


def handle_bpy_search_detail(params: dict, query: dict) -> dict:
    entry_id = params.get("id", "")
    index = _get_index()

    for entry in index:
        if entry["id"] == entry_id:
            if entry["kind"] == "class":
                return {
                    "id": entry["id"],
                    "kind": "class",
                    "module": entry["module"],
                    "doc": entry["_doc"],
                    "methods": entry["_methods"],
                    "properties": entry["_props"],
                }
            else:
                return {
                    "id": entry["id"],
                    "kind": "function",
                    "module": entry["module"],
                    "doc": entry["_doc"],
                    "params": entry["_params"],
                    "returns": entry["_returns"],
                }

    from core.errors import NotFoundError
    raise NotFoundError(f"No symbol found with id '{entry_id}'")
