#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""CI check that every CHANGELOG keeps the entries it had at a base commit."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_HEADER = re.compile(r"^Changelog: .*$", re.M)


def git(root: Path, *args: str) -> str | None:
    probe = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, capture_output=True, text=True)
    cwd = Path(probe.stdout.strip()) if probe.returncode == 0 else root
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def repository(root: Path) -> tuple[Path, Path]:
    """Return the enclosing git root and the project's path within it."""
    found = git(root, "rev-parse", "--show-toplevel")
    if found is None:
        raise ValueError(f"{root} is not inside a Git repository")
    git_root = Path(found.strip()).resolve()
    return git_root, root.resolve().relative_to(git_root)


def pathspec(root: Path) -> list[str]:
    _, prefix = repository(root)
    return ["--", prefix.as_posix()] if prefix != Path(".") else []


def headers(text: str) -> Counter[str]:
    return Counter(match.group(0).rstrip() for match in _HEADER.finditer(text))


def changelog_paths(root: Path, base: str) -> dict[str, str]:
    """Project-relative CHANGELOG names mapped to their paths in the base tree."""
    _, prefix = repository(root)
    scoped = git(root, "ls-tree", "-r", "--name-only", base, *pathspec(root)) or ""
    names = [Path(path) for path in scoped.splitlines() if Path(path).name == "CHANGELOG"]
    if names:
        return {path.relative_to(prefix).as_posix() if prefix != Path(".") else path.as_posix():
                path.as_posix() for path in names}

    # A standalone project may have been moved under a directory in the working tree but not yet staged.
    # Compare its files with the old root paths rather than claiming that there was no history.
    if prefix != Path("."):
        listing = git(root, "ls-tree", "-r", "--name-only", base) or ""
        names = [Path(path) for path in listing.splitlines()
                 if Path(path).name == "CHANGELOG" and len(Path(path).parts) > 1]
        return {path.as_posix(): path.as_posix() for path in names}
    return {}


def changelogs(root: Path, base: str) -> list[str]:
    """The project's CHANGELOG files at *base*, relative to its root."""
    return list(changelog_paths(root, base))


def renamed(root: Path, base: str) -> dict[str, str]:
    """CHANGELOG paths git sees renamed since *base*, with paths relative to the project root."""
    _, prefix = repository(root)
    found: dict[str, str] = {}
    for target in (["HEAD"], []):
        output = git(root, "diff", "-M", "--name-status", "--diff-filter=R", base, *target,
                     *pathspec(root)) or ""
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) != 3 or not parts[0].startswith("R"):
                continue
            old, new = (Path(part) for part in parts[1:])
            if prefix != Path("."):
                try:
                    old, new = old.relative_to(prefix), new.relative_to(prefix)
                except ValueError:
                    continue
            if old.name == "CHANGELOG" and new.name == "CHANGELOG":
                found.setdefault(old.as_posix(), new.as_posix())
    return found


def check(root: Path, base: str) -> list[str]:
    """What each CHANGELOG lost since *base*; an empty list means no history was lost."""
    problems = []
    sources = changelog_paths(root, base)
    moves = renamed(root, base)
    for path, source in sources.items():
        current = root / moves.get(path, path)
        if not current.is_file():
            if current.parent.is_dir():
                problems.append(f"{path}: removed, while its folder is still there")
            continue
        original = git(root, "show", f"{base}:{source}") or ""
        lost = headers(original) - headers(current.read_text(encoding="utf-8"))
        if lost:
            total = sum(headers(original).values())
            newest = next(header for header in headers(original) if header in lost)
            problems.append(f"{path}: {sum(lost.values())} of the {total} entries it had at {base} are gone "
                            f"(the newest: {newest!r})")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="commit to compare with (the last push or pull-request base)")
    args = parser.parse_args(argv)
    if not args.base:
        print("OK: no --base, nothing to compare with")
        return 0
    if git(ROOT, "rev-parse", "--verify", "-q", f"{args.base}^{{commit}}") is None:
        print(f"ERROR: {args.base} is not a commit here", file=sys.stderr)
        return 1
    problems = check(ROOT, args.base)
    for problem in problems:
        print(f"ERROR: {problem}", file=sys.stderr)
    if problems:
        print("A CHANGELOG is history: restore the lost entries from the base commit.", file=sys.stderr)
        return 1
    print(f"OK: {len(changelogs(ROOT, args.base))} CHANGELOGs keep every entry they had at {args.base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
