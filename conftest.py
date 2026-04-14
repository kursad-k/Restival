"""conftest.py (root) — install bpy stub before any addon module is imported.

Root conftest.py runs before child conftest files and before pytest imports
any test module. Blender's `bpy` module is unavailable outside Blender;
this stub provides just enough surface area for:
  - auto_load.py module-level initialisation (bpy.app.version)
  - Blender class definitions in preferences.py / operators.py / panels.py
  - Lazy bpy imports inside api/ handler functions (overridden per-test)
"""
from __future__ import annotations

import sys
import types


def _make_bpy_stub() -> types.ModuleType:
    bpy = types.ModuleType("bpy")

    # --- bpy.app ---
    bpy.app = types.SimpleNamespace(
        version=(4, 2, 0),
        version_string="4.2.0",
        timers=types.SimpleNamespace(
            register=lambda fn, **kw: None,
            unregister=lambda fn: None,
            is_registered=lambda fn: False,
        ),
        online_access=False,
    )

    # --- bpy.props helpers — return None (class-level descriptors are unused outside Blender) ---
    def _prop(**kwargs):
        return None

    bpy.props = types.SimpleNamespace(
        IntProperty=_prop,
        FloatProperty=_prop,
        BoolProperty=_prop,
        StringProperty=_prop,
        EnumProperty=_prop,
        CollectionProperty=_prop,
        PointerProperty=_prop,
    )

    # --- bpy.types base classes — minimal stubs for subclassing ---
    class _BlenderBase:
        bl_idname: str = ""
        bl_label: str = ""

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

    class Operator(_BlenderBase):
        def report(self, level, message): ...
        def execute(self, context): return {"FINISHED"}

    class Panel(_BlenderBase):
        bl_space_type: str = ""
        bl_region_type: str = ""
        bl_category: str = ""

        def draw(self, context): ...

    class AddonPreferences(_BlenderBase):
        bl_idname: str = ""

        def draw(self, context): ...

    class PropertyGroup(_BlenderBase): ...

    bpy.types = types.SimpleNamespace(
        Operator=Operator,
        Panel=Panel,
        AddonPreferences=AddonPreferences,
        PropertyGroup=PropertyGroup,
        Scene=types.SimpleNamespace(),  # Scene.restival_running assigned by operators.register()
        Context=object,
    )

    # --- bpy.utils — class registration no-ops ---
    bpy.utils = types.SimpleNamespace(
        register_class=lambda cls: None,
        unregister_class=lambda cls: None,
    )

    # --- bpy.context / bpy.data — minimal stubs (overridden per-test) ---
    bpy.context = types.SimpleNamespace(
        scene=types.SimpleNamespace(
            name="Scene",
            frame_start=1,
            frame_end=250,
            frame_current=1,
            render=types.SimpleNamespace(fps=24),
            camera=None,
            objects=[],
            collection=types.SimpleNamespace(name="Scene Collection"),
            unit_settings=types.SimpleNamespace(system="METRIC", scale_length=1.0),
        ),
        preferences=types.SimpleNamespace(
            addons={}
        ),
    )
    bpy.data = types.SimpleNamespace(
        filepath="",
        is_saved=False,
        scenes=[],
    )

    return bpy


if "bpy" not in sys.modules:
    sys.modules["bpy"] = _make_bpy_stub()
