# SPDX-License-Identifier: GPL-3.0-or-later
"""The window says whether the recorder runs, starts and stops it through the helper, and shows the minutes around a
time. The service is a fake here: the tests see the actions it would get."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from nexus_flight_recorder import main_window, service


class Fake:
    def __init__(self, **state):
        self.state, self.actions, self.problem = service.State(**state), [], ""

    def read(self):
        return self.state

    def run(self, action):
        self.actions.append(action)
        return self.problem


def window(recordings, fake):
    w = main_window.MainWindow(recordings, fake.read, fake.run)
    w.timer.stop()
    w.jobs = []
    w.worker.start = lambda job: w.jobs.append(job) or True         # kept: click() runs it on this thread
    return w


def click(w, pill):
    """A click, and the action it started brought to its end."""
    pill.click()
    while w.jobs:
        w._action_done(w.jobs.pop(0)())


def table(w, row):
    return [w.table.item(row, c).text() for c in range(4)]


def test_a_running_recorder(qapp, recordings):
    w = window(recordings, Fake(installed=True, running=True, at_boot=True, since="17:34"))
    assert w.since_box.value.text() == "17:34" and w.days_box.value.text() == "2 of 7"
    assert w.run_pill.text() == "Stop" and w.boot_pill.caption.text() == "On" and w.boot_pill.isEnabled()
    assert [w.day_box.itemText(i) for i in range(w.day_box.count())] == ["27-11-2026", "26-11-2026"]
    assert table(w, 5) == ["GPU clock", "1850 MHz", "1000 MHz", "1850 MHz"]
    assert "00:43:00 to 00:52:59" in w.busiest.text() and "steam (420 s)" in w.busiest.text()


def test_the_minutes_around_a_typed_time(qapp, recordings):
    w = window(recordings, Fake(installed=True, running=True))
    w.time_edit.setText("00:42")
    w.show_window()
    assert table(w, 5) == ["GPU clock", "1850 MHz", "1000 MHz", "1850 MHz"]
    assert w.table.horizontalHeaderItem(1).text() == "Last" and "00:40:00 to 00:47:00" in w.busiest.text()
    w.time_edit.setText("12:00")
    w.show_window()
    assert w.busiest.text() == "No lines were recorded in these minutes." and table(w, 5)[1:] == ["", "", ""]
    w.time_edit.setText("soon")
    w.show_window()
    assert "such as 00:46" in w.line.text()


def test_install_asks_first(qapp, recordings, monkeypatch):
    fake = Fake()
    w = window(recordings, fake)
    assert w.run_pill.text() == "Install" and not w.boot_pill.isEnabled() and w.since_box.value.text() == "—"
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No)
    click(w, w.run_pill)
    assert fake.actions == [] and asked[0].startswith("Install the flight recorder?\n\n")
    assert asked[0].endswith("You'll be asked for your password.")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    click(w, w.run_pill)
    assert fake.actions == ["install"]


def test_stop_start_and_at_boot(qapp, recordings):
    fake = Fake(installed=True, running=True, at_boot=True)
    w = window(recordings, fake)
    click(w, w.run_pill)
    fake.state = service.State(installed=True, running=False, at_boot=True)
    w.refresh()
    assert w.run_pill.text() == "Start"
    click(w, w.run_pill)
    click(w, w.boot_pill)
    fake.state = service.State(installed=True, running=True, at_boot=False)
    w.refresh()
    click(w, w.boot_pill)
    assert fake.actions == ["stop", "start", "boot-off", "boot-on"]


def test_a_failed_action_says_why_and_a_canceled_password_is_no_error(qapp, recordings):
    fake = Fake(installed=True, running=True)
    w = window(recordings, fake)
    fake.problem = "no such unit"
    click(w, w.run_pill)
    assert w.line.text() == "no such unit" and "color" in w.line.styleSheet()
    fake.problem = "Canceled."
    click(w, w.run_pill)
    assert w.line.text() == "Canceled." and "color" not in w.line.styleSheet()


def test_an_older_installed_recorder_is_replaced_at_start(qapp, recordings):
    fake = Fake(installed=True, running=False, current=False)
    w = window(recordings, fake)
    assert "differs from this checkout's" in w.line.text()
    click(w, w.run_pill)
    assert fake.actions == ["install"]


def test_the_service_state_and_its_commands(tmp_path):
    assert service.state(tmp_path) == service.State()
    lib = tmp_path / service.LIB
    lib.mkdir(parents=True)
    (lib / "recorder.py").write_bytes(service.RECORDER.read_bytes())
    answers = {"is-active": "active", "is-enabled": "enabled", "show": "Fri 2026-11-27 17:34:50 CET"}
    state = service.state(tmp_path, out=lambda argv: answers[argv[1]])
    assert state == service.State(True, True, True, "17:34", True)
    (lib / "recorder.py").write_text("# older\n")
    assert not service.state(tmp_path, out=lambda argv: "inactive").current
    assert service.command("stop") == ["pkexec", "/usr/bin/python3", "-I", str(service.HELPER), "stop"]
    install = service.command("install")
    assert install[4:6] == ["install", str(service.RECORDER)] and install[6].endswith("bazzite_console_core/sensors.py")
