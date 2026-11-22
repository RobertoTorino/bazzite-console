# SPDX-License-Identifier: GPL-3.0-or-later
"""The processes of a program, read from /proc, and their end (owner, 22-11-2026: Exit <emulator> in the game
managers ends the emulator at once, without a question; a game that runs ends without saving).

find() gives the processes whose name (comm, the first 15 characters) a test accepts; a finished one not collected
yet (a zombie) does not count, as in core's steam_running. end() sends SIGKILL to them and to every process they
started: an AppImage's own process stays while the program it unpacked runs, under it. Standard library only."""

from __future__ import annotations

import os
import signal
from collections.abc import Callable, Iterable
from pathlib import Path

Match = Callable[[str, Path], bool]     # (comm, the process's folder in /proc) -> whether it is the program's


def _state_and_parent(folder: Path) -> tuple[str, int]:
    """A process's state letter and its parent's number, from stat (after the name, which may hold spaces)."""
    fields = (folder / "stat").read_text().rsplit(")", 1)[1].split()
    return fields[0], int(fields[1])


def find(match: Match, proc: Path = Path("/proc")) -> list[int]:
    """The numbers of the running processes *match* accepts, zombies left out."""
    found = []
    for folder in proc.glob("[0-9]*"):
        try:
            if not match((folder / "comm").read_text().strip(), folder):
                continue
            state, _parent = _state_and_parent(folder)
        except (OSError, IndexError, ValueError):
            continue
        if state not in ("Z", "X"):
            found.append(int(folder.name))
    return found


def tree(pids: Iterable[int], proc: Path = Path("/proc")) -> list[int]:
    """*pids* and every process under them, the children before their parents."""
    children: dict[int, list[int]] = {}
    for folder in proc.glob("[0-9]*"):
        try:
            _state, parent = _state_and_parent(folder)
        except (OSError, IndexError, ValueError):
            continue
        children.setdefault(parent, []).append(int(folder.name))
    order: list[int] = []
    seen: set[int] = set()

    def walk(pid: int) -> None:
        if pid in seen:
            return
        seen.add(pid)
        for child in children.get(pid, []):
            walk(child)
        order.append(pid)

    for pid in pids:
        walk(pid)
    return order


def end(pids: Iterable[int], proc: Path = Path("/proc"),
        kill: Callable[[int, int], None] = os.kill) -> list[int]:
    """Ends *pids* and every process under them with SIGKILL; returns the numbers it was sent to. A process that is
    gone already, or not ours, is passed over."""
    sent = []
    for pid in tree(pids, proc):
        try:
            kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            continue
        sent.append(pid)
    return sent
