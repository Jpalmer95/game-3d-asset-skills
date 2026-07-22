# Game Asset Pipeline (Hermes Agent skills)

Text prompt → images → alpha-masked sprites → textured 3D GLBs → auto-rigged characters,
orchestrated end-to-end by Hermes Agent skills. Runs on Hugging Face ZeroGPU with your own
`HF_TOKEN` — no local GPU required for the 3D/rigging phases.

Built around two Hugging Face Spaces:
- [microsoft/TRELLIS.2](https://huggingface.co/spaces/microsoft/TRELLIS.2) — image → textured 3D GLB
- [VAST-AI/SkinTokens](https://huggingface.co/spaces/VAST-AI/SkinTokens) — static mesh → skeleton + skin weights (rigged GLB)

## The three skills

| Skill | Role | When it runs |
|---|---|---|
| `skills/game-asset-pipeline` | Orchestrator | "make me 10 enemy characters" — chains everything below |
| `skills/trellis-image-to-3d` | Phase: image → 3D | single/batch GLB generation, quality gates, engine presets |
| `skills/skintokens-rigging` | Phase: mesh → rig | single/batch auto-rigging with rig verification gates |

Each phase skill works standalone; the orchestrator invokes them as needed.

## Install (Hermes Agent)

```bash
# copy (or symlink) the skill folders into your Hermes skills dir
cp -r skills/* ~/.hermes/skills/gaming/      # or ~/.hermes/skills/<category>/
pip install "gradio_client>=1.0" "rembg[cpu]" pillow
export HF_TOKEN=hf_...   # read token: https://huggingface.co/settings/tokens
```

Restart Hermes (skills load at session start), then ask:
> "Generate 10 elemental ant enemies, rigged, for my Godot game"

## Quick start (manual, no agent)

```bash
T=~/.hermes/skills/gaming/trellis-image-to-3d/scripts/trellis_gen.py
R=~/.hermes/skills/gaming/skintokens-rigging/scripts/skintokens_rig.py

rembg i concept.png masked.png
python3 $T masked.png -o out.glb --target godot
python3 $R out.glb -o out_rigged.glb --preserve-texture-scale
```

See `examples/GUIDE.md` for the full workflow guide (prompt patterns, preprocessing
toolbox, Blender post-processing, versioning) and `examples/ant_elementals.txt` for a
ready 10-prompt batch.

## Features

- **Quality gates** (`pipeline_qgates.py`): alpha-mask coverage check, GLB parse +
  vertex/texture validation, rig joints + skin-weight verification. Bad inputs fail
  before burning GPU quota.
- **`--resume`**: crash-safe batch reruns — completed assets are skipped.
- **Engine presets** (`--target`): `godot-mobile` (30k faces/1k tex), `godot`/`unity`
  (80k/2k), `blender` (300k/2k), `film` (500k/4k).
- **Manifests**: per-run CSVs tracking prompt, seed, paths, and per-phase status.
- **Battle-tested**: built and debugged against the live Spaces (gradio_client 1.x
  `token=` auth, `handle_file()` inputs, list-valued rig outputs, numeric texture size).

## Notes & limitations

- ZeroGPU quota is per-HF-account and serialized — batches run sequentially, a few
  minutes per asset per phase.
- **`rembg` CLI is fragile**: its entrypoint eagerly imports server deps (gradio,
  aiohttp, fastapi). Use the Python API instead:
  `python3 -c "from rembg import remove; open('out.png','wb').write(remove(open('in.png','rb').read()))"`
- SkinTokens output includes a joint-visualization icosphere mesh; hide/delete it in
  Blender/Godot before shipping.
- Auto-rigs are a starting point: thin appendages may need a weight-paint pass.
- TRELLIS.2 is research code — check its license for commercial use of generated assets.

## License

MIT (skills and scripts). The underlying Spaces/models carry their own licenses.
