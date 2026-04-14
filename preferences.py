"""preferences.py — Restival addon preferences panel.

Registered automatically by auto_load.py (AddonPreferences subclass).
bl_idname must match the addon's module path. In Blender 4.2+ extensions this
is the full package name (e.g. bl_ext.vscode_development.Addon_Blender_Restival),
not just the id from blender_manifest.toml. Using __package__ covers both cases.
"""
import bpy


class RESTIVAL_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    port: bpy.props.IntProperty(
        name="Port",
        description="TCP port the REST API server listens on",
        default=2357,
        min=1024,
        max=65535,
    )  # type: ignore[assignment]

    network_mode: bpy.props.BoolProperty(
        name="Network Mode",
        description=(
            "When enabled the server binds 0.0.0.0 (all interfaces) instead of "
            "127.0.0.1 (localhost only)"
        ),
        default=False,
    )  # type: ignore[assignment]

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "port")
        layout.prop(self, "network_mode")
