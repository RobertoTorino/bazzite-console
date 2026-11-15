#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The CI matrix of the suite, read from its folders (owner, 30-10-2026, stage 2 of the release redesign: a new app
needs no workflow edit), for the plan job of ci.yml and for tools/ci_local.py:

    python3 tools/ci_matrix.py pytest           # dirs=<JSON list>: every folder with tests/

pytest lists the folders that have tests/ (core, dev/<name>, portal, tools, apps/<name>, ...), in alphabetical
order. The line is key=<JSON>, for $GITHUB_OUTPUT (tee -a), and the workflow's matrix reads it with fromJSON.
tools/tests/test_layout.py checks the folders against this list."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIPPED = {".git", "site", "node_modules", "__pycache__"}      # never a test folder's parent


def test_folders(folder: Path, root: Path) -> list[str]:
    """Every folder under *folder* with a tests/ folder, relative to *root* (posix), sorted."""
    found = []
    for tests in folder.glob("**/tests"):
        parts = tests.relative_to(root).parts
        if tests.is_dir() and not (set(parts) & SKIPPED) and not any(p.startswith(".venv") for p in parts):
            found.append(tests.parent.relative_to(root).as_posix())
    return sorted(found)


def pytest_dirs(root: Path = ROOT) -> list[str]:
    """The pytest matrix: the repository's folders with tests/."""
    return test_folders(root, root)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("matrix", choices=("pytest",))
    parser.parse_args(argv)
    print(f"dirs={json.dumps(pytest_dirs())}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
