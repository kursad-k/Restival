# Restival — Blender REST API

Restival embeds a read-only HTTP server inside Blender. It exposes live scene data as JSON over a local REST API. Default port: **2357**.

Start/stop the server from the Restival panel in Blender's Scene Properties or N-panel.

---

## Quick start

```bash
# Is the server alive?
curl -s http://localhost:2357/api/v1/health

# What endpoints exist?
curl -s http://localhost:2357/api/v1
```

---

## Response envelope

Every response — success or error — uses the same three-key envelope:

```json
{
  "data":  { ... },
  "meta":  { "elapsed_ms": 4.2 },
  "error": null
}
```

Paginated collection responses include full pagination info in `meta`:

```json
{
  "data":  [ ... ],
  "meta":  { "page": 1, "page_size": 50, "total": 312, "elapsed_ms": 12 },
  "error": null
}
```

Error response:

```json
{
  "data":  null,
  "meta":  {},
  "error": { "code": "NOT_FOUND", "message": "Object 'Foo' not found in scene 'Scene'" }
}
```

**Error codes:** `NOT_FOUND` (404) · `BAD_REQUEST` (400) · `SERVER_BUSY` (503) · `TIMEOUT` (503) · `INTERNAL_ERROR` (500)

---

## Route families

The API has two distinct access patterns:

| Family | Prefix | Use when |
|--------|--------|----------|
| **Structured** | `/api/v1/scenes`, `/api/v1/objects` | You want curated, friendly field names — scene inventory, object data, mesh geometry |
| **Traversal** | `/api/v1/data/` | You want raw `bpy.data` access — any RNA property, arbitrary depth |

`bpy.data` is Blender's root datablock container. Every object, mesh, material, image, scene, node tree, and camera in the file lives here, addressable by type and name, independent of what is linked into any scene.

---

## Common query parameters

### Pagination (collection endpoints)

| Param | Default | Max | Notes |
|-------|---------|-----|-------|
| `page` | 1 | — | 1-indexed |
| `page_size` | 50 | 200 | Max 10 000 for mesh arrays |

### Filtering (object lists)

| Param | Values |
|-------|--------|
| `type` | `MESH` · `CAMERA` · `LIGHT` · `ARMATURE` · `EMPTY` · any Blender object type |

### Name encoding

Object and scene names with spaces must be URL-encoded: `My Object` → `My%20Object`

---

## Endpoints

### `GET /api/v1`

Self-describing guide. Returns the full endpoint map with curl examples, route families, and compact-key legend. Hit this first if you are an agent discovering the API.

```bash
curl -s http://localhost:2357/api/v1
```

---

### `GET /api/v1/health`

Server liveness. Safe to poll. Runs without touching the scene.

Returns: `status`, `blender_version`, `uptime_seconds`, `is_saved`, `active_scene`

```bash
curl -s http://localhost:2357/api/v1/health
```

---

### `GET /api/v1/file`

Metadata about the open `.blend` file.

Returns: `filepath`, `is_saved`, `blender_version`, `active_scene`, `scenes[]`, `unit_system`, `unit_scale`

```bash
curl -s http://localhost:2357/api/v1/file
```

---

### `GET /api/v1/scenes`

List all scenes in the file.

```bash
curl -s http://localhost:2357/api/v1/scenes
```

---

### `GET /api/v1/scenes/{scene}`

Detail for a named scene.

Returns: `name`, `frame_start`, `frame_end`, `frame_current`, `fps`, `active_camera`, `object_count`, `collection`

```bash
curl -s http://localhost:2357/api/v1/scenes/Scene
```

---

### `GET /api/v1/scenes/{scene}/objects`

Objects linked to a specific scene. Paginated and filterable.

```bash
# All objects in scene
curl -s http://localhost:2357/api/v1/scenes/Scene/objects

# Filter by type
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects?type=MESH"
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects?type=CAMERA"
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects?type=LIGHT"

# Paginate
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects?page=1&page_size=10"
```

---

### `GET /api/v1/scenes/{scene}/objects/{name}`

Full detail for a named object within a scene.

Returns: transforms (location, rotation, scale), materials[], modifiers[], object type, parent

```bash
curl -s http://localhost:2357/api/v1/scenes/Scene/objects/Cube
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects/My%20Object"
```

---

### Mesh endpoints

All mesh data is **evaluated** — modifiers are applied before export. Only valid for `type=MESH` objects.

#### `GET /api/v1/scenes/{scene}/objects/{name}/mesh`

Full mesh in one block: verts, edges, faces, UVs. Each array includes a `schema` field describing the tuple layout.

```bash
curl -s http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh?normals=true"
```

#### `GET /api/v1/scenes/{scene}/objects/{name}/mesh/verts`

Vertex positions as flat tuples. Supports pagination (`page`, `page_size` up to 10 000).

```bash
# [x, y, z] per vertex
curl -s http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh/verts

# [x, y, z, nx, ny, nz] per vertex
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh/verts?normals=true"

# Paginated for large meshes
curl -s "http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh/verts?page=1&page_size=1000"
```

#### `GET /api/v1/scenes/{scene}/objects/{name}/mesh/edges`

Edge pairs `[v0, v1]` — vertex indices (0-based). Supports pagination.

```bash
curl -s http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh/edges
```

#### `GET /api/v1/scenes/{scene}/objects/{name}/mesh/faces`

Face tuples `[loop_start, loop_total, mat_idx, nx, ny, nz, use_smooth]`. Use `loop_start` + `loop_total` to index into the UV array. Supports pagination.

```bash
curl -s http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh/faces
```

#### `GET /api/v1/scenes/{scene}/objects/{name}/mesh/uvs`

UV pairs `[u, v]` indexed by loop index. Empty array if no UV layer. Supports pagination.

```bash
curl -s http://localhost:2357/api/v1/scenes/Scene/objects/Cube/mesh/uvs
```

---

### `GET /api/v1/objects`

All objects in `bpy.data` — scene-independent. Includes orphaned objects not linked to any scene. Paginated and filterable.

Use this when you need all objects regardless of scene membership.

```bash
curl -s http://localhost:2357/api/v1/objects
curl -s "http://localhost:2357/api/v1/objects?type=MESH"
curl -s "http://localhost:2357/api/v1/objects?page=1&page_size=20"
```

---

### `GET /api/v1/objects/{name}`

Full object detail from `bpy.data` by name, scene-independent.

```bash
curl -s http://localhost:2357/api/v1/objects/Cube
```

---

### `GET /api/v1/data/`

Directory of all `bpy.data` collections with item counts and scalar properties. Start here when using the traversal family to discover what is available.

```bash
curl -s http://localhost:2357/api/v1/data/
```

---

### `GET /api/v1/data/{path}`

Generic `bpy.data` traversal using raw Blender RNA property names. Each path segment resolves as:
1. Attribute access (`getattr`)
2. Collection lookup by name (`collection['key']`)
3. Collection lookup by index (`collection[0]`)

Max 10 segments. Use Blender's actual RNA names — `polygons` not `faces`, `vertices` not `verts`.

**Collections** return `{ tot, items[] }` with `{ i, t, n }` per item.  
**Structs** return their scalar properties.  
**Arrays** over 500 elements return a truncation stub `{ t, len, trunc: true }`.  
**Binary/bytes** properties return a size stub only.

```bash
# List all scenes
curl -s http://localhost:2357/api/v1/data/scenes

# Scalar property of a named scene
curl -s http://localhost:2357/api/v1/data/scenes/Scene/name

# All objects in bpy.data
curl -s http://localhost:2357/api/v1/data/objects

# Location of a named object
curl -s http://localhost:2357/api/v1/data/objects/Cube/location

# Vertex collection of a mesh datablock
curl -s http://localhost:2357/api/v1/data/objects/Cube/data/vertices

# Single vertex by index
curl -s http://localhost:2357/api/v1/data/objects/Cube/data/vertices/0

# Polygon (face) collection
curl -s http://localhost:2357/api/v1/data/objects/Cube/data/polygons

# Single polygon by index
curl -s http://localhost:2357/api/v1/data/objects/Cube/data/polygons/0

# Materials on a mesh datablock
curl -s http://localhost:2357/api/v1/data/meshes/Cube/materials

# Image dimensions
curl -s http://localhost:2357/api/v1/data/images/MyTexture/size

# Material node tree
curl -s http://localhost:2357/api/v1/data/materials/Material/node_tree/nodes
```

---

## Compact key legend (`/data/` responses)

| Key | Meaning |
|-----|---------|
| `t` | type name (RNA type or stub type) |
| `i` | index within a collection |
| `n` | name string |
| `tot` | total count of a collection |
| `trunc` | `true` when a collection or array was truncated |
| `len` | length of a truncated array |

---

## Notes

- All endpoints are **GET only**.
- All indices are **0-based**.
- Object and scene names with spaces must be **URL-encoded** (`%20`).
- The server binds to `127.0.0.1` by default. Enable network mode in preferences to bind to all interfaces.
- Per-request timeout: **5 seconds**. A `503 SERVER_BUSY` response means Blender's main thread is occupied — retry after the `Retry-After` header value.
- Drop `| python -m json.tool` from any curl command if you want raw output.
