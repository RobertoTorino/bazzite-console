#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The CI matrix of the suite, read from its folders (owner, 30-10-2026, stage 2 of the release redesign: a new app
needs no workflow edit), for the plan job of ci.yml and for tools/ci_local.py:

    python3 tools/ci_matrix.py pytest                # dirs=<JSON list>: every folder with tests/
    python3 tools/ci_matrix.py plan [--base COMMIT]  # what a push runs: dirs, installers, native, docs, full

pytest lists the folders that have tests/ (core, dev/<name>, portal, tools, apps/<name>, ...), in alphabetical
order. Each line is key=<value>, for $GITHUB_OUTPUT (tee -a); the workflow's matrix reads dirs with fromJSON.
tools/tests/test_layout.py checks the folders against this list.

plan is what CI runs for the files that differ from COMMIT (owner, 17-11-2026: a change to one app ran all 47 jobs,
here and on GitHub, and one stalled job held the release): the test folders with a changed file, tools always (its
tests hold the repository's rules), and the folders whose tests read a shared file that changed (portal/apps.toml,
icons/categories.toml); the installer tests that name a changed app, folder or tool; the native job when the
app with the native core changed; the wiki unless only Python code changed. Without --base, when the commit is not known here,
or when something every job stands on changed (core, the workflows, this tool, the local CI, the development
requirements), it is everything: full=true."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
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


# A change to one of these is a change to every job: what the jobs run on, not what one of them tests.
EVERYTHING = ("core/", ".github/workflows/", "tools/ci_matrix.py", "tools/ci_local.py", "tools/ci-local.sh",
              "tools/ci-local/", "tools/ci-qt-libs.sh", "requirements-dev.txt", "tools/installer-tests/shims.sh")
ALWAYS = "tools"                        # its tests hold the repository's rules: the layout, the manifest, the wiki
SHARED = ("portal/apps.toml", "icons/categories.toml")      # read by the tests of other folders, by their file name
NATIVE = "apps/*/native/Cargo.toml"     # an app with a native core (Remote Play): the native job is its own
INSTALLER_TESTS = "tools/installer-tests"
NOT_TESTS = {"shims.sh"}
LAST = "release.sh"                     # the release tarballs end to end: the longest, named last
_PYTHON_ONLY = re.compile(r"^(apps|dev|core|portal|tools)/.+\.py$")     # a change the wiki does not show


def changed_files(base: str, root: Path = ROOT) -> list[str] | None:
    """The files that differ from the commit *base*, as git names them: the commits since, and what is not committed
    yet. None when git cannot tell (the commit is not here: a new branch, a forced push)."""
    try:
        diff = subprocess.run(["git", "diff", "--name-only", base, "--"], cwd=root, capture_output=True, text=True,
                              timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return diff.stdout.split("\n")[:-1] if diff.returncode == 0 else None


def installer_tests(root: Path = ROOT) -> list[str]:
    """Every installer test, by file name, the release tarballs last."""
    names = sorted(p.name for p in (root / INSTALLER_TESTS).glob("*.sh") if p.name not in NOT_TESTS)
    return [n for n in names if n != LAST] + [n for n in names if n == LAST]


def native_apps(root: Path = ROOT) -> list[str]:
    """The folders of the apps with a native core, as a path's start: ["apps/consoles/"]."""
    return [cargo.parent.parent.relative_to(root).as_posix() + "/" for cargo in sorted(root.glob(NATIVE))]


def unit_of(path: str) -> str:
    """The folder a file belongs to, as the installer tests name it: apps/<name>, dev/<name>, else its first
    folder (portal, tools); the file itself at the root."""
    parts = path.split("/")
    return "/".join(parts[:2]) if parts[0] in ("apps", "dev") and len(parts) > 2 else parts[0]


def reads(folder: Path, name: str) -> bool:
    """Whether a test of *folder* names the file *name* (apps.toml): it reads it, so its change is that folder's."""
    return any(name in test.read_text(encoding="utf-8", errors="replace") for test in (folder / "tests").rglob("*.py"))


def plan(changed: list[str] | None, root: Path = ROOT) -> dict[str, object]:
    """What CI runs for a push that changes *changed* (None: unknown, so everything)."""
    dirs, tests = pytest_dirs(root), installer_tests(root)
    if changed is None or any(path.startswith(EVERYTHING) for path in changed):
        return {"dirs": dirs, "installers": " ".join(tests), "native": True, "docs": True, "full": True}
    chosen = {ALWAYS} & set(dirs)
    for path in changed:
        owners = [d for d in dirs if path.startswith(d + "/")]
        if owners:
            chosen.add(max(owners, key=len))
    for shared in SHARED:
        if shared in changed:
            chosen |= {d for d in dirs if reads(root / d, shared.rsplit("/", 1)[1])}
    units = {unit_of(path) for path in changed}
    picked = []
    for name in tests:
        text = (root / INSTALLER_TESTS / name).read_text(encoding="utf-8", errors="replace")
        every_app = "apps/*" in text and any(u.startswith(("apps/", "dev/")) for u in units)
        named = any(re.search(rf"(?<![\w-]){re.escape(u)}(?![\w-])", text) for u in units if "/" in u) \
            or ("portal" in units and "portal/" in text)
        tool = any(path in text for path in changed if path.startswith("tools/"))
        if f"{INSTALLER_TESTS}/{name}" in changed or every_app or named or tool:
            picked.append(name)
    return {"dirs": [d for d in dirs if d in chosen], "installers": " ".join(picked),
            "native": any(path.startswith(app) for path in changed for app in native_apps(root)),
            "docs": any(not _PYTHON_ONLY.match(path) for path in changed), "full": False}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("matrix", choices=("pytest", "plan"))
    parser.add_argument("--base", default="", help="plan: the commit the push is compared with")
    args = parser.parse_args(argv)
    if args.matrix == "pytest":
        print(f"dirs={json.dumps(pytest_dirs())}")
        return 0
    for key, value in plan(changed_files(args.base) if args.base else None).items():
        print(f"{key}={value if isinstance(value, str) else json.dumps(value)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
