# SPDX-License-Identifier: GPL-3.0-or-later

"""PS5 Core Unlock (owner, 24-11-2026: the name, before PS5 CPU Tools), one window that leads through the core
test and the core unlock in five steps, as CU Unlock does. It runs ps5-cores-bisect.sh in the window itself, and
ps5-cores-unlock.sh for Install and Uninstall."""

from pathlib import Path

APP_NAME = "PS5 Core Unlock"
APP_ID = "ps5-cores-bisect-gui"
ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / "ps5-cores-bisect.webp"
WINDOW_ICON_PATH = LOGO_PATH
REPO_URL = "https://github.com/RobertoTorino/bazzite-console/tree/main/apps/cores"


def _read_version() -> str:
    try:
        return (ROOT / "VERSION").read_text().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


__version__ = _read_version()


def window_title(part: str) -> str:
    """Title of a secondary window. On Linux/Windows Qt appends " — <display name>" itself."""
    import sys
    return f"{APP_NAME} — {part}" if sys.platform == "darwin" else part
