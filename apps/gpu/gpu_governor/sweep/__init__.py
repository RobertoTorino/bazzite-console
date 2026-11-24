# SPDX-License-Identifier: GPL-3.0-or-later

"""GPU Manager's GPU sweep (owner, 24-11-2026: PS5 GPU OC Bisect merged into GPU Manager, its sweep in a step window
of its own as Core Unlock and CU Unlock have). One window that runs ps5-gpu-sweep.sh in five steps: the scan, the
control at the config's top point, the clock ladder, the voltage ladder, and Install."""

from pathlib import Path

from .. import APP_NAME as MANAGER_NAME, __version__

APP_NAME = f"{MANAGER_NAME} · GPU sweep"
APP_ID = "ps5-gpu-sweep"
ROOT = Path(__file__).resolve().parent.parent.parent       # the app's folder: the script and the images
SCRIPT = "ps5-gpu-sweep.sh"
LOGO_PATH = ROOT / "images" / "ps5-governor-manager.webp"
WINDOW_ICON_PATH = LOGO_PATH
WIKI_URL = "https://robertotorino.github.io/bazzite-console/apps/gpu/"

__all__ = ["APP_ID", "APP_NAME", "LOGO_PATH", "ROOT", "SCRIPT", "WIKI_URL", "WINDOW_ICON_PATH", "__version__",
           "window_title"]


def window_title(part: str) -> str:
    """Title of a secondary window. On Linux/Windows Qt appends " — <display name>" itself."""
    import sys
    return f"{APP_NAME} — {part}" if sys.platform == "darwin" else part
