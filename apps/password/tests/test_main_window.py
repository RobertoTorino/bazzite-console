# SPDX-License-Identifier: GPL-3.0-or-later
"""The window opens offscreen with the suite's header and a password; Copy puts it on the clipboard for a while, and
a new password, the end of the time and closing take it off again. Nothing is written to a file."""

from __future__ import annotations

import pytest
from PyQt6.QtGui import QGuiApplication

from password_generator import APP_ID, APP_NAME, INFO, LOGO_PATH, ROOT, __version__
from password_generator.generator import LONG, SHORT, meets_rules
from password_generator.main_window import CLIPBOARD_SECONDS, SECRET_HINT, STANDARD, MainWindow


@pytest.fixture
def window(qapp):
    QGuiApplication.clipboard().clear()
    window = MainWindow()
    window.show()
    yield window
    window.close()


def test_version_is_the_single_source():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == __version__ == INFO.version


def test_icons_are_beside_the_package():
    assert LOGO_PATH.is_file() and LOGO_PATH.name == f"{APP_ID}.webp"
    assert (ROOT / "images" / f"{APP_ID}-128.png").is_file()


def test_window_opens_with_the_suites_header_and_a_password(window):
    assert window.windowTitle() == APP_NAME
    assert meets_rules(window.password) and window.password_label.text() == window.password
    assert window.state.text() == "Not stored" and window.state.kind == "warn"
    assert len(window.password) == SHORT
    assert [button.text() for button in window.new_buttons.values()] == ["8 characters", "15 characters"]
    assert window.copy_button.text() == "Copy"
    assert window.clipboard_box.caption.text() == "Clipboard" and window.clipboard_box.value.text() == "Empty"
    assert QGuiApplication.clipboard().text() == ""            # nothing is copied until you ask


def test_the_password_is_shown_as_plain_text(window):
    """A password with angle brackets is shown as it is, not read as markup."""
    from PyQt6.QtCore import Qt
    assert window.password_label.textFormat() == Qt.TextFormat.PlainText


@pytest.mark.parametrize("length", [SHORT, LONG])
def test_each_pill_makes_a_new_password_of_its_length(window, length):
    seen = {window.password}
    for _ in range(20):
        window.new_buttons[length].click()
        assert meets_rules(window.password, length) and window.password_label.text() == window.password
        seen.add(window.password)
    assert len(seen) == 21


def test_the_window_names_the_standards_with_both_lengths(window):
    from PyQt6.QtWidgets import QLabel
    assert "NIST SP 800-63B" in STANDARD and "OWASP" in STANDARD
    assert "8 characters only for an account that also has a second sign-in step" in STANDARD
    assert "15 characters where the password is the only step" in STANDARD
    assert any(label.text() == STANDARD for label in window.findChildren(QLabel))


def test_a_long_password_fits_the_window(window):
    window.new_buttons[LONG].click()
    assert window.password_label.sizeHint().width() <= window.width()


def test_copy_puts_the_password_on_the_clipboard_as_a_secret(window):
    window.copy_button.click()
    clipboard = QGuiApplication.clipboard()
    assert clipboard.text() == window.password
    assert bytes(clipboard.mimeData().data(SECRET_HINT)) == b"secret"
    assert window.timer.isActive() and window.seconds_left == CLIPBOARD_SECONDS
    assert window.clipboard_box.value.text() == f"{CLIPBOARD_SECONDS} s"
    assert window.state.text() == "Copied" and window.state.kind == "ok"


def test_the_clipboard_is_cleared_when_the_time_is_over(window):
    window.copy_button.click()
    for second in range(CLIPBOARD_SECONDS - 1):
        window.tick()
        assert QGuiApplication.clipboard().text() == window.password
        assert window.clipboard_box.value.text() == f"{CLIPBOARD_SECONDS - 1 - second} s"
    window.tick()
    assert QGuiApplication.clipboard().text() == ""
    assert not window.timer.isActive() and window.clipboard_box.value.text() == "Empty"
    assert window.state.text() == "Clipboard cleared"
    assert window.password_label.text() == window.password      # still in the window, to copy again


def test_a_new_password_takes_the_old_one_off_the_clipboard(window):
    window.copy_button.click()
    window.new_buttons[LONG].click()
    assert QGuiApplication.clipboard().text() == ""
    assert not window.timer.isActive() and window.state.text() == "Not stored"


def test_what_you_copied_elsewhere_stays_on_the_clipboard(window):
    window.copy_button.click()
    QGuiApplication.clipboard().setText("something else")
    window.tick()
    assert QGuiApplication.clipboard().text() == "something else"
    assert not window.timer.isActive() and window.clipboard_box.value.text() == "Empty"
    window.close()
    assert QGuiApplication.clipboard().text() == "something else"


def test_closing_ends_the_password(qapp):
    window = MainWindow()
    window.show()
    window.copy_button.click()
    window.close()
    assert QGuiApplication.clipboard().text() == ""
    assert window.password == "" and window.password_label.text() == ""


def test_nothing_is_written(window, settings_dir, tmp_path, monkeypatch):
    """The folder the settings would go to stays empty."""
    window.copy_button.click()
    window.new_buttons[LONG].click()
    window.close()
    assert not settings_dir.exists() or not any(settings_dir.rglob("*"))


def test_the_package_opens_no_file_and_keeps_no_setting():
    for source in (ROOT / "password_generator").glob("*.py"):
        text = source.read_text(encoding="utf-8")
        if source.name in ("main_window.py", "generator.py"):
            for word in ("open(", "write_text", "write_bytes", "QSettings", "open_settings", "logging", "print("):
                assert word not in text, f"{source.name}: {word}"
