# SPDX-License-Identifier: GPL-3.0-or-later
"""What can go from this machine: the places that fill up with files nobody needs again, their size, and the
command that empties each one. Our own tools' leftovers (old CI venvs, pytest and scratch folders in /tmp, unnamed
container images) are not here: tools/clean_caches.py removes those before every local CI run (owner, 22-11-2026:
"handled by that app only", the rest in this app).

Only the standard library here: the hourly check (--remind) runs without a window."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from bazzite_console_core.platform import config_home
from bazzite_console_core.steam import find_steam

DUMPS = Path("/var/lib/systemd/coredump")
NOTIFY_FROM = 1 << 30                   # the hourly check says so from this much garbage on
NOTIFY_AGAIN = 24 * 3600                # and again a day later, or sooner when it grew by NOTIFY_FROM
SHOWN_FROM = 1 << 20                    # a place with less than this is left out of the list
ALWAYS_SHOWN = ("trash",)               # but these show whenever they hold a file (owner, 24-11-2026: the Trash)


@dataclass
class Garbage:
    """One place that can be emptied. *command* empties it; *root*: it runs through pkexec, which asks for the
    password. *kept*: the folders in it that the command leaves, not measured."""
    key: str
    what: str
    where: Path
    why: str
    command: list[str]
    root: bool = False
    kept: tuple[str, ...] = ()
    size: int = 0
    files: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def command_text(self) -> str:
        return shlex.join(["sudo", *self.command] if self.root else self.command)


def measure(path: Path, kept: tuple[str, ...] = ()) -> tuple[int, int]:
    """The bytes and files under *path*, without its folders named in *kept*; what cannot be read counts as nothing.
    Links are not followed."""
    size = files = 0
    for folder, dirs, names in os.walk(path, onerror=lambda _error: None):
        if folder == str(path):
            dirs[:] = [name for name in dirs if name not in kept]
        for name in names:
            try:
                size += os.lstat(os.path.join(folder, name)).st_size
                files += 1
            except OSError:
                continue
    return size, files


def _empty(path: Path, depth: int = 1) -> list[str]:
    """find's command that deletes everything under *path* and keeps the folder itself (*depth* 2 keeps its
    subfolders too)."""
    return ["find", str(path), "-mindepth", str(depth), "-delete"]


def places(home: Path | None = None, steam: Path | None = None, dumps: Path = DUMPS,
           which: Callable[[str], str | None] = shutil.which) -> list[Garbage]:
    """Every place the app looks at, not measured yet."""
    home = home or Path.home()
    steam = steam if steam is not None else find_steam(home)
    found = [Garbage("dumps", "Crash dumps", dumps,
                     "The system keeps a dump of every program that crashed, for a developer to read. They are "
                     "not needed to use the machine. A crash loop can leave gigabytes.", _empty(dumps), root=True)]
    if steam is not None:
        reports = steam / "config" / "htmlcache" / "BrowserMetrics"
        found.append(Garbage("steam-reports", "Steam's crash reports", reports,
                             "Steam's built-in browser writes a report file each time it starts or crashes. Steam "
                             "never needs them again.", _empty(reports)))
    trash = home / ".local" / "share" / "Trash"
    found.append(Garbage("trash", "Trash", trash, "Files you deleted on the desktop. Emptying the Trash removes them "
                         "for good.", _empty(trash, depth=2)))
    thumbnails = home / ".cache" / "thumbnails"
    found.append(Garbage("thumbnails", "Picture previews", thumbnails, "Small previews the file manager made of "
                         "pictures and videos. It makes them again when it needs them.", _empty(thumbnails)))
    pip = home / ".cache" / "pip"
    found.append(Garbage("pip", "pip's download cache", pip, "Python packages pip downloaded once. pip downloads "
                         "them again when you install them once more.", _empty(pip)))
    brew_cache = home / ".cache" / "Homebrew"
    if which("brew"):
        # brew cleanup keeps Homebrew's package index (api) and its compiled Ruby (bootsnap): they would come back
        # as garbage after every Delete
        found.append(Garbage("homebrew", "Homebrew's downloads", brew_cache, "Downloads and old versions Homebrew "
                             "keeps. brew cleanup removes them, and what is installed stays.",
                             ["brew", "cleanup", "--prune=all"], kept=("api", "bootsnap", "tool-selection")))
    return found


def find(home: Path | None = None, steam: Path | None = None, dumps: Path = DUMPS,
         which: Callable[[str], str | None] = shutil.which) -> list[Garbage]:
    """The places that hold garbage now, measured, the largest first."""
    found = []
    for place in places(home, steam, dumps, which):
        place.size, place.files = measure(place.where, place.kept)
        if place.size >= SHOWN_FROM or (place.key in ALWAYS_SHOWN and place.files):
            found.append(place)
    return sorted(found, key=lambda place: place.size, reverse=True)


def size_text(size: int) -> str:
    for unit, step in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if size >= step:
            return f"{size / step:.1f} {unit}"
    return f"{size} B"


def remove(chosen: list[Garbage], run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
           which: Callable[[str], str | None] = shutil.which) -> list[str]:
    """Empties the *chosen* places: the user's with their command, the system's in one pkexec call (one password).
    Returns what went wrong, one line each; empty when all went."""
    problems = []
    for place in [p for p in chosen if not p.root]:
        done = run(place.command, capture_output=True, text=True)
        if done.returncode:
            problems.append(f"{place.what}: {(done.stderr or done.stdout).strip() or f'exit {done.returncode}'}")
    as_root = [p for p in chosen if p.root]
    if as_root:
        if not which("pkexec"):
            return problems + [f"{p.what}: pkexec is missing. Run {p.command_text}" for p in as_root]
        script = " && ".join(shlex.join(p.command) for p in as_root)
        done = run(["pkexec", "sh", "-c", script], capture_output=True, text=True)
        if done.returncode in (126, 127):
            problems.append("Not authorized: the password dialog was canceled or refused.")
        elif done.returncode:
            problems.append((done.stderr or done.stdout).strip() or f"pkexec: exit {done.returncode}")
    return problems


# --------------------------------------------------------------------------------------------- the hourly check
def state_file() -> Path:
    return config_home() / "nexus-garbage-remover" / "notified.json"


def should_notify(total: int, now: float, state: dict) -> bool:
    """Whether the hourly check tells the user about *total* bytes of garbage: from NOTIFY_FROM on, once a day, or
    sooner when it grew by NOTIFY_FROM since the last time."""
    if total < NOTIFY_FROM:
        return False
    last_time, last_size = float(state.get("time", 0)), int(state.get("size", 0))
    return now - last_time >= NOTIFY_AGAIN or total >= last_size + NOTIFY_FROM


def notify_text(found: list[Garbage]) -> str:
    total = sum(place.size for place in found)
    parts = ", ".join(f"{place.what} {size_text(place.size)}" for place in found[:3])
    return f"{size_text(total)} of garbage can be removed: {parts}."


def read_state(path: Path | None = None) -> dict:
    try:
        return json.loads((path or state_file()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_state(total: int, now: float | None = None, path: Path | None = None) -> None:
    path = path or state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"time": now if now is not None else time.time(), "size": total}),
                        encoding="utf-8")
    except OSError:
        pass
