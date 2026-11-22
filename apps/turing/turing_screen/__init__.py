# SPDX-License-Identifier: GPL-3.0-or-later
"""The board's live system values on a Turzx USB IPS screen (the Turing Smart Screen 3.5" and its family): CPU, GPU,
memory, fan, temperatures, network and disk."""

APP_NAME = "PS5 Turing Screen"
APP_ID = "ps5-turing-screen"
__version__ = "0.2.1"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-turing-screen/ps5-turing-screen.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-turing-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
