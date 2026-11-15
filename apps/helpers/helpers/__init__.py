# SPDX-License-Identifier: GPL-3.0-or-later
"""Small helpers for one job each, which come with the suite: Board Test's extras, MangoHud's config, the memory map,
the journal and the boot command line."""

APP_NAME = "Console Helpers"
APP_ID = "ps5-helpers"
__version__ = "0.1.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-helpers/ps5-helpers.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-helpers-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
