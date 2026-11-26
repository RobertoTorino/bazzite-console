# SPDX-License-Identifier: GPL-3.0-or-later
"""The View logs tab of a game manager (owner, 26-11-2026): the app's log or the emulator's, chosen with two radio
buttons, the hint naming the file shown with the home folder as ~, and Clear logs emptying the one shown."""

from __future__ import annotations

from bazzite_console_core import applog
from bazzite_console_core.log_page import LogPage


def _logs(tmp_path):
    log = tmp_path / "app" / "app.log"
    log.parent.mkdir()
    log.write_text("26-11-2026 10:00:00 INFO the app's line\n")
    emulator = log.with_name(applog.EMULATOR_LOG)
    emulator.write_text("printed\n")
    return log, emulator


def test_the_apps_log_first_then_the_emulators(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    log, emulator = _logs(tmp_path)
    page = LogPage("Some Manager", "Some", log, "Everything the app said and did, newest last.")
    assert [page.app_button.text(), page.emulator_button.text()] == ["Some Manager", "Some"]
    assert page.app_button.isChecked() and page.output.toPlainText() == "26-11-2026 10:00:00 INFO the app's line"
    assert page.hint.text() == ("Everything the app said and did, newest last. The same lines are in ~/app/app.log, "
                                "which turns over at 1 MB.")
    page.add_line("26-11-2026 10:00:02 INFO a new line")
    assert page.output.toPlainText().endswith("a new line")
    page.emulator_button.click()
    assert page.showing_emulator() and page.shown_path() == emulator and page.output.toPlainText() == "printed"
    assert page.hint.text() == ("What Some printed while the last games ran, newest last. The same lines are in "
                                "~/app/emulator.log, which turns over at 1 MB.")
    page.add_line("26-11-2026 10:00:03 INFO not shown here")
    assert page.output.toPlainText() == "printed"


def test_clear_empties_the_log_shown(qapp, tmp_path):
    log, emulator = _logs(tmp_path)
    older = emulator.with_name("emulator.log.1")
    older.write_text("old\n")
    page = LogPage("Some Manager", "Some", log, "Everything the app said and did.")
    page.emulator_button.click()
    assert page.clear("some-manager") is None
    assert emulator.read_text() == "" and not older.exists() and page.output.toPlainText() == ""
    assert log.read_text() == "26-11-2026 10:00:00 INFO the app's line\n"
    page.app_button.click()
    assert page.output.toPlainText() == "26-11-2026 10:00:00 INFO the app's line"


def test_without_an_emulator_log_yet(qapp, tmp_path):
    log = tmp_path / "app.log"
    page = LogPage("Some Manager", "Some", log, "Everything the app said and did.")
    page.emulator_button.click()
    assert page.output.toPlainText() == "" and "after a game ran" in page.output.placeholderText()
