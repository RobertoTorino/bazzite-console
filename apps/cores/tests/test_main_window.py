# SPDX-License-Identifier: GPL-3.0-or-later
"""The one window opens offscreen with the suite's header; its bisect part turns its form into the right command, and
its unlock part shows the gate's verdict, the cores and the unlock script's --status output, in the log behind its
button."""

from __future__ import annotations

import shlex

import pytest
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QLabel, QMessageBox, QPushButton, QWidget

from cores_bisect import __version__
from cores_bisect import gate
from cores_bisect import main_window as bisect_window
from cores_bisect import unlock_panel
from conftest import all_passed

SCRIPT = "/opt/ps5-cores-bisect/ps5-cores-bisect.sh"
UNLOCK = "/opt/test/ps5-cores-unlock.sh"            # not there: --status only fails, in the log


def _wait_for(predicate, ms=5000):
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(lambda: predicate() and loop.quit())
    timer.start(10)
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    timer.stop()
    return predicate()


def _header(window):
    labels = window.findChildren(QLabel)
    logo = next(label for label in labels if label.pixmap() is not None and not label.pixmap().isNull())
    title = next(label for label in labels if f"v{__version__}" in label.text())
    return logo, title


@pytest.fixture
def started(monkeypatch):
    """Runs Start without a terminal: the command it would open, and Yes to its summary."""
    commands = []
    monkeypatch.setattr(bisect_window, "launch_in_terminal", commands.append)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    return commands


@pytest.fixture(autouse=True)
def gate_state(monkeypatch, state):
    """The unlock part's gate reads the test's state folder; without a call, there are no results."""
    def use(**kwargs):
        folder = state(**kwargs)
        monkeypatch.setattr(unlock_panel, "check", lambda: gate.check(folder))
    use(phase=None)
    return use


def test_the_window_has_the_suite_header(qapp):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    logo, title = _header(window)
    assert logo.pixmap().width() == 96
    assert "PS5 CPU Tools" in title.text()
    window.close()


def test_start_with_the_defaults(qapp, started):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.start_pill.click()
    assert [shlex.split(c) for c in started] == [["bash", SCRIPT, "-t", "600", "-r", "3"]]


def test_start_with_mprime_and_rasdaemon(qapp, started):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.load_combo.setCurrentIndex(window.load_combo.findData("mprime"))
    window.ras_pill.setChecked(True)
    window.rounds_spin.setValue(2)
    window.same_boot_pill.setChecked(True)
    window.start_pill.click()
    assert shlex.split(started[0])[2:] == ["-t", "600", "-r", "2", "--load", "mprime", "--rasdaemon", "--same-boot"]


def test_unattended_installs_the_resume_unit(qapp, started, monkeypatch):
    installed = []
    monkeypatch.setattr("cores_bisect.service.install", lambda script, opts: installed.append(opts))
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    assert not window.autostart_pill.isEnabled()
    window.auto_pill.setChecked(True)
    assert window.autostart_pill.isEnabled() and window.autostart_pill.isChecked()
    window.start_pill.click()
    assert installed and installed[0].unattended
    assert "--auto" in shlex.split(started[0])


def test_the_estimate_is_short_and_follows_the_options(qapp):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    assert window.hint_label.text() == "About 3.0 h"               # 5 items x 3 rounds x (600 s + a reboot)
    assert "reboots included" in window.hint_label.toolTip()
    window.same_boot_pill.setChecked(True)
    assert window.hint_label.text() == "About 2.5 h" and "reboots" not in window.hint_label.toolTip()
    window.load_combo.setCurrentIndex(window.load_combo.findData("both"))
    assert window.hint_label.text() == "About 5.0 h"
    window.close()


def test_help_opens_the_scripts_help(qapp, monkeypatch):
    """Help is a pill under the title; a click opens the page. The help is the script's own --help, which starts
    after its SPDX line."""
    from pathlib import Path
    opened = []
    monkeypatch.setattr(bisect_window.HelpDialog, "exec", lambda self: opened.append(self.windowTitle()))
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.help_pill.click()
    assert [t.split(" ")[0] for t in opened] == ["help"]
    text = bisect_window.HelpDialog._help_text(str(Path(bisect_window.__file__).parents[1] / "ps5-cores-bisect.sh"))
    assert text.startswith("ps5-cores-bisect.sh - ") and "Usage:" in text and "SPDX" not in text
    window.close()


def test_the_header_has_four_pills_in_order(qapp):
    """Help, Start, Show status and Reset under the title, of one width; no About (owner, 20-11-2026)."""
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.show()
    qapp.processEvents()
    pills = [window.help_pill, window.start_pill, window.status_pill, window.reset_pill]
    assert [p.value.text() for p in pills] == ["Help", "Start", "Show status", "Reset"]
    assert not hasattr(window, "about_pill")
    assert len({p.width() for p in pills}) == 1
    assert sorted(pills, key=lambda p: p.x()) == pills
    assert window.width() >= bisect_window.WIDTH
    assert [b.text() for b in window.findChildren(QPushButton)] == ["Show logs"]   # every action is a pill
    window.close()


def test_the_numbers_on_one_line_and_the_switches_as_pills(qapp):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.show()
    qapp.processEvents()
    fields = [window.time_spin, window.rounds_spin, window.load_combo]
    assert len({field.mapTo(window, field.rect().center()).y() for field in fields}) == 1
    switches = [window.ras_pill, window.same_boot_pill, window.auto_pill, window.autostart_pill]
    assert [p.value.text() for p in switches] == ["Rasdaemon", "Same boot", "Unattended", "Auto resume"]
    assert all(p.caption.text() == "Off" for p in switches) and not window.autostart_pill.isEnabled()
    window.ras_pill.click()
    assert window.ras_pill.isChecked() and window.ras_pill.caption.text() == "On"
    window.autostart_pill.click()                                   # off without Unattended: nothing happens
    assert not window.autostart_pill.isChecked()
    window.auto_pill.click()
    assert window.autostart_pill.isEnabled() and window.autostart_pill.isChecked()
    window.auto_pill.click()
    assert not window.autostart_pill.isEnabled() and not window.autostart_pill.isChecked()
    assert all(p.toolTip() for p in switches) and all(f.toolTip() for f in fields)
    assert [window.load_combo.itemText(i) for i in range(window.load_combo.count())] == ["stress-ng", "mprime", "both"]
    labels = {label.text(): label.toolTip() for label in window.findChildren(QLabel)}
    assert labels["Load per attempt"] == window.time_spin.toolTip()           # the label tells it too
    infos = [w for w in window.findChildren(QWidget) if type(w).__name__ == "InfoButton"]
    assert infos == [window.unlock.legend_info]                         # only the cores' marks have one
    window.close()


def test_unlock_part_without_results(qapp, unlock_script):
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        assert unlock.gate_box.value.text() == "Not accepted"
        assert not unlock.install_pill.isEnabled()
        assert _wait_for(lambda: not unlock.runner.busy)
        assert "fake unlock: --status" in unlock.output.toPlainText()
    finally:
        window.close()


def test_one_page_with_the_unlock_under_the_bisect(qapp, unlock_script, gate_state):
    """One window, one page (owner, 20-11-2026, as CU Tools): the bisect's pills, numbers and switches, then the
    verdict and Install, Uninstall, Refresh, Root status and Re-check, the 8 cores with their i, and the log behind a
    Show logs / Hide logs button, hidden at the start."""
    gate_state(runs=all_passed())
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        window.show()
        assert _wait_for(lambda: not unlock.runner.busy)
        boxes = [unlock.gate_box, *unlock.pills]
        assert [b.value.text() for b in boxes] == ["Accepted", "Install", "Uninstall", "Refresh", "Root status",
                                                   "Re-check"]
        assert len({b.width() for b in boxes}) == 1 and sorted(boxes, key=lambda b: b.x()) == boxes
        assert unlock.install_pill.isEnabled() and unlock.gate_box.toolTip()
        assert window.auto_pill.mapTo(window, window.auto_pill.rect().topLeft()).y() < \
            unlock.gate_box.mapTo(window, unlock.gate_box.rect().topLeft()).y()
        assert window.width() >= bisect_window.WIDTH
        names = [name.text() for name, _cell in unlock.core_map._cells]
        marks = [cell.text() for _name, cell in unlock.core_map._cells]
        assert names == ["core0", "core1", "core2", "core4", "core5", "core6", "core3", "core7"]
        assert marks == ["stock"] * 6 + ["ok", "ok"]
        cell = unlock.core_map._cells[0][1]
        assert cell.height() >= unlock.core_map.CELL_HEIGHT and cell.width() >= 80
        assert unlock.core_map.y() < unlock.logs_button.y()
        assert "fails every time" in unlock.legend_info.text_
        assert unlock.output.isHidden()
        unlock.logs_button.click()
        assert not unlock.output.isHidden() and unlock.logs_button.text() == "Hide logs"
        unlock.recheck_pill.click()
        assert "Bisect results: accepted." in unlock.output.toPlainText()
        unlock.logs_button.click()
        assert unlock.output.isHidden() and unlock.logs_button.text() == "Show logs"
    finally:
        window.close()


def test_a_failed_install_shows_a_red_mark_not_a_message(qapp, unlock_script, monkeypatch):
    """A red ! with Check logs beside the logs button, as CU Tools; opening the log takes it away."""
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        window.show()
        assert _wait_for(lambda: not unlock.runner.busy)
        assert unlock.failed_label.isHidden()
        unlock._pending_action = "install"
        unlock._on_finished(1)
        assert not unlock.failed_label.isHidden() and "Check logs" in unlock.failed_label.text()
        assert unlock.failed_label.toolTip() == "Install failed (exit code 1): the log says why."
        assert unlock.output.isHidden() and warnings == []          # no message box, the log stays closed
        unlock.logs_button.click()
        assert unlock.failed_label.isHidden() and not unlock.output.isHidden()
    finally:
        window.close()


def test_hiding_the_log_gives_its_room_back(qapp, unlock_script):
    """Show logs, then Hide logs: the window is as tall as before and the cores stay where they were (owner,
    20-11-2026: CU Tools' rows spread over the log's room); a window made taller by hand keeps them in place too."""
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        window.show()
        assert _wait_for(lambda: not unlock.runner.busy)
        cells = lambda: [cell.y() for _name, cell in unlock.core_map._cells]  # noqa: E731
        height, before = window.height(), cells()
        unlock.logs_button.click()
        qapp.processEvents()
        assert window.height() > height
        unlock.logs_button.click()
        qapp.processEvents()
        assert window.height() == height and cells() == before
        window.resize(window.width(), height + 300)
        qapp.processEvents()
        assert cells() == before and unlock.core_map.height() == unlock.core_map.sizeHint().height()
    finally:
        window.close()
