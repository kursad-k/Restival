# Restival

Restival is a Blender addon that exposes your scene as a live REST API. It lets local models, external tools, and AI agents inspect objects, meshes, and scene data over HTTP without touching Blender's UI.

I built it because small models can often understand REST APIs more reliably than complex local MCP setups. In Blender, MCP-based workflows can add friction, create stale connections, and raise security concerns when arbitrary Python execution is involved. Restival keeps things simple. It is one addon, read-only for now, and easy for most models to use.

<p align="center">
  <img src="img/ui.png" alt="Restival UI" width="49%" />
  <img src="img/running.png" alt="Restival Running" width="49%" />
</p>

## Features

- REST API for live Blender scene data (read + limited write)
- Works well with local models, tools, and AI agents
- Inspect scenes, objects, meshes, and file metadata over HTTP
- Create Python scripts in Blender's text editor via POST
- Generic `bpy.data` traversal for deeper inspection
- Simple setup inside Blender with no extra MCP-style wiring
- Built-in UI panel to start and stop the server
- Shows the active API URL and local IPs in the addon UI
- Copy-ready to use curl URL and agent prompt actions from the panel

## Install

Blender 4.2 or newer is required.

1. Download this repo as a ZIP or package it as a Blender addon.
2. In Blender, go to `Edit > Preferences > Add-ons`.
3. Click `Install from Disk` and select the ZIP.
4. Enable `Restival`.

## Use

1. Open Blender.
2. Go to `View3D > Sidebar > Restival`.
3. Set the port if needed. Default is `2357`.
4. Leave Network Mode off for localhost only, or enable it to expose the API on your local network.
5. Click `Start Server`.

Base URL by default:

```text
http://127.0.0.1:2357/api/v1
```

All endpoints are `GET` only.

## Examples

```bash
curl -s http://127.0.0.1:2357/api/v1/health
curl -s http://127.0.0.1:2357/api/v1/scenes
curl -s http://127.0.0.1:2357/api/v1/scenes/Scene/objects
curl -s http://127.0.0.1:2357/api/v1/scenes/Scene/objects/Cube
curl -s http://127.0.0.1:2357/api/v1/scenes/Scene/objects/Cube/mesh
curl -s http://127.0.0.1:2357/api/v1/data/materials

# Create a Python script in Blender's text editor
curl -X POST http://127.0.0.1:2357/api/v1/texts \
  -H "Content-Type: application/json" \
  -d '{"name": "my_script.py", "content": "import bpy\nprint(\"Hello Blender!\")\n"}'
```

If you want the API to describe itself first:

```bash
curl -s http://127.0.0.1:2357/api/v1
```
