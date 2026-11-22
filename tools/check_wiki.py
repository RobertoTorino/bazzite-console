# SPDX-License-Identifier: GPL-3.0-or-later
"""The wiki's sections to read again after a change (owner, 22-11-2026: "keep it in sync so it stays accurate"): each
section that names a changed file, but did not change itself.

    python3 tools/check_wiki.py --base origin/main            # what changed since origin/main, the work tree with it
    python3 tools/check_wiki.py --base <commit> --head <commit>   # between two commits

A section is a page's part under one heading. It names a file when a code span in it holds the file's path (or a
folder above it), its file name (`emulator.py`), for a module of core its module name (`builds`), or a name the file
defines: a function, a class or a constant (`steam_running()`, `KNOWN_VERSION`). An app's chapter (docs/apps/<key>.md)
names all of apps/<key>/. A test, a CHANGELOG, a VERSION, a LICENSE, a dot-file such as .gitignore or a requirements-dev.txt is no reason to
read a page again, and neither is a generated file (DESIGN.md, its color samples, ALL-TESTS.md) or a picture.

It lists what to read; it decides nothing. Read each section against the change and correct what is no longer true.
Exit code 0 always: the list is the answer. Only the standard library."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_names import PATH, spans  # noqa: E402

DEFINES = re.compile(r"^(?:def|class|async def) ([A-Za-z_]\w+)|^([A-Z][A-Z0-9_]{3,}) *[:=]", re.M)
COMMON = {"main", "run", "setup", "install", "start", "stop", "build", "check", "close", "refresh", "show", "read",
          "write", "load", "save", "parse", "update", "apply", "remove", "VERSION", "ROOT", "INFO", "APP_ID",
          "APP_NAME"}                                       # names too common to point at one file
SEEN: dict[str, int] = {}                           # how many files define each name (review() fills it)
SHARED = {"main_window.py", "__init__.py", "__main__.py", "install.sh", "run.sh", "README.md", "conftest.py",
          "requirements.txt", "requirements-dev.txt"}       # file names every app has: no reason by themselves


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def changed(base: str, head: str | None) -> list[str]:
    """The files changed since *base*: up to *head*, or with the work tree and new files when there is no head."""
    if head:
        names = git("diff", "--name-only", f"{base}...{head}").split()
    else:
        names = git("diff", "--name-only", base).split() + git("ls-files", "--others", "--exclude-standard").split()
    return sorted(set(names))


def counts(name: str) -> bool:
    """Whether a change of this file is a reason to read the wiki again."""
    parts = name.split("/")
    return not ("tests" in parts or parts[-1].startswith(".") or name.startswith(("docs/", "design/"))
                or parts[-1] in ("CHANGELOG", "VERSION", "LICENSE", "requirements-dev.txt", "DESIGN.md", "ALL-TESTS.md")
                or Path(name).suffix in (".svg", ".webp", ".png", ".ogg", ".wav"))


def everywhere(root: Path) -> dict[str, int]:
    """How many of the repository's Python files define each name: a constant defined in several points at none."""
    found: dict[str, int] = {}
    for path in root.rglob("*.py"):
        if any(part.startswith(".venv") or part in ("tests", "site") for part in path.parts):
            continue
        for a, b in DEFINES.findall(path.read_text(encoding="utf-8", errors="replace")):
            found[a or b] = found.get(a or b, 0) + 1
    return found


def defined(name: str, head: str | None) -> set[str]:
    """The functions, classes and constants a Python file defines, as the change leaves it."""
    if not name.endswith(".py"):
        return set()
    try:
        text = git("show", f"{head}:{name}") if head else (ROOT / name).read_text(encoding="utf-8", errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {a or b for a, b in DEFINES.findall(text)} - COMMON


def sections(text: str) -> list[tuple[str, str]]:
    """A page's parts: (heading, text) for the part above the first heading and under each heading."""
    out, title, lines, fenced = [], "", [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and re.match(r"#{1,4} ", line):
            out.append((title, "\n".join(lines)))
            title, lines = line.lstrip("#").strip(), []
        else:
            lines.append(line)
    out.append((title, "\n".join(lines)))
    return [(t, body) for t, body in out if body.strip()]


def anchor(title: str) -> str:
    """MkDocs' anchor of a heading."""
    return re.sub(r"[^\w\- ]", "", title.lower()).strip().replace(" ", "-")


def reasons(body: str, files: dict[str, set[str]]) -> list[str]:
    """The changed files a section names, each with how."""
    found = []
    named = spans(body)
    for name, names in files.items():
        stem = Path(name).stem
        mine = {n for n in names if not n.isupper() or SEEN.get(n, 0) <= 1}
        module = "/_core/" in f"/{name}" or re.match(r"core/\w+_core/", name)
        for span in named:
            path = PATH.fullmatch(span.rstrip(".,:;)/"))
            if path and (name == path.group(0) or name.startswith(path.group(0).rstrip("/") + "/")):
                found.append(f"{name} (its path)")
                break
            word = re.sub(r"\(\)$", "", span).split(".")[-1]
            if span == Path(name).name and span not in SHARED:
                found.append(f"{name} (its file name)")
                break
            if module and span == stem:
                found.append(f"{name} (core's module)")
                break
            qualifier = re.sub(r"\(\)$", "", span).split(".")[-2] if "." in span else ""
            if word in mine and (word.isupper() or span == f"{word}()" or qualifier == stem):
                found.append(f"{name} (`{word}` is defined there)")
                break
    return found


def page_text(name: str, ref: str | None, root: Path = ROOT) -> str:
    """A page at *ref*, or in the work tree; "" when it is not there."""
    try:
        return git("show", f"{ref}:{name}") if ref else (root / name).read_text(encoding="utf-8")
    except (OSError, subprocess.CalledProcessError):
        return ""


def review(base: str, head: str | None = None, root: Path = ROOT) -> list[str]:
    """The sections to read again: "page#anchor: why", one line each. A section that changed itself is left out,
    also when other sections of its page did not change."""
    names = changed(base, head)
    files = {name: defined(name, head) for name in names if counts(name)}
    SEEN.clear()
    SEEN.update(everywhere(root))
    out = []
    for page in sorted((root / "docs").rglob("*.md")):
        name = page.relative_to(root).as_posix()
        text = page_text(name, head, root)
        before = dict(sections(page_text(name, base, root))) if name in names else None
        app = f"apps/{page.stem}/" if name.startswith("docs/apps/") else ""
        whole = [n for n in files if app and n.startswith(app)]
        if whole and name not in names:
            out.append(f"{name}: the app's chapter, and its app changed: {', '.join(whole)}")
            continue
        for title, body in sections(text):
            if before is not None and before.get(title) != body:
                continue                                    # this section changed with the code
            why = reasons(body, files)
            if why:
                out.append(f"{name}#{anchor(title)}: {', '.join(why)}" if title else f"{name}: {', '.join(why)}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main", help="the commit to compare with (default origin/main)")
    parser.add_argument("--head", help="the commit the change ends at (default: the work tree)")
    args = parser.parse_args(argv)
    found = review(args.base, args.head)
    if not found:
        print("No wiki section names a changed file without changing itself.")
        return 0
    print(f"{len(found)} wiki sections name a changed file. Read each against the change:")
    for line in found:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
