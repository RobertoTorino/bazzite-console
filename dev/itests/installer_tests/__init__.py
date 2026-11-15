# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Installer Tests: a window that runs a suite's installer tests (tools/installer-tests/*.sh, on Linux)
one at a time, with their live output. A Nexus app (dev/), run from the checkout and never
released; it was the Bazzite Console Suite's PS5 Installer Tests (tools/installer-tests/gui) until 02-11-2026
(owner: the tools for working on the suites are Nexus's, in one place)."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Installer Tests"
APP_ID = "nexus-installer-tests"

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/itests/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/nexus-installer-tests/nexus-installer-tests.ini: the suite chosen last
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT"]
