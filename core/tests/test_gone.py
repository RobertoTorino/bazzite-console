# SPDX-License-Identifier: GPL-3.0-or-later
"""The screen for a game that is no longer there: the Bazzite Console's desktop wording (gone.py; owner, 03-11-2026)."""

from __future__ import annotations

from pathlib import Path

from bazzite_console_core import gone


def test_the_desktop_message_names_the_file_and_what_to_do(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    game = tmp_path / "Games" / "PS2" / "Two.iso"
    text = gone.desktop_message("PCSX2 Manager", game)
    masked = "~/Games/PS2/Two.iso"                              # the home folder masked, as platform.private() does
    assert text.startswith(f"{masked}\n\n") and str(tmp_path) not in text
    assert "Open PCSX2 Manager: Refresh finds the game again" in text and "Update Steam" in text
