#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that each app, core, and portal version copy matches its VERSION file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = re.compile(r"\d+\.\d+\.\d+")
PATTERNS = {
    ".py": re.compile(r'^__version__ = "([^"]+)"[ \t]*(?:#[^\n]*)?$', re.M),
    ".sh": re.compile(r'^VERSION="([^"]+)"[ \t]*(?:#[^\n]*)?$', re.M),
    ".toml": re.compile(r'^version = "([^"]+)"', re.M),
}
CANDIDATES = {
    ".py": re.compile(r"""^__version__\s*=\s*["'].*$""", re.M),
    ".sh": re.compile(r"""^VERSION=["']?\d.*$""", re.M),
}


def units(root: Path) -> list[Path]:
    """The core, app, and portal folders with their own VERSION files."""
    folders = [root / "portal", root / "core"]
    apps = root / "apps"
    if apps.is_dir():
        folders.extend(path for path in apps.iterdir() if path.is_dir())
    dev = root / "dev"
    if dev.is_dir():
        folders.extend(path for path in dev.iterdir() if path.is_dir() and (path / "VERSION").is_file())
    return [path for path in folders if path.is_dir()]


def version_pattern(path: Path) -> re.Pattern[str] | None:
    if path.name == "Cargo.lock":
        manifest = path.with_name("Cargo.toml")
        if not manifest.is_file():
            return None
        name = re.search(r'^name = "([^"]+)"', manifest.read_text(encoding="utf-8"), re.M)
        if name is None:
            return None
        return re.compile(r'^\[\[package\]\]\nname = "' + re.escape(name.group(1)) +
                          r'"\nversion = "([^"]+)"', re.M)
    return PATTERNS.get(path.suffix)


def check(root: Path = ROOT, selected: list[Path] | None = None) -> list[str]:
    """Version copies that are malformed or differ from the owning folder's VERSION."""
    errors = []
    for unit in (units(root) if selected is None else selected):
        version_file = unit / "VERSION"
        if not version_file.is_file():
            errors.append(f"{unit.relative_to(root)}: no VERSION file")
            continue
        expected = version_file.read_text(encoding="utf-8").strip()
        if not VERSION.fullmatch(expected):
            errors.append(f"{version_file.relative_to(root)}: {expected!r} is not x.y.z")
            continue
        for path in unit.rglob("*"):
            if not path.is_file() or {"tests", "__pycache__", "target", ".venv"} & set(path.parts):
                continue
            pattern = version_pattern(path)
            if pattern is None:
                continue
            text = path.read_text(encoding="utf-8")
            candidate = CANDIDATES.get(path.suffix)
            if candidate is not None:
                for line in candidate.findall(text):
                    if not pattern.fullmatch(line):
                        errors.append(f"{path.relative_to(root)}: version copy not in a supported form: {line}")
            for found in pattern.findall(text):
                if found != expected:
                    errors.append(f"{path.relative_to(root)}: {found} != VERSION {expected}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--suite", help="suite name (the check remains scoped to this suite)")
    parser.add_argument("--nexus", action="store_true", help="check the shared core and developer tools")
    args = parser.parse_args(argv)
    if args.suite and args.suite not in {ROOT.name, "."}:
        parser.error(f"{args.suite!r} is not this suite ({ROOT.name})")
    selected = units(ROOT)
    if args.nexus:
        selected = [unit for unit in selected if unit.name == "core" or unit.parent.name == "dev"]
    errors = check(ROOT, selected)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"OK: versions in {len(selected)} core, app, and portal folders match their VERSION files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
