# Model choices (checked 2026-10-22)

The default chain stays on models a stranger can run without a paid
per-generation API, and whose license does not block shipping the asset.

| Stage | Default | Why this one | Not the default |
|---|---|---|---|
| Image | local ComfyUI (SDXL or Qwen-Image) if a GPU is up; else FLUX.1-schnell on ZeroGPU | Free. FLUX schnell is Apache-2.0. Its HF Space has **no negative prompt**, so "no wings" is ignored. When a negation or a limb count matters, edit a passing image or use a local model that has a negative prompt. | Paid image APIs |
| Mesh | [microsoft/TRELLIS.2](https://huggingface.co/spaces/microsoft/TRELLIS.2) | Still the open image-to-3D with an MIT model/code license and a live ZeroGPU Space. 512 is the preset that fits a free queue; 1024/1536 need more quota or a 24 GB card. | Hunyuan3D (Tencent community license, not plain MIT). Meshy, Tripo, Rodin (paid per call). |
| Rig | [VAST-AI/SkinTokens](https://huggingface.co/spaces/VAST-AI/SkinTokens) | Successor to UniRig. One mesh in, skeleton + skin weights out, MIT Space. Needs the voxel retry on glassy textures. | UniRig (older, split skeleton/skin stages). Puppeteer's own rigger (heavier, local only). |
| Animation | Seed3D/Puppeteer, local GPU | Apache-2.0, works on non-humanoid skeletons. Optional. | Text-to-motion models that only emit SMPL humanoids |

Re-check this table before swapping a stage. A higher-quality model with a
non-commercial license is not an improvement for a pipeline we hand to
other people.
