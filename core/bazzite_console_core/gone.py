# SPDX-License-Identifier: GPL-3.0-or-later
"""What a game's run wrapper shows for a game that is no longer there (owner, 01-11-2026: a game renamed after it was
put in Steam started its emulator without it): the emulator is not started, and a message box in the suite's design
says which file is missing and what to do. OK closes it, and it closes by itself after CLOSE_MS, so Steam sees the
game end either way."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer

from .app import create_app
from .appinfo import AppInfo
from .platform import private

CLOSE_MS = 60_000               # the screen closes by itself after this
TITLE = "This game is no longer there"


def desktop_message(app_name: str, game: Path) -> str:
    """The Bazzite Console's wording (owner, 03-11-2026): the file, and what to do in the app's desktop window."""
    return (f"{private(game)}\n\nIt was renamed, moved or deleted after it was put in Steam, or it is on a drive that "
            f"is not in, so the emulator was not started. Open {app_name}: Refresh finds the game again under its new "
            "name, with its Steam mark, and Update Steam brings its shortcut in Steam up to date.")


def show_dialog(info: AppInfo, app_name: str, game: Path, qt_args: list[str] | None = None) -> int:
    """The Bazzite Console's desktop apps: a message box in the suite's design, closed by OK or by itself after CLOSE_MS,
    instead of the emulator; the run wrapper's exit code (1: the game did not run)."""
    from PyQt6.QtWidgets import QMessageBox
    app = create_app(info, qt_args or [])
    box = QMessageBox(QMessageBox.Icon.Warning, f"{app_name}: {TITLE}", desktop_message(app_name, game))
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    QTimer.singleShot(CLOSE_MS, box.accept)
    box.exec()
    del app
    return 1

