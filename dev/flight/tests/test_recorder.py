# SPDX-License-Identifier: GPL-3.0-or-later
"""The recorder writes one line per reading with every column, reads the memory and the busiest program from /proc,
keeps the newest days, and its root helper installs, switches and removes the service in a root of its own."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest
from bazzite_console_core.sensors import Fan, Reading

from nexus_flight_recorder import helper, recorder


def reading(**values):
    base = dict(cpu_load=12.34, cpu_mhz=None, cpu_temp=66.0, soc_temp=60.0, board_temp=None, gpu_load=40.0,
                gpu_mhz=1850, gpu_temp=50.0, gpu_limit=90, vram=(1 << 30, 6 << 30), ram=(4 << 30, 9 << 30),
                nvme_temp=40.0, net=None, disk=None, fan=Fan(duty=40, mode="auto"))
    base.update(values)
    return Reading(**base)


@pytest.fixture
def proc(tmp_path):
    root = tmp_path / "proc"
    (root / "pressure").mkdir(parents=True)
    (root / "meminfo").write_text("MemTotal: 100 kB\nSwapTotal:  5000 kB\nSwapFree:   3800 kB\n")
    (root / "pressure/memory").write_text("some avg10=8.52 avg60=1.00 avg300=0.10 total=5\nfull avg10=0.00\n")
    (root / "loadavg").write_text("2.50 1.00 0.50 3/900 1234\n")
    for pid, name, ticks in (("10", "steam", 500), ("11", "my (odd), name", 100)):
        (root / pid).mkdir()
        (root / pid / "stat").write_text(f"{pid} ({name}) S 1 1 1 0 -1 0 0 0 0 0 {ticks} 0 0 0 20 0 1 0 0 0 0\n")
    return root


def test_a_line_has_every_column(proc):
    line = recorder.row(reading(), datetime.datetime(2026, 11, 27, 0, 46, 5), "aaaaaaaa", "steam", proc)
    assert len(line) == len(recorder.COLUMNS)
    got = dict(zip(recorder.COLUMNS, line))
    assert got["time"] == "00:46:05" and got["boot"] == "aaaaaaaa" and got["load1"] == "2.50"
    assert got["cpu_load"] == "12.3" and got["gpu_mhz"] == "1850" and got["fan_duty"] == "40"
    assert got["board_temp"] == "" and got["swap_used_kb"] == "1200" and got["mem_pressure"] == "8.52"
    assert got["busiest"] == "steam" and got["ram_used"] == str(4 << 30)


def test_memory_readings_without_their_files(tmp_path):
    assert recorder.swap_used_kb(tmp_path) is None and recorder.pressure(tmp_path) == ""


def test_the_busiest_program_is_the_one_that_used_most_cpu_since_the_last_look(proc):
    busiest = recorder.Busiest(proc)
    assert busiest() == ""                                      # the first look has nothing to compare with
    (proc / "11" / "stat").write_text("11 (my (odd), name) S 1 1 1 0 -1 0 0 0 0 0 190 0 0 0 20 0 1 0 0 0 0\n")
    (proc / "10" / "stat").write_text("10 (steam) S 1 1 1 0 -1 0 0 0 0 0 520 0 0 0 20 0 1 0 0 0 0\n")
    assert busiest() == "my (odd)  name"                        # the name only, and no comma to break the line


def test_a_new_day_gets_its_heading_and_the_oldest_days_go(tmp_path):
    out = tmp_path / "log"
    for day in range(1, 10):
        recorder.open_day(out, f"2026-11-{day:02d}", keep=7).close()
    assert sorted(p.stem for p in out.glob("*.csv")) == [f"2026-11-{d:02d}" for d in range(3, 10)]
    assert (out / "2026-11-09.csv").read_text() == ",".join(recorder.COLUMNS) + "\n"
    handle = recorder.open_day(out, "2026-11-09")
    handle.write("x\n")
    handle.close()
    assert (out / "2026-11-09.csv").read_text().count("time,boot") == 1     # the heading only once


def test_the_helper_installs_switches_and_removes(tmp_path, monkeypatch):
    root, calls = tmp_path / "root", []
    monkeypatch.setattr(helper.shutil, "which", lambda name: None)
    source, sensors = tmp_path / "recorder.py", tmp_path / "sensors.py"
    source.write_text("# recorder\n")
    sensors.write_text("# sensors\n")
    helper.install(root, source, sensors, run=calls.append)
    lib = root / helper.LIB
    assert (lib / "recorder.py").read_text() == "# recorder\n" and (lib / "recorder.py").stat().st_mode & 0o777 == 0o755
    assert (lib / "sensors.py").stat().st_mode & 0o777 == 0o644
    unit = (root / "etc/systemd/system" / helper.UNIT).read_text()
    assert unit.startswith("# SPDX-License-Identifier") and f"ExecStart=/{helper.LIB}/recorder.py" in unit
    assert "WantedBy=multi-user.target" in unit
    assert calls == [["systemctl", "daemon-reload"], ["systemctl", "enable", helper.UNIT],
                     ["systemctl", "restart", helper.UNIT]]
    calls.clear()
    helper.remove(root, run=calls.append)
    assert not lib.exists() and not (root / "etc/systemd/system" / helper.UNIT).exists()
    assert calls == [["systemctl", "disable", "--now", helper.UNIT], ["systemctl", "daemon-reload"]]


@pytest.mark.parametrize(("argv", "systemctl"), [(["start"], ["start"]), (["stop"], ["stop"]),
                                                 (["boot-on"], ["enable"]), (["boot-off"], ["disable"])])
def test_the_helpers_simple_actions(argv, systemctl, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(helper, "run", calls.append)
    assert helper.main(argv) == 0 and calls == [["systemctl", *systemctl, helper.UNIT]]
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_the_helper_says_why_it_failed(monkeypatch, capsys):
    def fail(argv):
        raise OSError("no such unit")
    monkeypatch.setattr(helper, "run", fail)
    assert helper.main(["start"]) == 1
    assert json.loads(capsys.readouterr().out) == {"ok": False, "error": "no such unit"}
    assert helper.main(["bogus"]) == 2 and "usage" in json.loads(capsys.readouterr().out)["error"]


def test_the_recorder_and_the_helper_need_only_the_standard_library():
    for module in (recorder, helper):
        text = Path(module.__file__).read_text()
        assert "bazzite_console_core" not in text and "PyQt6" not in text and text.startswith("#!/usr/bin/python3 -I\n")
