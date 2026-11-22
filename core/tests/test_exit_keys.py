# SPDX-License-Identifier: GPL-3.0-or-later
"""Escape and B close the app's window: what the window does with the key first, the windows left alone, and B only
for the app that has had the focus for a moment."""

from __future__ import annotations

import os

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QDialog, QLineEdit, QMainWindow, QMenu, QVBoxLayout, QWidget

from bazzite_console_core import exit_keys
from bazzite_console_core.exit_keys import GRACE_S, BackButton, ExitKeys


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.closed = 0
        self.field = QLineEdit()
        self.setCentralWidget(self.field)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.closed += 1
        super().closeEvent(event)


class BackWindow(Window):
    """An app's own Escape: back from a page while one is open."""

    page = True

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.key() == Qt.Key.Key_Escape and self.page:
            self.page = False
            event.accept()
            return
        super().keyPressEvent(event)


class Presses:
    def __init__(self):
        self.waiting = 0
        self.closed = False

    def pressed(self) -> int:
        count, self.waiting = self.waiting, 0
        return count

    def close(self) -> None:
        self.closed = True


def press(widget: QWidget, key=Qt.Key.Key_Escape, modifiers=Qt.KeyboardModifier.NoModifier) -> None:
    QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyPress, key, modifiers))


@pytest.fixture
def keys(qapp):
    made = ExitKeys(qapp, controller=False)
    yield made
    qapp.removeEventFilter(made)
    made.stop()
    made.deleteLater()


@pytest.fixture
def pad(qapp, monkeypatch):
    """ExitKeys with a controller whose B the test presses, a clock it sets, and the app's focus as it says."""
    now = [100.0]
    source = Presses()
    made = ExitKeys(qapp, source_factory=lambda: source, clock=lambda: now[0])
    made.start()
    made.timer.stop()                                   # the test polls
    made.now, made.presses = now, source
    yield made
    qapp.removeEventFilter(made)
    made.stop()
    made.deleteLater()


def test_escape_closes_the_window_from_the_widget_with_the_focus(keys):
    window = Window()
    window.show()
    press(window.field)
    assert window.closed == 1 and not window.isVisible()


def test_another_key_and_escape_with_a_modifier_do_nothing(keys):
    window = Window()
    window.show()
    press(window.field, Qt.Key.Key_A)
    press(window.field, Qt.Key.Key_Escape, Qt.KeyboardModifier.ShiftModifier)
    assert window.closed == 0 and window.isVisible()
    window.close()


def test_the_windows_own_escape_comes_first(keys):
    window = BackWindow()
    window.show()
    press(window.field)                                 # back from the page
    assert window.closed == 0 and not window.page
    press(window.field)                                 # nothing left to go back from
    assert window.closed == 1


def test_a_window_that_refuses_to_close_stays(keys):
    class Busy(Window):
        def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
            self.closed += 1
            event.ignore()

    window = Busy()
    window.show()
    press(window.field)
    assert window.closed == 1 and window.isVisible()
    window.destroy()


def test_a_dialog_a_menu_and_a_window_that_keeps_its_keys_are_left_alone(keys):
    class Stream(Window):
        exit_keys = False

    stream = Stream()
    assert not ExitKeys.closes(stream)
    assert not ExitKeys.closes(QDialog())
    assert not ExitKeys.closes(QMenu())
    assert not ExitKeys.closes(stream.field)            # not a window
    assert ExitKeys.closes(Window())
    stream.show()
    press(stream.field)
    assert stream.closed == 0
    stream.close()


def test_a_dialog_keeps_qts_escape(keys):
    window = Window()
    window.show()
    dialog = QDialog(window)
    field = QLineEdit()
    QVBoxLayout(dialog).addWidget(field)
    dialog.show()
    press(field)
    assert not dialog.isVisible() and window.closed == 0
    window.close()


def test_b_is_escape_for_the_app_with_the_focus(pad, monkeypatch):
    window = Window()
    window.show()
    monkeypatch.setattr(pad.app, "activeWindow", lambda: window)
    monkeypatch.setattr(pad.app, "focusWidget", lambda: window.field)
    pad.now[0] += GRACE_S
    pad.presses.waiting = 1
    pad.poll()
    assert window.closed == 1


def test_b_without_the_focus_is_read_and_dropped(pad, monkeypatch):
    window = Window()
    window.show()
    monkeypatch.setattr(pad.app, "activeWindow", lambda: None)
    pad.now[0] += 10
    pad.presses.waiting = 1
    pad.poll()
    assert window.closed == 0 and pad.presses.waiting == 0
    monkeypatch.setattr(pad.app, "activeWindow", lambda: window)
    pad.poll()                                          # the press does not come back with the focus
    assert window.closed == 0
    window.close()


def test_b_right_after_the_focus_came_is_the_press_that_closed_another_app(pad, monkeypatch):
    window = Window()
    window.show()
    monkeypatch.setattr(pad.app, "activeWindow", lambda: window)
    monkeypatch.setattr(pad.app, "focusWidget", lambda: window.field)
    pad.now[0] += 10
    pad._state_changed(Qt.ApplicationState.ApplicationActive)
    pad.now[0] += GRACE_S / 2
    pad.presses.waiting = 1
    pad.poll()
    assert window.closed == 0
    pad.now[0] += GRACE_S
    pad.presses.waiting = 1
    pad.poll()
    assert window.closed == 1


def test_b_closes_a_dialog_before_the_window(pad, monkeypatch):
    window = Window()
    window.show()
    dialog = QDialog(window)
    field = QLineEdit()
    QVBoxLayout(dialog).addWidget(field)
    dialog.show()
    monkeypatch.setattr(pad.app, "activeWindow", lambda: dialog)
    monkeypatch.setattr(pad.app, "focusWidget", lambda: field)
    pad.now[0] += GRACE_S
    pad.presses.waiting = 1
    pad.poll()
    assert not dialog.isVisible() and window.closed == 0
    window.close()


def test_without_a_controller_reader_there_is_escape_alone(qapp):
    def none():
        raise ImportError("no pygame")

    made = ExitKeys(qapp, source_factory=none)
    try:
        assert made.start() is False and not made.timer.isActive()
        window = Window()
        window.show()
        press(window.field)
        assert window.closed == 1
    finally:
        qapp.removeEventFilter(made)
        made.deleteLater()


def test_a_reader_that_fails_is_stopped_and_the_app_goes_on(pad, monkeypatch):
    source = pad.presses

    def gone() -> int:
        raise RuntimeError("video system not initialized")

    monkeypatch.setattr(source, "pressed", gone)
    pad.poll()
    assert pad.source is None and source.closed and not pad.timer.isActive()
    pad.poll()                                          # nothing left to read


def test_stop_closes_the_reader(pad):
    source = pad.presses
    pad.stop()
    assert source.closed and pad.source is None


def test_sdls_variables_do_not_stay_in_the_environment(monkeypatch):
    """What the app starts later (Steam, an emulator) must not inherit SDL's dummy video driver; a value that was
    there before (from the portal that started the app) stays as it was."""
    pytest.importorskip("pygame")
    monkeypatch.delenv("SDL_VIDEODRIVER", raising=False)
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    button = BackButton()
    try:
        assert "SDL_VIDEODRIVER" not in os.environ
        assert os.environ["SDL_AUDIODRIVER"] == "dummy"
        assert button.pressed() == 0
    finally:
        button.close()


def test_install_gives_the_app_its_exit_keys(qapp):
    made = exit_keys.install(qapp, controller=False)
    try:
        assert isinstance(made, ExitKeys) and made.parent() is qapp and not made.timer.isActive()
    finally:
        qapp.removeEventFilter(made)
        made.deleteLater()


# --- The whole controller (owner, 22-11-2026): the d-pad and the stick, A, LB and RB, the touchpad ---------------

class Events:
    """A reader whose events the test queues."""

    def __init__(self):
        self.queue: list[tuple[str, str, object]] = []
        self.closed = False

    def events(self):
        out, self.queue = self.queue, []
        return out

    def close(self) -> None:
        self.closed = True


class Mouse:
    def __init__(self):
        self.moves: list[tuple[float, float]] = []
        self.presses: list[tuple[int, bool]] = []
        self.closed = 0

    def move(self, dx: float, dy: float) -> None:
        self.moves.append((dx, dy))

    def press(self, button: int, down: bool) -> None:
        self.presses.append((button, down))

    def close(self) -> None:
        self.closed += 1


@pytest.fixture
def ctl(qapp, monkeypatch):
    """ExitKeys with a whole controller, a mouse that records, a clock the test sets, the app active for a while."""
    now = [100.0]
    source, mouse = Events(), Mouse()
    made = ExitKeys(qapp, source_factory=lambda: source, clock=lambda: now[0], mouse=mouse,
                    touch_speed=lambda: 1000.0)
    made.start()
    made.timer.stop()                                   # the test polls
    now[0] += GRACE_S
    made.now, made.events, made.recorded = now, source, mouse

    def send(*events):
        source.queue.extend(events)
        made.poll()

    made.send = send
    yield made
    qapp.removeEventFilter(made)
    made.stop()
    made.deleteLater()


class Grid(QWidget):
    """Two rows of two buttons, a list of three rows and a box to check."""

    def __init__(self):
        super().__init__()
        from PyQt6.QtWidgets import QCheckBox, QGridLayout, QListWidget, QPushButton
        grid = QGridLayout(self)
        self.pressed: list[str] = []
        self.buttons = {}
        for name, row, column in (("a", 0, 0), ("b", 0, 1), ("c", 1, 0), ("d", 1, 1)):
            button = QPushButton(name)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.clicked.connect(lambda _checked=False, n=name: self.pressed.append(n))
            grid.addWidget(button, row, column)
            self.buttons[name] = button
        self.box = QCheckBox("box")
        grid.addWidget(self.box, 2, 0)
        self.rows = QListWidget()
        self.rows.addItems(["one", "two", "three"])
        self.rows.setCurrentRow(0)
        grid.addWidget(self.rows, 3, 0, 1, 2)
        self.resize(300, 300)


def _active(monkeypatch, ctl, window):
    """*window* is the app's active window, as the desktop would make it (offscreen, the focus needs it), and has
    been for a moment."""
    window.activateWindow()
    ctl.app.processEvents()
    monkeypatch.setattr(ctl.app, "activeWindow", lambda: window)
    ctl.now[0] += GRACE_S


def test_the_dpad_moves_the_focus_to_the_nearest_control(ctl, monkeypatch):
    grid = Grid()
    grid.show()
    _active(monkeypatch, ctl, grid)
    grid.buttons["a"].setFocus()
    ctl.send(("button", "dpad_right", True), ("button", "dpad_right", False))
    assert QApplication.focusWidget() is grid.buttons["b"]
    ctl.send(("button", "dpad_down", True), ("button", "dpad_down", False))
    assert QApplication.focusWidget() is grid.buttons["d"]
    ctl.send(("button", "dpad_left", True), ("button", "dpad_left", False))
    assert QApplication.focusWidget() is grid.buttons["c"]
    ctl.send(("button", "dpad_up", True), ("button", "dpad_up", False))
    assert QApplication.focusWidget() is grid.buttons["a"]
    grid.close()


def test_a_held_direction_repeats_and_the_stick_moves_too(ctl, monkeypatch):
    from bazzite_console_core.exit_keys import FIRST_REPEAT, REPEAT
    grid = Grid()
    grid.show()
    _active(monkeypatch, ctl, grid)
    grid.buttons["a"].setFocus()
    ctl.send(("axis", "lefty", 1.0))                    # the stick down: at once
    assert QApplication.focusWidget() is grid.buttons["c"]
    ctl.now[0] += FIRST_REPEAT
    ctl.send()                                          # held: again after a moment
    assert QApplication.focusWidget() is grid.box
    ctl.send(("axis", "lefty", 0.0))
    ctl.now[0] += REPEAT * 5
    ctl.send()                                          # let go: no more
    assert QApplication.focusWidget() is grid.box
    grid.close()


def test_in_a_list_the_dpad_goes_through_the_rows_then_leaves_it(ctl, monkeypatch):
    grid = Grid()
    grid.show()
    _active(monkeypatch, ctl, grid)
    grid.rows.setFocus()
    grid.rows.setCurrentRow(1)
    ctl.send(("button", "dpad_down", True), ("button", "dpad_down", False))
    assert grid.rows.currentRow() == 2 and QApplication.focusWidget() is grid.rows
    ctl.send(("button", "dpad_up", True), ("button", "dpad_up", False))
    ctl.send(("button", "dpad_up", True), ("button", "dpad_up", False))
    assert grid.rows.currentRow() == 0
    ctl.send(("button", "dpad_up", True), ("button", "dpad_up", False))     # at the top: up out of the list
    assert QApplication.focusWidget() is grid.box
    grid.close()


def test_a_presses_a_button_and_checks_a_box(ctl, monkeypatch):
    grid = Grid()
    grid.show()
    _active(monkeypatch, ctl, grid)
    grid.buttons["d"].setFocus()
    ctl.send(("button", "a", True), ("button", "a", False))
    assert grid.pressed == ["d"]
    grid.box.setFocus()
    ctl.send(("button", "a", True), ("button", "a", False))
    assert grid.box.isChecked()
    grid.close()


def test_lb_and_rb_change_the_tab_and_pass_over_a_tab_that_acts(ctl, monkeypatch):
    from PyQt6.QtWidgets import QTabWidget

    from bazzite_console_core.action_tab import ActionTab
    window = QWidget()
    tabs = QTabWidget(window)
    for name in ("one", "two"):
        tabs.addTab(QWidget(), name)
    acted = []
    ActionTab(tabs, "Clear logs", "", lambda: acted.append(1))
    tabs.addTab(QWidget(), "three")
    window.show()
    _active(monkeypatch, ctl, window)
    ctl.send(("button", "rightshoulder", True), ("button", "rightshoulder", False))
    assert tabs.currentIndex() == 1
    ctl.send(("button", "rightshoulder", True))
    assert tabs.currentIndex() == 3 and not acted          # Clear logs is passed over, never pressed
    ctl.send(("button", "rightshoulder", True))
    assert tabs.currentIndex() == 0                         # round to the first
    ctl.send(("button", "leftshoulder", True))
    assert tabs.currentIndex() == 3
    window.close()


def test_the_touchpad_moves_the_pointer_and_clicks(ctl, monkeypatch):
    from bazzite_console_core.exit_keys import BTN_LEFT, BTN_RIGHT, TOUCH_ASPECT
    window = Window()
    window.show()
    _active(monkeypatch, ctl, window)
    ctl.send(("touch", "down", (0, 0.5, 0.5)), ("touch", "motion", (0, 0.51, 0.52)))
    dx, dy = ctl.recorded.moves[-1]
    assert dx == pytest.approx(10.0) and dy == pytest.approx(20.0 * TOUCH_ASPECT)
    ctl.send(("button", "touchpad", True), ("button", "touchpad", False))
    assert ctl.recorded.presses == [(BTN_LEFT, True), (BTN_LEFT, False)]
    ctl.send(("touch", "down", (1, 0.2, 0.2)), ("button", "touchpad", True))    # two fingers: a right click
    assert ctl.recorded.presses[-1] == (BTN_RIGHT, True)
    monkeypatch.setattr(ctl.app, "activeWindow", lambda: None)
    ctl.send()                                              # the focus went: the button is let go
    assert ctl.recorded.presses[-1] == (BTN_RIGHT, False)
    window.close()


def test_the_controller_does_nothing_without_the_focus_or_right_after_it_came(ctl, monkeypatch):
    grid = Grid()
    grid.show()
    _active(monkeypatch, ctl, grid)
    grid.buttons["a"].setFocus()
    monkeypatch.setattr(ctl.app, "activeWindow", lambda: None)
    ctl.send(("button", "a", True), ("button", "dpad_right", True), ("touch", "down", (0, 0.5, 0.5)),
             ("touch", "motion", (0, 0.6, 0.6)))
    assert grid.pressed == [] and ctl.recorded.moves == []
    _active(monkeypatch, ctl, grid)
    ctl._state_changed(Qt.ApplicationState.ApplicationActive)
    ctl.send(("button", "a", True))                         # the press that opened the app
    assert grid.pressed == []
    ctl.now[0] += GRACE_S
    ctl.send(("button", "a", True))
    assert grid.pressed == ["a"]
    grid.close()


def test_the_portals_touchpad_speed_is_read_from_its_settings(tmp_path):
    from bazzite_console_core.exit_keys import TOUCH_SPEED, portal_touch_speed
    ini = tmp_path / "portal.ini"
    assert portal_touch_speed(ini) == TOUCH_SPEED
    ini.write_text("[portal]\ntouchpad_speed=150\n")
    assert portal_touch_speed(ini) == TOUCH_SPEED * 1.5
    ini.write_text("[portal]\ntouchpad_speed=37\n")        # not one of the Touchpad's steps
    assert portal_touch_speed(ini) == TOUCH_SPEED
