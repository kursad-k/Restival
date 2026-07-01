"""operators.py — Restival start/stop server operators.

Registered automatically by auto_load.py.
Module-level singleton _server_backend holds the running backend so the
stop operator can reach it without importing server state from panels.py.

Scene property `restival_running` (BoolProperty) is registered/unregistered
here so panels.py can read run state without importing this module directly.
"""
import bpy
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

try:
    from bpy.app.handlers import persistent
except Exception:  # outside Blender or with a minimal bpy test stub
    def persistent(fn):
        return fn

# Module-level singleton — set on start, cleared on stop
_server_backend = None
_execution_strategy = None
_AUTO_START_RETRY_INTERVAL = 0.5
_PORT_CONFLICT_INCREMENT_LIMIT = 25
_last_error = ""
_PORT_PROBE_TIMEOUT = 0.25


def is_server_running() -> bool:
    """Return the actual backend state used by the UI."""
    return bool(_server_backend is not None and _server_backend.is_running)


def is_execution_ready() -> bool:
    """Return whether the server can dispatch work onto Blender's main thread."""
    return bool(
        _execution_strategy is not None
        and getattr(_execution_strategy, "is_registered", False)
    )


def get_last_error() -> str:
    """Return the last server lifecycle error for display."""
    return _last_error


def get_diagnostics() -> dict:
    """Return runtime diagnostics for distinguishing loaded addon copies."""
    bound_address = None
    if _server_backend is not None:
        bound_address = getattr(_server_backend, "bound_address", None)

    return {
        "operators_file": str(Path(__file__).resolve()),
        "process_id": os.getpid(),
        "blend_file": bpy.data.filepath,
        "fallback_limit": _PORT_CONFLICT_INCREMENT_LIMIT,
        "server_running": is_server_running(),
        "execution_ready": is_execution_ready(),
        "bound_address": bound_address,
        "last_error": _last_error,
    }


def _port_has_restival(port: int) -> bool:
    """Return whether a local Restival server already answers on *port*."""
    url = f"http://127.0.0.1:{port}/api/v1/health"
    try:
        with urllib.request.urlopen(url, timeout=_PORT_PROBE_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return False

    data = payload.get("data") if isinstance(payload, dict) else None
    return isinstance(data, dict) and data.get("status") == "ok"


def _set_last_error(message: str = "") -> None:
    global _last_error
    _last_error = message


def _set_scene_running_desired(
    context: bpy.types.Context | None,
    desired: bool,
) -> None:
    scene = getattr(context, "scene", None) if context is not None else None
    if scene is None:
        scene = bpy.context.scene

    if scene is not None and hasattr(scene, "restival_running"):
        scene.restival_running = desired


def _stop_server_backend() -> None:
    global _server_backend, _execution_strategy

    if _server_backend is not None:
        _server_backend.stop()
        _server_backend = None

    if _execution_strategy is not None:
        _execution_strategy.unregister()
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
                f"- Use HTTP GET for inspection endpoints\n"
                f"- Use HTTP POST /api/v1/texts to add the Python script that will solve the user's inquiry; "
                f"send the full script content because an existing text block with the same name is completely replaced\n"
                f"- Scene-scoped routes: {self.url}/scenes/{{scene}}/objects/{{name}}\n"
                f"- Mesh data: append /mesh, /mesh/verts, /mesh/edges, /mesh/faces, /mesh/uvs\n"
                f"- Generic traversal: {self.url}/data/{{path}} (mirrors bpy.data)\n"
                f"- Discovery: {self.url}/objects lists all objects; {self.url}/scenes lists all scenes\n\n"
                f"Note: if you are behind a proxy, bypass it for these local calls with "
                f"curl -s --noproxy '*' {self.url}"
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

        if is_server_running():
            if not is_execution_ready() and _execution_strategy is not None:
                try:
                    _execution_strategy.register()
                except Exception as exc:  # noqa: BLE001
                    message = f"Restival server dispatcher failed to start: {exc}"
                    _set_last_error(message)
                    _stop_server_backend()
                    _set_scene_running_desired(context, False)
                    self.report({"ERROR"}, message)
                    return {"CANCELLED"}

            _set_last_error("")
            _set_scene_running_desired(context, True)
            return {"FINISHED"}

        prefs = context.preferences.addons[__package__].preferences
        port: int = prefs.port
        host: str = "0.0.0.0" if prefs.network_mode else "127.0.0.1"

        from server.router import RegexRouter
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
        from api.text_files import handle_texts_list, handle_text_detail, handle_text_create, handle_text_run

        router = RegexRouter()
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

        # Text files
        router.register(r"^/api/v1/texts$", handle_texts_list, "GET")
        router.register(r"^/api/v1/texts$", handle_text_create, "POST")
        router.register(
            r"^/api/v1/texts/(?P<name>[^/]+)$",
            handle_text_detail,
            "GET",
        )
        router.register(
            r"^/api/v1/texts/(?P<name>[^/]+)/run$",
            handle_text_run,
            "POST",
        )

        max_port = min(65535, port + _PORT_CONFLICT_INCREMENT_LIMIT)
        last_bind_error: OSError | None = None
        backend = None

        for candidate_port in range(port, max_port + 1):
            if _port_has_restival(candidate_port):
                continue

            execution_strategy = TimerExecutionStrategy()
            backend = StdlibHTTPBackend(router, execution_strategy)

            try:
                execution_strategy.register()
                backend.start(host, candidate_port)
            except OSError as exc:
                execution_strategy.unregister()
                last_bind_error = exc
                backend = None
                continue
            except Exception as exc:  # noqa: BLE001
                execution_strategy.unregister()
                message = f"Restival server failed to start: {exc}"
                _set_last_error(message)
                _set_scene_running_desired(context, False)
                self.report({"ERROR"}, message)
                return {"CANCELLED"}

            if candidate_port != port:
                prefs.port = candidate_port
                self.report(
                    {"WARNING"},
                    f"Port {port} was unavailable; Restival started on {candidate_port}",
                )
            break
        else:
            message = (
                f"Ports {port}-{max_port} are unavailable — change port in addon preferences"
            )
            if last_bind_error is not None:
                _set_last_error(f"{message}: {last_bind_error}")
            else:
                _set_last_error(message)
            _set_scene_running_desired(context, False)
            self.report({"ERROR"}, message)
            return {"CANCELLED"}

        _server_backend = backend
        _execution_strategy = execution_strategy
        _set_last_error("")
        _set_scene_running_desired(context, True)
        return {"FINISHED"}


class RESTIVAL_OT_stop_server(bpy.types.Operator):
    bl_idname = "restival.stop_server"
    bl_label = "Stop REST Server"
    bl_description = "Stop the Restival HTTP REST API server"

    def execute(self, context: bpy.types.Context):
        _stop_server_backend()
        _set_last_error("")
        _set_scene_running_desired(context, False)
        return {"FINISHED"}


def _auto_start_server_after_init():
    """Start server when preferences or saved scene state request it."""
    if _server_backend is not None and _server_backend.is_running:
        return None

    addon = bpy.context.preferences.addons.get(__package__)
    if addon is None:
        return None

    prefs = addon.preferences
    scene = bpy.context.scene
    if scene is None:
        return _AUTO_START_RETRY_INTERVAL

    scene_wants_running = bool(getattr(scene, "restival_running", False))
    prefs_wants_running = bool(getattr(prefs, "auto_start_server", False))
    if not scene_wants_running and not prefs_wants_running:
        return None

    try:
        bpy.ops.restival.start_server()
    except Exception as exc:
        message = f"Restival auto start failed: {exc}"
        _set_last_error(message)
        _set_scene_running_desired(bpy.context, False)
        print(message)

    return None


@persistent
def _restival_load_pre(_filepath):
    """Stop the old file's backend before Blender replaces scene data."""
    _stop_server_backend()


@persistent
def _restival_load_post(_filepath):
    """Honor saved scene state after a new file is loaded."""
    _set_last_error("")
    if not bpy.app.timers.is_registered(_auto_start_server_after_init):
        bpy.app.timers.register(
            _auto_start_server_after_init,
            first_interval=_AUTO_START_RETRY_INTERVAL,
            persistent=True,
        )


def register():
    bpy.types.Scene.restival_running = bpy.props.BoolProperty(
        name="Restival Running",
        default=False,
    )
    # bpy.data is restricted during register(); default=False already covers this.
    # for scene in bpy.data.scenes:
    #     scene.restival_running = False

    if not bpy.app.timers.is_registered(_auto_start_server_after_init):
        bpy.app.timers.register(
            _auto_start_server_after_init,
            first_interval=_AUTO_START_RETRY_INTERVAL,
            persistent=True,
        )

    if _restival_load_pre not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(_restival_load_pre)
    if _restival_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_restival_load_post)


def unregister():
    # Stop any running server before unloading
    global _server_backend, _execution_strategy
    if _server_backend is not None:
        _server_backend.stop()
        _server_backend = None
    if _execution_strategy is not None:
        _execution_strategy.unregister()
        _execution_strategy = None
    if bpy.app.timers.is_registered(_auto_start_server_after_init):
        bpy.app.timers.unregister(_auto_start_server_after_init)
    if _restival_load_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_restival_load_pre)
    if _restival_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_restival_load_post)

    if hasattr(bpy.types.Scene, "restival_running"):
        del bpy.types.Scene.restival_running
