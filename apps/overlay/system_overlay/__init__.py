# SPDX-License-Identifier: GPL-3.0-or-later
"""A small always-on-top window with the PlayStation 5's live system values: CPU, GPU, memory, fan and
temperatures."""

APP_NAME = "System Overlay"
APP_ID = "ps5-system-overlay"
__version__ = "0.2.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-system-overlay/ps5-system-overlay.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-overlay-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
