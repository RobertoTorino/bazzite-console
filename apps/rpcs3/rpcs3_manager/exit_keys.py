# SPDX-License-Identifier: GPL-3.0-or-later
"""Close the active window with Escape or a controller's back button."""

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import QApplication, QDialog

from bazzite_console_core.gamepad import Gamepad


class ExitKeys(QObject):
    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app
        self.gamepad = Gamepad(self)
        self.gamepad.action.connect(self._gamepad_action)
        self.gamepad.start()
        app.aboutToQuit.connect(self.gamepad.stop)
        app.installEventFilter(self)

    def _close_active(self) -> bool:
        window = self.app.activeModalWidget() or self.app.activeWindow()
        if window is None:
            return False
        if isinstance(window, QDialog):
            window.reject()
        else:
            window.close()
        return True

    def _gamepad_action(self, action: str) -> None:
        if action == "back":
            self._close_active()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            return self._close_active()
        return False


def install(app: QApplication) -> ExitKeys:
    return ExitKeys(app)
