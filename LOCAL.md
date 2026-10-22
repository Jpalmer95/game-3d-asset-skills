# Local hardware (no Hugging Face token)

Checked 2026-10-22 against upstream READMEs. This repo has **not** run
TRELLIS.2 or SkinTokens from local weights, and its scripts do not install
them. `skills/trellis-image-to-3d/scripts/trellis_gen.py` and
`skills/skintokens-rigging/scripts/skintokens_rig.py` call the
Hugging Face Spaces. An agent that only clones this repo and runs
`asset_stage.py` is on the Spaces path. That path is the one that works
from this repo alone.

`python3 scripts/which_backend.py` prints which of those two facts applies
to the machine in front of you.

## What is actually turnkey

| Path | From this repo alone? | What you install |
|---|---|---|
| Spaces (mesh + rig) | Yes | `pip install "gradio_client>=1.0" "rembg[cpu]" pillow`, an `HF_TOKEN`, the four skills. See README. |
| Local images | No, not in this repo | ComfyUI plus SDXL, or FLUX.1-schnell via diffusers. Not invoked by `asset_stage.py`. |
| Local mesh | No | Upstream [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) `setup.sh`. CUDA toolkit 12.4, conda, Linux, 24 GB NVIDIA. Separate env from everything else. |
| Local rig | No | Upstream [SkinTokens](https://github.com/VAST-AI-Research/SkinTokens). Python ≥ 3.11, CUDA ≥ 12.1, 14 GB NVIDIA. Separate env from Puppeteer (Python 3.10). |
| Local animation | Documented, not one command | `skills/puppeteer-animation/SKILL.md`. NVIDIA, 12 GB only after its patches and a decimated mesh. |

Do not describe the local mesh or rig as "clone this repo and go." The
weights, CUDA extensions (`flash-attn`, `nvdiffrast`, `CuMesh`, `FlexGEMM`),
and conda env live upstream. Wiring those into `asset_stage.py run` is
future work, and it has to be verified on a 24 GB NVIDIA card before this
repo claims it.

## The number to quote

**24 GB NVIDIA, Linux, run one stage at a time.** That is the published
floor for TRELLIS.2, and it also covers SkinTokens (14 GB) and the
animation step. A 12 GB card is not a full-local machine for this pipeline.
A 16 GB card meets the rigging floor and still misses the mesh floor.

| Card | What actually runs locally | What does not |
|---|---|---|
| 8 GB | SDXL concepts, rembg on CPU, Blender import | FLUX bf16, TRELLIS.2, SkinTokens, Puppeteer |
| 12 GB | SDXL or a quantized image model; Puppeteer **only** with the 12 GB patches in `skills/puppeteer-animation` (decimate the mesh first) | Official TRELLIS.2, official SkinTokens |
| 16 GB | SkinTokens (published floor is 14 GB); image models; Puppeteer | Official TRELLIS.2 (published floor is 24 GB) |
| **24 GB** | **Every stage, sequentially, at TRELLIS 512³** | 1024³ / 1536³ are slower and not the starting point |
| 40 GB+ (A100 40 GB, H100) | The hardware upstream verified | — |

Community write-ups claim TRELLIS.2 at 512 on 6–12 GB via ComfyUI
`low_vram`. Those are not the upstream requirement and are not the spec
this repo recommends. If a card is under 24 GB, use the Hugging Face Space
for the mesh step instead of promising a local run.

## Per stage

| Stage | Published or measured floor | Source | Notes |
|---|---|---|---|
| Mask (`rembg`) | CPU | — | Do not spend VRAM here. |
| Image, SDXL | 8 GB | practical | Fits a 4070-class card. Has a negative prompt, which FLUX schnell's Space does not. |
| Image, FLUX.1-schnell | ~24 GB to keep bf16 resident; less with CPU offload or fp8 | 12B params, bf16 ≈ 24 GB of weights. Official diffusers sample calls `enable_model_cpu_offload()` and does not publish a VRAM floor. | Apache-2.0. Offload makes a 12 GB card possible and slow. Not required if SDXL is good enough. |
| Mesh, TRELLIS.2 | **24 GB NVIDIA, Linux** | [TRELLIS.2 README](https://github.com/microsoft/TRELLIS.2): "at least 24GB of memory", verified on A100 and H100 | 4B model. H100 times they publish: 512³ ~3 s, 1024³ ~17 s, 1536³ ~60 s. Those times are not a 24 GB consumer-card promise. Start at 512. |
| Rig, SkinTokens | **14 GB NVIDIA** | [SkinTokens README](https://github.com/VAST-AI-Research/SkinTokens) and the HF model card | CUDA ≥ 12.1, Python ≥ 3.11. Both checkpoints are required (TokenRig + FSQ-CVAE). |
| Animate, Puppeteer | 12 GB **with patches**, after decimating the mesh | Measured on an RTX 4070 Ti 12 GB in `skills/puppeteer-animation` | Upstream is heavier. 204k-vert TRELLIS meshes OOM at 12 GB. `--decimate 20000` before optimizing. ~25 min/clip. Optional. |
| Blender strip / import | negligible | Blender 5 headless on this machine | `scripts/strip_icosphere.py`. |

## Also budget

- **System RAM:** 32 GB is the practical minimum once a 24 GB weight set
  offloads to CPU. 64 GB is the comfortable number. Upstream does not
  publish a RAM floor; do not treat 32 GB as a Microsoft or VAST figure.
- **Disk:** plan **60 GB free** before the first download (FLUX bf16 is
  ~24 GB of weights alone; TRELLIS.2, SkinTokens, and Puppeteer checkpoints
  sit on top). This repo has not measured the TRELLIS.2 tree byte-for-byte.
- **OS:** Linux. TRELLIS.2's install notes are Linux. Do not promise Windows
  or macOS for the mesh step.
- **Vendor:** NVIDIA. Enough VRAM on an AMD or Apple GPU does not run this
  stack. TRELLIS.2's setup compiles CUDA extensions (`nvdiffrast`, `CuMesh`,
  `FlexGEMM`, `flash-attn`). SkinTokens' install is CUDA ≥ 12.1. A 32 GB
  Radeon AI PRO R9700 is a ROCm card; a 64 GB unified-memory chip (Apple
  Silicon or an APU) has more memory and still no CUDA. For this pipeline
  the faster card is a 24 GB+ NVIDIA, because it is the one the code runs on.
  Dedicated GDDR beats unified LPDDR only after the software starts.
- **One venv will not run every stage.** SkinTokens wants Python 3.11 and
  CUDA 12.1+. The Puppeteer skill pins Python 3.10 and torch 2.1.1+cu118.
  Separate environments. Unload the GPU between them (`nvidia-smi`, then
  the server's free-memory call).

## What to tell a person choosing a card

- No NVIDIA GPU, or under 24 GB, and they still want rigged characters:
  use the Spaces with their own `HF_TOKEN`. That is the supported path.
  ZeroGPU is serial and a few minutes per asset per phase.
- 24 GB NVIDIA, Linux, 32 GB RAM, 60 GB free disk: full local is in spec,
  one stage at a time, TRELLIS at 512 first.
- 12 GB (RTX 4070 Ti class): local images, local animation of a decimated
  mesh, Spaces for mesh and rig. Do not tell them to clone TRELLIS.2 and
  expect it to fit.
