#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""CI check: every version hard-coded in an app or in core (Python ``__version__ = "x.y.z"``, shell
``VERSION="x.y.z"``, pyproject and Cargo.toml ``version = "x.y.z"``, and a Rust crate's own entry in its
Cargo.lock) must equal that folder's VERSION file. VERSION is the single source; the literals exist so each script
and package still works on its own. Cargo.lock matters because CI builds with --locked, which fails when the lock
file's version of the crate differs from Cargo.toml. The development apps (dev/) have no VERSION.

    python3 tools/check_versions.py                        # core, the portal and the apps"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = {                            # a comment may follow on the line
    ".py": re.compile(r'^__version__ = "([^"]+)"[ \t]*(?:#[^\n]*)?$', re.M),
    ".sh": re.compile(r'^VERSION="([^"]+)"[ \t]*(?:#[^\n]*)?$', re.M),
    ".toml": re.compile(r'^version = "([^"]+)"', re.M),         # pyproject.toml [project] version, Cargo.toml
}


def cargo_lock_pattern(lock: Path) -> re.Pattern | None:
    """The version of the crate itself in a Cargo.lock (the crate named in the Cargo.toml next to it), as group 1;
    None when there is no such Cargo.toml."""
    manifest = lock.with_name("Cargo.toml")
    if lock.name != "Cargo.lock" or not manifest.is_file():
        return None
    name = re.search(r'^name = "([^"]+)"', manifest.read_text(encoding="utf-8"), re.M)
    if name is None:
        return None
    return re.compile(r'^\[\[package\]\]\nname = "' + re.escape(name.group(1)) + r'"\nversion = "([^"]+)"', re.M)


# A line that assigns a literal version: one the pattern cannot read is an error, not a copy that is skipped (and
# then left behind by the Nexus Release Tool's bump, which changes exactly the copies found here). Lines that read VERSION at
# run time (VERSION=$(...), __version__ = _read_version()) are no copies and stay out.
CANDIDATES = {".py": re.compile(r"""^__version__\s*=\s*["'].*$""", re.M),
              ".sh": re.compile(r"""^VERSION=["']?\d.*$""", re.M)}


def unreadable(path: Path, text: str) -> list[str]:
    """The lines of *text* that look like a version copy but do not match its pattern."""
    candidate, pattern = CANDIDATES.get(path.suffix), PATTERNS.get(path.suffix)
    if candidate is None:
        return []
    return [line for line in candidate.findall(text) if not pattern.fullmatch(line)]


def version_pattern(path: Path) -> re.Pattern | None:
    """How a version copy looks in this file, or None when the file holds none."""
    if path.name == "Cargo.lock":
        return cargo_lock_pattern(path)
    return PATTERNS.get(path.suffix)


SKIPPED = {"tests", "target", "__pycache__", ".venv"}      # test data, cargo's build output, caches, venvs


def units(root: Path = ROOT) -> list[Path]:
    """The folders with a VERSION of their own: core, the portal and the apps (the development apps in dev/ have
    none: they are never released)."""
    return [root / "core", root / "portal", *sorted(p for p in (root / "apps").iterdir() if p.is_dir())]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args([] if argv is None else argv)
    errors = []
    checked = 0
    found = units()
    for unit in found:
        version_file = unit / "VERSION"
        if not version_file.is_file():
            errors.append(f"{unit.relative_to(ROOT)}: no VERSION file")
            continue
        want = version_file.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+", want):
            errors.append(f"{version_file.relative_to(ROOT)}: {want!r} is not x.y.z")
        for path in unit.rglob("*"):
            parts = path.relative_to(unit).parts
            if not path.is_file() or set(parts) & SKIPPED or any(p.startswith(".venv") for p in parts):
                continue
            pattern = version_pattern(path)
            if pattern is None:
                continue
            text = path.read_text(encoding="utf-8")
            for line in unreadable(path, text):
                errors.append(f"{path.relative_to(ROOT)}: version copy not in the form check_versions.py reads: {line}")
            for got in pattern.findall(text):
                checked += 1
                if got != want:
                    errors.append(f"{path.relative_to(ROOT)}: {got} != VERSION {want}")
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {checked} versions in {len(found)} folders match their VERSION file")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
