#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the install tree of one app (or the portal) from the checkout:

    python3 tools/stage_app.py <app|portal> <dest-dir>

<dest-dir> gets the app's own files without development leftovers (tests, venvs, caches) and, when the app imports
bazzite_console_core, a copy of core/bazzite_console_core beside its package: each app ships the core it was tested with, and its
launcher starts from that folder so this copy is the one Python imports. An app also gets its chapter of the
manual (docs/apps/<app>.md) as MANUAL.md, so it can be read without a network.

The app comes from apps/<app> (or portal/), core from core/bazzite_console_core.
The release workflow tars this tree; the portal uses the same function to install from a local checkout."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT                                # the repository is the suite; the functions take another for the tests
SKIP_DIRS = {"tests", "python", "_python", "__pycache__", ".pytest_cache", ".idea", ".venv",
             "target"}                          # cargo's build output (consoles/native)
SKIP_FILES = {"requirements-dev.txt", ".gitignore", ".gitattributes", ".standalone"}
_USES_CORE = re.compile(r"^\s*(from|import)\s+bazzite_console_core\b", re.M)


def _ignore(folder: str, names: list[str]) -> set[str]:
    return {n for n in names
            if n in SKIP_DIRS or n in SKIP_FILES or n.endswith(".pyc") or n.startswith(".venv")}


def uses_core(src: Path) -> bool:
    """Whether a Python file of *src* imports bazzite_console_core. The skipped folders are not entered: cargo's
    target holds thousands of folders that come and go while it builds, and a walk through them failed on one that
    was gone again (FileNotFoundError in tools/nrt.sh --list while CI's native job built beside it, 17-11-2026)."""
    for folder, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".venv")]
        for name in files:
            if name.endswith(".py") and _USES_CORE.search(
                    Path(folder, name).read_text(encoding="utf-8", errors="replace")):
                return True
    return False


def source_dir(name: str, suite: Path = SUITE) -> Path:
    src = suite / "portal" if name == "portal" else suite / "apps" / name
    if not src.is_dir():
        raise SystemExit(f"no such app: {name} (looked in {src})")
    return src


def manual_chapter(name: str, suite: Path = SUITE) -> Path | None:
    chapter = suite / "docs" / "apps" / f"{name}.md"
    return chapter if name != "portal" and chapter.is_file() else None


def core_dir(suite: Path = SUITE) -> Path:
    """core/bazzite_console_core of the suite."""
    return suite / "core" / "bazzite_console_core"


def stage(name: str, dest: Path, suite: Path = SUITE) -> Path:
    """Copy app *name* of *suite* into *dest* (created; must not exist yet), bundle bazzite_console_core when the app uses
    it and add the app's chapter of the manual as MANUAL.md."""
    src = source_dir(name, suite)
    shutil.copytree(src, dest, ignore=_ignore)
    if uses_core(src):
        shutil.copytree(core_dir(suite), dest / "bazzite_console_core", ignore=_ignore)
    chapter = manual_chapter(name, suite)
    if chapter is not None:
        shutil.copyfile(chapter, dest / "MANUAL.md")
    return dest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", help="the app's key, or portal")
    parser.add_argument("dest", type=Path, help="the folder to create")
    args = parser.parse_args(argv)
    if args.dest.exists():
        print(f"{args.dest} exists already", file=sys.stderr)
        return 1
    stage(args.app, args.dest)
    print(f"staged {args.app} in {args.dest}" + (" (with bazzite_console_core)" if (args.dest / "bazzite_console_core").is_dir() else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
