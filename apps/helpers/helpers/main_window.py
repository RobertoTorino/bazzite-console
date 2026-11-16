# SPDX-License-Identifier: GPL-3.0-or-later
"""The window of the app menu entry: the suite's header (the icon at 96 px, the name with the version, the state, the
info symbol), then every helper, a button with its summary beside it; a click opens the helper's own window. In the
portal each helper is a tile of its own, which opens it straight away (ps5-helpers <key>)."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QMainWindow, QVBoxLayout, QWidget

from bazzite_console_core.theme import ORANGE
from bazzite_console_core.widgets import ActionPill, AppHeader, InfoButton, StatusText, hint_label, same_width

from . import APP_NAME, LOGO_PATH, __version__
from .catalog import HELPERS
from .windows import WINDOWS, HelperWindow

ABOUT = ("<b>Console Helpers</b> are small windows for one job each, which come with the suite. In the portal each "
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
        self.state.set_status(f"{len(HELPERS)} helpers", "ok")
        contents = QWidget()
        layout = QVBoxLayout(contents)
        layout.addLayout(header)
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        self.buttons: dict[str, ActionPill] = {}
        for row, helper in enumerate(HELPERS):
            button = ActionPill(helper.name, "Click to open")
            button.clicked.connect(lambda _=False, k=helper.key: self.open_helper(k))
            self.buttons[helper.key] = button
            grid.addWidget(button, row, 0)
            board = f" <span style='color:{ORANGE};'>Changes the board.</span>" if helper.changes_board else ""
            grid.addWidget(hint_label(helper.summary + board), row, 1)
        same_width(list(self.buttons.values()))
        layout.addLayout(grid)
        layout.addStretch(1)
        self.setCentralWidget(contents)
        self.open: dict[str, HelperWindow] = {}

    def open_helper(self, key: str) -> HelperWindow:
        window = self.open.get(key)
        if window is None or not window.isVisible():
            window = self.open[key] = WINDOWS[key]()
        window.show()
        window.raise_()
        window.activateWindow()
        return window
