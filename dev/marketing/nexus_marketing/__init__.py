# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Marketing for PS5: an article that presents the portal and every app in it, as a web page to share. It
is written from the checkout, so it keeps up with the suite. A Nexus app (dev/), run from the checkout and never
released (owner, 25-11-2026)."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Marketing for PS5"
APP_ID = "nexus-marketing"

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/marketing/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT"]
