# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Dashboard for PS5: the one door to the tools for working on the suites (owner, 02-11-2026: they were spread
over the suites and the root). It starts the Nexus apps of the checkout (Nexus Release Tool, Nexus Installer Tests,
Nexus Demo Recorder, Nexus Sound Lab, Nexus TTS, Nexus Remix Studio) and opens the tours and the icons of the suite
chosen in its header. A Nexus app (dev/), run from the checkout and never released."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Dashboard for PS5"
APP_ID = "nexus-dashboard-ps5"            # its own per suite: both suites' dashboards can be installed side by side

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/dash/ in it
LOGO_PATH = ROOT / "images" / "nexus-dashboard.webp"

# Settings in ~/.config/nexus-dashboard-ps5/nexus-dashboard-ps5.ini: the suite chosen last
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT"]
