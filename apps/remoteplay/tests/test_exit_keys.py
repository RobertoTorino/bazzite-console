# SPDX-License-Identifier: AGPL-3.0-or-later
"""Escape closes ordinary windows, while dialogs and streams keep their own keys."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog, QLineEdit, QMenu, QVBoxLayout, QWidget

from remoteplay.exit_keys import EscapeToClose
from remoteplay.stream_view import StreamWindow


@pytest.fixture
def escape_filter(qapp):
    handler = EscapeToClose(qapp)
    yield handler
    qapp.removeEventFilter(handler)


def test_unhandled_escape_from_child_closes_window(qapp, escape_filter):
    window = QWidget()
    child = QLineEdit(window)
    QVBoxLayout(window).addWidget(child)
    window.show()
    child.setFocus()
    QTest.keyClick(child, Qt.Key.Key_Escape)
    assert not window.isVisible()


def test_handled_and_modified_escape_do_not_close(qapp, escape_filter):
    class HandlesEscape(QWidget):
        def keyPressEvent(self, event):
            event.accept()

    window = HandlesEscape()
    window.show()
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert window.isVisible()
    QTest.keyClick(window, Qt.Key.Key_Escape, Qt.KeyboardModifier.ControlModifier)
    assert window.isVisible()
    window.close()


def test_dialog_keeps_qt_escape(qapp, escape_filter):
    dialog = QDialog()
    dialog.show()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    assert dialog.result() == QDialog.DialogCode.Rejected


def test_menu_keeps_qt_escape(qapp, escape_filter):
    menu = QMenu()
    menu.addAction("Item")
    menu.show()
    QTest.keyClick(menu, Qt.Key.Key_Escape)
    assert not menu.isVisible()


def test_close_can_be_refused_and_repeat_is_ignored(qapp, escape_filter):
    class BusyWindow(QWidget):
        closes = 0

        def closeEvent(self, event):
            self.closes += 1
            event.ignore()

    window = BusyWindow()
    window.show()
    repeat = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier, "", True)
    QApplication.sendEvent(window, repeat)
    assert window.isVisible() and window.closes == 0
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert window.isVisible() and window.closes == 1
    window.hide()


def test_escape_leaves_fullscreen_without_closing_stream(qapp, escape_filter):
    closed = []
    window = StreamWindow("PS5", lambda: closed.append(True))
    window.showFullScreen()
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert window.isVisible() and not window.isFullScreen() and not closed
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert window.isVisible() and not closed
    window.close()
    assert closed == [True]
