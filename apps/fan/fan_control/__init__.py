# SPDX-License-Identifier: GPL-3.0-or-later
"""Watches the PlayStation 5's temperatures and its fan: a thermal guard that runs as a system service warns, cools
and, at a critical temperature, shuts the console down cleanly. Nothing changes until you turn the guard on."""

APP_NAME = "Fan Control"
APP_ID = "ps5-fan-control"
__version__ = "0.1.2"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-fan-control/ps5-fan-control.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-fan-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
