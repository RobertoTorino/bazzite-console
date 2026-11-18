# SPDX-License-Identifier: GPL-3.0-or-later
"""Text to Speech: a window that speaks an English text in a natural female voice (the Kokoro model, on this machine
alone) and saves the speech as an OGG, MP3, FLAC or WAV file: a voice and a speed, Speak, Stop, Save as. The speech
engine is a program of its own (engine.py) with its own Python, which the window sets up once (engine_setup.py). A
Nexus app (dev/), run from the checkout and never released (owner, 18-11-2026: grown from a small Gradio example)."""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.nexus import checkout_commit

APP_NAME = "Text to Speech"
APP_ID = "nexus-text-to-speech"

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT = ROOT.parents[1]                  # the repository, dev/text/ in it
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"

# Settings in ~/.config/nexus-text-to-speech/nexus-text-to-speech.ini: the text, the voice, the speed, the save folder
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=checkout_commit(CHECKOUT)[0], logo=LOGO_PATH, settings_ini=True)

__all__ = ["APP_ID", "APP_NAME", "CHECKOUT", "INFO", "LOGO_PATH", "ROOT"]
