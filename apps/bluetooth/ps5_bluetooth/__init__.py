# SPDX-License-Identifier: GPL-3.0-or-later
"""Pair your Bluetooth keyboard, mouse and controllers at boot, with no USB keyboard or mouse needed."""

APP_NAME = "PS5 Bluetooth"
APP_ID = "ps5-bluetooth"
__version__ = "0.6.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-bluetooth/ps5-bluetooth.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-bluetooth-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
