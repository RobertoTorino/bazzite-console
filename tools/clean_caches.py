#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Removes what the development tools leave behind on this computer (owner, 20-11-2026: "make it a service or
feature or script or whatever that does this automatically"). /tmp is kept in memory on Bazzite: 3.7 GB of old test
files and scratch folders in it left the computer short of memory, and a CI run here was killed for it.

    python3 tools/clean_caches.py             # remove, and say what went
    python3 tools/clean_caches.py --dry-run   # only say what would go
    python3 tools/clean_caches.py --quiet     # say nothing when nothing went

tools/ci-local.sh runs it before every run, so nobody has to remember it. What goes:

- a venv of tools/ci-local.sh that no run used for a week (tools/ci_local.py marks the ones it uses): a job whose
  requirements changed gets a new venv, and the old one stayed for good (61 venvs, 18 GB);
- the folders pytest keeps of its last runs in /tmp, once they are a day old (./test.sh keeps none of a test that
  passed; a run by hand keeps its last three, 1.1 GB each for PS5 PCSX2 Manager's memory cards);
- the scratch folders an AI assistant left in /tmp (claude-<user id>), once nothing in one changed for six
  hours (owner, 20-11-2026: "make sure your cache is cleaned up frequently"; two held 2.4 GB of memory);
- container images without a name (podman image prune): what a rebuilt image leaves.

It only reports the crash dumps the system keeps (/var/lib/systemd/coredump) when they pass 1 GB: removing them
takes sudo, and it names the command. Nothing outside these places is touched, and nothing of another user."""

from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

CI_CACHE = "bazzite-console-ci-local"   # tools/ci-local.sh's folder in ~/.cache
USED = ".last-used"                     # in a venv: tools/ci_local.py touches it when a job takes the venv
DAY = 24 * 3600
VENV_AGE = 7 * DAY                      # a venv no run used this long goes
TEMP_AGE = DAY                          # pytest's folders older than this go
SCRATCH_AGE = 6 * 3600                  # an assistant's scratch folder without a change this long goes
SMALL = 1 << 20                         # what is smaller is counted, not listed
DUMPS = Path("/var/lib/systemd/coredump")
DUMPS_LIMIT = 1 << 30                   # crash dumps are reported from this size on
DUMPS_COMMAND = f"sudo find {DUMPS} -type f -delete"


@dataclass(frozen=True)
class Found:
    """Something to remove: where, how big, and why."""
    path: Path
    size: int
    why: str


def cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")


def tree(path: Path) -> tuple[int, float]:
    """The size of everything under *path* in bytes and the time its newest file was written (the folder's own
    time when it holds no file); links are not followed."""
    size, newest = 0, 0.0
    for folder, _dirs, files in os.walk(path):
        for name in files:
            try:
                info = os.lstat(os.path.join(folder, name))
            except OSError:
                continue                    # gone meanwhile, or not ours to read
            size += info.st_size
            newest = max(newest, info.st_mtime)
    return size, newest or path.lstat().st_mtime


def mine(path: Path) -> bool:
    """A real folder of this user: never a link, never another user's."""
    try:
        return path.is_dir() and not path.is_symlink() and path.lstat().st_uid == os.getuid()
    except OSError:
        return False


def stale_venvs(venvs: Path, now: float, write: bool = True) -> list[Found]:
    """The venvs under *venvs* whose mark is older than VENV_AGE. A venv without a mark is from before the marks:
    it gets one now (unless *write* is off) and stays, so the first run removes nothing a job still uses."""
    found = []
    for venv in sorted(venvs.iterdir()) if venvs.is_dir() else []:
        if not mine(venv):
            continue
        mark = venv / USED
        if not mark.exists():
            if write:
                mark.touch()
            continue
        if now - mark.stat().st_mtime > VENV_AGE:
            found.append(Found(venv, tree(venv)[0], "a ci-local venv no run used for a week"))
    return found


def old_pytest_runs(temp: Path, user: str, now: float) -> list[Found]:
    """pytest's folders of earlier runs (<temp>/pytest-of-<user>/pytest-<n>) whose newest file is a day old."""
    found = []
    base = temp / f"pytest-of-{user}"
    for run in sorted(base.glob("pytest-[0-9]*")) if mine(base) else []:
        if mine(run):
            size, newest = tree(run)
            if now - newest > TEMP_AGE:
                found.append(Found(run, size, "pytest's files of a run a day ago or longer"))
    return found


def old_scratch(temp: Path, uid: int, now: float) -> list[Found]:
    """The session folders in an AI assistant's scratch folder (<temp>/claude-<uid>/<project>/<session>) in which
    nothing changed for six hours: a session that still runs writes to its folder, so it stays."""
    found = []
    base = temp / f"claude-{uid}"
    for project in sorted(base.iterdir()) if mine(base) else []:
        for session in sorted(project.iterdir()) if mine(project) else []:
            if mine(session):
                size, newest = tree(session)
                if now - newest > SCRATCH_AGE:
                    found.append(Found(session, size, "an assistant's scratch folder, six hours without a change"))
    return found


def crash_dumps(folder: Path = DUMPS) -> int:
    """The size of the system's crash dumps in bytes, 0 when they cannot be read."""
    try:
        return sum(entry.stat().st_size for entry in os.scandir(folder) if entry.is_file(follow_symlinks=False))
    except OSError:
        return 0


def prune_images(dry_run: bool) -> int:
    """Removes the container images without a name; how many went (0 without podman, and on a dry run how many
    would go)."""
    podman = shutil.which("podman")
    if not podman:
        return 0
    command = [podman, "images", "--filter", "dangling=true", "-q"] if dry_run else [podman, "image", "prune", "-f"]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return len(done.stdout.split()) if done.returncode == 0 else 0


def size_text(size: int) -> str:
    for unit, step in (("GB", 1 << 30), ("MB", 1 << 20)):
        if size >= step:
            return f"{size / step:.1f} {unit}"
    return f"{size // 1024} kB"


def find(now: float, write: bool = True) -> list[Found]:
    temp = Path(tempfile.gettempdir())
    return (stale_venvs(cache_home() / CI_CACHE / "venvs", now, write)
            + old_pytest_runs(temp, getpass.getuser(), now) + old_scratch(temp, os.getuid(), now))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="only say what would go")
    parser.add_argument("--quiet", action="store_true", help="say nothing when nothing went")
    args = parser.parse_args(argv)
    found = find(time.time(), write=not args.dry_run)
    verb = "would go" if args.dry_run else "removed"
    small = 0
    for item in found:
        if not args.dry_run:
            shutil.rmtree(item.path, ignore_errors=True)
        if item.size < SMALL:
            small += 1                      # dozens of empty scratch folders: one line for them all
        else:
            print(f"{verb}: {item.path} ({size_text(item.size)}): {item.why}")
    if small:
        print(f"{verb}: {small} folder{'s' if small != 1 else ''} under 1 MB")
    images = prune_images(args.dry_run)
    if images:
        print(f"{verb}: {images} container image{'s' if images != 1 else ''} without a name")
    if found:
        print(f"{verb}: {size_text(sum(item.size for item in found))} in all")
    elif not images and not args.quiet:
        print("Nothing to remove.")
    dumps = crash_dumps()
    if dumps > DUMPS_LIMIT:
        print(f"The system keeps {size_text(dumps)} of crash dumps; to remove them: {DUMPS_COMMAND}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
