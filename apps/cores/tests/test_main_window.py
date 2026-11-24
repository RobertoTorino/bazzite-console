# SPDX-License-Identifier: GPL-3.0-or-later
"""The one window opens offscreen with the suite's header and leads through the five steps: the scan, the stock cores,
the unlock and its restart, the new cores, and Install. The script runs in a fake session here: the tests see the
arguments it would get and play its events back. The cores online come from a fake sysfs reading."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QLabel, QMessageBox

from cores_bisect import __version__ as APP_VERSION
from cores_bisect import main_window, progress, resume
from cores_bisect.runner import UnlockRunner
from cores_bisect.session import ScriptSession
from cores_bisect.widgets import Pill, RoundedToolTip

SCRIPT = "/opt/test/ps5-cores-bisect.sh"
UNLOCK = "/opt/test/ps5-cores-unlock.sh"
STOCK = [0, 1, 2, 4, 5, 6]                         # the owner's boards: the unlock adds 3 and 7
ALL = list(range(8))
SCAN = {"mask": "0x77", "threads": "12", "cores": "0 1 2 4 5 6", "service": "not-found",
        "stress-ng": "/usr/bin/stress-ng", "load": "stress-ng"}
NEW_ITEMS = ["post-control", "core3", "core7", "combined"]


@pytest.fixture
def online(monkeypatch):
    """The cores sysfs reports online; the stock 6 unless a test says otherwise."""
    cores = list(STOCK)
    monkeypatch.setattr(progress, "online_cores", lambda cpu_dir=None: list(cores))
    return cores


@pytest.fixture
def results(home, tmp_path, monkeypatch, online):
    """Writes the script's files where the window and the gate read them; no boot service installed."""
    folder = home / ".local" / "share" / "ps5-cores-bisect"
    folder.mkdir(parents=True)
    monkeypatch.setattr(progress, "UNLOCK_UNIT", tmp_path / "ps5-cores-unlock.service")

    def write(phase="control", rounds=3, runs=(), this_boot=False, wizard="", new=True):
        (folder / "config").write_text(
            f"BASE_CORES=0 1 2 4 5 6\nCREATED=2026-11-24 04:34:07\nROUNDS={rounds}\nTIME=60\nLOAD_TOOL=stress-ng\n"
            f"RAS=0\nBASE_THREADS=12\n" + (f"NEW_CORES=3 7\n" if new and phase == "bisect" else "")
            + f"PHASE={phase}\n")
        (folder / "runs.tsv").write_text("".join(
            f"2026-11-24 04:35:08\tabcd1234\t{r}\t{item}\t0-11\t{outcome}\t0\t0\t63\t3493\t-\t60\tstress-ng\t0\n"
            for r, item, outcome in runs))
        (folder / "lastboot").write_text((progress.boot_id() if this_boot else "an-older-boot") + "\n")
        if wizard:
            (folder / "tools-wizard").write_text(wizard)
        return folder
    return write


@pytest.fixture
def installed(tmp_path):
    (tmp_path / "ps5-cores-unlock.service").write_text("[Unit]\n")


class Runs(list):
    sleeps: list[bool]


@pytest.fixture
def runs(monkeypatch):
    """The arguments of every script run, without running it; .sleeps says which ones block sleep."""
    calls = Runs()
    monkeypatch.setattr(ScriptSession, "start", lambda self, args, block_sleep=False: (
        calls.append(list(args)), sleeps.append(block_sleep)))
    calls.sleeps = sleeps = []
    return calls


@pytest.fixture
def unlock_runs(monkeypatch):
    """The arguments of every ps5-cores-unlock.sh run, as root without a password."""
    calls = []
    monkeypatch.setattr(UnlockRunner, "sudo_ready", staticmethod(lambda: True))
    monkeypatch.setattr(UnlockRunner, "run", lambda self, args, pw=None: calls.append(list(args)))
    return calls


@pytest.fixture(autouse=True)
def notes(monkeypatch):
    """The desktop notifications the window sends, without sending them."""
    sent = []
    monkeypatch.setattr(main_window.notify, "notify", lambda summary, body: sent.append((summary, body)) or True)
    return sent


@pytest.fixture(autouse=True)
def no_restart(monkeypatch):
    restarted = []
    monkeypatch.setattr(resume, "restart", lambda: restarted.append(1) or True)
    return restarted


@pytest.fixture
def restarts(home):
    """Same boot off: one restart per attempt."""
    from PyQt6.QtCore import QSettings
    QSettings().setValue("advanced/same_boot", "false")


@pytest.fixture
def yes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)


def control(outcome="PASS", rounds=3):
    return [(r, "control", outcome) for r in range(1, rounds + 1)]


def new_cores(bad=(), rounds=3, upto=None):
    attempts = [(r, item, "MCE" if item in bad else "PASS") for r in range(1, rounds + 1) for item in NEW_ITEMS]
    return attempts[:upto] if upto is not None else attempts


def window(**kwargs):
    return main_window.MainWindow(SCRIPT, UNLOCK, **kwargs)


def pills(w):
    return [p.value.text() for p in w.actions]


def primary(w):
    return [p.value.text() for p in w.actions if getattr(p, "primary", False)]


def test_the_suite_header(qapp, results):
    w = window()
    assert w.windowTitle() == f"PS5 Core Unlock {APP_VERSION}"
    assert [b.caption.text() for b in w.boxes] == ["Cores on now", "Boot unlock", "Attempts done", "Test"]
    assert [r.title.text() for r in w.step_boxes] == [
        "Step 1 · Scan", "Step 2 · Test the stock cores", "Step 3 · Unlock and restart",
        "Step 4 · Test the new cores", "Step 5 · Install"]


def test_a_new_window_starts_at_the_scan(qapp, home, online, runs):
    w = window()
    assert w.step == 0 and primary(w) == ["Scan"] and w.cores_box.value.text() == "6 of 8"
    w.pill("Scan").click()
    assert runs == [["--scan"]] and runs.sleeps == [False]


def test_a_scan_shows_the_board_and_offers_the_test(qapp, home, online):
    w = window()
    w.scan = dict(SCAN)
    w._render()
    assert "6 of 8 cores are on. Cores 3 and 7 are switched off." in w.text.text()
    assert "<b>0x77</b>" in w.text.text() and primary(w) == ["Start test"]
    assert w.core_map.states == ["on", "on", "on", "wait", "on", "on", "on", "wait"]


@pytest.mark.parametrize("key, value, says", [
    ("mask", "0xff", "an unlock is active"),
    ("mask", "0x33", "very likely defective"),
    ("stress-ng", "-", "stress-ng was not found"),
])
def test_what_blocks_the_test(qapp, home, online, key, value, says):
    w = window()
    w.scan = dict(SCAN, **{key: value})
    w._render()
    assert says in w.text.text() and not w.pill("Start test").isEnabled()


def test_start_asks_once_then_tests_the_stock_cores(qapp, home, online, runs, yes):
    w = window()
    w.scan = dict(SCAN)
    w._render()
    w.pill("Start test").click()
    assert runs == [["-t", "600", "-r", "3", "--same-boot"]] and runs.sleeps == [True]
    assert not resume.armed()                          # one boot: nothing to come back for


def test_with_restarts_the_window_comes_back(qapp, home, online, runs, yes, restarts):
    w = window()
    w.scan = dict(SCAN)
    w._render()
    w.pill("Start test").click()
    assert runs == [["-t", "600", "-r", "3"]] and resume.armed()


def test_a_started_test_keeps_its_own_settings(qapp, results, runs):
    results(runs=control()[:1])                        # the run started with 60 s per attempt
    w = window()
    assert w.step == 1 and w.time_spin.value() == 60
    w.pill("Go on").click()
    assert runs == [["-t", "60", "-r", "3", "--same-boot"]]


def test_failed_stock_cores_stop_at_step_2(qapp, results, notes):
    results(runs=[(1, "control", "MCE")])
    w = window()
    assert w.step == 1 and w.step_boxes[1].caption.text() == "Stopped"
    assert "machine-check errors" in w.text.text() and primary(w) == ["Stay at 6"]
    w.job = "test"
    w._on_finished(0)
    assert notes and notes[-1][0] == "Core test stopped"


def test_passed_stock_cores_offer_the_unlock(qapp, results, runs, yes, notes):
    results(runs=control())
    w = window()
    assert w.step == 2 and primary(w) == ["Unlock"] and w.state_box.value.text() == "Ready"
    w.job = "test"
    w._on_finished(0)
    assert notes[-1] == ("Stock cores passed", "All 3 rounds passed. Next: Unlock, in step 3 of Core Unlock.")
    w.pill("Unlock").click()
    assert runs == [["-t", "60", "-r", "3", "--same-boot"]] and w.job == "unlock"


def test_only_a_click_on_unlock_answers_yes(qapp, results, monkeypatch):
    results(runs=control())
    w = window()
    sent = []
    monkeypatch.setattr(w.session, "send", sent.append)
    w.job = "test"
    w._on_notice(["ask", "unlock"])
    w.job = "unlock"
    w._on_notice(["ask", "unlock"])
    w._on_notice(["ask", "restart"])
    assert sent == ["n", "y", "n"]                      # the window restarts the board itself


def test_after_the_unlock_the_window_restarts_and_comes_back(qapp, results, no_restart):
    results(runs=control())
    w = window()
    w.job = "unlock"
    w._on_notice(["unlocked"])
    results(phase="unlock-pending", runs=control())
    w._on_finished(0)
    assert w.countdown == main_window.RESTART_SECS and resume.armed()
    assert "restarts by itself" in w.todo.text() and primary(w) == ["Restart now"]
    w.pill("Restart now").click()
    assert no_restart == [1]


def test_a_paused_unlock_restart_offers_restart(qapp, results):
    results(phase="unlock-pending", runs=control(), wizard=f"unlock_boot={progress.boot_id()}\n")
    w = window()
    assert w.step == 2 and primary(w) == ["Restart"]
    assert "Restart, don't switch off." in w.text.text()


def test_cores_gone_after_a_power_off_offer_the_unlock_again(qapp, results):
    results(phase="unlock-pending", runs=control(), wizard="unlock_boot=an-older-boot\n")
    w = window()
    assert w.step == 2 and primary(w) == ["Unlock"]
    assert "did not come up" in w.text.text()


def test_after_the_restart_the_new_cores_are_next(qapp, results, online, runs, yes):
    online[:] = ALL
    results(phase="unlock-pending", runs=control())
    resume.arm()
    w = window()
    w._resume()
    assert not resume.armed() and w.countdown == 0      # the window shows the next step and waits for you
    assert w.step == 3 and primary(w) == ["Start"]
    assert "The test of cores 3 and 7 takes about 20 minutes." in w.todo.text()
    assert w.count_box.value.text() == "0 of 12" and w.state_box.value.text() == "Ready"
    assert w.cores_box.value.text() == "8 of 8"
    assert w.core_map.states == ["on", "on", "on", "wait", "on", "on", "on", "wait"]
    w.pill("Start").click()
    assert runs == [["-t", "60", "-r", "3", "--same-boot"]]


def test_the_new_cores_go_on_or_restart_first(qapp, results, online, runs, restarts):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores(upto=4))
    w = window()
    assert w.step == 3 and primary(w) == ["Go on"] and w.next_label.text() == "Next: round 2, post-control."
    results(phase="bisect", runs=control() + new_cores(upto=4), this_boot=True)
    assert window().pill("Restart") is not None


def test_after_a_login_the_test_goes_on(qapp, results, online, runs, restarts):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores(upto=4))
    resume.arm()
    w = window()
    w._resume()
    assert w.countdown == main_window.GO_ON_SECS
    w.pill("Go on now").click()
    assert runs == [["-t", "60", "-r", "3"]]


def test_a_power_off_during_the_test_turns_the_cores_on_again(qapp, results, unlock_runs, yes, online):
    results(phase="bisect", runs=control() + new_cores(upto=4))
    resume.arm()
    w = window()
    w._resume()
    assert w.countdown == 0 and primary(w) == ["Unlock"] and "full power off" in w.text.text()
    w.pill("Unlock").click()
    assert unlock_runs == [["--apply"]]
    w._on_unlock_finished(0)
    assert w.countdown == main_window.RESTART_SECS and resume.armed()


def test_healthy_cores_can_be_installed(qapp, results, online, unlock_runs, yes, notes):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores())
    w = window()
    assert w.step == 4 and primary(w) == ["Install"]
    w.job = "test"
    w._on_finished(0)
    assert notes[-1][0] == "Core test passed" and "Install, in step 5" in notes[-1][1]
    w.pill("Install").click()
    assert unlock_runs == [["--install"]]


def test_installed_with_all_cores_on_is_finished(qapp, results, online, installed):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores())
    w = window()
    assert w.finished_bar.isVisibleTo(w) and "runs all 8 cores at every boot" in w.finished_bar.text()
    assert all(r.caption.text() == "Done" for r in w.step_boxes)
    assert w.boot_box.value.text() == "Installed" and pills(w) == ["Uninstall", "Start over"]


def test_a_failing_core_advises_the_stock_cores(qapp, results, online, notes):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores(bad=("core7",)))
    w = window()
    assert w.step == 4 and primary(w) == ["Stay at 6"] and "Failed every time: core7" in w.text.text()
    assert w.core_map.states[3] == "ok" and w.core_map.states[7] == "bad"
    w.job = "test"
    w._on_finished(0)
    assert notes[-1][0] == "Core test done" and "core7" in notes[-1][1]


def test_staying_stock_needs_a_power_off_then_is_finished(qapp, results, online, yes):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores(bad=("core7",)))
    w = window()
    w.pill("Stay at 6").click()
    assert not w.finished_bar.isVisibleTo(w) and "Switch the board fully off once" in w.todo.text()
    online[:] = STOCK
    w.refresh()
    assert w.finished_bar.isVisibleTo(w) and "stays at the stock cores" in w.finished_bar.text()


def test_the_rows_say_what_came_out(qapp, results, online):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores())
    w = window()
    lines = [r.line.text() for r in w.step_boxes[:4]]
    assert lines == ["6 of 8 cores were on. Cores 3 and 7 were switched off.",
                     "Passed 3 of 3 rounds on the 6 stock cores.", "Cores 3 and 7 came on with the unlock.",
                     "Cores 3 and 7 passed, alone and together."]


def test_the_scripts_questions(qapp, results, monkeypatch):
    results(phase="bisect", runs=control())
    w = window()
    sent = []
    monkeypatch.setattr(w.session, "send", sent.append)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    for question in ("reset", "crash", "settings", "something"):
        w._on_notice(["ask", question])
    assert sent == ["y", "n", "n", ""]


def test_the_live_attempt(qapp, results, online):
    online[:] = ALL
    results(phase="bisect", runs=control())
    w = window()
    w.job = "test"
    busy = type(w.session).busy
    try:
        type(w.session).busy = property(lambda self: True)
        w._on_notice(["attempt", "1", "core3", "3,11"])
        w._on_notice(["phase", "stress-ng"])
        w._on_notice(["load", "40", "60", "63", "3493"])
        assert w.hint.text() == "Now: round 1, core3 · stress-ng 40 of 60 s · 63 °C · 3493 MHz"
        assert w.core_map.states[3] == "now" and w.core_map.states[7] == "wait"
        assert "Nothing to do. The test runs by itself" in w.todo.text() and pills(w) == ["Stop"]
        assert w.step_boxes[3].caption.text() == "Running"
    finally:
        type(w.session).busy = busy


def test_quiet_between_attempts(qapp, results, online, runs, notes):
    online[:] = ALL
    results(phase="bisect", runs=control() + new_cores(upto=4))
    w = window()
    w.job = "test"
    w._on_finished(0)
    w.job = "test"
    w._on_finished(130)                                 # Stop, pressed yourself
    assert notes == []


def test_only_a_test_blocks_sleep(qapp, results, runs, yes):
    results(runs=control())
    w = window()
    w._scan()
    w.job = ""
    w._run_test()
    assert runs.sleeps == [False, True]


def test_the_window_never_opens_higher_than_the_screen(qapp, results, monkeypatch):
    monkeypatch.setattr(main_window.MainWindow, "_room", lambda self: 500)
    w = window()
    assert w.height() <= 500
    w.show_details(True)
    w.show_advanced(True)
    assert w.height() <= 500 and w.body.sizeHint().height() > 500  # the page scrolls instead


def test_details_and_advanced_are_pills_on_the_actions_row(qapp, results):
    """No "Other actions" label: the step's pills on the left, Details and Advanced as pills at the right end of the
    same row (owner, 24-11-2026). Under the name they say Show or Hide."""
    w = window()
    assert not [label for label in w.findChildren(QLabel) if label.text() == "Other actions"]
    assert isinstance(w.details_button, Pill) and isinstance(w.advanced_button, Pill)
    assert w.details_button.caption.text() == w.advanced_button.caption.text() == "Show"
    w.details_button.click()
    assert w.output.isVisibleTo(w) and w.details_button.caption.text() == "Hide"
    w.advanced_button.click()
    assert w.advanced.isVisibleTo(w) and w.advanced_button.caption.text() == "Hide"


def test_the_window_opens_at_its_width_and_fits_its_page_once_shown(qapp, results, monkeypatch):
    """Never at a wider saved width, and as high as its page after it shows: before that, the page doesn't know its
    height yet (owner, 24-11-2026: a first window cut half of it off)."""
    monkeypatch.setattr(main_window.MainWindow, "_room", lambda self: 5000)
    w = window()
    w.resize(1200, 300)
    w.close()                                                   # saves the wider geometry
    w = window()
    w.show()
    qapp.processEvents()
    assert w.width() == main_window.WIDTH
    assert w.height() == w.body.sizeHint().height() + 2
    w.close()


def test_all_cores_on_without_results_opens(qapp, home, online):
    """All 8 cores on and no results, as after Start over with the boot service installed: the window opens."""
    online[:] = ALL
    w = window()
    assert w.cores_box.value.text() == "8 of 8"


def test_tooltips_have_rounded_corners(qapp, home, online):
    """The tooltips as the suite's other apps show them: a rounded box on the window's dark background."""
    tip = RoundedToolTip.install(qapp)
    try:
        w = window()
        tip.show_text(QPoint(10, 10), "Shows or hides what the scripts print.", w.details_button)
        assert tip.popup.isVisible() and tip.label.text() == "Shows or hides what the scripts print."
        assert "border-radius:6px" in tip.label.styleSheet() and "palette(window)" in tip.label.styleSheet()
    finally:
        tip.hide()
        RoundedToolTip.uninstall()


def test_every_step_has_one_thing_to_do(qapp, results, online):
    """The current step's row names one thing to do, and its pill sits on that row."""
    for setup in ("stock", "unlock", "cores", "install"):
        online[:] = ALL if setup in ("cores", "install") else STOCK
        if setup == "stock":
            results(runs=control()[:1])
        elif setup == "unlock":
            results(runs=control())
        elif setup == "cores":
            results(phase="unlock-pending", runs=control())
        else:
            results(phase="bisect", runs=control() + new_cores())
        w = window()
        assert len(primary(w)) == 1 and w.step_boxes[w.step].slot.count() == 1, setup
