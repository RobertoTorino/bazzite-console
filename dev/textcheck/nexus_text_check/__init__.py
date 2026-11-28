# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Text Check for PS5: a window around the suite's text check (tools/text_check.py). It runs the tool on the
whole suite or on one file or folder, lists the files worst first with their counts per check, and shows a file's
problems. It starts and stops the tool's shared LanguageTool server. A Nexus app (dev/), run from the checkout and
never released (owner, 28-11-2026)."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Text Check for PS5"
APP_ID = "nexus-text-check"

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/textcheck/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"
TEXT_CHECK = CHECKOUT / "tools" / "text_check.py"

INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT", "TEXT_CHECK"]
