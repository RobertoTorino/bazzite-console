# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Flight Recorder: the board's sensors, memory and load, one line per second, kept on disk by a system
service, so the minutes before a fault are there afterwards; a window that starts and stops it and shows the minutes
around a time. A Nexus app (dev/), run from the checkout and never released (owner, 27-11-2026, after a night of
crashes that no later test brought back)."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Flight Recorder"
APP_ID = "nexus-flight-recorder"

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/flight/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT"]
