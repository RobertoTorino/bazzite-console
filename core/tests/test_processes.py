# SPDX-License-Identifier: GPL-3.0-or-later
"""processes: finding a program's processes in /proc and ending them with everything under them."""

from __future__ import annotations

import signal
from pathlib import Path

from bazzite_console_core import processes


def _proc(tmp_path: Path, table: dict[int, tuple[str, str, int]]) -> Path:
    """A /proc of *table*: pid -> (comm, state, parent pid)."""
    proc = tmp_path / "proc"
    for pid, (comm, state, parent) in table.items():
        folder = proc / str(pid)
        folder.mkdir(parents=True)
        (folder / "comm").write_text(comm + "\n")
        (folder / "stat").write_text(f"{pid} ({comm}) {state} {parent} 0 0\n")
    return proc


def _named(name: str):
    return lambda comm, _folder: comm == name


def test_find_leaves_out_zombies_and_other_programs(tmp_path):
    proc = _proc(tmp_path, {10: ("vita3k.AppImage", "S", 1), 11: ("vita3k.AppImage", "Z", 1),
                            12: ("bash", "S", 1)})
    assert processes.find(_named("vita3k.AppImage"), proc) == [10]
    assert processes.find(_named("ppsspp.AppImage"), proc) == []


def test_find_reads_a_name_with_spaces_and_brackets(tmp_path):
    proc = _proc(tmp_path, {7: ("Shadps4-sdl (x)", "R", 1)})
    assert processes.find(lambda comm, _f: comm.startswith("Shadps4-sdl"), proc) == [7]


def test_end_kills_the_program_and_everything_under_it_children_first(tmp_path):
    """An AppImage's own process stays while the program it unpacked runs under it: both end."""
    proc = _proc(tmp_path, {10: ("vita3k.AppImage", "S", 1), 20: ("Vita3K", "S", 10), 30: ("helper", "S", 20),
                            40: ("bash", "S", 1)})
    sent: list[tuple[int, int]] = []
    assert processes.end([10], proc, kill=lambda pid, sig: sent.append((pid, sig))) == [30, 20, 10]
    assert sent == [(30, signal.SIGKILL), (20, signal.SIGKILL), (10, signal.SIGKILL)]


def test_end_passes_over_a_process_that_is_gone_or_not_ours(tmp_path):
    proc = _proc(tmp_path, {10: ("xenia.AppImage", "S", 1), 20: ("xenia", "S", 10), 30: ("other", "S", 10)})

    def kill(pid: int, sig: int) -> None:
        if pid == 20:
            raise ProcessLookupError
        if pid == 30:
            raise PermissionError

    assert processes.end([10], proc, kill=kill) == [10]


def test_end_of_nothing_sends_nothing(tmp_path):
    proc = _proc(tmp_path, {40: ("bash", "S", 1)})
    assert processes.end([], proc, kill=lambda pid, sig: (_ for _ in ()).throw(AssertionError)) == []
