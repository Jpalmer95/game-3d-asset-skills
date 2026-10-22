#!/usr/bin/env python3
"""Drop SkinTokens' joint-viz Icosphere and re-export a GLB.

Run with Blender, not with Python:

    blender -b --factory-startup -noaudio --python scripts/strip_icosphere.py -- in.glb out.glb

SkinTokens adds an Icosphere mesh so you can see joints. Engines import it
as geometry. This deletes any mesh whose name contains 'ico' and writes a
new GLB. The input file is not modified.
"""
import sys
from pathlib import Path

import bpy


def _args() -> tuple[str, str]:
    if "--" not in sys.argv:
        raise SystemExit("usage: blender -b --python strip_icosphere.py -- in.glb out.glb")
    rest = sys.argv[sys.argv.index("--") + 1 :]
    if len(rest) != 2:
        raise SystemExit("need exactly two paths: in.glb out.glb")
    return rest[0], rest[1]


def main() -> None:
    src, dest = _args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    removed = []
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and "ico" in obj.name.lower():
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=dest, export_format="GLB")
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    print(f"STRIPPED {removed or 'nothing'}")
    print(f"ARMATURES {[(a.name, len(a.data.bones)) for a in arms]}")
    print(f"MESHES {[(m.name, len(m.data.vertices)) for m in meshes]}")
    print(f"WROTE {dest}")


if __name__ == "__main__":
    main()
