# SPDX-License-Identifier: GPL-3.0-or-later
"""The one window opens offscreen with the suite's header; its bisect part turns its form into the right command, and
its unlock part shows the gate's verdict and the unlock script's --status output, in the log behind its button."""

from __future__ import annotations

import shlex

import pytest
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QLabel, QMessageBox, QPushButton, QWidget

from cu_bisect import __version__ as BISECT_VERSION
from cu_bisect import main_window as bisect_window

SCRIPT = "/opt/test/ps5-cu-bisect.sh"
UNLOCK = "/opt/test/ps5-cu-unlock.sh"            # not there: --status only fails, in the log


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
    title = next(label for label in labels if "v" + BISECT_VERSION in label.text())
    return logo, title


@pytest.fixture
def started(monkeypatch):
    """Runs Start without a terminal: the command it would open, and Yes to its summary."""
    commands = []
    monkeypatch.setattr(bisect_window, "launch_in_terminal", commands.append)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    return commands


def test_bisect_window_has_the_suite_header(qapp):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    logo, title = _header(window)
    assert logo.pixmap().width() == 96
    assert "PS5 CU Tools" in title.text()
    window.close()


def test_start_with_the_defaults(qapp, started):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.start_pill.click()
    assert [shlex.split(c) for c in started] == [["bash", SCRIPT, "-t", "180", "-r", "3"]]


def test_start_with_a_custom_baseline_and_switches(qapp, started):
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.time_spin.setValue(300)
    window.baseline_combo.setCurrentText("Custom...")
    window.baseline_custom.setText("0x0f,0x0f,0x0f,0x0f")
    window.control_only_pill.setChecked(True)
    window.rounds_spin.setValue(1)
    window.same_boot_pill.setChecked(True)
    window.no_watch_pill.setChecked(True)
    window.start_pill.click()
    assert shlex.split(started[0])[2:] == ["-t", "300", "-r", "1", "--baseline", "0x0f,0x0f,0x0f,0x0f",
                                           "--control-only", "--same-boot", "--no-watch"]


def test_unattended_offers_the_autostart_service(qapp, started, monkeypatch):
    installed = []
    monkeypatch.setattr("cu_bisect.service.install", lambda *args: installed.append(args))
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    assert not window.autostart_pill.isEnabled()
    window.auto_pill.setChecked(True)
    assert window.autostart_pill.isEnabled() and window.autostart_pill.isChecked()
    window.start_pill.click()
    assert installed == [(SCRIPT, 180, 3)]
    assert "--auto" in shlex.split(started[0])


def test_invalid_options_start_nothing(qapp, started, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda _p, _t, text: warnings.append(text))
    window = bisect_window.MainWindow(SCRIPT, UNLOCK)
    window.baseline_combo.setCurrentText("Custom...")
    window.baseline_custom.setText("0x07")
    window.start_pill.click()
    assert started == [] and "4 masks" in warnings[0]


def test_unlock_part_without_results(qapp, unlock_script, state):
    state()
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        assert unlock.gate_box.value.text() == "Not accepted"
        assert not unlock.install_pill.isEnabled()
        assert _wait_for(lambda: not unlock.runner.busy)
        assert "fake unlock: --status" in unlock.output.toPlainText()
    finally:
        window.close()


def test_unlock_part_accepts_a_retested_mask(qapp, unlock_script, state):
    state("0x1f,0x1f,0x1f,0x1f", rounds=1, runs=[(1, "control", "PASS")])
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        assert _wait_for(lambda: not unlock.runner.busy)
        assert unlock.gate_box.value.text() == "Accepted"
        assert unlock.install_pill.isEnabled()
    finally:
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
    text = bisect_window.HelpDialog._help_text(str(Path(bisect_window.__file__).parents[1] / "ps5-cu-bisect.sh"))
    assert text.startswith("ps5-cu-bisect.sh - ") and "Usage:" in text and "SPDX" not in text
    window.close()


def test_the_header_has_four_pills_in_order(qapp):
    """Help, Start, Show status and Reset under the title, of one width; no About (owner, 19-11-2026)."""
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
    fields = [window.time_spin, window.rounds_spin, window.baseline_combo]
    assert len({field.mapTo(window, field.rect().center()).y() for field in fields}) == 1
    switches = [window.control_only_pill, window.same_boot_pill, window.auto_pill, window.autostart_pill,
                window.no_watch_pill]
    assert [p.value.text() for p in switches] == ["Control only", "Same boot", "Unattended", "Auto resume",
                                                  "No watch"]
    assert all(p.caption.text() == "Off" for p in switches) and not window.autostart_pill.isEnabled()
    window.no_watch_pill.click()
    assert window.no_watch_pill.isChecked() and window.no_watch_pill.caption.text() == "On"
    window.autostart_pill.click()                                   # off without Unattended: nothing happens
    assert not window.autostart_pill.isChecked()
    window.auto_pill.click()
    assert window.autostart_pill.isEnabled() and window.autostart_pill.isChecked()
    window.auto_pill.click()
    assert not window.autostart_pill.isEnabled() and not window.autostart_pill.isChecked()
    assert all(p.toolTip() for p in switches) and all(f.toolTip() for f in fields)
    labels = {label.text(): label.toolTip() for label in window.findChildren(QLabel)}
    assert labels["Load per attempt"] == window.time_spin.toolTip()           # the label tells it too
    infos = [w for w in window.findChildren(QWidget) if type(w).__name__ == "InfoButton"]
    assert infos == [window.unlock.preview_info]                        # only Preview a mask has one
    window.close()


def test_one_page_with_the_unlock_under_the_bisect(qapp, unlock_script, state):
    """One window, one page (owner, 19-11-2026): the bisect's pills, numbers and switches, then the verdict and
    Install, Uninstall, Refresh and Re-check, the WGP rows, the preview with its i, and the log behind a Show logs /
    Hide logs button, hidden at the start."""
    state("0x1f,0x1f,0x1f,0x1f", rounds=1, runs=[(1, "control", "PASS")])
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        window.show()
        assert _wait_for(lambda: not unlock.runner.busy)
        boxes = [unlock.gate_box, unlock.install_pill, unlock.uninstall_pill, unlock.status_pill,
                 unlock.recheck_pill]
        assert [b.value.text() for b in boxes] == ["Accepted", "Install", "Uninstall", "Refresh", "Re-check"]
        assert len({b.width() for b in boxes}) == 1 and sorted(boxes, key=lambda b: b.x()) == boxes
        assert window.no_watch_pill.mapTo(window, window.no_watch_pill.rect().topLeft()).y() < \
            unlock.gate_box.mapTo(window, unlock.gate_box.rect().topLeft()).y()
        assert [b.text() for b in window.findChildren(QPushButton)] == ["Show logs"]   # the only button
        assert window.width() >= bisect_window.WIDTH and unlock.gate_box.toolTip()
        cell = unlock.cu_map._cells[0][0]
        assert cell.height() >= unlock.cu_map.CELL_HEIGHT and cell.width() >= 110
        assert unlock.cu_map.y() < unlock.mask_preview_input.y() < unlock.logs_button.y()
        assert "0x0f" in unlock.preview_info.text_
        assert unlock.output.isHidden()
        unlock.logs_button.click()
        assert not unlock.output.isHidden() and unlock.logs_button.text() == "Hide logs"
        unlock.recheck_pill.click()
        assert "Bisect results: accepted." in unlock.output.toPlainText()
        unlock.logs_button.click()
        assert unlock.output.isHidden() and unlock.logs_button.text() == "Show logs"
        unlock.mask_preview_input.setText("0x1f,0x1f,0x0f,0x1f")
        assert "not installable" in unlock.mask_preview_label.text()
    finally:
        window.close()


def test_a_failed_install_shows_a_red_mark_not_a_message(qapp, unlock_script, state, monkeypatch):
    """A red ! with Check logs beside the logs button (owner, 19-11-2026); opening the log takes it away."""
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))
    state()
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


def test_hiding_the_log_gives_its_room_back(qapp, unlock_script, state):
    """Show logs, then Hide logs: the window is as tall as before and the WGP rows stay together (owner, 20-11-2026:
    the rows spread over the log's room); a window made taller by hand keeps them together too."""
    state()
    window = bisect_window.MainWindow(SCRIPT, str(unlock_script))
    unlock = window.unlock
    try:
        window.show()
        assert _wait_for(lambda: not unlock.runner.busy)
        rows = lambda: [unlock.cu_map._cells[r][0].y() for r in range(4)]  # noqa: E731
        height, before = window.height(), rows()
        unlock.logs_button.click()
        qapp.processEvents()
        assert window.height() > height
        unlock.logs_button.click()
        qapp.processEvents()
        assert window.height() == height and rows() == before
        window.resize(window.width(), height + 300)
        qapp.processEvents()
        assert rows() == before and unlock.cu_map.height() == unlock.cu_map.sizeHint().height()
    finally:
        window.close()
