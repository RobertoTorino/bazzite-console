# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: the suite's header (the icon at 96 px, the name with the version, the state, the info symbol, and the
pills on the second row: a new password of 8 characters, one of 15, Copy and what the clipboard holds), then the
password in large type.

The password is in this window and nowhere else: no file, no setting, no log. Copy puts it on the clipboard for
CLIPBOARD_SECONDS, marked as a secret so a clipboard history does not keep it; then the app takes it off again, as it
does when a new password is made and when the window closes."""

from __future__ import annotations

from PyQt6.QtCore import QMimeData, Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from bazzite_console_core.theme import GREEN, GREY, surface_style
from bazzite_console_core.widgets import (ActionPill, AppHeader, InfoButton, MetricBox, StatusText, current_theme,
                                          hint_label, same_width)

from . import APP_NAME, LOGO_PATH, __version__
from .generator import LONG, SHORT, Generator

CLIPBOARD_SECONDS = 60
SECRET_HINT = "x-kde-passwordManagerHint"       # Plasma's clipboard history skips what carries it
STANDARD = (f"The rules meet the minimum of NIST SP 800-63B and OWASP. NIST accepts {SHORT} characters only for an "
            f"account that also has a second sign-in step, and asks for {LONG} characters where the password is the "
            "only step.")
ABOUT = (f"<b>{APP_NAME}</b> makes a random password of {SHORT} or {LONG} characters with at least one capital "
         "letter, one small letter, one number and one special character.<br><br>The password is <b>kept "
         "nowhere</b>: not in a file, not in a setting, not in a log. A new password replaces it and closing the "
         f"app ends it, for good.<br><br><b>Copy</b> puts it on the clipboard for {CLIPBOARD_SECONDS} seconds, so "
         "you can paste it where you keep your passwords. Then the app clears the clipboard.<br><br>" + STANDARD
         + " The special characters are OWASP's list of password special characters, without the space.")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 400)
        self.generator = Generator()
        self.password = ""
        self._copied = ""               # what Copy put on the clipboard, until the app clears it
        self.seconds_left = 0
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)

        header = AppHeader(LOGO_PATH, APP_NAME, __version__)
        self.state = StatusText()
        header.add_state(self.state)
        header.add_state(InfoButton(ABOUT))
        self.new_buttons: dict[int, ActionPill] = {}
        for length, where in ((SHORT, "With a second sign-in step"), (LONG, "The password is the only step")):
            button = ActionPill(f"{length} characters", where,
                                f"Makes a new password of {length} characters. The one shown now is gone for good.")
            button.clicked.connect(lambda length=length: self.new_password(length))
            self.new_buttons[length] = button
        self.copy_button = ActionPill("Copy", f"On the clipboard for {CLIPBOARD_SECONDS} s",
                                      f"Puts the password on the clipboard for {CLIPBOARD_SECONDS} seconds, so you "
                                      "can paste it where you keep your passwords.")
        self.copy_button.clicked.connect(self.copy)
        self.clipboard_box = MetricBox("Clipboard")
        pills = [*self.new_buttons.values(), self.copy_button, self.clipboard_box]
        same_width(pills)
        for pill in pills:
            header.add_second(pill)
        header.second_row.addStretch(1)

        self.password_label = QLabel()
        self.password_label.setTextFormat(Qt.TextFormat.PlainText)       # a password may hold <, > and &
        self.password_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.password_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.password_label.setToolTip("The password. It is shown here and kept nowhere.")
        self.password_label.setStyleSheet(
            surface_style(None, "QLabel", 8, theme=current_theme())
            + "QLabel { font-family:monospace; font-size:48px; font-weight:700; letter-spacing:6px; "
              "padding:18px; }")

        contents = QWidget()
        layout = QVBoxLayout(contents)
        layout.addLayout(header)
        layout.addWidget(self.password_label)
        layout.addWidget(hint_label(
            "A capital letter, a small letter, a number and a special character. The password is kept nowhere: "
            "store it yourself before you make a new one or close the app."))
        layout.addWidget(hint_label(STANDARD))
        layout.addStretch(1)
        self.setCentralWidget(contents)
        self.new_password()

    def new_password(self, length: int = SHORT) -> None:
        """A new password of *length* characters in the window; the one before it leaves the clipboard too."""
        self.clear_clipboard()
        self.password = self.generator.new(length)
        self.password_label.setText(self.password)
        self.state.set_status("Not stored", "warn", "This password is only in this window. Copy it and store it "
                                                    "before you make a new one or close the app.")

    def copy(self) -> None:
        """The password on the clipboard, marked as a secret, for CLIPBOARD_SECONDS."""
        data = QMimeData()
        data.setText(self.password)
        data.setData(SECRET_HINT, b"secret")
        QGuiApplication.clipboard().setMimeData(data)
        self._copied = self.password
        self.seconds_left = CLIPBOARD_SECONDS
        self.timer.start()
        self._show_clipboard()
        self.state.set_status("Copied", "ok", "The password is on the clipboard. Paste it where you keep your "
                                              "passwords.")

    def tick(self) -> None:
        """A second of the clipboard's time; at the end, or when something else was copied, the countdown stops."""
        self.seconds_left -= 1
        if self.seconds_left <= 0 or not self.holds_clipboard():
            self.clear_clipboard()
        else:
            self._show_clipboard()

    def holds_clipboard(self) -> bool:
        """Whether the clipboard still holds the password Copy put there."""
        if not self._copied:
            return False
        clipboard = QGuiApplication.clipboard()
        return clipboard.ownsClipboard() or clipboard.text() == self._copied

    def clear_clipboard(self) -> None:
        """Takes the password off the clipboard. What you copied elsewhere since stays."""
        if self.holds_clipboard():
            QGuiApplication.clipboard().clear()
        was_copied = bool(self._copied)
        self._copied = ""
        self.seconds_left = 0
        self.timer.stop()
        self._show_clipboard()
        if was_copied and self.password:
            self.state.set_status("Clipboard cleared", "warn", "The password is off the clipboard. It is still in "
                                                               "this window: Copy puts it there again.")

    def _show_clipboard(self) -> None:
        if self.seconds_left > 0:
            self.clipboard_box.set_value(f"{self.seconds_left} s", "The password is on the clipboard for this long.")
            self.clipboard_box.set_colour(GREEN)
        else:
            self.clipboard_box.set_value("Empty", "The password is not on the clipboard.")
            self.clipboard_box.set_colour(GREY)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Closing ends the password: off the clipboard, out of the window."""
        self.clear_clipboard()
        self.password = ""
        self.password_label.clear()
        super().closeEvent(event)
