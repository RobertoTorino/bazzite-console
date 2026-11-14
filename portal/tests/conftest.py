# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures: bazzite_console_core from the checkout and an offscreen QApplication."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PORTAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORTAL.parent / "core"))
sys.path.insert(0, str(PORTAL))


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".local" / "bin").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    return home


@pytest.fixture
def settings_dir(tmp_path, qapp):
    from PyQt6.QtCore import QSettings

    for fmt in (QSettings.Format.NativeFormat, QSettings.Format.IniFormat):
        QSettings.setPath(fmt, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    return tmp_path / "settings"


@pytest.fixture(autouse=True)
def desktop(tmp_path, monkeypatch):
    from bazzite_console_portal import desktop_icons

    folder = tmp_path / "Desktop"
    folder.mkdir()
    monkeypatch.setattr(desktop_icons, "desktop_dir", lambda: folder)
    return folder


class SilentPlayer:
    """Stands in for the music's player: it records what the portal asked and plays nothing."""

    def __init__(self):
        self.path = None
        self.playing = False
        self.calls: list[str] = []

    def set_track(self, path) -> None:
        self.path = path
        self.calls.append("track")

    def play(self) -> None:
        self.playing = True
        self.calls.append("play")

    def pause(self) -> None:
        self.playing = False
        self.calls.append("pause")

    def stop(self) -> None:
        self.playing = False
        self.calls.append("stop")


@pytest.fixture(autouse=True)
def silent_music(monkeypatch):
    """No test plays the portal's music on the machine the tests run on: a window's player is a SilentPlayer. A test
    of the player itself makes one from the class this returns."""
    from bazzite_console_portal import music
    real = music.Player
    monkeypatch.setattr(music, "Player", SilentPlayer)
    return real
