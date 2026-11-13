# SPDX-License-Identifier: GPL-3.0-or-later
from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent

from vita3k_manager import exit_keys


class FakeGamepad(QObject):
    action = pyqtSignal(str)

    def start(self):
        return True

    def stop(self):
        pass


def test_escape_and_controller_back(qapp, monkeypatch):
    monkeypatch.setattr(exit_keys, "Gamepad", FakeGamepad)
    closed = []
    monkeypatch.setattr(exit_keys.ExitKeys, "_close_active", lambda self: closed.append(True) or True)
    handler = exit_keys.install(qapp)
    try:
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        assert handler.eventFilter(qapp, event)
        handler.gamepad.action.emit("accept")
        handler.gamepad.action.emit("back")
        assert closed == [True, True]
    finally:
        qapp.removeEventFilter(handler)
        handler.deleteLater()


def test_closes_active_dialog_and_window(qapp, monkeypatch):
    monkeypatch.setattr(exit_keys, "Gamepad", FakeGamepad)
    from PyQt6.QtWidgets import QDialog, QWidget

    dialog, window = QDialog(), QWidget()
    dialog.show()
    window.show()
    handler = exit_keys.install(qapp)
    monkeypatch.setattr(qapp, "activeModalWidget", lambda: dialog)
    monkeypatch.setattr(qapp, "activeWindow", lambda: window)
    try:
        assert handler._close_active()
        assert not dialog.isVisible() and window.isVisible()
        monkeypatch.setattr(qapp, "activeModalWidget", lambda: None)
        assert handler._close_active()
        assert not window.isVisible()
    finally:
        qapp.removeEventFilter(handler)
        handler.deleteLater()
