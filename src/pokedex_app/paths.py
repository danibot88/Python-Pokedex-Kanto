"""Resolução de caminhos de recursos que funcionam no código e no executável."""

import sys
from pathlib import Path


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            return Path(bundle_dir)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


RESOURCE_ROOT = _resource_root()
ASSETS_DIR = RESOURCE_ROOT / "assets"
