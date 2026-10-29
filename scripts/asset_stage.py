#!/usr/bin/env python3
"""Back-compat shim: the stage ledger now ships inside the skill.

The canonical implementation lives at
``skills/game-asset-pipeline/scripts/asset_stage.py`` so that people who install
the skill from the Hermes Skills Hub (or as a GitHub tap) get the ledger with it.
This wrapper keeps the historic ``python3 scripts/asset_stage.py ...`` lines in
the README working.
"""
import runpy
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[1]
    / "skills" / "game-asset-pipeline" / "scripts" / "asset_stage.py"
)

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
