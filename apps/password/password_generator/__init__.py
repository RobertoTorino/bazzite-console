# SPDX-License-Identifier: GPL-3.0-or-later
"""Makes a random password of 8 or 15 characters with a capital letter, a small letter, a number and a special character, and keeps it nowhere."""

APP_NAME = "PS5 Password Generator"
APP_ID = "ps5-password"
__version__ = "0.2.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# The app keeps no settings and writes no file: a password is only in its window.
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-password-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
