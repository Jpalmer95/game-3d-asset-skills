---
name: puppeteer-animation
description: "Use when animating a rigged 3D mesh (GLB with skeleton + skin weights, e.g. SkinTokens output) with a driving video via Seed3D/Puppeteer video-guided optimization. Works on ANY rigged asset (quadrupeds, creatures, articulated props), not just humanoids. Pairs with skintokens-rigging (produces the rig) and trellis-image-to-3d (produces the mesh). Runs locally on a 12GB GPU with the settings in this skill."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [3d, animation, video-guided, game-dev, puppeteer, optimization, glb, skeleton]
    related_skills: [skintokens-rigging, trellis-image-to-3d, game-asset-pipeline, blender-mcp, hermes-3d-mcp]
---

# Puppeteer Video-Guided Animation (local)

## Overview

`Seed3D/Puppeteer` (NeurIPS 2025 Spotlight, Apache-2.0) takes a rigged mesh + a short driving video and optimizes per-frame skeletal joint rotations (quaternions) + root translation so the skinned mesh's rendered motion matches the video. Unlike text-to-motion models (MotionGPT/MDM — SMPL humanoid only), this works for **any skeleton topology**: quadrupeds, insects, dragons, articulated props.

Pipeline: rigged GLB → convert to RigNet rig.txt + mesh.obj (Blender) → driving video (image-to-video of a rendered first frame, or any clip) → precompute optical flow (dpflow), depth (Video-Depth-Anything), 2D tracks (CoTracker3) → optimization loop → raw motion tensors → bake keyframes onto the GLB armature in Blender → animated GLB for Godot.

## Setup (one time, ~15 min + ~12GB checkpoints)

```bash
cd ~/dev && git clone https://github.com/Seed3D/Puppeteer.git --recursive && cd Puppeteer
uv venv --python 3.10 .venv && source .venv/bin/activate
uv pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu118
uv pip install setuptools wheel "setuptools<81" cython==0.29.36   # BEFORE requirements (tetgen/flash-attn build deps)
uv pip install -r requirements.txt
uv pip install flash-attn==2.6.3 --no-build-isolation
uv pip install torch-scatter -f https://data.pyg.org/whl/torch-2.1.1+cu118.html
uv pip install --no-index --no-cache-dir pytorch3d -f https://dl.fbaipublicfiles.com/pytorch3d/packaging/wheels/py310_cu118_pyt211/download.html
```

Checkpoints (run each module's `download.py`, BUT see pitfalls 4/5):
- `animation/download.py` → CoTracker3 (98M) + Video-Depth-Anything-Large (1.5G)
- `skeleton/download.py` + `skinning/download.py` → only needed if you ALSO want Puppeteer's own rigging (we normally use SkinTokens instead).

**Required patches** (already applied in the user's `~/dev/Puppeteer`; reapply on a fresh clone):
1. `animation/optimization.py` — skip `DepthModule` load when `depth/depth_gt_raw.pt` cache exists (saves 1.5GB VRAM; enables 12GB cards). Companion: `precompute_depth.py` at repo root runs VDA standalone.
2. Frame loader resizes to `--img_size` (upstream assumes extracted frames already match).

## Usage

Full run on a rigged GLB:
```bash
python3 scripts/puppeteer_animate.py goblin_rigged.glb --video goblin_walk.mp4 \
    --puppeteer ~/dev/Puppeteer -o working/goblin/ --iter 500
```

Then bake to an animated GLB:
```bash
blender -b --factory-startup -noaudio --python scripts/bake_animation.py -- \
    goblin_rigged.glb --rig-txt working/goblin/objs/rig.txt \
    --results-dir working/goblin/results/goblin_anim/raw/ \
    --fps 10 -o goblin_animated.glb
```

Getting the driving video (the "AI animation" front-end):
1. Render first frames: `cd ~/dev/Puppeteer/animation && PYTHONPATH=. python utils/render_first_frame.py --input_path <dir-containing-seq> --seq_name <name>` → 4 viewpoint PNGs.
2. Pick the view that shows joints best, animate it with image-to-video (local ComfyUI, or FAL pixverse — cheap, 4-8s clip, e.g. "the ant walks forward, legs stepping"). Save as `input.mp4` in the seq dir.

Useful flags: `--iter 200` = draft (~13 min on 4070 Ti), `--iter 500` = final. `--main-renderer front_left --additional-renderers "right,front_right,back_right"` for 3/4 views. `--smooth-weight 1` for organic creatures.

## Pitfalls (all hit live on a 4070 Ti 12GB)

1. **OOM: optimization at img_size 960 needs >12GB.** Use `--img-size 512` (peak ~8GB) AND precompute depth standalone. If still OOM, check for stale GPU processes (`nvidia-smi`).
2. **Resolution mismatch crashes.** Puppeteer caches flow/track/depth at the resolution of `imgs/*.png` and NEVER resizes them. Extract frames with `scale=W:W` in ffmpeg (the wrapper does this). If you change `--img-size`, delete `imgs flow flow_vis track_2d_joints track_2d_verts depth` in the seq dir and re-run.
3. **`ModuleNotFoundError: No module named 'third_partys'`** — run everything with `PYTHONPATH=.` from `animation/` (wrapper handles it).
4. **hf-xet silently drops large downloads** (transfers vanish). Verify with `ls`; if missing, `HF_HUB_DISABLE_XET=1` and re-run, or `hf_hub_download` directly.
5. **skinning/download.py nests checkpoints** at `skinning/skinning/skinning_ckpts/` — move up one level. (Only matters for Puppeteer's own rigging.)
6. **tetgen/flash-attn build failures** — install `setuptools<81 wheel cython==0.29.36` into the venv BEFORE `requirements.txt`; setuptools 83+ removed pkg_resources which flash-attn's setup.py imports.
7. **Optimization is minutes-per-animation, not seconds** (~5s/iter at 384px on 4070 Ti). Batch overnight; use `terminal(background=true, notify_on_complete=true)`.
8. Garbage video in = garbage motion out. The driving video must keep the whole asset in frame, roughly match the rest pose's camera angle, and show the motion from ONE dominant viewpoint.
9. **TRELLIS meshes (250k+ faces) OOM the optimization loop** — memory scales with VERTEX count (pytorch3d rasterizer + tracking), not img_size. Measured on 12GB: 204k verts OOM at tracking, 68k verts OOM at rasterization, 31k verts runs at ~11.6GB peak. Rule: pass `--decimate 20000` (faces) to glb_to_rignet.py for TRELLIS outputs; ≤10k-face meshes are comfortable at img_size 512.
10. **Never decimate the OBJ externally after rig.txt is written** — skin weights index vertices positionally. Decimate in glb_to_rignet.py (Blender keeps vertex groups) or redo the whole conversion.
11. **video_generate / FAL needs a public URL for local first-frame PNGs.** 0x0.st and tmpfiles are dead/redirect-looping; working path: `python3 -m http.server 8899` + `cloudflared tunnel --url http://127.0.0.1:8899` (free, no account) → pass the trycloudflare URL. Tailscale funnel is disabled on our tailnet.
12. Keep driving videos ≤4s @ 10fps (40 frames). 50 frames pushed CoTracker3 offline over the edge at 512px.

## Verification Checklist

- [ ] `results/<seq>/<name>/raw/{local_quats,root_quats,root_pos}.pt` exist
- [ ] `front_left.mp4` (and additional views) render without OOM
- [ ] Rendered motion visibly tracks the input video (watch side by side)
- [ ] Baked GLB plays in Blender timeline / Godot AnimationPlayer
