# SPDX-License-Identifier: GPL-3.0-or-later
"""The wheel guard (owner, 26-11-2026), a copy of core's: the wheel changes a list, a number field or a slider only
after a click on it. A turn left ignored goes on to the page under it (QApplication::notify); a sent event is never
spontaneous, so that part needs a real wheel and is not tested here."""
import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import (QApplication, QComboBox, QPushButton, QScrollBar, QSlider, QSpinBox, QVBoxLayout,
                             QWidget)

from cu_bisect.widgets import WheelGuard


def turn(widget: QWidget) -> bool:
    event = QWheelEvent(QPointF(5, 5), QPointF(widget.mapToGlobal(QPoint(5, 5))), QPoint(), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)
    return event.isAccepted()


@pytest.mark.parametrize("guard_class", [WheelGuard])
def test_the_wheel_changes_a_value_only_after_a_click(qapp, guard_class):
    guard = guard_class.install(qapp)
    try:
        page = QWidget()
        lay = QVBoxLayout(page)
        button = QPushButton("Has the focus")
        combo, spin, slider, bar = QComboBox(), QSpinBox(), QSlider(Qt.Orientation.Horizontal), QScrollBar()
        combo.addItems(["one", "two", "three"])
        combo.setCurrentIndex(1)
        for w in (spin, slider, bar):
            w.setValue(50)
        for w in (button, combo, spin, slider, bar):
            lay.addWidget(w)
        page.show()
        button.setFocus()
        qapp.processEvents()
        for widget in (combo, spin, slider):
            assert widget.focusPolicy() == Qt.FocusPolicy.StrongFocus
            assert not turn(widget)
        assert (combo.currentIndex(), spin.value(), slider.value()) == (1, 50, 50)
        turn(bar)
        assert bar.value() != 50                    # a scroll bar scrolls as before
        for widget in (combo, spin, slider):
            widget.setFocus()
            qapp.processEvents()
            turn(widget)
        assert combo.currentIndex() != 1 and spin.value() != 50 and slider.value() != 50
        page.close()
    finally:
        guard_class.uninstall()
