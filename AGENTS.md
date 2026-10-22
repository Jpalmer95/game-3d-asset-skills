# AGENTS.md — Game 3D Asset Skills

**Text prompt → images → alpha-masked sprites → textured 3D GLBs → auto-rigged characters**,
orchestrated end-to-end by Hermes Agent skills.

Runs the 3D and rigging phases on **Hugging Face ZeroGPU with the owner's own `HF_TOKEN`** — no
local GPU required. Only `puppeteer-animation` needs the local GPU.

## The four skills
| Skill | Role | Runs when |
|---|---|---|
| `game-asset-pipeline` | **Orchestrator** | "make me 10 enemy characters" — chains everything below |
| `trellis-image-to-3d` | image → 3D | single/batch GLB generation, quality gates, engine presets |
| `skintokens-rigging` | mesh → rig | single/batch auto-rigging with rig verification gates |
| `puppeteer-animation` | rig → animation | video-guided animation (**local GPU**) |

Each phase skill works standalone. `scripts/asset_stage.py` is the re-entry ledger:
edit a prompt, a PNG, or a Blender export and only the downstream stages rerun.
Model defaults and the licenses that keep them defaults are in `MODELS.md`.
Local VRAM floors are in `LOCAL.md`. Do not promise a full local run on a
card under 24 GB: TRELLIS.2 publishes 24 GB, SkinTokens publishes 14 GB.
A 12 GB card runs images and (patched) Puppeteer only; mesh and rig stay
on the user's own HF Space quota. `scripts/which_backend.py` classifies the
GPU. `asset_stage.py run` still calls Spaces even on a 24 GB card — local
weight loading is not wired.

## External dependencies
- `microsoft/TRELLIS.2` — image → textured 3D GLB
- `VAST-AI/SkinTokens` — static mesh → skeleton + skin weights (rigged GLB)

Both are third-party Spaces. Tests must not call them. If a live check fails, name the Space and stop — do not invent a fallback mesh.

## Install
These skills live in this repo under `skills/`. Another Hermes user should install
them from here, not from a second wrapper skill:

```bash
hermes skills install Jpalmer95/game-3d-asset-skills/skills/game-asset-pipeline
hermes skills install Jpalmer95/game-3d-asset-skills/skills/trellis-image-to-3d
hermes skills install Jpalmer95/game-3d-asset-skills/skills/skintokens-rigging
hermes skills install Jpalmer95/game-3d-asset-skills/skills/puppeteer-animation
```

Skill install does **not** include `scripts/` (the stage ledger) or `examples/`.
Clone the repo for those. A manual copy of `skills/` into `~/.hermes/skills/`
also works; see `README.md`.

## Notes & limitations
Read the README "Notes & limitations" before promising output quality. Auto-rigs
fail silently on cropped or glassy meshes; the rig script retries with
`--voxel-postprocess` for the glassy case. It cannot invent legs the image
never had.

Do not depend on the author's other checkouts (`~/dev/knowledge`, ForgeDNA,
HermesForge). This repo is the whole public surface.

## Related
Upstream Spaces: `microsoft/TRELLIS.2`, `VAST-AI/SkinTokens`. Model choice and
licenses: `MODELS.md`.
