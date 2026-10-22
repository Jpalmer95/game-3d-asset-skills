#!/usr/bin/env python3
"""One image from the FLUX.1-schnell ZeroGPU Space.

Uses the caller's HF_TOKEN. Retries once — a cold Space often fails the
first call. No width/height overrides beyond what the Space accepts; the
defaults match the Space UI (1024) and are what TRELLIS reconstructs from.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


def generate(prompt: str, out: Path, seed: int, width: int, height: int) -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("ERROR: HF_TOKEN is not set")
    try:
        from gradio_client import Client
    except ImportError:
        sys.exit("ERROR: pip install 'gradio_client>=1.0'")
    last = None
    for attempt in (1, 2):
        try:
            print(f"[flux] attempt {attempt}", flush=True)
            client = Client("black-forest-labs/FLUX.1-schnell", token=token)
            image_result, used_seed = client.predict(
                prompt=prompt,
                seed=seed,
                randomize_seed=seed < 0,
                width=width,
                height=height,
                num_inference_steps=4,
                api_name="/infer",
            )
            src = image_result["path"] if isinstance(image_result, dict) else str(image_result)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
            print(f"[flux] OK seed={used_seed} -> {out} ({out.stat().st_size} bytes)", flush=True)
            return 0
        except Exception as e:
            last = e
            print(f"[flux] failed: {type(e).__name__}: {e}", flush=True)
    sys.exit(f"ERROR: FLUX.1-schnell failed twice: {last}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    args = ap.parse_args()
    generate(args.prompt, Path(args.output), args.seed, args.width, args.height)


if __name__ == "__main__":
    main()
