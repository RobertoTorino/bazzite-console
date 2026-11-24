# SPDX-License-Identifier: GPL-3.0-or-later
"""The GPU sweep window opens offscreen with the suite's header and leads through the five steps: the scan, the
control, the clock ladder, the voltage ladder and Install. The script runs in a fake session here: the tests see the
arguments it would get and play its events back. The governor's config and the results sit in a temp folder, so
nothing reads this machine's governor."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox

from conftest import SHIPPED
from gpu_governor.sweep import main_window, progress, resume
from gpu_governor.sweep.session import ScriptSession

SCAN = {"gpu": "/sys/class/drm/card1/device", "governor": "smu", "service": "active",
        "config": "/etc/cyan-skillfish-governor-smu/config.toml", "load": "memtest_vulkan", "top": "2000 900",
        "points": "3", "snapshot": "none", "saved-governor": ""}
PLAN = ["control", "oc:2050", "oc:2100", "oc:2150", "uv:875", "uv:850", "uv:825"]
POINTS = {"control": (2000, 900), "oc:2050": (2050, 900), "oc:2100": (2100, 900), "oc:2150": (2150, 900),
          "uv:875": (2000, 875), "uv:850": (2000, 850), "uv:825": (2000, 825)}


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch, qapp):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local/share"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    for fmt in (QSettings.Format.NativeFormat, QSettings.Format.IniFormat):
        QSettings.setPath(fmt, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    QSettings().clear()
    etc = tmp_path / "etc"
    (etc / "cyan-skillfish-governor-smu").mkdir(parents=True)
    (etc / "cyan-skillfish-governor-smu" / "config.toml").write_text(SHIPPED)
    monkeypatch.setattr(progress, "ETC", etc)
    monkeypatch.setattr(progress, "service_active", lambda governor: governor == "smu")
    monkeypatch.setattr(resume, "restart", lambda: True)
    return home


class Calls(list):
    pass


@pytest.fixture
def started(monkeypatch):
    """The fake session: start() records the arguments and says the script runs, finish() ends it."""
    calls = Calls()

    def start(self, args, block_sleep=False):
        calls.append(list(args))
        self._running = True
    monkeypatch.setattr(ScriptSession, "start", start)
    monkeypatch.setattr(ScriptSession, "send", lambda self, text: calls.append(["send", text]))
    return calls


def finish(window, code=0):
    window.session._running = False
    window.session.finished.emit(code)


@pytest.fixture
def results(sandbox):
    folder = sandbox / ".local/share/ps5-gpu-sweep"

    def write(runs=(), wizard="", installed=""):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "governor-config.orig").write_text(SHIPPED)
        (folder / "config").write_text("CREATED=2026-11-24 16:00:00\nGOVERNOR=smu\nROUNDS=2\nTIME=60\nOC_VOLT=900\n"
                                       "SWEEP=oc,uv,\nMAX_FREQ=2150\nMIN_VOLT=825\nFREQ_STEP=50\nVOLT_STEP=25\n"
                                       + (f"INSTALLED={installed}\n" if installed else ""))
        (folder / "runs.tsv").write_text("".join(
            f"2026-11-24 16:01:00\tabcd1234\t{r}\t{item}\t{POINTS[item][0]}\t{POINTS[item][1]}\t{outcome}\t0\t0\t70\t"
            f"{POINTS[item][0]}\t99\t-\n" for r, item, outcome in runs))
        if wizard:
            (folder / "sweep-wizard").write_text(wizard)
        return folder
    return write


def rounds(*items_outcomes):
    return [(r, item, outcome) for item, outcome in items_outcomes for r in (1, 2)]


ALL_DONE = rounds(("control", "PASS"), ("oc:2050", "PASS"), ("oc:2100", "PASS"), ("oc:2150", "FAULT"),
                  ("uv:875", "PASS"), ("uv:850", "PASS"), ("uv:825", "ERRORS"))


def window():
    w = main_window.MainWindow("/opt/test/ps5-gpu-sweep.sh")
    w.show()
    return w


def answer(monkeypatch, button=QMessageBox.StandardButton.Yes):
    asked = []

    def question(*args, **kwargs):
        asked.append(args[2])
        return button
    monkeypatch.setattr(QMessageBox, "question", question)
    return asked


def test_it_opens_at_the_scan_with_the_header(started):
    w = window()
    assert w.windowTitle().startswith("PS5 GPU Manager · GPU sweep")
    assert w.step == 0 and w.width() >= main_window.WIDTH
    assert [b.title.text() for b in w.step_boxes] == [f"Step {i + 1} · {s}" for i, s in enumerate(main_window.STEPS)]
    assert w.governor_box.value.text() == "smu" and w.top_box.value.text() == "2000 MHz"
    assert w.top_box.caption.text() == "Top point now, 900 mV" and w.width() == main_window.WIDTH
    assert w.pill("Details") is None and w.details_button.caption.text() == "Show"
    w.pill("Scan").clicked.emit()
    assert started == [["--scan"]]


def test_the_scan_offers_start_and_names_what_blocks_it(started, monkeypatch):
    w = window()
    w._scan()
    for key, value in SCAN.items():
        w._on_notice(["scan", key, *value.split()])
    finish(w)
    assert w.pill("Start").isEnabled()
    assert "cyan-skillfish-governor-smu" in w.text.text() and "2000 MHz @ 900 mV" in w.text.text()
    # The plan of the default Advanced options: the control, 2050-2200 MHz, then 875 and 850 mV.
    assert [w.ladder.item(r, 0).text() for r in range(w.ladder.rowCount())] == [
        "Control", "Clock +50 MHz", "Clock +100 MHz", "Clock +150 MHz", "Clock +200 MHz", "Voltage −25 mV",
        "Voltage −50 mV"]
    asked = answer(monkeypatch)
    w.pill("Start").clicked.emit()
    assert asked[0].startswith("Test your config's top point?")
    assert started[-1][-2:] == ["--only", "control"] and "-t" in started[-1]
    w._on_notice(["ask", "start"])
    assert started[-1] == ["send", "y"]

    w2 = window()
    w2._scan()
    for key, value in {**SCAN, "load": "-", "service": "inactive"}.items():
        w2._on_notice(["scan", key, *value.split()])
    finish(w2)
    assert not w2.pill("Start").isEnabled()
    assert "memtest_vulkan" in w2.text.text() and "Service page" in w2.text.text()


def test_the_control_passes_and_the_clock_ladder_is_next(started, results, monkeypatch):
    results(rounds(("control", "PASS")))
    w = window()
    assert w.step == 2 and w.p.state("control") == "passed"
    assert w.step_boxes[1].caption.text() == "Done"
    assert "Passed 2 of 2 rounds at 2000 MHz @ 900 mV." in w.step_boxes[1].line.text()
    asked = answer(monkeypatch)
    w.pill("Start").clicked.emit()
    assert asked[0].startswith("Raise the clock one step at a time?")
    assert started[-1][-2:] == ["--only", "oc"] and "--max-freq" in started[-1]
    assert not w.max_freq_spin.isEnabled()                 # a started sweep keeps its ladder


def test_a_failed_control_stops_the_sweep(started, results):
    results([(1, "control", "PASS"), (2, "control", "CRASH-LOAD")])
    w = window()
    assert w.step == 1 and w.step_boxes[1].caption.text() == "Stopped"
    assert w.pill("Start") is None and w.pill("Go on") is None
    assert "CRASH-LOAD" in w.text.text()


def test_the_ladder_table_shows_every_round(started, results):
    results(rounds(("control", "PASS"), ("oc:2050", "PASS")) + [(1, "oc:2100", "FAULT")])
    w = window()
    assert w.step == 2 and w.pill("Go on") is not None
    rows = {w.ladder.item(r, 0).text(): [w.ladder.item(r, c).text() for c in range(1, 5)]
            for r in range(w.ladder.rowCount())}
    assert rows["Clock +50 MHz"] == ["2050 MHz", "900 mV", "Passed", "Passed"]
    assert rows["Clock +100 MHz"] == ["2100 MHz", "900 mV", "FAULT", "Later"]
    assert rows["Voltage −25 mV"] == ["2000 MHz", "875 mV", "Later", "Later"]


def test_install_writes_the_margin_step_and_drops_higher_points(started, results, monkeypatch):
    results(ALL_DONE)
    w = window()
    assert w.step == 4
    assert "2050 MHz @ 875 mV" in w.text.text() and "2000 MHz @ 900 mV" in w.text.text()
    asked = answer(monkeypatch)
    w.pill("Install").clicked.emit()
    assert asked[0].startswith("Write the best step into the governor's config?")
    assert "These points go, as their voltage is above 875 mV: 2000 MHz @ 900 mV." in asked[0]
    assert started[-1] == ["--install"]
    w._on_notice(["ask", "install"])
    assert started[-1] == ["send", "y"]


def test_installed_and_kept_are_finished(started, results):
    results(ALL_DONE, installed="2050 875 /etc/cyan-skillfish-governor-smu/config.toml.bak-20261124-170000")
    w = window()
    assert w.finished_bar.isVisible() and "best step is in the governor's config" in w.finished_bar.text()
    assert "Backups page" in w.text.text()
    results(ALL_DONE, wizard="keep=1\n")
    w.refresh()
    assert w.finished_bar.isVisible() and "Your own config stays" in w.finished_bar.text()


def test_one_boot_each_restarts_and_goes_on_after_the_login(started, results, monkeypatch):
    results(rounds(("control", "PASS")) + [(1, "oc:2050", "PASS")])
    w = window()
    w.per_boot_pill.setChecked(True)
    w._go_on("oc")
    assert "--per-boot" in started[-1] and resume.armed()
    w._on_notice(["restart-first"])
    finish(w)
    assert w.countdown_action == "restart" and w.pill("Restart now") is not None
    w._pause()
    assert not resume.armed() and w.countdown == 0


def test_a_crash_is_asked_in_the_window(started, results, monkeypatch):
    folder = results(rounds(("control", "PASS")))
    (folder / "pending").write_text("1 oc:2050 2050 900 an-earlier-boot\n")
    w = window()
    asked = answer(monkeypatch, QMessageBox.StandardButton.No)
    w._go_on("oc")
    w._on_notice(["ask", "crash"])
    assert asked[0].startswith("Did the board freeze, crash or restart by itself?")
    assert "Round 1, Clock +50 MHz did not finish." in asked[0]
    assert started[-1] == ["send", "n"]
