"""panels.py — Restival N-panel in 3D Viewport sidebar.

Registered automatically by auto_load.py.
Reads `context.scene.restival_running` (set by operators.py) to determine
display state — no direct import of server modules (avoids circular deps).
"""
import bpy
from core.network import get_local_ips


def _rest_api_url(ip: str, port: int) -> str:
    return f"http://{ip}:{port}/api/v1"


def _draw_copy_row(layout: bpy.types.UILayout, label: str, url: str, icon: str = "NONE") -> None:
    row = layout.row(align=True)
    split = row.split(factor=0.78, align=True)
    split.label(text=label, icon=icon)
    btn_row = split.row(align=False)
    url_op = btn_row.operator("restival.copy_rest_url", text="", icon="COPYDOWN")
    url_op.url = url
    url_op.mode = "url"
    btn_row.separator(factor=0.3)
    agent_op = btn_row.operator("restival.copy_rest_url", text="", icon="SCRIPT")
    agent_op.url = url
    agent_op.mode = "agent"


class RESTIVAL_PT_main(bpy.types.Panel):
    bl_label = "Restival"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Restival"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        prefs = context.preferences.addons[__package__].preferences
        is_running: bool = getattr(context.scene, "restival_running", False)
        port: int = prefs.port
        network_mode: bool = prefs.network_mode

        # --- Status row ---
        status_row = layout.row()
        if is_running:
            status_row.label(text="RUNNING", icon="CHECKBOX_HLT")
        else:
            status_row.label(text="STOPPED", icon="CHECKBOX_DEHLT")

        # --- Active URL(s) when running ---
        if is_running:
            local_ips = get_local_ips()

            if network_mode:
                # Show all local IPs as active URLs
                for ip in local_ips:
                    url = _rest_api_url(ip, port)
                    _draw_copy_row(layout, f"{ip}:{port}/api/v1", url, icon="WORLD")
            else:
                url = _rest_api_url("127.0.0.1", port)
                _draw_copy_row(layout, f"127.0.0.1:{port}/api/v1", url, icon="WORLD")

        # --- Port field (read-only when running) ---
        port_row = layout.row()
        port_row.enabled = not is_running
        port_row.prop(prefs, "port")

        # --- Network mode toggle (disabled when running) ---
        net_row = layout.row()
        net_row.enabled = not is_running
        net_row.prop(prefs, "network_mode")

        # --- Local IPs listing ---
        if not is_running:
            box = layout.box()
            box.label(text="Local IPs:", icon="NETWORK_DRIVE")
            for ip in get_local_ips():
                _draw_copy_row(box, ip, _rest_api_url(ip, port))

        # --- Start / Stop button ---
        layout.separator()
        if is_running:
            layout.operator("restival.stop_server", text="Stop Server", icon="PAUSE")
        else:
            layout.operator("restival.start_server", text="Start Server", icon="PLAY")
