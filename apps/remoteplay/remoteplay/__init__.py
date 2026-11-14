# SPDX-License-Identifier: AGPL-3.0-or-later
"""Remote Play for the system: find the consoles on the network, wake them, register the board with one, and start
and close a Remote Play session and its stream with it. The protocol code is ported from the reference implementation
(AGPL-3.0; see the README's License section)."""

from . import steam_env

steam_env.settle()                      # before Qt loads: started by Steam, the app leaves Steam's libraries

APP_NAME = "Remote Play"
APP_ID = "ps5-remoteplay"
__version__ = "0.3.0"

from pathlib import Path

from bazzite_console_core import AppInfo

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/ps5-remoteplay/ps5-remoteplay.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-remoteplay-v",
               settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "INFO", "LOGO_PATH", "ROOT", "__version__"]
