#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ALL-TESTS.md, the list of every test of the suite, written from the tests themselves (owner, 17-11-2026: the
list is kept in step with the tests, and the wiki shows it under Development):

    python3 tools/all_tests.py            # write it again: the tests as they are now, the times as they were
    python3 tools/all_tests.py --run      # run every test folder first, for each test's cases and time
    python3 tools/all_tests.py --check    # exit 1 when the file is not what the first form would write

A row per test function of every folder with tests/ (tools/ci_matrix.py): its file, its name, how many cases a
parametrized test runs, the time it took when that was 0.1 s or more, and what it checks (its docstring's first
sentence, else its name). A row per installer test (tools/installer-tests/*.sh), with the first sentence of its
header. The cases and the times come from a run (--run, one pytest per folder with this Python, so from the
development venv); without one they stay as the file has them, and a new test has none until the next run. That
makes --check a question about the tests alone: tools/tests/test_all_tests.py asks it, so CI fails when a test was
added, renamed or removed without the list. Nexus Release Tool's Commit step writes the file before it adds the
changes."""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET     # the reports are pytest's own, written here a moment before
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ci_matrix  # noqa: E402

NAME = "ALL-TESTS.md"
NATIVE = " (Not run here: it needs the built native module, which CI's native job tests.)"
SKIPPED = " (Skipped here.)"
ROW = re.compile(r"^\| `([^`]+)` \| `([^`]+)` \| (\d*) \| ([\d.]* ?s?) \| (.*) \|$")
FOLDER_TIME = re.compile(r"^(\d+) tests in (\d+) files(?:, ([\d.]+) s in a local run)?\.$")
Kept = dict[tuple[str, str, str], tuple[int, float, str]]       # (folder, file, test): cases, seconds, note


def suite_name(root: Path = ROOT) -> str:
    """The suite's name as its wiki gives it: mkdocs.yml's "site_name: Some Suite". CLAUDE.md is the same in every
    suite and names none."""
    try:
        text = (root / "mkdocs.yml").read_text(encoding="utf-8")
    except OSError:
        return root.name
    found = re.search(r"(?m)^site_name:\s*(.+?)\s*$", text)
    return found[1] if found else root.name


def sentence(doc: str | None, name: str) -> str:
    """What a test checks: its docstring's first sentence, else its name as words."""
    if doc:
        text = " ".join(doc.strip().split("\n\n")[0].split())
        found = re.match(r"(.+?[.!?])(?:\s|$)", text)
        return (found[1] if found else text.rstrip(".:") + ".").replace("|", "\\|")
    words = name.removeprefix("test_").replace("_", " ").strip()
    return (words[:1].upper() + words[1:] + ".") if words else name


def tests_of(path: Path) -> list[tuple[str, str, str | None]]:
    """The tests of a file in the order they are written: (its id in the file, its name, its docstring); a test of
    a class is Class::name."""
    found = []
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            found.append((node.name, node.name, ast.get_docstring(node)))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            found += [(f"{node.name}::{sub.name}", sub.name, ast.get_docstring(sub)) for sub in node.body
                      if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test")]
    return found


def installer_sentence(script: Path) -> str:
    """The first sentence of an installer test's header comment: up to its first colon or full stop, outside
    brackets."""
    lines = []
    for line in script.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.startswith("#"):
            break
        if "SPDX-License-Identifier" not in line:
            lines.append(line.lstrip("# ").strip())
    text, depth = " ".join(lines), 0
    for i, char in enumerate(text):
        depth += (char == "(") - (char == ")")
        if depth == 0 and (char == ":" or (char == "." and text[i + 1:i + 2] in ("", " "))):
            return text[:i] + "."
    return text.rstrip(".") + "."


def kept(text: str) -> tuple[Kept, dict[str, float]]:
    """The cases, times and notes of the file as it is, by test, and each folder's time."""
    rows: Kept = {}
    folders: dict[str, float] = {}
    folder = ""
    for line in text.splitlines():
        if line.startswith("## "):
            folder = line[3:].strip()
        elif (found := FOLDER_TIME.match(line)) and found[3]:
            folders[folder] = float(found[3])
        elif found := ROW.match(line):
            note = next((n for n in (NATIVE, SKIPPED) if found[5].endswith(n)), "")
            rows[(folder, found[1], found[2])] = (int(found[3] or 1), float(found[4].rstrip(" s") or 0), note)
    return rows, folders


def run(folders: list[str], root: Path = ROOT, python: str = sys.executable) -> tuple[Kept, dict[str, float]]:
    """Every folder's tests run once (pytest, offscreen), one after the other: the cases and the seconds of each
    test, and of each folder. A folder whose tests fail still gives its times; the failure is said."""
    rows: dict[tuple[str, str, str], list] = defaultdict(lambda: [0, 0.0, 0])
    times: dict[str, float] = {}
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    with tempfile.TemporaryDirectory(prefix="all-tests-") as temp:
        for folder in folders:
            report = Path(temp) / "junit.xml"
            done = subprocess.run([python, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider",
                                   "-o", "tmp_path_retention_policy=failed", f"--junitxml={report}"], cwd=root / folder, env=env, capture_output=True,
                                  text=True, check=False)
            print(f"  {folder}: {done.stdout.strip().splitlines()[-1] if done.stdout.strip() else done.stderr[-200:]}",
                  flush=True)
            if not report.is_file():
                continue
            tree = ET.parse(report).getroot()
            times[folder] = sum(float(s.get("time", 0)) for s in tree.iter("testsuite"))
            for case in tree.iter("testcase"):
                parts = case.get("classname", "").split(".")
                file = next((p for p in parts if p.startswith("test_")), parts[-1]) + ".py"
                name = case.get("name", "").split("[")[0]
                key = (folder, file, f"{parts[-1]}::{name}" if parts[-1].startswith("Test") else name)
                rows[key][0] += 1
                rows[key][1] += float(case.get("time", 0))
                rows[key][2] += case.find("skipped") is not None
    return ({key: (cases, seconds, SKIPPED if skipped == cases else "") for key, (cases, seconds, skipped)
             in rows.items()}, times)


def write(root: Path = ROOT, values: Kept | None = None, times: dict[str, float] | None = None,
          ran: bool = False) -> str:
    """The file's text. *values* and *times* are a run's, or the file's own; a test without values has no cases and
    no time, after a run the note that it was not run."""
    values, times = values or {}, times or {}
    folders = ci_matrix.pytest_dirs(root)
    scripts = ci_matrix.installer_tests(root)
    sections, summary = [], []
    tests = cases = 0
    for folder in folders:
        files = sorted((root / folder / "tests").rglob("test_*.py"))
        rows = []
        for file in files:
            for key, name, doc in tests_of(file):
                count, seconds, note = values.get((folder, file.name, key), (0, 0.0, NATIVE if ran else ""))
                cases += max(count, 1)
                rows.append(f"| `{file.name}` | `{key}` | {count if count > 1 else ''} | "
                            f"{f'{seconds:.1f} s' if seconds >= 0.05 else ''} | {sentence(doc, name)}{note} |")
        tests += len(rows)
        took = f", {times[folder]:.1f} s in a local run" if folder in times else ""
        summary.append(f"| [{folder}](#{folder.replace('/', '')}) | {len(files)} | {len(rows)} | "
                       f"{f'{times[folder]:.1f} s' if folder in times else ''} |")
        sections.append(f"## {folder}\n\n{len(rows)} tests in {len(files)} files{took}.\n\n"
                        "| File | Test | Cases | Time | What it checks |\n|---|---|---|---|---|\n"
                        + "\n".join(rows) + "\n")
    installers = "\n".join(f"| `{name}` | {installer_sentence(root / ci_matrix.INSTALLER_TESTS / name)} |"
                           for name in sorted(scripts))
    return f"""# All tests ({suite_name(root)})

Every test of the suite, by test folder: the test file, the test, how many cases a parametrized test runs, the time it took when that was 0.1 s or more, and what it checks (its docstring's first sentence, else its name). `tools/all_tests.py` writes this page from the tests, and CI fails when it is not the list of the tests as they are. The cases and the times are of one local pytest run of each folder (`tools/all_tests.py --run`), without the container and package setup each CI job has first; a test added since has none yet.

{tests} test functions ({cases} cases counting the parametrized ones) in {len(folders)} test folders, and {len(scripts)} installer tests.

## Summary

| Test folder | Files | Tests | Time |
|---|---|---|---|
{chr(10).join(summary)}
| **All** | | **{tests}** | **{sum(times.get(f, 0) for f in folders):.0f} s** |

The pytest runs together take the time above. The rest of a local CI run is the setup of each job (a container, Python 3.12 and the job's own packages, once per test folder) and the jobs that are not pytest: the installer tests, the shell checks (shellcheck), the native build (FFmpeg) and the wiki. A push runs the jobs of what it changed, not all of them.

## Installer tests

`tools/installer-tests/`, one per app and the portal; CI runs the ones of what a push changed, side by side.

| Script | What it checks |
|---|---|
{installers}

""" + "\n".join(sections)


def current(root: Path = ROOT) -> str:
    """The file as the tests are now, with the cases and the times it has."""
    path = root / NAME
    values, times = kept(path.read_text(encoding="utf-8")) if path.is_file() else ({}, {})
    return write(root, values, times)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="store_true", help="run every test folder for the cases and the times")
    parser.add_argument("--check", action="store_true", help="exit 1 when the file is not the list of the tests")
    args = parser.parse_args(argv)
    path = ROOT / NAME
    if args.check:
        if path.is_file() and path.read_text(encoding="utf-8") == current():
            return 0
        print(f"{NAME} is not the list of the tests as they are: run python3 tools/all_tests.py", file=sys.stderr)
        return 1
    text = write(ROOT, *run(ci_matrix.pytest_dirs(ROOT)), ran=True) if args.run else current()
    changed = not path.is_file() or path.read_text(encoding="utf-8") != text
    path.write_text(text, encoding="utf-8")
    print(f"{NAME}: {'written' if changed else 'as it was'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
