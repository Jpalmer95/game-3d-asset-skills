# 3D Pipeline Guide — Image → 3D → Rigged Game Assets

A practical guide for the Hermes skills `trellis-image-to-3d` and `skintokens-rigging`,
driven by the scripts in this folder. Everything runs on your Hugging Face ZeroGPU quota
(no local GPU needed), or optionally on local ComfyUI for the image step.

---

## 0. Setup (once)

```bash
# 1. Token — get a READ token at https://huggingface.co/settings/tokens
export HF_TOKEN=hf_********************************
#    (or add HF_TOKEN=... to ~/dev/<project>/.env or ~/.hermes/.env — never commit it)

# 2. Python deps
pip install "gradio_client>=1.0"        # required
pip install rembg                       # optional, local background removal

# 3. Skill script locations
TRELLIS=~/.hermes/skills/gaming/trellis-image-to-3d/scripts/trellis_gen.py
RIG=~/.hermes/skills/gaming/skintokens-rigging/scripts/skintokens_rig.py
```

Folder layout (this scaffold):

```
3D Pipeline/
  prompts/         one-prompt-per-line txt files
  images/          raw generated/edited source images (NN_slug.png)
  images_masked/   alpha-masked RGBA versions
  assets/glb/      static TRELLIS.2 meshes + manifest.csv (via --out-root assets)
  assets/rigged/   rigged GLBs + rig_manifest.csv
  working/         scratch: LoRA outputs, editor exports, iterations
```

---

## 1. Prompt style guide

Consistency matters more than cleverness. Every character prompt should carry these anchors:

**Core anchors (keep on every prompt):**
`full body, T-pose front view, centered with margin, dark background, fantasy game asset`

Why: TRELLIS reconstructs exactly what it sees — cropped feet become cropped meshes, and
limbs glued to the torso give SkinTokens nothing to articulate.

**Prompt patterns by goal:**

| Goal | Pattern | Example |
|---|---|---|
| Single hero character | `[creature/class], [signature material/detail], [silhouette], anchors` | `dwarf viking warrior, horned steel helm, lit lantern in right hand, braided red beard, full body T-pose front view, centered, dark background` |
| Elemental variant set (same type) | keep sentence structure identical, swap element words | see `prompts/ant_elementals.txt` — same skeleton sentence, only carapace/element/size words change |
| Mixed asset types (props + characters) | props: `single object, three-quarter view, centered` / characters: T-pose anchors | `wooden treasure chest, iron bands, slightly open lid, single object, centered, dark background` |
| Size variants | put size word FIRST — it strongly shapes proportions | `tiny sprite ant ...` vs `giant ant queen boss ...` |

**Things that break generation:**
- busy or scenic backgrounds (they become geometry) — always say `dark background` and mask anyway
- action poses, weapon-across-body poses (rigging fails later)
- multiple characters in one image (TRELLIS fuses them)

---

## 2. Recipes by scope

### Recipe A — One asset, full chain (image → 3D → rigged)

```bash
cd "/home/jonathan/Desktop/3D Pipeline"

# generate or drop your image into images/01_dwarf.png, then:
python3 $TRELLIS images/01_dwarf.png -o assets/glb/01_dwarf.glb --preprocess
python3 $RIG assets/glb/01_dwarf.glb -o assets/rigged/01_dwarf_rigged.glb --preserve-texture-scale
```

### Recipe B — Images only (stop at 2D, e.g. for concept review)

Just generate/save into `images/` and stop. Nothing to run. Optionally mask for review:

```bash
for f in images/*.png; do rembg i "$f" "images_masked/$(basename "$f")"; done
```

### Recipe C — Images → static 3D only (skip rigging, e.g. props batch)

```bash
python3 $TRELLIS --batch images_masked/ --out-root assets --keep-image
# -> assets/glb/*.glb + assets/manifest.csv
```

### Recipe D — Full batch: 10 elemental ants (the flagship run)

```bash
# 1. generate the 10 images from prompts/ant_elementals.txt into images/
#    (ComfyUI local, HF image Space, or Hermes image_generate — one per line,
#     name them 01_fire_ant.png ... 10_lava_ant.png so sort order matches prompts)

# 2. mask locally (more control than server-side --preprocess)
for f in images/*.png; do rembg i "$f" "images_masked/$(basename "$f")"; done
#    eyeball images_masked/ — bad mask = melted 3D. Fix/redo before spending GPU.

# 3. batch to 3D (several min per asset — run as a Hermes background task)
python3 $TRELLIS --batch images_masked/ --out-root assets \
    --prompts-file prompts/ant_elementals.txt --keep-image

# 4. batch rig (sequential; ~min per asset)
python3 $RIG --batch assets/glb/ -o assets/rigged/ --preserve-texture-scale

# 5. verify: open assets/rigged/01_*_rigged.glb in Blender/Godot,
#    check manifest.csv + rig_manifest.csv both show 10 ok rows
```

### Recipe E — Same-type multiples with variations

Run Recipe D twice with different seeds (`--seed 42` / `--seed 1337`) into separate
out-roots, or duplicate prompt lines with small material swaps (`obsidian` vs `granite`)
to get visually distinct squads that still read as one family.

---

## 3. Preprocessing toolbox (getting the input image right)

Goal: one clean, isolated subject on transparency before TRELLIS ever sees it.

| Task | Free/open tool | How |
|---|---|---|
| Background removal (auto) | `rembg` (u2net, local) | `rembg i in.png out.png` |
| Background removal (manual touch-up) | **GIMP** (free) | Fuzzy-select bg → delete → clean edges with eraser/mask; export PNG with alpha |
| Precise segmentation | **Segment Anything (SAM)** — see Hermes skill `segment-anything-model` | point/box prompts → export exact mask; best for fiddly silhouettes (lanterns, antennae) |
| Edit one part of a character | **Stable Diffusion inpainting** (local ComfyUI or HF Space) | mask the region → inpaint with a new prompt ("replace axe with hammer") |
| Style consistency across a set | **LoRA** in ComfyUI | train/apply a style LoRA so all 10 ants share an art direction; see `comfyui` / `forgedna-comfyui-assets` skills |
| Upscale/cleanup before 3D | Real-ESRGAN via ComfyUI | sharper textures in = sharper textures out |
| Crop/framing fix | GIMP / Krita | subject should fill ~80% of frame, full silhouette visible, margin on all sides |

**Krita** (free) is the better pick when you'll paint edits by hand; **GIMP** for
selection/mask surgery. Both export alpha PNGs fine.

Rule of thumb: fix it in 2D, not in 3D. A 2-minute inpaint beats 20 minutes of mesh surgery.

---

## 4. Postprocessing (Blender & beyond)

After `assets/rigged/` is populated:

1. **Import** — Blender: File → Import → glTF 2.0. Godot 4: drag the .glb into the project.
2. **Sanity checks** — armature bones inside the mesh; rotate spine/limb bones in Pose Mode;
   texture present (TRELLIS bakes into vertex/UV texture, preserved with `--preserve-texture-scale`).
3. **Common fixes**
   - thin appendage weights (antennae, fingers): manual weight paint pass, or re-run rig with `--voxel-postprocess`
   - scale: TRELLIS output is roughly meters; apply Ctrl+A scale before animating
   - decimation: if 300k faces is too heavy for your game, re-run extract with `--decimation 50000` (same seed keeps geometry identity) or decimate in Blender
4. **Versioning workflow** — never overwrite the pipeline output:
   - `working/dwarf_v1.blend` = raw import
   - edit → File → Save As `dwarf_v2.blend` → export `assets/rigged/dwarf_v2.glb`
   - note the change in your project MASTER_PLAN/README so future sessions know which is canonical
5. **Animation** — retarget Mixamo/GLB clips onto the SkinTokens skeleton in Blender
   (Rokoko/Auto-Rig Pro addons or manual bone mapping), or build AnimationTrees in Godot
   (`hermes-3d-mcp` / HermesForge).

---

## 5. Quota & reliability notes

- ZeroGPU is per-HF-account and serialized: **never run batch calls in parallel**.
- `extract_glb` server-side can take 30–60s+; the scripts retry automatically.
  Re-running with the same `--seed` retries extraction on the cached generation for free.
- A failed batch leaves partial results — re-running only processes what's missing if you
  delete/keep rows in the manifest accordingly (or just re-run; it overwrites outputs).
- If the Space is sleeping/cold, the first call of a session may take a minute to warm up.

## 6. Skill map (what loads when)

| You say... | Skill that handles it |
|---|---|
| "make this image a 3D model" | `trellis-image-to-3d` |
| "rig these characters" | `skintokens-rigging` |
| "generate concept images locally" | `comfyui` / `forgedna-comfyui-assets` |
| "mask/segment this precisely" | `segment-anything-model` |
| "clean it up / animate in Blender" | `blender-mcp` |
| "drop it into my Godot game" | `hermes-3d-mcp` (HermesForge) |
