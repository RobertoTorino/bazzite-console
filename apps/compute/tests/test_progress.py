# SPDX-License-Identifier: GPL-3.0-or-later
"""progress.py reads ps5-cu-bisect.sh's files by the script's own rules: the plan, each item's verdict, the next
attempt (with --only), and the even levels. The levels are held against the script's own --status suggestion."""

from __future__ import annotations

import re
import subprocess
import sys

import pytest

from cu_bisect import progress

SCRIPT = progress.Path(__file__).resolve().parents[1] / "ps5-cu-bisect.sh"
WGPS = [f"{row}.WGP{b}" for row in progress.ROWS for b in (3, 4)]


def write(folder, base, rounds, runs, control_only=0):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "umr-config").write_text(f"BASE={base}\nROUNDS={rounds}\nTIME=180\nCONTROL_ONLY={control_only}\n")
    (folder / "umr-runs.tsv").write_text("".join(
        f"2026-11-23 21:00:00\tabcd1234\t{r}\t{item}\t{base}\t{outcome}\t0\t0\t-\t60\t1500\t90\t-\n"
        for r, item, outcome in runs))
    return folder


def full_run(bad=(), random=()):
    runs = [(r, "control", "PASS") for r in (1, 2, 3)]
    for r in (1, 2, 3):
        for item in WGPS:
            outcome = "FAULT" if item in bad or (item in random and r == 2) else "PASS"
            runs.append((r, item, outcome))
    return runs


def test_the_plan_is_the_control_then_every_locked_wgp():
    items = progress.plan("0x07,0x07,0x07,0x07", False)
    assert [it for it, _ in items] == ["control", *WGPS]
    assert dict(items)["SE1.SH0.WGP3"] == "0x07,0x07,0x0f,0x07"
    assert progress.plan("0x0f,0x0f,0x0f,0x0f", True) == [("control", "0x0f,0x0f,0x0f,0x0f")]


def test_another_boards_baseline_plans_its_own_locked_wgps():
    """A die with other fused WGPs: the plan follows the live masks, not a stock layout."""
    items = [it for it, _ in progress.plan("0x0b,0x07,0x1c,0x07", False)]
    assert "SE0.SH0.WGP2" in items and "SE0.SH0.WGP3" not in items and "SE1.SH0.WGP0" in items


def test_verdicts_and_the_next_attempt(tmp_path):
    folder = write(tmp_path / "s", "0x07,0x07,0x07,0x07", 3,
                   [(1, "control", "PASS"), (1, "SE0.SH0.WGP3", "FAULT"), (1, "SE0.SH0.WGP4", "ABORTED")])
    p = progress.load(folder)
    assert p.verdict("SE0.SH0.WGP3") == "bad" and p.verdict("SE0.SH0.WGP4") == "none"
    assert p.next_attempt() == (1, "SE0.SH0.WGP4")             # an aborted attempt runs again
    assert p.next_attempt("control") == (2, "control")
    assert p.control == "running" and p.done("control") == 1 and p.total("control") == 3
    assert p.total() == 27


def test_a_failed_control_stops_the_safety_check(tmp_path):
    p = progress.load(write(tmp_path / "s", "0x07,0x07,0x07,0x07", 3, [(1, "control", "FAULT")]))
    assert p.control == "failed"


def test_random_is_some_rounds_only(tmp_path):
    p = progress.load(write(tmp_path / "s", "0x07,0x07,0x07,0x07", 3, full_run(random=("SE0.SH1.WGP4",))))
    assert p.verdict("SE0.SH1.WGP4") == "random" and p.control == "passed" and p.next_attempt() is None


@pytest.mark.parametrize("bad, levels", [
    ((), {24: "0x07,0x07,0x07,0x07", 32: "0x0f,0x0f,0x0f,0x0f", 40: "0x1f,0x1f,0x1f,0x1f"}),
    (("SE1.SH0.WGP3",), {24: "0x07,0x07,0x07,0x07", 32: "0x0f,0x0f,0x17,0x0f"}),
    (("SE0.SH0.WGP3", "SE0.SH0.WGP4"), {24: "0x07,0x07,0x07,0x07"}),
])
def test_levels(tmp_path, bad, levels):
    p = progress.load(write(tmp_path / "s", "0x07,0x07,0x07,0x07", 3, full_run(bad)))
    assert p.levels() == levels


@pytest.mark.skipif(sys.platform == "win32", reason="runs ps5-cu-bisect.sh with bash")
@pytest.mark.parametrize("bad", [(), ("SE1.SH0.WGP3",), ("SE0.SH1.WGP4", "SE1.SH1.WGP3")])
def test_the_highest_level_is_the_scripts_suggestion(tmp_path, home, bad):
    folder = write(home / ".local" / "share" / "ps5-cu-bisect", "0x07,0x07,0x07,0x07", 3, full_run(bad))
    out = subprocess.run(["bash", str(SCRIPT), "--status"], capture_output=True, text=True, timeout=60).stdout
    even = re.search(r"Use the even version instead: (\S+)", out) or re.search(r"Combined: (\S+)", out)
    levels = progress.load(folder).levels()
    assert even and levels[max(levels)] == even.group(1)


def test_the_window_keeps_the_bisect_run_for_the_combined_test(tmp_path):
    folder = write(tmp_path / "s", "0x07,0x07,0x07,0x07", 3, full_run(("SE1.SH0.WGP3",)))
    progress.keep_bisect(folder)
    write(folder, "0x0f,0x0f,0x17,0x0f", 1, [(1, "control", "PASS")], control_only=1)
    kept = progress.kept_bisect(folder)
    assert kept.verdict("SE1.SH0.WGP3") == "bad" and 32 in kept.levels()
    progress.write_wizard({"phase": "combined", "level": "32"}, folder)
    assert progress.read_wizard(folder) == {"phase": "combined", "level": "32"}
    progress.forget(folder)
    assert progress.kept_bisect(folder) is None and progress.read_wizard(folder) == {}


def test_installed_masks(tmp_path):
    path = tmp_path / "masks"
    assert progress.installed_masks(path) == ""
    path.write_text("0x0f,0x0f,0x0f,0x0f\n")
    assert progress.installed_masks(path) == "0x0f,0x0f,0x0f,0x0f"


def test_the_uneven_counts_for_comparison(tmp_path):
    """One WGP fails every time on a board with its own masks: 32 is the highest even level, 38 the healthy total."""
    base = "0x07,0x07,0x07,0x0b"
    items = [it for it, _ in progress.plan(base, False)]
    runs = [(1, "control", "PASS"), (2, "control", "PASS"), (3, "control", "PASS")] + [
        (r, it, "FAULT" if it == "SE1.SH0.WGP3" else "PASS") for r in (1, 2, 3) for it in items if it != "control"]
    p = progress.load(write(tmp_path / "s", base, 3, runs))
    assert max(p.levels()) == 32
    assert p.uneven() == [(34, [5, 4, 4, 4]), (36, [5, 5, 4, 4]), (38, [5, 5, 4, 5])]
    assert progress.load(write(tmp_path / "t", "0x07,0x07,0x07,0x07", 3, full_run())).uneven() == []


def test_the_unlock_is_on_only_when_saved_before_this_boot(tmp_path):
    import os
    stat = tmp_path / "stat"
    stat.write_text("cpu  1 2 3\nbtime 2000\nprocesses 5\n")
    masks = tmp_path / "masks"
    assert progress.boot_time(stat) == 2000.0
    assert not progress.unlock_on(masks, stat)                      # nothing installed
    masks.write_text("0x0f,0x0f,0x0f,0x0f\n")
    os.utime(masks, (3000, 3000))
    assert not progress.unlock_on(masks, stat)                      # installed in this boot: waits for a restart
    os.utime(masks, (1000, 1000))
    assert progress.unlock_on(masks, stat)
    stat.write_text("cpu  1 2 3\n")
    assert progress.boot_time(stat) == 0.0 and not progress.unlock_on(masks, stat)   # unknown boot: not claimed
