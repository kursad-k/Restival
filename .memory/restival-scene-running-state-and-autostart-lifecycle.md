# Restival Scene Running State and Autostart Lifecycle Investigation

Date: 2026-06-29

## Summary

Restival had a lifecycle/state mismatch around Blender startup, file load, and file revert. The UI could show that Restival was running even when the REST server was not actually accepting usable requests, or when the HTTP listener existed but the Blender main-thread dispatcher was not draining queued work.

The agreed behavior is:

- `scene.restival_running=True` is the saved desired state for the scene.
- If the property says Restival should be running, the add-on should try to make it actually run.
- If the server cannot start, the UI state must not remain stuck on running. The add-on should clear `scene.restival_running=False` and expose/report an error.
- If the server is running but the Blender dispatcher timer is missing, the add-on should repair or restart the dispatcher instead of claiming healthy state.

## Initial Symptoms

- After starting Blender, loading a new file, or reverting a file, Restival could show as running in the UI.
- External connections to `http://127.0.0.1:2357/api/v1` were sometimes refused.
- In one observed state, the TCP listener accepted requests, but all endpoints returned Restival timeout envelopes:
  - `GET /api/v1`
  - `GET /api/v1/health`
  - `GET /api/v1/scenes`
- That timeout state showed that the HTTP layer could receive traffic, but the queued Blender main-thread work was not being executed.

## Important Live Observations

The live API guide was fetched first as required:

```text
curl -s http://127.0.0.1:2357/api/v1
```

The guide confirmed the standard envelope shape:

```json
{"data": ..., "meta": ..., "error": ...}
```

At one point before the fix, live health had worked and reported:

```text
status=ok
blender_version=5.2.0 LTS Beta
active_scene=CONSTRUCTOR
script_execution_allowed=true
```

After a later Blender start/load, all tested endpoints returned:

```json
{"data": null, "meta": {}, "error": {"code": "TIMEOUT", "message": "Request timed out"}}
```

That was strong evidence that `_server_backend` was listening, but `TimerExecutionStrategy` was not draining the queue through `bpy.app.timers`.

After the lifecycle fix and reloading/restarting Blender, the live checks succeeded:

```text
GET /api/v1        -> guide returned successfully
GET /api/v1/health -> status=ok, Blender 5.2.0 LTS Beta, active_scene=MATERIAL, script_execution_allowed=true
GET /api/v1/scenes -> scenes MATERIAL and Scene returned
```

The live text endpoint test also passed:

```text
python -m pytest test_text_api.py
1 passed
```

## Root Cause

There were two related problems.

### 1. UI State Was Scene Data

`operators.py` registered:

```python
bpy.types.Scene.restival_running = bpy.props.BoolProperty(...)
```

The panel used:

```python
getattr(context.scene, "restival_running", False)
```

as if it were runtime truth.

That is dangerous because scene properties live in `.blend` data. If a scene had been saved with `restival_running=True`, reopening that file could make the panel show running even before any backend existed.

Initially the property had `options={"SKIP_SAVE"}`, but the desired product behavior was clarified: scene state should be saved and should mean "Restival should be running for this scene." Therefore the right model is not to avoid saving it, but to honor it operationally.

### 2. Dispatcher Timer Could Be Lost Across File Loads

The HTTP server dispatches Blender work through `TimerExecutionStrategy`, which uses `bpy.app.timers`.

Original code registered the drain loop without persistence:

```python
bpy.app.timers.register(_drain_loop, first_interval=0.0)
```

Blender file loads/reverts can remove non-persistent timers and handlers. That can leave the HTTP server accepting requests while the main-thread queue is never drained, producing `TIMEOUT` responses.

Official Blender API docs relevant to this:

- `bpy.app.handlers.persistent` keeps handlers from being removed when loading new files.
- `bpy.app.timers.register(..., persistent=True)` keeps timers persistent across file loads.

References:

- https://docs.blender.org/api/current/bpy.app.handlers.html
- https://docs.blender.org/api/current/bpy.app.timers.html

## Implemented Solution

The solution keeps `scene.restival_running` as saved desired state and adds runtime validation/repair around it.

### `execution/timer_strategy.py`

`TimerExecutionStrategy.register()` is now idempotent and persistent:

```python
if self.is_registered:
    return

bpy.app.timers.register(_drain_loop, first_interval=0.0, persistent=True)
```

New property:

```python
@property
def is_registered(self) -> bool:
    return bool(
        self._drain_fn is not None
        and bpy.app.timers.is_registered(self._drain_fn)
    )
```

Purpose:

- Prevent duplicate timer registration.
- Allow operators/UI logic to tell whether the HTTP server can actually dispatch Blender work.
- Keep the queue drain loop alive across file loads where possible.

### `operators.py`

New lifecycle helpers:

```python
def is_server_running() -> bool
def is_execution_ready() -> bool
def get_last_error() -> str
def _set_last_error(message: str = "") -> None
def _set_scene_running_desired(context, desired: bool) -> None
def _stop_server_backend() -> None
```

Behavior:

- `is_server_running()` checks the actual module-level backend, not the scene property.
- `is_execution_ready()` checks whether the timer dispatcher is registered.
- `_last_error` stores lifecycle/startup failure text for panel display.
- `_set_scene_running_desired()` writes the active scene's saved desired state.
- `_stop_server_backend()` centralizes stopping the backend and unregistering the dispatcher.

`RESTIVAL_OT_start_server.execute()` now:

- Repairs dispatcher registration if the backend exists but timer registration is missing.
- Sets `scene.restival_running=True` only after start or repair succeeds.
- On `OSError` such as port already in use:
  - unregisters the execution strategy,
  - stores an error,
  - clears `scene.restival_running=False`,
  - reports the error,
  - returns `CANCELLED`.
- On any other startup exception:
  - unregisters the execution strategy,
  - stores an error,
  - clears `scene.restival_running=False`,
  - reports the error,
  - returns `CANCELLED`.

`RESTIVAL_OT_stop_server.execute()` now:

- Stops the backend through `_stop_server_backend()`.
- Clears lifecycle error.
- Sets `scene.restival_running=False`.

Autostart behavior now considers both:

- Add-on preference `auto_start_server`.
- Saved scene state `scene.restival_running`.

If either says Restival should start, `_auto_start_server_after_init()` calls:

```python
bpy.ops.restival.start_server()
```

If that auto-start call raises, it:

- stores the error,
- clears `scene.restival_running=False`,
- prints the error.

Persistent load handlers were added:

```python
@persistent
def _restival_load_pre(_filepath):
    _stop_server_backend()

@persistent
def _restival_load_post(_filepath):
    _set_last_error("")
    bpy.app.timers.register(
        _auto_start_server_after_init,
        first_interval=_AUTO_START_RETRY_INTERVAL,
        persistent=True,
    )
```

Purpose:

- `load_pre`: stop the old file's backend before Blender replaces the scene data.
- `load_post`: after the new file is loaded, schedule autostart so the newly loaded active scene can be inspected for saved `restival_running=True`.

`register()` now:

- Registers `Scene.restival_running` without `SKIP_SAVE`, intentionally allowing the desired state to persist in the `.blend`.
- Registers `_auto_start_server_after_init` with `persistent=True`.
- Appends `_restival_load_pre` and `_restival_load_post` to Blender handlers.

`unregister()` now:

- Stops backend and execution strategy.
- Unregisters the auto-start timer.
- Removes the load handlers.
- Deletes the scene property.

There is also a fallback for importing outside full Blender:

```python
try:
    from bpy.app.handlers import persistent
except Exception:
    def persistent(fn):
        return fn
```

This preserves compatibility with minimal test stubs.

### `panels.py`

The panel no longer treats scene state as runtime truth.

It now reads:

```python
is_running = operators.is_server_running()
wants_running = bool(getattr(context.scene, "restival_running", False))
lifecycle_error = operators.get_last_error()
```

Panel states:

- `RUNNING`: actual backend is running.
- `STARTING`: scene wants Restival running but no backend is up yet and no error is recorded.
- `ERROR`: scene wants Restival running and a lifecycle error exists.
- `STOPPED`: scene does not want Restival running and backend is not running.

If a lifecycle error exists, it is shown in a UI box.

## Expected Behavior After Fix

### Opening a Scene Saved With Restival On

1. Blender loads the file.
2. `_restival_load_post` schedules `_auto_start_server_after_init`.
3. `_auto_start_server_after_init` sees `scene.restival_running=True`.
4. It calls `bpy.ops.restival.start_server()`.
5. If start succeeds:
   - backend is running,
   - dispatcher timer is registered,
   - panel shows `RUNNING`.
6. If start fails:
   - error is stored,
   - `scene.restival_running=False`,
   - panel shows `ERROR` or `STOPPED` depending on redraw timing and state.

### Reverting or Loading Another File

1. `_restival_load_pre` stops the existing backend.
2. Blender replaces scene data.
3. `_restival_load_post` schedules auto-start.
4. The new active scene's saved desired state determines whether Restival starts again.

### Server Exists But Dispatcher Timer Is Missing

If `Start Server` is invoked while the backend exists but the timer is not registered, it attempts:

```python
_execution_strategy.register()
```

If repair succeeds, desired scene state is set true and error is cleared.

If repair fails, backend is stopped, scene desired state is cleared, and the panel can show the failure.

## Verification Performed

Syntax check:

```text
python -m py_compile operators.py panels.py execution\timer_strategy.py
```

Result:

```text
passed
```

Live API checks after Blender reloaded/picked up code:

```text
curl -s http://127.0.0.1:2357/api/v1
curl -s http://127.0.0.1:2357/api/v1/health
curl -s http://127.0.0.1:2357/api/v1/scenes
```

Results:

- Guide returned successfully.
- Health returned `status=ok`.
- Blender version was `5.2.0 LTS Beta`.
- Active scene was `MATERIAL`.
- `script_execution_allowed=true`.
- Scene list returned `MATERIAL` and `Scene`.

Live integration test:

```text
python -m pytest test_text_api.py
```

Result:

```text
1 passed
```

Before Blender had picked up the code or when no server was accepting connections, this same test failed with `ConnectionRefusedError`, which is expected for a live integration test when Restival is not running.

## Worktree Notes

At the time this note was written, source changes relevant to the fix were in:

- `operators.py`
- `panels.py`
- `execution/timer_strategy.py`

There was an unrelated existing `.gitignore` modification in the worktree. It was not part of this issue.

Running `py_compile` created or updated generated `__pycache__` output, including:

- `execution/__pycache__/timer_strategy.cpython-313.pyc`

That generated file is not part of the intended source fix.

## Remaining Caveats and Follow-Up Ideas

1. Panel status currently uses module-level backend state, which is correct for actual running status. The saved scene property is only desired state. Keep this distinction.

2. `_last_error` is module-level, not scene-specific. If multi-scene error reporting becomes important, this could move to a non-saved add-on/window-manager runtime property or a per-scene diagnostic string.

3. The HTTP backend's `is_running` only checks whether `_server` is non-`None`; it does not actively probe socket health. If future symptoms show stale backend objects, consider adding a stronger backend health method.

4. The live test `test_text_api.py` requires an already-running Blender Restival server. It is not a pure unit test and will fail if no server is listening on port `2357`.

5. For complete regression coverage, add unit tests using the fake `bpy` stubs for:
   - saved `scene.restival_running=True` triggers auto-start timer path,
   - `OSError` during start clears scene desired state,
   - missing dispatcher timer is repaired when start is called on an existing backend,
   - load handlers are registered and removed.

