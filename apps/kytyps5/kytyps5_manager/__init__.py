# SPDX-License-Identifier: GPL-3.0-or-later
"""PS5 games with the KytyPS5-Native emulator. It sets up a tested KytyPS5-Native release, checks what the emulator needs from the board, finds your games and adds them to Steam."""

APP_NAME = "KytyPS5 Manager"
APP_ID = "ps5-kytyps5"
__version__ = "0.1.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-kytyps5/ps5-kytyps5.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-kytyps5-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
