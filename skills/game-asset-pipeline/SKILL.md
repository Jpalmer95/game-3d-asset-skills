---
name: game-asset-pipeline
description: "Use when the user wants game-ready 3D characters/props from text descriptions or concept art in one go — orchestrates the full chain: concept prompts -> image generation -> alpha masking -> TRELLIS.2 image-to-3D -> SkinTokens auto-rigging -> engine-ready rigged GLBs, with quality gates, resume, and engine presets (Godot/Unity/Blender). Invoke for requests like 'make me 10 enemy characters for my game'."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [3d, game-dev, pipeline, orchestrator, trellis, skintokens, glb, rigging]
    related_skills: [trellis-image-to-3d, skintokens-rigging, puppeteer-animation, comfyui, segment-anything-model, blender-mcp, hermes-3d-mcp]
---

# Game Asset Pipeline — Concept to Rigged Characters

## Overview

Orchestrates the phase skills into a single end-to-end run. The agent drives the phases; each phase is independently usable via its own skill when the user only needs part of the chain.

```
prompts.txt -> [1 image gen] -> images/
            -> [2 mask]      -> images_masked/
            -> [3 3D gen]    -> assets/glb/ + manifest.csv      (trellis-image-to-3d)
            -> [4 rig]       -> assets/rigged/ + rig_manifest   (skintokens-rigging)
            -> [5 animate]   -> assets/animated/                (puppeteer-animation, optional)
            -> [6 verify]    -> Blender/Godot import checks     (blender-mcp / hermes-3d-mcp)
```

Phase 5 (optional, characters only): video-guided animation via `puppeteer-animation` — render first frame of each rigged GLB, animate with image-to-video (FAL pixverse / local ComfyUI), optimize skeletal motion (~25 min/asset on a 12GB GPU; pass `--decimate 20000` for TRELLIS meshes), bake keyframes to animated GLB. Batch overnight.

## When to Use

- "Make me N characters/enemies/props for my game" from text descriptions
- "Turn this folder of concept art into rigged models"
- Don't use for: single static prop (just call trellis-image-to-3d directly), re-rigging existing GLBs (just skintokens-rigging), 2D-only work

## Phase Execution

1. **Concepts.** Write/confirm `prompts.txt` — one line per asset, consistent anchors: `full body, T-pose front view, centered with margin, dark background, fantasy game asset`. Characters only for rigging; props skip phase 4.
2. **Images.** Prefer local ComfyUI (`comfyui` skill) > HF image Space > `image_generate` tool. Name files `NN_slug.png` so sort order matches prompt lines. GATE: `vision_analyze` each image — subject fully visible, correct limb count/anatomy, plain dark background. Regenerate failures NOW (cheap) rather than after GPU phases. (Lesson: "ant" prompts can produce centipedes without "exactly six legs, three body segments, two antennae".)
3. **Mask.** Use the rembg **Python API**, not its CLI (the CLI eagerly imports server deps — gradio/aiohttp/fastapi — and crashes without them):
   ```python
   from rembg import remove; from pathlib import Path
   for f in Path("images").glob("*.png"):
       (Path("images_masked")/f.name).write_bytes(remove(f.read_bytes()))
   ```
   Or rely on TRELLIS `--preprocess`. Local rembg preferred — inspectable before spending quota.
4. **3D.** `python3 <trellis-skill>/scripts/trellis_gen.py --batch images_masked/ --out-root assets --prompts-file prompts.txt --keep-image --target godot --resume`. Runs sequential (ZeroGPU serializes), applies quality gates per asset (alpha coverage in, GLB geometry+texture out). Always run as a Hermes background task (`terminal(background=true, notify_on_complete=true)`) — expect 3-8 min per asset.
5. **Rig (characters only).** `python3 <rig-skill>/scripts/skintokens_rig.py --batch assets/glb/ -o assets/rigged/ --preserve-texture-scale --resume`. Rig gate verifies joints + JOINTS_0/WEIGHTS_0. **For any asset that fails with "No output files were produced", retry that asset with `--voxel-postprocess` — confirmed to rescue all failures in the 10-ant dogfood batch (translucent/glossy/rocky textures trip the default path).**
6. **Verify.** Import one output into Blender via `blender-mcp` (or headless `blender -b --python-expr`): check bone count, vertex groups match bones, pose 2-3 bones and screenshot. SkinTokens outputs include a stray `Icosphere` joint-viz mesh — hide/delete it before export. Consider renaming bones to readable names (keep vertex groups in sync) for hand animation work.

## Re-entry (edit any stage, rerun only downstream)

Do not re-roll the whole batch because one sentence or one mesh changed.
`scripts/asset_stage.py` in the `game-3d-asset-skills` repo is the ledger.

```
prompt → image → mask → mesh → rig → animation
```

1. `adopt <project dir>` on an existing colony, or `add` a new slug + prompt.
2. When the user edits text: `set-prompt`. When they replace a PNG/GLB: `import --stage image|mask|mesh|rig`, or overwrite the canonical file and `refresh` (hash mismatch marks that stage an external edit and stales everything after it).
3. `plan --slug X` prints only the phase commands still needed. `run <slug> --through rig` executes them and records each stage. A failed rig is retried once with `--voxel-postprocess`.
4. Canonical paths: `images/{slug}.png`, `images_masked/{slug}.png`, `assets/glb/{slug}.glb`, `assets/rigged/{slug}_rigged.glb`.
5. Vision-gate images against a *successful* reference, not against "looks cool". The 10-ant dogfood that rigged is a symmetrical front view, legs spread clear of the body, no spread wings. A 3/4 hero render with open wings fails this gate even if the prompt said "T-pose" — regenerate before TRELLIS.
6. Prompt files: skip `#` comments. `trellis_gen.py` now does; older runs shifted every prompt by the comment-line count.

## Script Flags Reference

Both phase scripts support:
- `--resume` — skip assets whose output already exists (crash-safe reruns)
- `--skip-gates` — disable quality gates
- trellis_gen.py additionally: `--target godot-mobile|godot|unity|blender|film` (sets decimation 30k/80k/80k/300k/500k + texture 1024/2048/2048/2048/4096), `--preprocess`, `--seed N`

Quality gates live in `trellis-image-to-3d/scripts/pipeline_qgates.py`: alpha-mask coverage, GLB parse + vertex count + texture presence, rig joints + skin weights. `gate_failed` rows appear in the manifest instead of burning GPU.

## Deliverables (completion criteria)

- `assets/manifest.csv` — one row per asset: slug, prompt, image path, glb path, seed, status
- `assets/rigged/rig_manifest.csv` — rig status per character
- Every status `ok`; every GLB opens in the target engine
- Verified sample posed in Blender without mesh tearing

## Common Pitfalls

1. **Anatomy drift at image gen.** Vision-gate every image before phase 3; specify limb counts explicitly in prompts for non-humanoid creatures. Gate against a *passing* reference (symmetrical front view, legs clear of the body), not against "looks cool". FLUX.1-schnell's Space has no negative prompt — "no wings" is ignored. When a negation or a limb count will not hold, edit a passing image (img2img, or a pixel/hue edit) instead of re-rolling text-to-image.
2. **Skipping --resume on reruns.** Without it, a crash at asset 8 of 10 restarts from 1.
3. **Rigging props.** Only characters go to phase 5; split prompts.txt or filter assets/glb/ accordingly.
4. **HF_TOKEN not visible to the shell.** Export in the same shell that launches the batch, or `set -a; . ~/.hermes/.env; set +a` first.
5. **Forgetting the Icosphere.** SkinTokens adds joint-viz spheres to the GLB; strip in Blender before shipping to an engine.

## Verification Checklist

- [ ] All images vision-gated (anatomy, framing, background) before GPU phases
- [ ] Batch run used `--resume` and appropriate `--target`
- [ ] manifest.csv + rig_manifest.csv: all rows `ok` (or known/accepted failures)
- [ ] One rigged sample pose-tested in Blender (bones deform mesh smoothly)
- [ ] Icosphere joint-viz removed from shipped assets
