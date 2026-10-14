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

Each phase skill works standalone; the orchestrator invokes them as needed.

## External dependencies
- `microsoft/TRELLIS.2` — image → textured 3D GLB
- `VAST-AI/SkinTokens` — static mesh → skeleton + skin weights (rigged GLB)

Both are third-party Spaces. **Do not let tests depend on their health** — select fixtures at test
time and fail loudly with the Space name when one is unavailable (see
`~/dev/knowledge` → `wiki/decisions/recurring-architecture-principles.md` §6).

## Install
These are Hermes Agent skills — install them into `~/.hermes/skills/` rather than invoking the
scripts by hand. A manual, no-agent quick start is documented in `README.md`.

## Notes & limitations
See the README's "Notes & limitations" before promising output quality. Rig verification gates
exist because auto-rigging silently produces bad skeletons.

## Related
Cross-cutting context: `~/dev/knowledge` → `wiki/projects/game-and-xr.md`.
