"""api/text_files.py — text file handlers for Blender's text editor.

Routes:
  GET  /api/v1/texts                — list all text files in bpy.data.texts
  GET  /api/v1/texts/{name}         — get content of a specific text file
  POST /api/v1/texts                — create or replace a text file with content

All handlers run on Blender's main thread (dispatched by ExecutionStrategy).
"""
from __future__ import annotations

from core.errors import BadRequestError, NotFoundError


def _activate_existing_text_editor(bpy_module, text) -> bool:
    """Make text current in the first existing Text Editor area."""
    window_manager = getattr(bpy_module.context, "window_manager", None)
    if window_manager is None:
        return False

    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == "TEXT_EDITOR":
                area.spaces.active.text = text
                return True
    return False


def handle_texts_list(params: dict, query: dict) -> dict:
    """Return list of all text files in bpy.data.texts."""
    import bpy  # noqa: PLC0415

    return {
        "texts": [
            {
                "name": text.name,
                "is_dirty": text.is_dirty,
                "is_modified": text.is_modified,
                "filepath": text.filepath if text.filepath else None,
                "lines": len(text.lines),
            }
            for text in bpy.data.texts
        ]
    }


def handle_text_detail(params: dict, query: dict) -> dict:
    """Return content and metadata for a specific text file."""
    import bpy  # noqa: PLC0415

    name: str = params.get("name", "")
    text = bpy.data.texts.get(name)
    if text is None:
        raise NotFoundError(f"Text file '{name}' not found")

    return {
        "name": text.name,
        "content": text.as_string(),
        "is_dirty": text.is_dirty,
        "is_modified": text.is_modified,
        "filepath": text.filepath if text.filepath else None,
        "lines": len(text.lines),
    }


def handle_text_create(params: dict, query: dict, body: dict) -> dict:
    """Create or replace a text file in Blender's text editor.
    
    Expected body:
    {
        "name": "script_name.py",
        "content": "print('Hello from Blender!')"
    }
    """
    import bpy  # noqa: PLC0415

    if not isinstance(body, dict):
        raise BadRequestError("Request body must be a JSON object")

    name = body.get("name")
    content = body.get("content")

    if not name:
        raise BadRequestError("Missing required field: 'name'")
    
    if not isinstance(name, str):
        raise BadRequestError("Field 'name' must be a string")
    
    if content is None:
        content = ""
    
    if not isinstance(content, str):
        raise BadRequestError("Field 'content' must be a string")

    text = bpy.data.texts.get(name)
    created = text is None
    if created:
        text = bpy.data.texts.new(name)
    else:
        text.clear()

    text.from_string(content)
    activated = _activate_existing_text_editor(bpy, text)

    return {
        "name": text.name,
        "content": text.as_string(),
        "is_dirty": text.is_dirty,
        "is_modified": text.is_modified,
        "filepath": text.filepath if text.filepath else None,
        "lines": len(text.lines),
        "created": created,
        "replaced": not created,
        "activated": activated,
    }
