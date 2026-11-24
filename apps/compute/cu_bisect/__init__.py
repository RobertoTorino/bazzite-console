# SPDX-License-Identifier: GPL-3.0-or-later

"""PyQt6 window for ps5-cu-bisect.sh and ps5-cu-unlock.sh: it runs the CU test itself, in four steps, and
installs a tested CU unlock. The bisecting is the script's own, exactly as if typed by hand."""

APP_NAME = "PS5 CU Unlock"
APP_ID = "ps5-cu-bisect-gui"
__version__ = "1.0.1"

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / "ps5-cu-bisect.webp"
WINDOW_ICON_PATH = LOGO_PATH
REPO_URL = "https://github.com/RobertoTorino/bazzite-console/tree/main/apps/compute"


def window_title(part: str) -> str:
    """Title of a secondary window. On Linux/Windows Qt appends " — <display name>" itself."""
    import sys
    return f"{APP_NAME} — {part}" if sys.platform == "darwin" else part
