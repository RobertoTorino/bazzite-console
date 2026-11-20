# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Remix Studio: a window that mixes a voice track with a synthesized background and saves the result. The
voice is an audio file, or a text spoken by Nexus TTS's engine; the background is a pad or a drone made from a
preset, a chord and a few sliders (pad.py); the mix sets their volumes, the lead-in, the tail and the fades (mix.py).
A Nexus app (dev/), run from the checkout and never released (owner, 18-11-2026: a small remix studio beside Text to
Speech and Nexus Sound Lab)."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Nexus Remix Studio"
APP_ID = "nexus-remix-studio"

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/studio/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/nexus-remix-studio/nexus-remix-studio.ini: the voice file, the background, the mix, the
# save folder
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT"]
