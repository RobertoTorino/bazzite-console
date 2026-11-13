# SPDX-License-Identifier: GPL-3.0-or-later
"""PyQt6 front-end for test-bazzite.sh: diagnostics for a PlayStation 5 running Bazzite (ps5-linux kernel)."""

APP_NAME = "Bazzite Test"
APP_ID = "bazzite-test"
__version__ = "0.2.1"

from pathlib import Path

from bazzite_console_core import SUITE_REPO_URL, AppInfo
from bazzite_console_core.text import plain_tooltip
from bazzite_console_core.text import window_title as _window_title

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"
ICON_PATH = ROOT / "images" / f"{APP_ID}-128.png"      # for notify-send: a desktop may not read WebP
WINDOW_ICON_PATH = LOGO_PATH
DISPLAY_NAME = f"{APP_NAME} {__version__}"
REPO_URL = SUITE_REPO_URL

# Settings in ~/.config/bazzite-test/bazzite-test.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-bazzite-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "DISPLAY_NAME", "ICON_PATH", "INFO", "LOGO_PATH", "REPO_URL", "ROOT",
           "WINDOW_ICON_PATH", "__version__", "plain_tooltip", "window_title"]


def window_title(part: str) -> str:
    """Title of a secondary window. On Linux/Windows Qt appends " — <display name>" itself."""
    return _window_title(part, APP_NAME)
