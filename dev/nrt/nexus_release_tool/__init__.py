# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Release Tool: the file edits of a release (versions, CHANGELOG entries, pins, the portal bump) of the suite,
and the board checks of a portal release. It works on the checkout it lives in, so it is not part of a portal's
releases and has none of its own: no version, its header names the checkout's commit."""

APP_NAME = "Nexus Release Tool"
HEADER_NAME = f"{APP_NAME} for PS5"    # in the window's header: which suite's checkout it releases
APP_ID = "nexus-release-tool"

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the checkout it edits: the repository, dev/nrt/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/nexus-release-tool/nexus-release-tool.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "HEADER_NAME", "INFO", "LOGO_PATH", "ROOT"]
