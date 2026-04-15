"""operators.py — Restival start/stop server operators.

Registered automatically by auto_load.py.
Module-level singleton _server_backend holds the running backend so the
stop operator can reach it without importing server state from panels.py.

Scene property `restival_running` (BoolProperty) is registered/unregistered
here so panels.py can read run state without importing this module directly.
"""
import bpy

# Module-level singleton — set on start, cleared on stop
_server_backend = None
_execution_strategy = None


class RESTIVAL_OT_copy_rest_url(bpy.types.Operator):
    bl_idname = "restival.copy_rest_url"
    bl_label = "Copy REST URL"
    bl_description = "Copy the REST API base URL to the clipboard"

    url: bpy.props.StringProperty(options={"SKIP_SAVE"})
    mode: bpy.props.StringProperty(default="url", options={"SKIP_SAVE"})

    def execute(self, context: bpy.types.Context):
        if self.mode == "agent":
            text = (
                f"You have access to a live Blender REST API (Restival).\n"
                f"Base URL: {self.url}\n\n"
                f"Start by fetching the guide:\n"
                f"  curl -s {self.url}\n"
                f"This returns a full JSON guide — all available endpoints, parameters, "
                f"and examples. Ingest it before making any other calls.\n\n"
                f"Rules:\n"
                f"- All responses follow the envelope: {{\"data\": ..., \"meta\": ..., \"error\": ...}}\n"
                f"- Use HTTP GET only (read-only API)\n"
                f"- Scene-scoped routes: {self.url}/scenes/{{scene}}/objects/{{name}}\n"
                f"- Mesh data: append /mesh, /mesh/verts, /mesh/edges, /mesh/faces, /mesh/uvs\n"
                f"- Generic traversal: {self.url}/data/{{path}} (mirrors bpy.data)\n"
                f"- Discovery: {self.url}/objects lists all objects; {self.url}/scenes lists all scenes"
            )
            self.report({"INFO"}, f"Copied agent prompt for {self.url}")
        else:
            text = f"curl -s {self.url}"
            self.report({"INFO"}, f"Copied curl command for {self.url}")
        context.window_manager.clipboard = text
        return {"FINISHED"}


class RESTIVAL_OT_start_server(bpy.types.Operator):
    bl_idname = "restival.start_server"
    bl_label = "Start REST Server"
    bl_description = "Start the Restival HTTP REST API server"

    def execute(self, context: bpy.types.Context):
        global _server_backend, _execution_strategy

        prefs = context.preferences.addons[__package__].preferences
        port: int = prefs.port
        host: str = "0.0.0.0" if prefs.network_mode else "127.0.0.1"

        from server.router import RegexRouter
        from server.response import HTTPResponseWriter
        from server.http_server import StdlibHTTPBackend
        from execution.timer_strategy import TimerExecutionStrategy
        from api.guide import handle_guide
        from api.health import handle_health
        from api.file_meta import handle_file
        from api.scene import handle_scenes_list, handle_scene_detail
        from api.objects import (
            handle_scene_objects_list,
            handle_scene_object_detail,
            handle_objects_list,
            handle_object_detail,
        )
        from api.mesh import (
            handle_mesh_full,
            handle_mesh_verts,
            handle_mesh_edges,
            handle_mesh_faces,
            handle_mesh_uvs,
        )
        from api.traverse import handle_data_root, handle_traverse
        from api.bpy_search import handle_bpy_search, handle_bpy_search_detail

        router = RegexRouter()
        response_writer = HTTPResponseWriter()
        execution_strategy = TimerExecutionStrategy()

        # Guide
        router.register(r"^/api/v1/?$", handle_guide)

        # Utility
        router.register(r"^/api/v1/health$", handle_health)
        router.register(r"^/api/v1/file$", handle_file)

        # Scenes
        router.register(r"^/api/v1/scenes$", handle_scenes_list)
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)$",
            handle_scene_detail,
        )

        # Scene-scoped objects — mesh sub-routes before object detail (first-match)
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)/objects$",
            handle_scene_objects_list,
        )
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)/objects/(?P<name>[^/]+)/mesh/verts$",
            handle_mesh_verts,
        )
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)/objects/(?P<name>[^/]+)/mesh/edges$",
            handle_mesh_edges,
        )
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)/objects/(?P<name>[^/]+)/mesh/faces$",
            handle_mesh_faces,
        )
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)/objects/(?P<name>[^/]+)/mesh/uvs$",
            handle_mesh_uvs,
        )
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)/objects/(?P<name>[^/]+)/mesh$",
            handle_mesh_full,
        )
        router.register(
            r"^/api/v1/scenes/(?P<scene>[^/]+)/objects/(?P<name>[^/]+)$",
            handle_scene_object_detail,
        )

        # Global objects — bpy.data, scene-independent
        router.register(r"^/api/v1/objects$", handle_objects_list)
        router.register(
            r"^/api/v1/objects/(?P<name>[^/]+)$",
            handle_object_detail,
        )

        # Generic bpy.data traversal
        router.register(r"^/api/v1/data/?$", handle_data_root)
        router.register(
            r"^/api/v1/data/(?P<path>.+)$",
            handle_traverse,
        )

        # bpy API search (fake-bpy-module stubs)
        router.register(
            r"^/api/v1/search/(?P<term>[^/]+)/(?P<id>.+)$",
            handle_bpy_search_detail,
        )
        router.register(
            r"^/api/v1/search/(?P<term>[^/]+)$",
            handle_bpy_search,
        )

        backend = StdlibHTTPBackend(router, execution_strategy)

        try:
            execution_strategy.register()
            backend.start(host, port)
        except OSError:
            execution_strategy.unregister()
            self.report(
                {"ERROR"},
                f"Port {port} is already in use — change port in addon preferences",
            )
            return {"CANCELLED"}

        _server_backend = backend
        _execution_strategy = execution_strategy
        context.scene.restival_running = True
        return {"FINISHED"}


class RESTIVAL_OT_stop_server(bpy.types.Operator):
    bl_idname = "restival.stop_server"
    bl_label = "Stop REST Server"
    bl_description = "Stop the Restival HTTP REST API server"

    def execute(self, context: bpy.types.Context):
        global _server_backend, _execution_strategy

        if _server_backend is not None:
            _server_backend.stop()
            _server_backend = None

        if _execution_strategy is not None:
            _execution_strategy.unregister()
            _execution_strategy = None

        context.scene.restival_running = False
        return {"FINISHED"}


def register():
    bpy.types.Scene.restival_running = bpy.props.BoolProperty(
        name="Restival Running",
        default=False,
    )


def unregister():
    # Stop any running server before unloading
    global _server_backend, _execution_strategy
    if _server_backend is not None:
        _server_backend.stop()
        _server_backend = None
    if _execution_strategy is not None:
        _execution_strategy.unregister()
        _execution_strategy = None

    if hasattr(bpy.types.Scene, "restival_running"):
        del bpy.types.Scene.restival_running
