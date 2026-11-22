# SPDX-License-Identifier: GPL-3.0-or-later
"""Escape and a controller close the app's window, and the controller works the app (owner, 12-11-2026: B inside
the apps, as it closes the portal; 22-11-2026: the whole controller, as in the portal), for an app that asks
for it: install(app) once the QApplication is there.

Escape: a key press nothing in the window took for itself (a text being edited, a list that goes back a level, a
page of the app's own) closes the window, as its close button does, so the window's own closeEvent still asks what
it asks. A dialog and a menu keep Qt's own Escape. A window that must not close on it (a stream, where the keys are
the game's) says so with a class attribute, exit_keys = False.

The controller, read with pygame-ce (SDL's game controller layer, which gives every pad the same button names):
- the d-pad and the left stick move the focus to the nearest control in that direction (a held direction
  repeats); in a list they move through its rows first, in an open menu or list through its entries
- A presses what has the focus: a button, a pill, a box to check, a list to open, the chosen entry of a menu
- LB and RB open the tab before and after, in the row of tabs around the focus (a tab that acts is passed over)
- B is Escape for whatever has the focus: it closes an open menu, then a dialog, then the window
- the touchpad of a DualShock 4 or a DualSense moves the mouse pointer, as in the portal: a finger moves it, a
  press of the pad clicks, a press with two fingers on it is a right click, at the speed of the portal's Touchpad
  setting
The controller only acts while the app has the focus and has had it for a moment: every app reads the same press,
so the one that closes on it would otherwise take the app behind it along. Without pygame-ce, or without a
controller, there is none of it and nothing is said. An app in which the controller is the app's subject (a stream,
a controller's test) installs it without: install(app, controller=False).

SDL needs no window: it is started with the dummy video driver, set in the environment only while it starts, so a
program the app starts later (Steam, an emulator) does not inherit it. Wayland lets no program move the pointer, so
the touchpad moves a mouse of the app's own, made through the kernel's uinput at the first touch (as the portal's
pointer.py): without access to /dev/uinput the touchpad does nothing and the rest works.

Self-contained (PyQt6 and the standard library; pygame-ce only when it is there), so an app not on core yet carries
a copy; tools/tests/test_instance_copies.py keeps the copies equal."""

from __future__ import annotations

import configparser
import fcntl
import os
import struct
import time
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QPoint, QTimer, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QScrollArea, QTabBar, QTabWidget,
                             QWidget)

POLL_MS = 30
GRACE_S = 0.5                   # the controller counts once the app has had the focus this long (the press that
                                # closed another)
# What SDL reads when it starts, gone from the environment again after (the names core's platform.py lists)
SDL_VARIABLES = {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS": "1",
                 "PYGAME_HIDE_SUPPORT_PROMPT": "1"}
SDL_SET_BY_PYGAME = ("SDL_VIDEO_X11_WMCLASS",)   # what pygame sets itself when it starts: gone again too
# Windows that are not an app's window: Qt closes a menu on Escape itself, and the others never have the keyboard
NOT_WINDOWS = (Qt.WindowType.Popup, Qt.WindowType.ToolTip, Qt.WindowType.SplashScreen)

# As the portal's gamepad.py: the stick, a held direction, the touchpad
DEADZONE = 0.55                 # of the stick's travel: beyond it the stick counts as pushed
FIRST_REPEAT = 0.4              # s before a held direction repeats, then every REPEAT s
REPEAT = 0.12
DIRECTIONS = {"dpad_up": "up", "dpad_down": "down", "dpad_left": "left", "dpad_right": "right"}
KEYS = {"up": Qt.Key.Key_Up, "down": Qt.Key.Key_Down, "left": Qt.Key.Key_Left, "right": Qt.Key.Key_Right}
TOUCH_SPEED = 1000              # pixels for a finger across the touchpad's whole width at the portal's 100 %
TOUCH_ASPECT = 0.49             # the pad's height over its width (DualShock 4 and DualSense alike)
TOUCHPAD_BUTTON = 20            # SDL_CONTROLLER_BUTTON_TOUCHPAD, which pygame-ce has no name for
TOUCH_SPEEDS = (50, 75, 100, 125, 150)   # the portal's Touchpad steps, in % of TOUCH_SPEED
SUITE = "bazzite-console-suite" # the portal's settings: ~/.config/<SUITE>/<SUITE>-portal.ini, [portal] touchpad_speed


def portal_touch_speed(path: Path | None = None) -> float:
    """The touchpad's speed the portal's Settings page set, in pixels for a finger across the pad; 100 % until set."""
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    parser = configparser.ConfigParser()
    try:
        parser.read(path or config / SUITE / f"{SUITE}-portal.ini", encoding="utf-8")
        percent = parser.getint("portal", "touchpad_speed", fallback=100)
    except (configparser.Error, ValueError, OSError):
        percent = 100
    return TOUCH_SPEED * (percent if percent in TOUCH_SPEEDS else 100) / 100


def stick_direction(x: float, y: float) -> str | None:
    """The direction a stick (each axis -1 to 1, y down) is pushed, along its stronger axis; None in the dead zone."""
    if max(abs(x), abs(y)) < DEADZONE:
        return None
    if abs(x) >= abs(y):
        return "right" if x > 0 else "left"
    return "down" if y > 0 else "up"


class PadReader:
    """The controllers' events, as ("button", name, pressed), ("axis", "leftx" or "lefty", -1 to 1), ("touch", down,
    motion or up, (finger, x, y)) with x and y from 0 to 1, and ("removed", "", False) when a pad goes. pressed() is
    how often B went down since the last read."""

    def __init__(self):
        saved = {name: os.environ.get(name) for name in (*SDL_VARIABLES, *SDL_SET_BY_PYGAME)}
        try:
            for name, value in SDL_VARIABLES.items():
                os.environ.setdefault(name, value)
            import pygame
            from pygame._sdl2 import controller
            self.pygame, self.controller = pygame, controller
            pygame.display.init()
            controller.init()
        finally:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
        self.pads: dict[int, object] = {}               # SDL's instance id: the open controller
        for index in range(controller.get_count()):
            self._open(index)
        self.buttons = {getattr(pygame, f"CONTROLLER_BUTTON_{name.upper()}"): name
                        for name in ("a", "b", "leftshoulder", "rightshoulder", *DIRECTIONS)}
        self.buttons[getattr(pygame, "CONTROLLER_BUTTON_TOUCHPAD", TOUCHPAD_BUTTON)] = "touchpad"
        self.touches = {pygame.CONTROLLERTOUCHPADDOWN: "down", pygame.CONTROLLERTOUCHPADMOTION: "motion",
                        pygame.CONTROLLERTOUCHPADUP: "up"}
        self.axes = {pygame.CONTROLLER_AXIS_LEFTX: "leftx", pygame.CONTROLLER_AXIS_LEFTY: "lefty"}

    def _open(self, index: int) -> None:
        try:
            if self.controller.is_controller(index):
                pad = self.controller.Controller(index)
                self.pads[pad.id] = pad
        except Exception:  # noqa: BLE001  (a pad that cannot be opened is left alone)
            pass

    def events(self) -> list[tuple[str, str, object]]:
        pygame = self.pygame
        found: list[tuple[str, str, object]] = []
        for event in pygame.event.get():
            if event.type == pygame.CONTROLLERDEVICEADDED:
                self._open(event.device_index)
            elif event.type == pygame.CONTROLLERDEVICEREMOVED:
                self.pads.pop(event.instance_id, None)
                found.append(("removed", "", False))
            elif event.type in (pygame.CONTROLLERBUTTONDOWN, pygame.CONTROLLERBUTTONUP):
                name = self.buttons.get(event.button)
                if name:
                    found.append(("button", name, event.type == pygame.CONTROLLERBUTTONDOWN))
            elif event.type == pygame.CONTROLLERAXISMOTION:
                name = self.axes.get(event.axis)
                if name:
                    found.append(("axis", name, max(-1.0, min(1.0, event.value / 32767))))
            elif event.type in self.touches:
                finger = getattr(event, "finger_id", getattr(event, "finger", 0))   # pygame-ce: finger_id
                found.append(("touch", self.touches[event.type], (finger, event.x, event.y)))
        return found

    def pressed(self) -> int:
        return sum(1 for kind, name, down in self.events() if kind == "button" and name == "b" and down)

    def close(self) -> None:
        self.pads.clear()
        try:
            self.controller.quit()
            self.pygame.display.quit()
        except Exception:  # noqa: BLE001  (closing never fails the app)
            pass


BackButton = PadReader          # its name before the whole controller (owner, 22-11-2026)

# The touchpad's mouse, as the portal's pointer.py: linux/uinput.h and linux/input-event-codes.h
UINPUT = "/dev/uinput"
MOUSE_NAME = b"Bazzite Console Suite touchpad"
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_RELBIT = 0x40045564, 0x40045565, 0x40045566
UI_DEV_SETUP, UI_DEV_CREATE, UI_DEV_DESTROY = 0x405C5503, 0x5501, 0x5502
EV_SYN, EV_KEY, EV_REL = 0x00, 0x01, 0x02
SYN_REPORT = 0
REL_X, REL_Y = 0x00, 0x01
BTN_LEFT, BTN_RIGHT = 0x110, 0x111
BUS_VIRTUAL = 0x06
EVENT = struct.Struct("llHHi")              # struct input_event: the time (the kernel fills it in), type, code, value


class VirtualMouse:
    """move(dx, dy) in pixels (fractions add up), press(button, down) with BTN_LEFT or BTN_RIGHT. Made at the first
    use, so an app without a touchpad adds no mouse; fails silently after the first failure (no access, no device)."""

    def __init__(self, path: str | None = None):
        self.path = path or UINPUT
        self.fd: int | None = None
        self.failed = False
        self.rest = [0.0, 0.0]                  # the fractions of a pixel not moved yet

    def _open(self) -> bool:
        if self.fd is not None:
            return True
        if self.failed:
            return False
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            self.failed = True
            return False
        try:
            fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
            for button in (BTN_LEFT, BTN_RIGHT):
                fcntl.ioctl(fd, UI_SET_KEYBIT, button)
            fcntl.ioctl(fd, UI_SET_EVBIT, EV_REL)
            for axis in (REL_X, REL_Y):
                fcntl.ioctl(fd, UI_SET_RELBIT, axis)
            # struct uinput_setup: the id (bus, vendor, product, version), the name, ff_effects_max
            fcntl.ioctl(fd, UI_DEV_SETUP, struct.pack("HHHH80sI", BUS_VIRTUAL, 0, 0, 1, MOUSE_NAME, 0))
            fcntl.ioctl(fd, UI_DEV_CREATE)
        except OSError:
            os.close(fd)
            self.failed = True
            return False
        self.fd = fd
        return True

    def _send(self, *events: tuple[int, int, int]) -> None:
        if not self._open():
            return
        data = b"".join(EVENT.pack(0, 0, kind, code, value) for kind, code, value in events)
        try:
            os.write(self.fd, data + EVENT.pack(0, 0, EV_SYN, SYN_REPORT, 0))
        except OSError:
            pass                                # a full queue drops a move: the next one comes in milliseconds

    def move(self, dx: float, dy: float) -> None:
        self.rest[0] += dx
        self.rest[1] += dy
        x, y = int(self.rest[0]), int(self.rest[1])
        if not x and not y:
            return
        self.rest[0] -= x
        self.rest[1] -= y
        self._send(*[(EV_REL, axis, value) for axis, value in ((REL_X, x), (REL_Y, y)) if value])

    def press(self, button: int, down: bool) -> None:
        self._send((EV_KEY, button, int(down)))

    def close(self) -> None:
        if self.fd is None:
            return
        try:
            fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        except OSError:
            pass
        os.close(self.fd)
        self.fd = None


class ExitKeys(QObject):
    """Escape, and the controller when *controller*, for the window of *app* that has the focus. *source_factory*
    makes the controller's reader (events() or, for B alone, pressed(); close()); *clock* is the time in seconds;
    *mouse* is the touchpad's mouse; *touch_speed* reads the portal's Touchpad setting (tests pass their own)."""

    def __init__(self, app: QApplication, controller: bool = True,
                 source_factory: Callable[[], object] = PadReader, clock: Callable[[], float] = time.monotonic,
                 mouse: VirtualMouse | None = None, touch_speed: Callable[[], float] = portal_touch_speed):
        super().__init__(app)
        self.app = app
        self.clock = clock
        self.source_factory = source_factory
        self.source = None
        self.active_since = clock()
        self._own = False                               # the window is being given the key: not ours again
        self.mouse = mouse or VirtualMouse()            # made at the first touch
        self.read_touch_speed = touch_speed
        self.touch_speed = TOUCH_SPEED
        self.held: dict[str, tuple[str, float]] = {}    # a d-pad button or the stick: its direction, its next repeat
        self.stick = [0.0, 0.0]
        self.fingers: dict[int, tuple[float, float]] = {}   # on the touchpad: each finger's last place
        self.right = False                              # the pad's press that is down is a right click
        self.clicking: int | None = None                # the mouse button the pad holds down
        self.timer = QTimer(self)
        self.timer.setInterval(POLL_MS)
        self.timer.timeout.connect(self.poll)
        app.installEventFilter(self)
        if controller:
            app.applicationStateChanged.connect(self._state_changed)
            app.aboutToQuit.connect(self.stop)
            QTimer.singleShot(0, self.start)            # once the window shows: pygame-ce takes a moment to load

    # ---------------------------------------------------------------------------------------------- Escape
    @staticmethod
    def closes(window: QWidget) -> bool:
        """Whether Escape closes *window*: an app's window, not a dialog or a menu (Qt's own Escape), and not one
        that keeps its keys (exit_keys = False)."""
        return (window.isWindow() and not isinstance(window, QDialog) and window.windowType() not in NOT_WINDOWS
                and getattr(window, "exit_keys", True))

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (Qt override)
        # A key nobody took goes up the parents to the window: there it is ours, after the window's own
        # keyPressEvent had it (an app's page that goes back on Escape accepts it).
        if (self._own or event.type() != QEvent.Type.KeyPress or event.key() != Qt.Key.Key_Escape
                or event.modifiers() != Qt.KeyboardModifier.NoModifier or event.isAutoRepeat()
                or not isinstance(watched, QWidget) or not self.closes(watched)):
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

    # ------------------------------------------------------------------------------------------ the controller
    def start(self) -> bool:
        """Start reading the controller; False without pygame-ce or SDL (the app then has Escape alone)."""
        if self.source is None:
            try:
                self.source = self.source_factory()
            except Exception:  # noqa: BLE001  (no pygame-ce, or no SDL: no controller support, no message)
                return False
        self.touch_speed = self.read_touch_speed()
        self.timer.start()
        return True

    def stop(self) -> None:
        self.timer.stop()
        self._let_go()
        self.mouse.close()
        if self.source is not None:
            self.source.close()
            self.source = None

    def _state_changed(self, state) -> None:
        if state == Qt.ApplicationState.ApplicationActive:
            self.active_since = self.clock()
            self.touch_speed = self.read_touch_speed()  # the portal's Touchpad may have changed meanwhile

    def _acting(self) -> bool:
        return self.app.activeWindow() is not None and self.clock() - self.active_since >= GRACE_S

    def poll(self) -> None:
        if self.source is None:
            return
        try:
            if hasattr(self.source, "events"):
                found = self.source.events()        # read also without the focus: they must not wait in SDL
            else:
                found = [("button", "b", True)] * self.source.pressed()
        except Exception:  # noqa: BLE001  (SDL went away under the reader: Escape alone from here on)
            self.stop()
            return
        acting = self._acting()
        if not acting:
            self._let_go()                          # a press without the focus is dropped, a held one let go
        for kind, name, value in found:
            self.handle(kind, name, value, acting)
        if acting:
            now = self.clock()
            for source, (direction, due) in list(self.held.items()):
                if now >= due:
                    self.held[source] = (direction, now + REPEAT)
                    self.move(direction)

    def _let_go(self) -> None:
        self.held.clear()
        self.stick = [0.0, 0.0]
        self.fingers.clear()
        if self.clicking is not None:               # a release always goes through
            self.mouse.press(self.clicking, False)
            self.clicking = None

    def handle(self, kind: str, name: str, value, acting: bool = True) -> None:
        """One event of the reader; *acting*: the app has had the focus for a moment."""
        if kind == "removed":                       # a pad was unplugged with a direction or a finger on it
            self._let_go()
            return
        if kind == "touch":
            if acting:
                self._touch(name, *value)
            return
        if name == "touchpad":                      # the pad pressed: a click, with two fingers a right click
            if value and acting:
                self.right = len(self.fingers) >= 2
                self.clicking = BTN_RIGHT if self.right else BTN_LEFT
                self.mouse.press(self.clicking, True)
            elif not value and self.clicking is not None:
                self.mouse.press(self.clicking, False)
                self.clicking = None
            return
        if not acting:
            return
        if kind == "axis":
            self.stick[0 if name == "leftx" else 1] = float(value)
            self._push("stick", stick_direction(*self.stick))
            return
        if name in DIRECTIONS:
            self._push(name, DIRECTIONS[name] if value else None)
        elif not value:
            return
        elif name == "a":
            self.accept()
        elif name == "b":
            self.back()
        elif name in ("leftshoulder", "rightshoulder"):
            self.tab(-1 if name == "leftshoulder" else 1)

    def _push(self, source: str, direction: str | None) -> None:
        """A direction pressed or released by *source* (a d-pad button or the stick): a new one acts at once."""
        if direction is None:
            self.held.pop(source, None)
        elif source not in self.held or self.held[source][0] != direction:
            self.held[source] = (direction, self.clock() + FIRST_REPEAT)
            self.move(direction)

    def _touch(self, what: str, finger: int, x: float, y: float) -> None:
        """A finger on the touchpad: the first one down moves the pointer by how far it goes; a second one only
        counts for the right click."""
        if what == "up":
            self.fingers.pop(finger, None)
            return
        last = self.fingers.get(finger)
        self.fingers[finger] = (x, y)
        if what == "motion" and last is not None and finger == min(self.fingers):
            self.mouse.move((x - last[0]) * self.touch_speed, (y - last[1]) * self.touch_speed * TOUCH_ASPECT)

    @staticmethod
    def _key(target: QWidget, key) -> None:
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QApplication.sendEvent(target, QKeyEvent(kind, key, Qt.KeyboardModifier.NoModifier))

    def back(self) -> None:
        """B: Escape for what has the focus, the open menu first, then the dialog or the window."""
        target = self.app.activePopupWidget() or self.app.focusWidget() or self.app.activeWindow()
        if target is None:
            return
        self._key(target, Qt.Key.Key_Escape)

    def accept(self) -> None:
        """A: the chosen entry of an open menu or list; else what has the focus, as Space presses it (a button, a
        pill, a box to check, a list to open), and Enter in a list whose row has no box."""
        popup = self.app.activePopupWidget()
        if popup is not None:
            self._key(popup.focusWidget() or popup, Qt.Key.Key_Return)
            return
        focus = self.app.focusWidget()
        if focus is None or not focus.isEnabled():
            return
        if isinstance(focus, QAbstractItemView):
            index = focus.currentIndex()
            checkable = index.isValid() and bool(index.flags() & Qt.ItemFlag.ItemIsUserCheckable)
            self._key(focus, Qt.Key.Key_Space if checkable else Qt.Key.Key_Return)
            return
        self._key(focus, Qt.Key.Key_Space)

    def move(self, direction: str) -> None:
        """The d-pad or the stick: through an open menu or list, up and down through the rows of a list with the
        focus, else to the nearest control in *direction*."""
        popup = self.app.activePopupWidget()
        if popup is not None:
            self._key(popup.focusWidget() or popup, KEYS[direction])
            return
        window = self.app.activeWindow()
        if window is None:
            return
        focus = self.app.focusWidget()
        if isinstance(focus, QAbstractItemView) and direction in ("up", "down"):
            before = focus.currentIndex()
            self._key(focus, KEYS[direction])
            if focus.currentIndex() != before or not before.isValid():
                return                              # moved through the list; at its edge the focus leaves it
        target = self.nearest(window, focus, direction)
        if target is None:
            return
        target.setFocus(Qt.FocusReason.TabFocusReason)  # the focus border shows, as with Tab
        area = target.parentWidget()
        while area is not None and not isinstance(area, QScrollArea):
            area = area.parentWidget()
        if area is not None:
            area.ensureWidgetVisible(target)

    @staticmethod
    def controls(window: QWidget) -> list[QWidget]:
        """What the focus can go to in *window*: shown, on and taking the focus by Tab, the window's own controls
        only (not those of another window in it, nor a tab bar's scroll buttons)."""
        found = []
        for widget in window.findChildren(QWidget):
            if (widget.isVisible() and widget.isEnabled() and widget.window() is window
                    and widget.focusPolicy() & Qt.FocusPolicy.TabFocus and widget.focusProxy() is None
                    and not isinstance(widget.parentWidget(), QTabBar)):
                found.append(widget)
        return found

    @classmethod
    def nearest(cls, window: QWidget, focus: QWidget | None, direction: str) -> QWidget | None:
        """The control nearest to *focus* in *direction*, the distance across counted twice; without a focus in the
        window, the first control."""
        controls = cls.controls(window)
        if focus is None or focus.window() is not window or focus not in controls:
            return controls[0] if controls else None

        def center(widget: QWidget) -> QPoint:
            return widget.mapTo(window, widget.rect().center())

        here = center(focus)
        best, best_score = None, None
        for widget in controls:
            if widget is focus or focus.isAncestorOf(widget) or widget.isAncestorOf(focus):
                continue
            there = center(widget)
            dx, dy = there.x() - here.x(), there.y() - here.y()
            along, across = {"right": (dx, dy), "left": (-dx, dy), "down": (dy, dx), "up": (-dy, dx)}[direction]
            if along <= 0:
                continue
            score = along + 2 * abs(across)
            if best_score is None or score < best_score:
                best, best_score = widget, score
        return best

    def tab(self, step: int) -> None:
        """LB and RB: the tab before or after in the row of tabs around the focus, or else the first row of tabs
        in the window; a tab that acts goes back to its page by itself, so the one beyond it opens."""
        window = self.app.activeWindow()
        if window is None:
            return
        tabs = None
        widget = self.app.focusWidget()
        while widget is not None and tabs is None:
            if isinstance(widget, QTabWidget):
                tabs = widget
            widget = widget.parentWidget()
        if tabs is None:
            shown = [t for t in window.findChildren(QTabWidget) if t.isVisible() and t.window() is window]
            tabs = shown[0] if shown else None
        if tabs is None or tabs.count() < 2:
            return
        start = tabs.currentIndex()
        for k in range(1, tabs.count()):
            index = (start + step * k) % tabs.count()
            if not tabs.isTabEnabled(index) or not tabs.isTabVisible(index):
                continue
            tabs.setCurrentIndex(index)
            if tabs.currentIndex() == index:
                return


def install(app: QApplication, controller: bool = True) -> ExitKeys:
    """Escape and, with *controller*, the controller work the app's window from now on. The QApplication keeps it."""
    return ExitKeys(app, controller)
