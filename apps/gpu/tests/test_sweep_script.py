# SPDX-License-Identifier: GPL-3.0-or-later
"""ps5-gpu-sweep.sh from the scan to Install, with fake tools: sudo runs the command, systemctl says the governor
runs, lspci shows the PS5's GPU, sleep and timeout don't wait, and memtest_vulkan reports errors when the governor's
config has a top point above 2100 MHz or under 840 mV. The governor's config sits in a temp folder
(PS5_SWEEP_ETC). The window's progress.py reads the same results as the script."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SHIPPED

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="runs the bash script")

APP = Path(__file__).resolve().parents[1]
SCRIPT = APP / "ps5-gpu-sweep.sh"

FAKES = {
    "sudo": '[ "$1" = -n ] && shift\n[ "$1" = -v ] && exit 0\nexec "$@"\n',
    "systemctl": '[ "$1" = is-active ] && [ "$2" != --quiet ] && echo active\nexit 0\n',
    "lspci": 'echo "03:00.0 VGA compatible controller [0300]: AMD [1002:13fe]"\n',
    "journalctl": "exit 0\n",
    "sleep": "exit 0\n",
    "timeout": 'shift 3\nexec "$@"\n',
    "xdg-user-dir": 'echo "$HOME/Desktop"\n',
    "memtest_vulkan": ('conf="$PS5_SWEEP_ETC/cyan-skillfish-governor-smu/config.toml"\n'
                       "top=$(awk '/^frequency/ {f=$3} /^voltage/ {v=$3} END {print f, v}' \"$conf\")\n"
                       'read -r f v <<<"$top"\n'
                       '[ "$f" -gt 2100 ] || [ "$v" -lt 840 ] && echo "Error found at 0x1000"\nexit 0\n'),
}


@pytest.fixture
def sweep(tmp_path, monkeypatch):
    fakes = tmp_path / "bin"
    fakes.mkdir()
    for name, body in FAKES.items():
        path = fakes / name
        path.write_text("#!/usr/bin/env bash\n" + body)
        path.chmod(0o755)
    etc = tmp_path / "etc" / "cyan-skillfish-governor-smu"
    etc.mkdir(parents=True)
    (etc / "config.toml").write_text(SHIPPED)
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    env = {**os.environ, "PATH": f"{fakes}:{os.environ['PATH']}", "HOME": str(home),
           "XDG_DATA_HOME": str(home / ".local/share"), "PS5_SWEEP_ETC": str(tmp_path / "etc"), "PS5_GUI": "1",
           "PS5_SWEEP_DRM": str(tmp_path / "no-drm")}                     # never this machine's own GPU
    monkeypatch.setenv("XDG_DATA_HOME", env["XDG_DATA_HOME"])

    def run(*args: str, answers: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(SCRIPT), *args], env=env, input=answers, capture_output=True, text=True,
                              timeout=120)
    run.config = etc / "config.toml"
    run.state = home / ".local/share/ps5-gpu-sweep"
    return run


LADDER = ["-t", "60", "-r", "2", "--max-freq", "2150", "--min-volt", "825"]


def events(out: str, name: str) -> list[list[str]]:
    return [line.split()[2:] for line in out.splitlines() if line.startswith(f"@@ {name} ")]


def test_the_scan_reads_and_writes_nothing(sweep):
    result = sweep("--scan")
    assert result.returncode == 0, result.stderr
    scan = {e[0]: " ".join(e[1:]) for e in events(result.stdout, "scan")}
    assert scan["governor"] == "smu" and scan["service"] == "active" and scan["load"] == "memtest_vulkan"
    assert scan["top"] == "2000 900" and scan["points"] == "3" and scan["snapshot"] == "none"
    assert not sweep.state.exists()


def test_a_whole_sweep_and_install(sweep):
    from gpu_governor.sweep import progress
    original = sweep.config.read_text()
    control = sweep(*LADDER, "--only", "control", answers="y\n")
    assert control.returncode == 0, control.stdout + control.stderr
    assert sweep.config.read_text() == original                       # the own config is back after each attempt
    assert [e[2] for e in events(control.stdout + control.stderr, "result")] == ["PASS", "PASS"]

    early = sweep(*LADDER, "--only", "uv", answers="y\n")             # the ladders don't start before the control
    assert early.returncode == 0                                       # it passed already, so uv may run
    oc = sweep(*LADDER, "--only", "oc", answers="y\n")
    assert oc.returncode == 0, oc.stdout + oc.stderr
    assert sweep.config.read_text() == original

    p = progress.load(sweep.state)
    assert p.items == ["control", "oc:2050", "oc:2100", "oc:2150", "uv:875", "uv:850", "uv:825"]
    assert [p.verdict(it) for it in p.items] == ["good", "good", "good", "bad", "good", "good", "bad"]
    assert p.finished and p.best() == (2050, 875)
    assert p.install_plan() == ([(1000, 700), (1500, 800)], [(2000, 900)])

    other = sweep("-t", "60", "-r", "2", "--max-freq", "2200", "--only", "oc")   # another ladder needs a reset
    assert other.returncode != 0 and "Reset first" in other.stderr

    install = sweep("--install", answers="y\n")
    assert install.returncode == 0, install.stdout + install.stderr
    assert "Dropped, as their voltage is above 875 mV: 2000 MHz @ 900 mV" in install.stdout
    assert progress.safe_points(sweep.config.read_text()) == [(1000, 700), (1500, 800), (2050, 875)]
    backups = list(sweep.config.parent.glob("config.toml.bak-*"))
    assert len(backups) == 1 and backups[0].read_text() == original
    assert progress.load(sweep.state).installed.split()[:2] == ["2050", "875"]
    assert "[temperature]" in sweep.config.read_text()                # everything but the safe-points stays


def test_a_crash_counts_after_the_restart(sweep):
    from gpu_governor.sweep import progress
    assert sweep(*LADDER, "--only", "control", answers="y\n").returncode == 0
    sweep.state.joinpath("pending").write_text("1 oc:2050 2050 900 an-earlier-boot\n")
    result = sweep(*LADDER, "--only", "oc", answers="y\ny\n")         # yes, it froze; yes, go on
    assert "@@ ask crash" in result.stderr
    p = progress.load(sweep.state)
    assert p.outcome(1, "oc:2050") == "CRASH-LOAD" and p.verdict("oc:2050") == "random"


def test_a_changed_config_blocks_until_a_reset(sweep):
    assert sweep(*LADDER, "--only", "control", answers="y\n").returncode == 0
    sweep.config.write_text(SHIPPED.replace("voltage = 900", "voltage = 905"))
    blocked = sweep(*LADDER, "--only", "oc", answers="y\n")
    assert blocked.returncode != 0 and "changed since this run started" in blocked.stderr
    assert sweep("--reset", answers="y\n").returncode == 0
    assert not (sweep.state / "runs.tsv").exists()
