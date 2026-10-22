#!/usr/bin/env python3
"""Tell an agent which backend this machine can actually run.

The runners in this repo call Hugging Face Spaces. They do not load
TRELLIS.2 or SkinTokens weights. This script only classifies the GPU so
nobody promises a local mesh or rig on a card that cannot host it.
"""
from __future__ import annotations

import shutil
import subprocess


def nvidia_vram_mib() -> int | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    # First GPU only. Multi-GPU is not a supported layout here.
    try:
        return int(out.stdout.strip().splitlines()[0].strip())
    except ValueError:
        return None


def main() -> None:
    mib = nvidia_vram_mib()
    print("runners: Hugging Face Spaces (trellis_gen.py, skintokens_rig.py)")
    print("local weights: not installed or invoked by this repo")
    if mib is None:
        print("gpu: no NVIDIA device visible to nvidia-smi")
        print("path: Spaces for mesh and rig. Image models may still run if this")
        print("      machine has a ROCm or Metal port; TRELLIS.2 and SkinTokens")
        print("      publish CUDA installs, so do not start those checkouts here.")
        return
    gb = mib / 1024
    print(f"gpu: NVIDIA {gb:.0f} GB")
    if gb >= 24:
        print("path: hardware meets the published TRELLIS.2 floor (24 GB) and")
        print("      the SkinTokens floor (14 GB). This repo still calls Spaces")
        print("      until you install the upstream checkouts in LOCAL.md and")
        print("      point a future local runner at them. Do not tell the user")
        print("      that `asset_stage.py run` is already local.")
    elif gb >= 14:
        print("path: SkinTokens' published floor is met. TRELLIS.2's is not.")
        print("      Use the Space for the mesh. Do not clone TRELLIS.2 expecting it to fit.")
    else:
        print("path: Spaces for mesh and rig. Local images (SDXL) and, at 12 GB")
        print("      with the Puppeteer skill's patches, animation of a decimated mesh.")
        print("      Do not clone TRELLIS.2 or SkinTokens onto this card.")


if __name__ == "__main__":
    main()
