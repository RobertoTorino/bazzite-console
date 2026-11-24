# SPDX-License-Identifier: GPL-3.0-or-later
"""The one window opens offscreen with the suite's header and leads through the four steps: the scan, the safety
check (--only control), each WGP, and the choice of 24, 32 or 40 CUs with its combined test and Install. The script
runs in a fake session here: the tests see the arguments it would get and play its events back."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QLabel, QMessageBox

from cu_bisect import __version__ as BISECT_VERSION
from cu_bisect import gate, main_window, progress, resume
from cu_bisect.session import ScriptSession
from cu_bisect.widgets import Pill, RoundedToolTip

SCRIPT = "/opt/test/ps5-cu-bisect.sh"
UNLOCK = "/opt/test/ps5-cu-unlock.sh"
STOCK = "0x07,0x07,0x07,0x07"
WGPS = [f"{row}.WGP{b}" for row in progress.ROWS for b in (3, 4)]
SCAN = {"live": STOCK, "at-boot": "no", "service": "not-found", "load": "memtest_vulkan", "gov-max": "1500",
        "sysfs": "yes"}


@pytest.fixture
def results(home, tmp_path, monkeypatch):
    """Writes the script's files where both the window and the gate read them; no boot unlock installed."""
    folder = home / ".local" / "share" / "ps5-cu-bisect"
    folder.mkdir(parents=True)
    for name, value in (("STATE_DIR", folder), ("CONFIG", folder / "umr-config"), ("RUNS", folder / "umr-runs.tsv"),
                        ("PENDING", folder / "umr-pending")):
        monkeypatch.setattr(gate, name, value)
    monkeypatch.setattr(progress, "UNLOCK_MASKS", tmp_path / "etc-masks")

    def write(base=STOCK, rounds=3, runs=(), control_only=0, this_boot=False, wizard=""):
        (folder / "umr-config").write_text(f"BASE={base}\nROUNDS={rounds}\nTIME=180\nCONTROL_ONLY={control_only}\n")
        (folder / "umr-runs.tsv").write_text("".join(
            f"2026-11-23 21:00:00\tabcd1234\t{r}\t{item}\t{base}\t{outcome}\t0\t0\t-\t60\t1500\t90\t-\n"
            for r, item, outcome in runs))
        (folder / "umr-lastboot").write_text((progress.boot_id() if this_boot else "an-older-boot") + "\n")
        if wizard:
            (folder / "tools-wizard").write_text(wizard)
        return folder
    return write


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


@pytest.fixture(autouse=True)
def notes(monkeypatch):
    """The desktop notifications the window sends, without sending them."""
    sent = []
    monkeypatch.setattr(main_window.notify, "notify", lambda summary, body: sent.append((summary, body)) or True)
    return sent


@pytest.fixture
def restarts(home):
    """Same boot off: one restart per attempt, as for testing a failing WGP again."""
    from PyQt6.QtCore import QSettings
    QSettings().setValue("advanced/same_boot", "false")


@pytest.fixture
def yes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)


def full(bad=()):
    return [(r, "control", "PASS") for r in (1, 2, 3)] + [
        (r, item, "FAULT" if item in bad else "PASS") for r in (1, 2, 3) for item in WGPS]


def window(**kwargs):
    return main_window.MainWindow(SCRIPT, UNLOCK, **kwargs)


def pills(w):
    return [(p.value.text(), p.isEnabled()) for p in w.actions]


def test_the_suite_header(qapp, results):
    w = window()
    labels = w.findChildren(QLabel)
    logo = next(label for label in labels if label.pixmap() is not None and not label.pixmap().isNull())
    assert logo.pixmap().width() == 96
    assert any("PS5 CU Unlock" in label.text() and "v" + BISECT_VERSION in label.text() for label in labels)
    assert [b.caption.text() for b in w.boxes] == ["Active now", "Boot unlock", "Attempts done", "Test"]
    assert "background" in w.info.styleSheet()                  # the filled info symbol
    assert w.refresh_button.text() == "\u21bb" and w.refresh_button.width() == w.info.width()
    assert [b.title.text() for b in w.step_boxes][1:] == ["Step 2 · Safety check", "Step 3 · Test each WGP",
                                                         "Step 4 · Choose and install"]
    assert [b.caption.text() for b in w.step_boxes] == ["Do this now", "Later", "Later", "Later"]


def test_a_new_window_starts_at_the_scan(qapp, results, runs):
    w = window()
    assert w.step == 0 and w.heading.text() == "Step 1 · Scan"
    assert pills(w) == [("Scan", True), ("Help", True)]
    w.pill("Scan").click()
    assert runs == [["--scan"]]


def test_a_scan_shows_the_board_and_offers_the_test(qapp, results, runs):
    w = window()
    w.job = "scan"
    for key, value in SCAN.items():
        w._on_notice(["scan", key, *value.split()])
    w._on_finished(0)
    assert w.active_box.value.text() == "24 CUs"
    assert "runs 24 of 40 CUs. 12 WGPs are on and 8 are locked" in w.text.text()
    assert "27 attempts" in w.text.text()
    assert pills(w) == [("Start test", True), ("Scan again", True), ("Help", True)]
    assert w.cu_map.states[0] == ["on", "on", "on", "wait", "wait"]


@pytest.mark.parametrize("key, value, says", [
    ("at-boot", "yes", "A CU unlock is active from the boot"),
    ("load", "-", "No GPU load tool was found"),
])
def test_what_blocks_the_test(qapp, results, key, value, says):
    w = window()
    w.scan = dict(SCAN, **{key: value})
    w._render()
    assert says in w.text.text() and w.pill("Start test").isEnabled() is False


def test_start_asks_once_then_runs_the_safety_check(qapp, results, runs, yes, home):
    w = window()
    w.scan = dict(SCAN)
    w._render()
    w.pill("Start test").click()
    assert runs == [["-t", "180", "-r", "3", "--only", "control", "--same-boot"]]
    assert not resume.armed()                                   # one boot: nothing opens after a login


def test_the_advanced_options_reach_the_script(qapp, results, runs, yes):
    w = window()
    assert not hasattr(w, "baseline_combo")                     # the baseline is always the board's own
    w.time_spin.setValue(300)
    w.rounds_spin.setValue(4)
    w.no_watch_pill.setChecked(True)
    w.scan = dict(SCAN)
    w._render()
    w.pill("Start test").click()
    assert runs == [["-t", "300", "-r", "4", "--only", "control", "--same-boot", "--no-watch"]]   # no --baseline
    assert window().time_spin.value() == 300                    # kept for the next time


def test_a_failed_safety_check_stops_at_step_2(qapp, results, runs, yes):
    results(runs=[(1, "control", "FAULT")], this_boot=True)
    w = window()
    assert w.step == 1 and w.step_boxes[1].caption.text() == "Stopped"
    assert "Round 1 ended with FAULT: the GPU reset or faulted." in w.text.text()
    assert [v for v, _ in pills(w)] == ["Stay at 24", "Restart", "Start over", "Details"]
    assert not w.step_boxes[2].isEnabled()
    w.pill("Stay at 24").click()
    assert w.step == 3 and progress.read_wizard()["phase"] == "stock"


def test_the_wgps_go_on_or_restart_first(qapp, restarts, results, runs):
    results(runs=full()[:12])                                   # the control and 9 attempts of round 1
    w = window()
    assert w.step == 2 and w.pill("Go on") is not None
    assert "Next: round 2, SE0.SH0.WGP3." == w.next_label.text() or "Next: round" in w.next_label.text()
    w.pill("Go on").click()
    assert runs == [["-t", "180", "-r", "3"]]
    results(runs=full()[:12], this_boot=True)
    assert window().pill("Restart") is not None


def test_after_an_attempt_the_window_restarts_the_board(qapp, restarts, results, runs, monkeypatch):
    restarted = []
    monkeypatch.setattr(resume, "restart", lambda: restarted.append(1) or True)
    results(runs=full()[:12], this_boot=True)
    resume.arm()
    w = window()
    w.job = "test"
    w._on_finished(0)
    assert w.countdown == main_window.RESTART_SECS and w.pill("Restart now") and w.pill("Pause")
    w.pill("Restart now").click()
    assert restarted == [1]


def test_pause_stops_the_countdown_and_the_autostart(qapp, restarts, results, runs):
    results(runs=full()[:12], this_boot=True)
    resume.arm()
    w = window()
    w.job = "test"
    w._on_finished(0)
    w.pill("Pause").click()
    assert w.countdown == 0 and not resume.armed() and w.state_box.value.text() == "Paused"


def test_after_a_login_the_window_goes_on(qapp, restarts, results, runs):
    results(runs=full()[:12])
    resume.arm()
    w = window()
    w._resume()
    assert w.countdown == main_window.GO_ON_SECS
    w.pill("Go on now").click()
    assert runs == [["-t", "180", "-r", "3"]]


def test_nothing_left_after_a_login_removes_the_autostart(qapp, results, runs):
    results(runs=[(1, "control", "FAULT")])
    resume.arm()
    w = window()
    w._resume()
    assert not resume.armed() and w.countdown == 0 and runs == []


def test_the_levels_the_healthy_wgps_allow(qapp, results):
    results(runs=full(bad=("SE1.SH0.WGP3",)))
    w = window()
    assert w.step == 3
    assert pills(w) == [("24 CUs", True), ("32 CUs", True), ("40 CUs", False), ("Uninstall", False)]
    assert "Fails every time: SE1.SH0.WGP3" in w.text.text()
    assert w.cu_map.states[2] == ["on", "on", "on", "bad", "ok"]


def test_choosing_a_level_runs_the_combined_test(qapp, results, runs, yes):
    folder = results(runs=full(bad=("SE1.SH0.WGP3",)))
    w = window()
    w.pill("32 CUs").click()
    assert runs == [["--reset"]]
    assert (folder / "bisect-runs.tsv").is_file() and progress.read_wizard()["phase"] == "combined"
    w._on_finished(0)                                           # --reset is done
    assert runs[1] == ["-t", "180", "--baseline", "0x0f,0x0f,0x17,0x0f", "--control-only", "-r", "1", "--same-boot"]


def test_no_combined_test_in_a_boot_with_an_attempt(qapp, restarts, results, runs, yes):
    results(runs=full(), this_boot=True)
    w = window()
    assert w.pill("Restart") is not None
    w.pill("32 CUs").click()
    assert runs == []


def test_a_passed_combined_test_can_be_installed(qapp, results, runs, yes, monkeypatch):
    folder = results(runs=full(bad=("SE1.SH0.WGP3",)))
    progress.keep_bisect(folder)
    results(base="0x0f,0x0f,0x17,0x0f", rounds=1, runs=[(1, "control", "PASS")], control_only=1,
            wizard="phase=combined\nlevel=32\n")
    started = []
    monkeypatch.setattr(main_window.UnlockRunner, "sudo_ready", lambda self: True)
    monkeypatch.setattr(main_window.UnlockRunner, "run", lambda self, args, pw=None: started.append(args))
    w = window()
    assert w.step == 3 and "32 CUs passed the combined test" in w.todo.text() and primary(w) == ["Install"]
    assert w.cu_map.states[2] == ["on", "on", "on", "bad", "on"]
    w.pill("Install").click()
    assert started == [["--install", "0x0f,0x0f,0x17,0x0f"]]


def _installed(results, tmp_path, before_boot: bool):
    """A passed combined test of 32 CUs, installed in this boot or before it."""
    import os
    folder = results(runs=full())
    progress.keep_bisect(folder)
    results(base="0x0f,0x0f,0x0f,0x0f", rounds=1, runs=[(1, "control", "PASS")], control_only=1,
            wizard="phase=combined\nlevel=32\n")
    masks = tmp_path / "etc-masks"
    masks.write_text("0x0f,0x0f,0x0f,0x0f\n")
    if before_boot:
        os.utime(masks, (1000, 1000))                           # saved long before this boot started


def test_installed_in_this_boot_waits_for_a_restart(qapp, results, tmp_path, monkeypatch):
    _installed(results, tmp_path, before_boot=False)
    w = window()
    assert "Install" not in dict(pills(w)) and dict(pills(w))["Uninstall"] is True
    assert primary(w) == ["Restart"] and "Restart the board to turn on 32 CUs" in w.todo.text()
    assert w.boot_box.value.text() == "32 CUs" and w.active_box.value.text() == "—"
    assert not w.finished_bar.isVisibleTo(w)
    restarted, asked = [], []
    monkeypatch.setattr(resume, "restart", lambda: restarted.append(1) or True)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No)
    w.pill("Restart").click()
    assert asked[0].startswith("Restart the board now?") and restarted == []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w.pill("Restart").click()
    assert restarted == [1]


def test_installed_before_this_boot_is_finished(qapp, results, tmp_path):
    _installed(results, tmp_path, before_boot=True)
    w = window()
    assert w.finished_bar.isVisibleTo(w) and "Your board runs 32 CUs at every boot" in w.finished_bar.text()
    assert [b.caption.text() for b in w.step_boxes] == ["Done"] * 4
    assert "32 CUs are installed and on" in w.step_boxes[3].line.text()
    assert [v for v, _ in pills(w)] == ["Uninstall", "Start over"] and primary(w) == []
    assert w.active_box.value.text() == "32 CUs"


def test_staying_stock_is_finished(qapp, results, yes):
    results(runs=[(1, "control", "FAULT")])
    w = window()
    w.pill("Stay at 24").click()
    assert w.finished_bar.isVisibleTo(w) and "stays at the stock CUs" in w.finished_bar.text()


def test_the_rows_say_what_came_out(qapp, results):
    results(runs=full(bad=("SE1.SH0.WGP3",)))
    w = window()
    assert [b.caption.text() for b in w.step_boxes] == ["Done", "Done", "Done", "Do this now"]
    assert "Passed 3 of 3 rounds" in w.step_boxes[1].line.text()
    assert "SE1.SH0.WGP3 failed every time and stays off." in w.step_boxes[2].line.text()


def test_a_failed_combined_test_offers_the_lower_levels(qapp, results):
    folder = results(runs=full())
    progress.keep_bisect(folder)
    results(base="0x1f,0x1f,0x1f,0x1f", rounds=1, runs=[(1, "control", "FAULT")], control_only=1,
            wizard="phase=combined\nlevel=40\n")
    w = window()
    assert "The combined test of 40 CUs failed" in w.text.text()
    assert dict(pills(w))["32 CUs"] is True and dict(pills(w))["40 CUs"] is False
    assert w.pill("40 CUs").caption.text() == "Failed together"


def test_the_scripts_questions(qapp, results, monkeypatch):
    w = window()
    sent = []
    monkeypatch.setattr(w.session, "send", sent.append)
    w._on_notice(["ask", "restart"])
    w._on_notice(["ask", "reset"])
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.Yes)
    w._on_line("=== Before you start ===")
    w._on_line("- The governor may run the GPU up to 2000 MHz.")
    w._on_notice(["ask", "warnings"])
    w._on_line("=== Before you start ===")
    w._on_line("- The governor may run the GPU up to 2000 MHz.")
    w._on_notice(["ask", "warnings"])                          # the same warnings: asked once
    assert sent == ["n", "y", "y", "y"] and len(asked) == 1


def test_the_live_attempt(qapp, results):
    results(runs=full()[:12])
    w = window()
    w.job = "test"
    monkeypatch_busy = type(w.session).busy
    try:
        type(w.session).busy = property(lambda self: True)
        w._on_notice(["attempt", "2", "SE0.SH0.WGP3", STOCK])
        w._on_notice(["phase", "load"])
        w._on_notice(["load", "40", "180", "61", "1500", "99"])
        assert w.cu_map.states[0][3] == "now"
        assert "40 of 180 s" in w.hint.text() and "61 °C" in w.hint.text()
        assert [v for v, _ in pills(w)] == ["Stop"]
    finally:
        type(w.session).busy = monkeypatch_busy


def test_the_uneven_counts_show_for_comparison(qapp, results):
    base = "0x07,0x07,0x07,0x0b"
    items = [it for it, _ in progress.plan(base, False)]
    results(base=base, runs=[(r, "control", "PASS") for r in (1, 2, 3)] + [
        (r, it, "FAULT" if it == "SE1.SH0.WGP3" else "PASS") for r in (1, 2, 3) for it in items if it != "control"])
    w = window()
    assert w.uneven_row.isVisibleTo(w)
    assert [(b.value.text(), b.caption.text()) for b in w.uneven_boxes] == [
        ("34 CUs", "5\u00b74\u00b74\u00b74 WGPs"), ("36 CUs", "5\u00b75\u00b74\u00b74 WGPs"),
        ("38 CUs", "5\u00b75\u00b74\u00b75 WGPs")]
    assert dict(pills(w))["32 CUs"] is True and dict(pills(w))["40 CUs"] is False
    link = next(l for l in w.uneven_row.findChildren(QLabel) if "href" in l.text())
    assert main_window.WHY_EVEN in link.text() and link.openExternalLinks()


def test_no_comparison_row_when_every_row_is_even(qapp, results):
    results(runs=full())
    w = window()
    assert not w.uneven_row.isVisibleTo(w) and w.uneven_boxes == []


def test_a_safety_check_from_the_terminal_offers_start_over(qapp, results, runs, yes):
    results(base="0x07,0x07,0x07,0x0b", rounds=1, runs=[(1, "control", "PASS")], control_only=1)
    w = window()
    assert w.step == 0 and "A safety check from the terminal passed" in w.text.text()
    assert [v for v, _ in pills(w)] == ["Start over", "Help"]
    w.pill("Start over").click()
    assert runs == [["--reset"]]


def test_one_boot_goes_from_the_safety_check_to_the_wgps(qapp, results, runs):
    """Same boot, the default: when the safety check passed, the WGP test starts without a click."""
    results(runs=[(r, "control", "PASS") for r in (1, 2, 3)], this_boot=True)
    w = window()
    w.job = "test"
    w._on_finished(0)
    assert runs == [["-t", "180", "-r", "3", "--same-boot"]] and w.countdown == 0


def test_one_boot_stops_after_a_failed_safety_check(qapp, results, runs):
    results(runs=[(1, "control", "FAULT")], this_boot=True)
    w = window()
    w.job = "test"
    w._on_finished(0)
    assert runs == [] and w.step == 1


def test_the_mask_column(qapp, results):
    w = window()
    w.scan = {"live": "0x07,0x07,0x07,0x0b", "load": "memtest_vulkan"}
    w._render()
    texts = [label.text() for label in w.cu_map.masks]
    assert "0x07" in texts[0] and "00111" in texts[0] and "0x0b" in texts[3] and "01011" in texts[3]
    assert "Your masks are <b>0x07,0x07,0x07,0x0b</b>" in w.text.text()


def test_a_done_test_notifies(qapp, results, runs, notes):
    results(runs=full(bad=("SE1.SH0.WGP3",)), this_boot=True)
    w = window()
    w.job = "test"
    w._on_finished(0)
    assert notes == [("CU test done", "27 attempts. Fails every time: 1 WGP. Random: 0. Highest even level: 32 CUs. "
                                      "Choose in step 4 of CU Unlock.")]


def test_a_failed_safety_check_notifies(qapp, results, runs, notes):
    results(runs=[(1, "control", "FAULT")], this_boot=True)
    w = window()
    w.job = "test"
    w._on_finished(0)
    assert notes[0][0] == "CU test stopped" and "FAULT" in notes[0][1]


def test_quiet_between_attempts_and_after_stop(qapp, results, runs, notes):
    results(runs=full()[:12], this_boot=True)
    w = window()
    w.job = "test"
    w._on_finished(0)                                           # one boot: the next attempts follow
    w.job = "test"
    w._on_finished(130)                                         # Stop
    assert notes == []


def test_a_script_error_notifies(qapp, results, runs, notes):
    w = window()
    w.job = "test"
    w._on_line("ERROR: umr not found. Install it: sudo rpm-ostree install umr, then restart.")
    w._on_finished(1)
    assert notes == [("CU test stopped", "ps5-cu-bisect.sh stopped: umr not found. Install it: sudo rpm-ostree "
                                         "install umr, then restart.")]


def test_with_restarts_the_end_notifies_after_the_login(qapp, results, runs, restarts, notes):
    results(runs=full())
    resume.arm()
    w = window()
    w._resume()
    assert not resume.armed() and notes[0][0] == "CU test done"


def test_only_a_test_blocks_sleep(qapp, results, runs, yes):
    w = window()
    w.pill("Scan").click()
    w.job = ""
    w.scan = dict(SCAN)
    w._render()
    w.pill("Start test").click()
    assert runs == [["--scan"], ["-t", "180", "-r", "3", "--only", "control", "--same-boot"]]
    assert runs.sleeps == [False, True]


def primary(w):
    return [p.value.text() for p in w.actions if getattr(p, "primary", False)]


@pytest.mark.parametrize("setup, todo, pill", [
    ("new", "Click <b>Scan</b>", ["Scan"]),
    ("scanned", "Click <b>Start test</b>. A question opens. Answer <b>Yes</b>.", ["Start test"]),
    ("terminal", "Click <b>Start over</b> and answer <b>Yes</b>", ["Start over"]),
    ("failed", "The test stopped. Click <b>Stay at 24</b>", ["Stay at 24"]),
    ("wgps", "Click <b>Go on</b>", ["Go on"]),
    ("choose", "Click <b>32 CUs</b> to test that level as a whole", ["32 CUs"]),
])
def test_one_thing_to_do_and_its_pill(qapp, results, setup, todo, pill):
    if setup == "terminal":
        results(base="0x07,0x07,0x07,0x0b", rounds=1, runs=[(1, "control", "PASS")], control_only=1)
    elif setup == "failed":
        results(runs=[(1, "control", "FAULT")])
    elif setup == "wgps":
        results(runs=full()[:12])
    elif setup == "choose":
        results(runs=full(bad=("SE1.SH0.WGP3",)))
    w = window()
    if setup == "scanned":
        w.scan = dict(SCAN)
        w._render()
    assert todo in w.todo.text() and primary(w) == pill
    assert w.step_boxes[w.step].slot.count() == 1                # its pill sits on the step's own row


def test_while_a_test_runs_there_is_nothing_to_do_and_the_indicator_turns(qapp, results):
    results(runs=full()[:12])
    w = window()
    w.job = "test"
    busy = type(w.session).busy
    try:
        type(w.session).busy = property(lambda self: True)
        w._start_spin()
        w._on_notice(["attempt", "2", "SE0.SH0.WGP3", STOCK])
        w._render()
        assert "Nothing to do. The test runs by itself" in w.todo.text() and primary(w) == []
        assert w.step_boxes[w.step].caption.text() == "Running"            # not "Do this now"
        first = w.running.text()
        w._on_spin()
        assert w.running.isVisibleTo(w) and "Running: round 2, SE0.SH0.WGP3" in w.running.text()
        assert w.running.text()[0] != first[0]                     # the symbol turns
    finally:
        type(w.session).busy = busy
    w._on_spin()
    assert not w.running.isVisibleTo(w)                             # gone when nothing runs


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


def test_tooltips_have_rounded_corners(qapp):
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


def test_the_window_follows_the_running_test(qapp, results):
    """Started from step 1: the first attempt moves the window to the safety check, its result counts at once."""
    w = window()
    w.scan = dict(SCAN)
    w._render()
    assert w.step == 0
    results(base=STOCK, runs=[])
    w.job = "test"
    w._on_notice(["attempt", "1", "control", STOCK])
    assert w.step == 1 and w.heading.text().startswith("Step 2")
    results(base=STOCK, runs=[(r, "control", "PASS") for r in (1, 2, 3)] + [(1, "SE0.SH0.WGP3", "PASS")])
    w._on_notice(["result", "1", "SE0.SH0.WGP3", "PASS"])
    assert w.step == 2 and w.count_box.value.text() == "4 of 27"
