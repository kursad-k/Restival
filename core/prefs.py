"""core/prefs.py — addon preferences accessor for use inside the api/ layer.

The api/ handlers run on Blender's main thread but don't have access to the
addon's __package__ name (which differs between Blender 4.1 extensions and
classic addon paths). This helper finds the Restival preferences by looking
for a known attribute rather than hard-coding the package name.
"""
from __future__ import annotations

from typing import Any


def get_addon_prefs() -> Any | None:
    """Return the RESTIVAL_AddonPreferences instance, or None if unavailable."""
    try:
        import bpy  # noqa: PLC0415
        for addon in bpy.context.preferences.addons.values():
            if hasattr(addon.preferences, "allow_script_execution"):
                return addon.preferences
    except Exception:  # noqa: BLE001
        pass
    return None
