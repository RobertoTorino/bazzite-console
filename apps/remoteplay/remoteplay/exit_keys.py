# SPDX-License-Identifier: AGPL-3.0-or-later
"""Close ordinary app windows on unhandled Escape without taking stream or dialog keys."""

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import QDialog, QWidget


class EscapeToClose(QObject):
    def __init__(self, app):
        super().__init__(app)
        self._dispatching = False
        app.installEventFilter(self)

    def eventFilter(self, watched, event):  # noqa: N802 (Qt override)
        if (self._dispatching or event.type() != QEvent.Type.KeyPress or event.key() != Qt.Key.Key_Escape
                or event.modifiers() != Qt.KeyboardModifier.NoModifier or event.isAutoRepeat()
                or not isinstance(watched, QWidget) or not watched.isWindow() or isinstance(watched, QDialog)
                or watched.windowType() in (Qt.WindowType.Popup, Qt.WindowType.ToolTip, Qt.WindowType.SplashScreen)
                or not getattr(watched, "exit_keys", True)):
            return False
        self._dispatching = True
        try:
            event.accept()
            watched.event(event)
        finally:
            self._dispatching = False
        if not event.isAccepted():
            event.accept()
            watched.close()
        return True
