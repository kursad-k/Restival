# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
from pathlib import Path

# Add the addon directory to sys.path so that subpackage imports like
# `from core.errors import ...` resolve correctly regardless of how Blender
# namespaces the extension (e.g. bl_ext.vscode_development.Addon_Blender_Restival).
_addon_dir = str(Path(__file__).resolve().parent)
if _addon_dir not in sys.path:
    sys.path.insert(0, _addon_dir)


def _purge_addon_modules() -> None:
    """Remove all addon submodule entries from sys.modules.

    Called before auto_load.init() so that a Blender addon reload (F8 or
    disable/enable) picks up the current source files rather than returning
    stale cached modules.
    """
    to_remove = [
        name for name, mod in sys.modules.items()
        if hasattr(mod, "__file__")
        and mod.__file__ is not None
        and mod.__file__.startswith(_addon_dir)
        and name != __name__
    ]
    for name in to_remove:
        del sys.modules[name]

bl_info = {
    "name": "Restival",
    "author": "Kursad Karatas",
    "description": "Embedded REST API server for querying Blender scene data",
    "blender": (4, 2, 0),
    "version": (0, 1, 0),
    "location": "View3D > Sidebar > Restival",
    "warning": "",
    "category": "System",
}

try:
    from . import auto_load
    _AUTO_LOAD_AVAILABLE = True
except Exception:  # outside Blender (unit tests)
    _AUTO_LOAD_AVAILABLE = False


def register():
    if _AUTO_LOAD_AVAILABLE:
        _purge_addon_modules()
        auto_load.init()
        auto_load.register()


def unregister():
    if _AUTO_LOAD_AVAILABLE:
        auto_load.unregister()
