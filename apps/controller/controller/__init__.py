# SPDX-License-Identifier: GPL-3.0-or-later
"""A controller information and profile utility for Sony DualSense and DualSense Edge on Bazzite.

It has not been validated on PS5 hardware.
"""

APP_NAME = "Controller"
APP_ID = "ps5-controller"
__version__ = "1.0.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-controller/ps5-controller.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-controller-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
