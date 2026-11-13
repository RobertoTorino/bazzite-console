# SPDX-License-Identifier: GPL-3.0-or-later
"""Close ordinary windows on an unhandled Escape, leaving streams and dialogs alone.

Adapted from the source suite's shared exit-key handler; controller input belongs to the stream.
"""

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import QApplication, QDialog, QWidget


class ExitKeys(QObject):
    def __init__(self, app: QApplication):
        super().__init__(app)
        self._own = False
        app.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (Qt override)
        if (self._own or event.type() != QEvent.Type.KeyPress or event.key() != Qt.Key.Key_Escape
                or event.modifiers() != Qt.KeyboardModifier.NoModifier or event.isAutoRepeat()
                or not isinstance(watched, QWidget) or not watched.isWindow() or isinstance(watched, QDialog)
                or watched.windowType() in (Qt.WindowType.Popup, Qt.WindowType.ToolTip, Qt.WindowType.SplashScreen)
                or not getattr(watched, "exit_keys", True)):
            return False
        self._own = True
        try:
            event.accept()
            watched.event(event)
        finally:
            self._own = False
        if not event.isAccepted():
            event.accept()
            watched.close()
        return True


def install(app: QApplication) -> ExitKeys:
    return ExitKeys(app)
