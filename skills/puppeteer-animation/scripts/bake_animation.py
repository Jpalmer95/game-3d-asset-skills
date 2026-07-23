#!/usr/bin/env python3
"""
bake_animation.py — Bake Puppeteer raw motion tensors (local_quats.pt,
root_pos.pt) onto the original rigged GLB's armature and export an
animated GLB usable in Godot/Unity/Blender.

Run inside Blender:

  blender -b --factory-startup -noaudio --python bake_animation.py -- \
      rigged.glb --results-dir out/results/SEQ/SEQ_anim/raw/ \
      --fps 10 -o animated.glb

Joint order: the Puppeteer tensor axis J follows the `joints` line order of
rig.txt. Pass --rig-txt pointing at the rig.txt produced by glb_to_rignet.py
so bone names line up (names are sanitized the same way).
"""
import argparse
import os
import re
import sys

import bpy
import torch
from mathutils import Matrix, Quaternion, Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("glb", help="Original rigged GLB")
    p.add_argument("--results-dir", required=True,
                   help="Dir containing local_quats.pt / root_pos.pt")
    p.add_argument("--rig-txt", required=True,
                   help="rig.txt used for the Puppeteer run (joint order)")
    p.add_argument("--fps", type=int, default=10)
    p.add_argument("-o", "--out", required=True)
    return p.parse_args(argv)


def clean(name):
    return re.sub(r"\W+", "_", name)


def main():
    args = parse_args()

    # Joint order from rig.txt
    joint_order = []
    root_name = None
    with open(args.rig_txt) as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "joints":
                joint_order.append(parts[1])
            elif parts[0] == "root":
                root_name = parts[1]

    local_quats = torch.load(os.path.join(args.results_dir, "local_quats.pt"),
                             map_location="cpu")  # [T, J, 4] (wxyz)
    root_pos = torch.load(os.path.join(args.results_dir, "root_pos.pt"),
                          map_location="cpu")  # [T, 3]
    T, J, _ = local_quats.shape
    assert J == len(joint_order), f"tensor has {J} joints, rig.txt has {len(joint_order)}"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=args.glb)
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")

    scene = bpy.context.scene
    scene.render.fps = args.fps
    scene.frame_start = 0
    scene.frame_end = T - 1

    if not arm.animation_data:
        arm.animation_data_create()
    action = bpy.data.actions.new("PuppeteerAnim")
    arm.animation_data.action = action

    # Bone lookup by sanitized name
    pose_bones = {clean(b.name): b for b in arm.pose.bones}

    for t in range(T):
        scene.frame_set(t)
        for j, jname in enumerate(joint_order):
            pb = pose_bones.get(jname)
            if pb is None:
                continue
            w, x, y, z = local_quats[t, j].tolist()
            q = Quaternion((w, x, y, z))
            # Puppeteer local quats are relative to rest orientation in the
            # parent frame. Blender pose bones: rotation_quaternion is in the
            # bone's local (rest) space — same convention.
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=t)
            if jname == root_name:
                pb.location = Vector(root_pos[t].tolist())
                pb.keyframe_insert("location", frame=t)

    bpy.ops.export_scene.gltf(filepath=args.out, export_format="GLB",
                              export_animation_mode="ACTIONS",
                              export_anim_single_armature=True)
    print(f"OK wrote animated GLB: {args.out} ({T} frames @ {args.fps}fps)")


main()
