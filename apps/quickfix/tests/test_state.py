# SPDX-License-Identifier: GPL-3.0-or-later
"""What the quickfixes read, from folders that stand in for /etc, /proc, /sys and /var: Bazzite's own max_map_count and
journal, the PS5 loader's cmdline.txt, and a system that has none of them."""

from __future__ import annotations

import os
from pathlib import Path

from quickfix import state, system


def put(root: Path, path: str, text: str = "") -> Path:
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)
    return file


def test_mangohud_logging_lines():
    text = "fps\n# a comment\noutput_folder=/old  # where\nposition=top-left\n"
    values = state.conf_values(text)
    assert values == {"fps": "1", "output_folder": "/old", "position": "top-left"}
    assert not state.logging_on(values)
    new = state.with_logging(text, Path("/home/u/mangohud-logs"))
    assert new.splitlines()[:4] == ["fps", "# a comment", "output_folder=/home/u/mangohud-logs", "position=top-left"]
    assert new.splitlines()[-2:] == ["autostart_log=1", f"log_interval={state.LOG_INTERVAL}"]
    assert state.logging_on(state.conf_values(new))
    assert state.with_logging(new, Path("/home/u/mangohud-logs")) == new                # set already: unchanged
    assert state.with_logging("", Path("/l")).splitlines()[1:] == ["output_folder=/l", "autostart_log=1",
                                                                   "log_interval=500"]


def test_log_files(tmp_path):
    for name in ("Game_2026-11-15.csv", "Game_2026-11-15_summary.csv", "notes.txt"):
        put(tmp_path, name)
    assert [p.name for p in state.log_files(tmp_path)] == ["Game_2026-11-15.csv", "Game_2026-11-15_summary.csv"]
    assert state.log_files(tmp_path / "none") == []


def test_mapcount_and_journal(tmp_path):
    assert state.mapcount(tmp_path) == state.MapCount(0, False)
    put(tmp_path, "proc/sys/vm/max_map_count", "2147483642\n")
    assert state.mapcount(tmp_path).value == system.MAPCOUNT
    assert state.journal(tmp_path) == state.Journal(False, False)
    (tmp_path / "var/log/journal").mkdir(parents=True)
    assert state.journal(tmp_path) == state.Journal(True, False)
    put(tmp_path, f"var/{system.JOURNAL_DIR}/{system.JOURNAL_MARK}")
    assert state.journal(tmp_path) == state.Journal(True, True)


def port(root, name: str, carrier: str = "1", kind: str = "1", device: bool = True, wireless: bool = False) -> None:
    put(root, f"sys/class/net/{name}/type", kind + "\n")
    put(root, f"sys/class/net/{name}/carrier", carrier + "\n")
    if device:
        (root / f"sys/class/net/{name}/device").mkdir()
    if wireless:
        (root / f"sys/class/net/{name}/wireless").mkdir()


def test_ethernet(tmp_path):
    assert state.ethernet(tmp_path) == state.Ethernet(False, False, False)
    port(tmp_path, "docker0", device=False)                     # a bridge: no device behind it
    port(tmp_path, "wlan0", wireless=True)
    port(tmp_path, "lo", kind="772", device=False)
    port(tmp_path, "enp1s0", carrier="0")
    assert not state.cable(tmp_path)
    put(tmp_path, "sys/class/net/enp1s0/carrier", "1\n")
    put(tmp_path, f"etc/{system.ETHERNET_HOOK}")
    put(tmp_path, f"var/{system.ETHERNET_MARK}")
    assert state.ethernet(tmp_path) == state.Ethernet(True, True, True)


def test_cmdline(tmp_path):
    c = state.cmdline(tmp_path)
    assert (c.text, c.exists, c.backups) == ("", False, 0)
    put(tmp_path, f"boot/{system.CMDLINE}", "root=UUID=1 rw\n")
    put(tmp_path, f"boot/{system.CMDLINE}.bak-20261115-201000", "root=UUID=1\n")
    c = state.cmdline(tmp_path)
    assert (c.text, c.exists, c.backups) == ("root=UUID=1 rw\n", True, 1)
    assert state.cmdline_files(tmp_path) == ["cmdline.txt"]
    put(tmp_path, "boot/efi/cmdline.txt.usb", "root=UUID=2 rw\n")
    assert state.cmdline_files(tmp_path) == ["cmdline.txt", "cmdline.txt.usb"]
    usb = state.cmdline(tmp_path, "cmdline.txt.usb")
    assert (usb.text, usb.backups) == ("root=UUID=2 rw\n", 0)                 # cmdline.txt's backups are not its own


def test_find_tool_where_the_tests_look(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "BREW_BIN", tmp_path / "brew")
    tool = put(tmp_path, "home/.local/bin/vkpeak", "#!/bin/sh\n")
    assert state.find_tool("vkpeak", tmp_path / "home", path="") == ""                 # not executable
    os.chmod(tool, 0o755)
    assert state.find_tool("vkpeak", tmp_path / "home", path="") == str(tool)
    put(tmp_path, "bin/fio", "#!/bin/sh\n")
    os.chmod(tmp_path / "bin/fio", 0o755)
    assert state.find_tool("fio", tmp_path / "home", path=str(tmp_path / "bin")) == str(tmp_path / "bin/fio")


def test_board_tests_installer(tmp_path):
    assert state.installer(tmp_path / "opt", tmp_path / "none") is None
    script = put(tmp_path, f"opt/{state.INSTALLER}")
    assert state.installer(tmp_path / "opt", tmp_path / "none") == script
    assert state.installer(tmp_path / "none").name == "install-requirements.sh"          # the checkout's
