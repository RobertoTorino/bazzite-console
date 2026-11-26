# SPDX-License-Identifier: GPL-3.0-or-later
"""The View logs tab of a game manager (owner, 26-11-2026): the app's own log or the emulator's, chosen with two
radio buttons above it. The run wrapper writes what the emulator prints to emulator.log beside the app's log
(applog.EMULATOR_LOG); before, it went to Steam's console, where no one saw it. The hint under the buttons names the
file shown, and Clear logs empties the one shown, with the older ones kept beside it."""

from __future__ import annotations

from html import escape
from pathlib import Path

from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QRadioButton, QVBoxLayout, QWidget

from . import applog
from .platform import private
from .widgets import Terminal, hint_label


class LogPage(QWidget):
    """*app_name*'s log (*log_path*) or *emulator*'s (emulator.log beside it). *app_hint*: what the app's log holds,
    before the sentence that names its file. output is the terminal both are shown in."""

    def __init__(self, app_name: str, emulator: str, log_path: Path, app_hint: str):
        super().__init__()
        self.emulator = emulator
        self.log_path = log_path
        self.emulator_log = log_path.with_name(applog.EMULATOR_LOG)
        self.app_hint = app_hint
        self.app_button = QRadioButton(app_name)
        self.app_button.setToolTip(f"What {app_name} said and did")
        self.emulator_button = QRadioButton(emulator)
        self.emulator_button.setToolTip(f"What {emulator} printed while the last games ran")
        self.group = QButtonGroup(self)
        buttons = QHBoxLayout()
        for button in (self.app_button, self.emulator_button):
            self.group.addButton(button)
            buttons.addWidget(button)
        buttons.addStretch(1)
        self.app_button.setChecked(True)
        self.group.buttonClicked.connect(lambda _button: self.show_chosen())
        self.hint = hint_label("")
        self.output = Terminal()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.addLayout(buttons)
        layout.addWidget(self.hint)
        layout.addWidget(self.output, 1)
        self.show_chosen()

    def showing_emulator(self) -> bool:
        return self.emulator_button.isChecked()

    def shown_path(self) -> Path:
        """The file the tab shows: the app's log or the emulator's."""
        return self.emulator_log if self.showing_emulator() else self.log_path

    def show_chosen(self) -> None:
        """The chosen log read again from its file, newest last, with the hint that names it."""
        if self.showing_emulator():
            self.hint.setText(f"What {escape(self.emulator)} printed while the last games ran, newest last. The same "
                              f"lines are in {escape(private(self.emulator_log))}, which turns over at 1 MB.")
            self.output.setPlaceholderText(f"What {self.emulator} printed appears here after a game ran.")
        else:
            self.hint.setText(f"{self.app_hint} The same lines are in {escape(private(self.log_path))}, which turns "
                              "over at 1 MB.")
            self.output.setPlaceholderText("What the app did, with the time, appears here.")
        self.output.set_text(applog.tail(self.shown_path()))

    def add_line(self, line: str) -> None:
        """A line the app just logged, shown at once while its log is the one shown."""
        if not self.showing_emulator():
            self.output.appendPlainText(line)

    def clear(self, app_id: str) -> Path | None:
        """Clear logs: the log shown emptied, with the older ones kept beside it, and the tab with it. The file that
        could not be cleared, or None."""
        path = self.shown_path()
        if not applog.clear(app_id, path):
            return path
        self.output.clear()
        return None
