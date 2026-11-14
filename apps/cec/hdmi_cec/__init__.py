# SPDX-License-Identifier: GPL-3.0-or-later
"""HDMI-CEC for the PlayStation 5: the console's CEC adapter (the kernel's ps5-cec), the TV on the other end, buttons
to turn the TV on or off and switch it to the PS5, and the automatic behavior of Valve's CEC daemon (cecd) that
Bazzite ships."""

APP_NAME = "HDMI CEC Manager"
APP_ID = "ps5-hdmi-cec"
__version__ = "1.0.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-hdmi-cec/ps5-hdmi-cec.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-cec-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
