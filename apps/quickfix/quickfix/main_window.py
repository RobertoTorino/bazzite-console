# SPDX-License-Identifier: GPL-3.0-or-later
"""The window of the app menu entry: the suite's header (the icon at 96 px, the name with the version, the state, the
info symbol), then every quickfix, a button with its summary beside it; a click opens the quickfix's own window. In the
portal each quickfix is a tile of its own, which opens it straight away (ps5-quickfix <key>)."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QMainWindow, QVBoxLayout, QWidget

from bazzite_console_core.theme import ORANGE
from bazzite_console_core.widgets import ActionPill, AppHeader, InfoButton, StatusText, hint_label, same_width

from . import APP_NAME, LOGO_PATH, __version__
from .catalog import QUICKFIXES
from .windows import WINDOWS, QuickfixWindow

ABOUT = ("<b>PS5 Quickfix</b> are small windows for one job each, which come with the suite. In the portal each "
         "one is a tile of its own in Utilities; here they are all in one list.<br><br>The ones marked "
         "<b>changes the board</b> ask for your password and change a setting of the system; each one says what "
         "it changes, and its Turn off undoes it.")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(820, 480)
        header = AppHeader(LOGO_PATH, APP_NAME, __version__)
        self.state = StatusText()
        header.add_state(self.state)
        header.add_state(InfoButton(ABOUT))
        self.state.set_status(f"{len(QUICKFIXES)} quickfixes", "ok")
        contents = QWidget()
        layout = QVBoxLayout(contents)
        layout.addLayout(header)
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        self.buttons: dict[str, ActionPill] = {}
        for row, quickfix in enumerate(QUICKFIXES):
            button = ActionPill(quickfix.name, "Click to open")
            button.clicked.connect(lambda _=False, k=quickfix.key: self.open_quickfix(k))
            self.buttons[quickfix.key] = button
            grid.addWidget(button, row, 0)
            board = f" <span style='color:{ORANGE};'>Changes the board.</span>" if quickfix.changes_board else ""
            grid.addWidget(hint_label(quickfix.summary + board), row, 1)
        same_width(list(self.buttons.values()))
        layout.addLayout(grid)
        layout.addStretch(1)
        self.setCentralWidget(contents)
        self.open: dict[str, QuickfixWindow] = {}

    def open_quickfix(self, key: str) -> QuickfixWindow:
        window = self.open.get(key)
        if window is None or not window.isVisible():
            window = self.open[key] = WINDOWS[key]()
        window.show()
        window.raise_()
        window.activateWindow()
        return window
