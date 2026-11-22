# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Garbage Remover: what can go from this machine (crash dumps, Steam's crash reports, the Trash, caches), its
size, and a delete for it; an hourly notification when there is much of it. A Nexus app (dev/), run from the
checkout and never released (owner, 22-11-2026, after a Steam crash loop left gigabytes of dumps and reports)."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Garbage Remover"
APP_ID = "nexus-garbage-remover"

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/garbage/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT"]
