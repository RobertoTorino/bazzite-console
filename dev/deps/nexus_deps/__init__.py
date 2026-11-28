# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Dependencies for PS5: a suite's Python packages and external tools on this machine, what is missing or
outdated, and a fix for it; and Bazzite's update state. A Nexus app (dev/), run from the checkout and never released."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Dependencies for PS5"
APP_ID = "nexus-deps"

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/deps/ in it
CATALOGS = PACKAGE / "catalogs"
SUITE = "bazzite-console"                   # the suite the repository is: its catalog, catalogs/<suite>.toml
SUITE_NAME = "Bazzite Console Suite"
CATALOG = CATALOGS / f"{SUITE}.toml"
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/nexus-deps/nexus-deps.ini
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)


__all__ = ["APP_ID", "APP_NAME", "CATALOG", "CATALOGS", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT", "SUITE",
           "SUITE_NAME"]
