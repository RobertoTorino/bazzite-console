#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The file edits of a release, for the window in main_window.py (and on their own: tools/nrt.sh --list lists
the apps). Nothing here commits, tags or pushes; it prints the git commands for that instead. It needs no PyQt6 and
no bazzite_console_core, so it also runs with the system python3.

A release is one action of the window, Start new release (flow.py writes it with the edits here): each part's new
VERSION, every copy tools/check_versions.py checks and a "Release x.y.z." CHANGELOG entry, the new tags in
portal/apps.toml (their sha256 is the release workflow's) and the portal's version, at least what
tools/check_manifest.py asks. The version offered first follows semantic versioning from the CHANGELOG entries
since the last tag: one that starts with Breaking. asks for a major release, Added. for a minor one, Fixed. for a
patch. A part whose only changes since its tag are those edits (release_only) needs no release.

A withdrawal (owner's decisions, 13-10-2026): an app release that must not be used any more (privacy, security, any
reason) is marked withdrawn in portal/apps.toml with the reason, and on GitHub (a pre-release titled "Withdrawn: ...",
so no update check offers it; the release itself stays). The next portal release shows the app as not available and
removes it from the boards that have it. Test it on a board with Test withdrawal before that portal is released."""

from __future__ import annotations

import datetime
import importlib.util
import json
import re
import shlex
import urllib.error
import urllib.request
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[3]        # dev/nrt/nexus_release_tool/plan.py: the checkout, the suite
TOOLS = CHECKOUT / "tools"              # the suite's tools (check_versions.py, stage_app.py, suites.py)
TAG_SCRIPT = "tools/tag-release.sh"     # tags only a pushed HEAD that holds the version: never one before the bump
ALL_TESTS = "tools/all_tests.py"        # ALL-TESTS.md from the tests, before a commit
CI_LOCAL = "tools/ci-local.sh"          # CI's jobs here, in a container: the push only when they pass
VERSIONS_CHECK = "tools/check_versions.py"
CHECK_SCRIPT = "tools/check-release.sh"     # the board checks of a portal release (local|release|draft|remove)
MANIFEST_CHECK = "tools/check_manifest.py"
CHECKOUT_ONLY = ".checkout-only"        # an app folder with this marker runs from the checkout and is never released
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def _load(name: str, folder: Path = TOOLS):
    spec = importlib.util.spec_from_file_location(name, folder / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check_versions = _load("check_versions")
stage_app = _load("stage_app")
suite_tools = _load("suites")
check_manifest = _load("check_manifest")    # the manifest's parser and the pin tool, as the portal reads apps.toml
pin_app = _load("pin_app")


def tag_prefix(root: Path) -> str:
    """What the suite's release tags start with (its TAG_PREFIX, tools/suites.py): "ps5-"."""
    return suite_tools.tag_prefix(root)


def manifest_path(root: Path) -> Path:
    return root / "portal" / "apps.toml"


def write_manifest(root: Path, text: str) -> list[Path]:
    """Writes apps.toml. Returns the files written."""
    path = manifest_path(root)
    path.write_bytes(text.encode("utf-8"))
    return [path]


def version_tuple(version: str) -> tuple[int, int, int]:
    a, b, c = (int(x) for x in version.split("."))
    return a, b, c


def next_versions(version: str) -> dict[str, str]:
    a, b, c = version_tuple(version)
    return {"patch": f"{a}.{b}.{c + 1}", "minor": f"{a}.{b + 1}.0", "major": f"{a + 1}.0.0"}


def check_new_version(current: str, new: str, released: bool) -> str:
    """"" when *new* can be released after *current*, otherwise why not. A version that was never tagged (the
    first release, 0.1.0) can be released as it is."""
    if not _VERSION.match(new):
        return f"{new!r} is not x.y.z"
    if version_tuple(new) < version_tuple(current) or (released and new == current):
        return f"{new} is not higher than {current}" + (", which is already tagged" if released else "")
    return ""


# --- git (read-only) -------------------------------------------------------------------------------------------

def git_run(root: Path, *args: str) -> subprocess.CompletedProcess:
    """git *args in *root*, finished: its exit code, what it printed and what it said (stderr), for a caller that
    shows git's own words when it failed. git() is the same with only the output."""
    # UTF-8, as git writes it, whatever the locale says: another encoding garbled every é and × of a CHANGELOG read at
    # a tag, so its entries no longer matched and the release counted them all as new. No optional locks: the build pill's poll runs
    # git status here, which otherwise takes .git/index.lock to refresh the index, and a poll that came while the
    # Commands tab ran git add -A or git commit made that fail ("Unable to create .git/index.lock: File exists").
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})


def git(root: Path, *args: str) -> str | None:
    result = git_run(root, *args)
    return result.stdout if result.returncode == 0 else None


def all_tags(root: Path) -> list[str]:
    """Every tag of the checkout, read once: load_units() picks each unit's from it, as one git process per unit
    made the window slow (owner, 27-10-2026)."""
    return (git(root, "tag", "--list") or "").split()


def tags_of(root: Path, key: str, prefix: str = "", tags: list[str] | None = None) -> list[str]:
    """The release tags of one app (or the portal), oldest first; *prefix*: the suite's (tag_prefix()); *tags*:
    all_tags() when already read."""
    found = []
    head = f"{prefix}{key}-v"
    listed = (git(root, "tag", "--list", f"{head}*") or "").split() if tags is None else \
        [tag for tag in tags if tag.startswith(head)]
    for tag in listed:
        version = tag[len(head):]
        if _VERSION.match(version):
            found.append((version_tuple(version), tag))
    return [tag for _, tag in sorted(found)]


def commits_since(root: Path, tag: str | None, path: str) -> int | None:
    out = git(root, "rev-list", "--count", f"{tag}..HEAD" if tag else "HEAD", "--", path)
    return int(out) if out and out.strip().isdigit() else None


def tag_targets(root: Path) -> dict[str, str]:
    """Every tag with the commit it points at (an annotated tag's dereferenced), in one git process."""
    out = git(root, "for-each-ref", "--format=%(refname:short) %(objectname) %(*objectname)", "refs/tags") or ""
    found = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            found[parts[0]] = parts[2] if len(parts) > 2 else parts[1]
    return found


def _under(path: str, folders: list[str]) -> bool:
    return path in folders or path.startswith(tuple(f.rstrip("/") + "/" for f in folders))


class History:
    """The commits since the units' last tags, read once for every unit instead of two git processes per unit
    (owner, 01-11-2026: the window was slow, a refresh started some 135 git processes). One
    git log from the common ancestor of the tags to HEAD gives each commit, its parents and its files; a unit's
    commits since its tag are the ones of that log not reachable from the tag's commit. A file those commits
    touched counts as changed only when it still differs from the tag (one git cat-file and one git ls-files for
    all of them): a change made and undone since the tag is no change, as git diff says."""

    def __init__(self, root: Path, tags: list[str]):
        self.root = root
        targets = tag_targets(root)
        self.tip = {tag: targets.get(tag, "") for tag in tags}
        bases = sorted({sha for sha in self.tip.values() if sha})
        base = (git(root, "merge-base", "--octopus", *bases) or "").strip() if bases else ""
        log = (git(root, "log", "--format=%x00%H %P", "--name-only", "--no-renames", f"{base}..HEAD")
               if base else "")
        self.order: list[str] = []              # newest first
        self.parents: dict[str, list[str]] = {}
        self.files: dict[str, list[str]] = {}
        for block in log.split("\x00")[1:]:
            header, _, body = block.partition("\n")
            sha, *parents = header.split()
            self.order.append(sha)
            self.parents[sha] = parents
            self.files[sha] = [line for line in body.splitlines() if line]
        # What differs from HEAD in the index or the working tree: changed whatever the tag says.
        self.uncommitted = set((git(root, "diff", "--name-only", "HEAD") or "").splitlines())

    def since(self, tag: str) -> list[str]:
        """The commits in tag..HEAD, newest first; every commit of the log for a tag that is not in it."""
        tip = self.tip.get(tag, "")
        seen, stack = set(), [tip]
        while stack:
            sha = stack.pop()
            if sha in seen or sha not in self.parents:
                continue
            seen.add(sha)
            stack.extend(self.parents[sha])
        return [sha for sha in self.order if sha not in seen and sha != tip]

    def touched(self, tag: str, path: str, paths: list[str]) -> tuple[int, set[str]]:
        """How many commits since *tag* touched *path* (as git rev-list --count tag..HEAD -- path counts them), and
        the files under *paths* those commits touched."""
        folder, under = path.rstrip("/") + "/", tuple(p.rstrip("/") + "/" for p in paths)
        count, files = 0, set()
        for sha in self.since(tag):
            listed = self.files[sha]
            if any(f == path or f.startswith(folder) for f in listed):
                count += 1
            files.update(f for f in listed if f in paths or f.startswith(under))
        return count, files

    def verify(self, wanted: dict[str, set[str]]) -> dict[str, set[str]]:
        """Of each tag's candidate files, those that differ from the tag now: a file in the index with another blob
        than at the tag, or on one side only. Files changed in the working tree are different whatever the index
        says and are not asked about."""
        specs = sorted(f"{tag}:{f}" for tag, files in wanted.items() for f in files if f not in self.uncommitted)
        if not specs:
            return {tag: set(files) for tag, files in wanted.items()}
        result = subprocess.run(["git", "cat-file", "--batch-check"], cwd=self.root, capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                input="".join(f"{spec}\n" for spec in specs),
                                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        at_tag: dict[str, str] = {}
        for spec, line in zip(specs, result.stdout.splitlines()):
            parts = line.split()
            at_tag[spec] = parts[0] if len(parts) >= 3 and parts[1] == "blob" else ""
        files = sorted({spec.split(":", 1)[1] for spec in specs})
        listing = git(self.root, "ls-files", "-s", "--", *files) or ""
        in_index = {line.split("\t", 1)[1]: line.split()[1] for line in listing.splitlines() if "\t" in line}
        found = {}
        for tag, candidates in wanted.items():
            kept = set()
            for f in candidates:
                if f in self.uncommitted or at_tag.get(f"{tag}:{f}", "") != in_index.get(f, ""):
                    kept.add(f)
            found[tag] = kept
        return found


# --- The units -------------------------------------------------------------------------------------------------

@dataclass
class Unit:
    key: str                            # "gpu", "portal", "core"
    path: str                           # "apps/gpu", relative to the checkout
    version: str
    last_tag: str | None                # newest <key>-v* tag; None for core (bundled, never tagged)
    commits: int | None                 # commits touching the folder since that tag
    pinned_tag: str = ""                # apps only: what portal/apps.toml pins
    pinned_sha: str = ""
    changed: list[str] | None = None    # shipped files that differ from the last tag; None: never released
    in_apps: list[str] = field(default_factory=list)  # core only: the apps whose release would carry its changes
    current: bool = False               # core only: nothing it ships changed since its VERSION was last bumped
    standalone: bool = False            # apps only: released separately, never pinned in the portal
    prefix: str = ""                    # the suite's tag prefix: "ps5-" makes ps5-gpu-v0.1.0

    @property
    def needs_release(self) -> bool:
        """Something it ships changed since its last tag (or it was never released). Core is never released."""
        return self.kind != "core" and (self.last_tag is None or bool(self.changed))

    @property
    def release_reason(self) -> str:
        if self.kind == "core":
            n = len(self.in_apps)
            releases = f"{n} app release{'s' if n != 1 else ''}"
            if n and self.current:
                return f"{self.version} has it: goes into {releases}"
            return f"changed: goes into {releases}" if n else "no"
        if self.last_tag is None:
            return "first release"
        if not self.changed:
            return "no"
        core = [f for f in self.changed if f.startswith("core/")]
        own = len(self.changed) - len(core)
        parts = ([f"{own} file{'s' if own != 1 else ''}"] if own else []) + (["core"] if core else [])
        return "yes: " + " + ".join(parts)

    @property
    def kind(self) -> str:
        return self.key if self.key in ("core", "portal") else "app"

    @property
    def tag(self) -> str:
        """The tag of the current VERSION."""
        return f"{self.tag_head}{self.version}"

    @property
    def tag_head(self) -> str:
        """What its tags start with, before the version: "ps5-gpu-v"."""
        return f"{self.prefix}{self.key}-v"

    @property
    def released(self) -> bool:
        return self.last_tag == self.tag


def shipped_sources(root: Path, key: str, path: str) -> list[str]:
    """The source paths a release of *key* is made from, as tools/stage_app.py stages it."""
    paths = [path]
    if key != "core" and stage_app.uses_core(root / path):
        paths.append("core/bazzite_console_core")
    if key not in ("core", "portal") and (root / "docs" / "apps" / f"{key}.md").is_file():
        paths.append(f"docs/apps/{key}.md")
    return paths


def is_shipped(rel: str) -> bool:
    parts = rel.split("/")
    return not (set(parts) & stage_app.SKIP_DIRS) and parts[-1] not in stage_app.SKIP_FILES \
        and not parts[-1].endswith(".pyc") and not any(p.startswith(".venv") for p in parts)


def untracked(root: Path) -> list[str]:
    """The checkout's new files that git does not know yet (and does not ignore), read once for every unit."""
    return (git(root, "ls-files", "--others", "--exclude-standard") or "").splitlines()


def changed_since(root: Path, tag: str, paths: list[str], new_files: list[str] | None = None) -> list[str]:
    """Shipped files under *paths* that differ between *tag* and the working tree: committed, not yet committed
    and new (untracked) files alike; *new_files*: untracked() when already read."""
    diff = git(root, "diff", "--name-only", tag, "--", *paths) or ""
    if new_files is None:
        new = (git(root, "ls-files", "--others", "--exclude-standard", "--", *paths) or "").splitlines()
    else:
        new = [f for f in new_files if any(f == p or f.startswith(p.rstrip("/") + "/") for p in paths)]
    return sorted({f for f in [*diff.splitlines(), *new] if f and is_shipped(f)})


def read_blobs(root: Path, specs: list[str]) -> dict[str, str | None]:
    """The text of each "<rev>:<path>" in *specs*, read by one git cat-file --batch (None for one that does not
    exist), instead of a git show per file."""
    if not specs:
        return {}
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input="".join(f"{s}\n" for s in specs).encode(),
                            capture_output=True)
    out, at, found = result.stdout, 0, {}
    for spec in specs:
        end = out.find(b"\n", at)
        if end < 0:
            found[spec] = None
            continue
        header = out[at:end].decode(errors="replace").split()
        at = end + 1
        if len(header) == 3 and header[1] == "blob":
            size = int(header[2])
            found[spec] = out[at:at + size].decode("utf-8", errors="replace")
            at += size + 1                                  # the blob and its closing newline
        else:
            found[spec] = None                              # "<spec> missing", or not a blob
    return found


def bad_tags(root: Path, units: list[Unit]) -> list[str]:
    """Tags that point at a commit whose VERSION is not the tag's version: tagged before the version bump was
    committed. release.yml refuses to build those; delete the tag and tag the right commit again."""
    out = []
    tagged = [unit for unit in units if unit.kind != "core" and unit.last_tag]
    versions = read_blobs(root, [f"{unit.last_tag}:{unit.path}/VERSION" for unit in tagged])
    for unit in tagged:
        at_tag = (versions.get(f"{unit.last_tag}:{unit.path}/VERSION") or "").strip()
        want = unit.last_tag[len(unit.tag_head):]
        if at_tag and at_tag != want:
            out.append(f"{unit.last_tag} points at a commit where {unit.path}/VERSION is {at_tag}")
    return out


def load_units(root: Path = CHECKOUT) -> list[Unit]:
    """Core, the portal and the apps, each with its version, tags and pin."""
    pins = {}
    tools = check_manifest
    prefix = tag_prefix(root)
    every_tag, new_files = all_tags(root), untracked(root)        # once, not per unit: see all_tags()
    try:
        for entry in tools.manifest.load(manifest_path(root)):
            pins[entry.key] = entry
    except (OSError, tools.manifest.ManifestError):
        pass
    units = []
    folders = [("core", "core"), ("portal", "portal")]
    folders += [(p.name, f"apps/{p.name}") for p in sorted((root / "apps").iterdir())
                if (p / "VERSION").is_file() and not (p / CHECKOUT_ONLY).is_file()]
    for key, path in folders:
        version = (root / path / "VERSION").read_text(encoding="utf-8").strip()
        tags = tags_of(root, key, prefix, every_tag) if key != "core" else []
        last = tags[-1] if tags else None
        unit = Unit(key, path, version, last, None,
                    standalone=(root / path / ".standalone").is_file(),
                    prefix="" if key == "core" else prefix)
        if key in pins:
            unit.pinned_tag, unit.pinned_sha = pins[key].tag, pins[key].sha256
        units.append(unit)

    # Each unit's two git questions (commits since its tag, files changed since it) are answered from one reading of
    # the history (History: a handful of git processes for all of them, not two per unit; owner, 01-11-2026: the
    # window was slow). A unit without a tag keeps its own count, every commit of its folder.
    tagged = [u for u in units if u.last_tag]
    history = History(root, [u.last_tag for u in tagged])
    sources = {u.key: shipped_sources(root, u.key, u.path) for u in tagged}
    wanted = {}
    for unit in tagged:
        unit.commits, wanted[unit.last_tag] = history.touched(unit.last_tag, unit.path, sources[unit.key])
    differing = history.verify(wanted)
    for unit in tagged:
        paths = sources[unit.key]
        new = [f for f in new_files if _under(f, paths)]
        changed = differing[unit.last_tag] | {f for f in history.uncommitted if _under(f, paths)} | set(new)
        shipped = sorted(f for f in changed if f and is_shipped(f))
        written = release_only(root, unit, shipped)
        unit.changed = [f for f in shipped if f not in written]
    for unit in units:
        if not unit.last_tag:
            unit.commits = commits_since(root, None, unit.path)
    # Core is never tagged: it ships inside each app that imports it, so its changes are the core files those
    # apps' releases would carry.
    core = units[0]
    carriers = [u for u in units if u.kind != "core" and any(f.startswith("core/") for f in u.changed or [])]
    core.in_apps = [u.key for u in carriers]
    core.changed = sorted({f for u in carriers for f in u.changed or [] if f.startswith("core/")})
    core.current = core_is_current(root, new_files)
    return units


def release_only(root: Path, unit: Unit, files: list[str]) -> set[str]:
    """Of *files* (changed since the unit's last tag), those that hold only what the release tools write: VERSION and
    its copies (check_versions.py's) whose only change is the version, and the CHANGELOG when its entries since the
    tag are all tool entries ("Release x.y.z.", "Withdrawn: ..."). They ship nothing new, so they need no release
    (owner, 15-11-2026: a portal bump with nothing else in it was released as a second portal of the same apps)."""
    if not unit.last_tag:
        return set()
    tagged = unit.last_tag[len(unit.tag_head):]
    found = set()
    for name in files:
        path = root / name
        if not path.is_file():
            continue
        if path.name == "CHANGELOG" and Path(name).parent.as_posix() == Path(unit.path).as_posix():
            old = set(changelog_entries(git(root, "show", f"{unit.last_tag}:{name}") or ""))
            new = [entry_body(e) for e in changelog_entries(path.read_text(encoding="utf-8")) if e not in old]
            if all(b.startswith(TOOL_ENTRIES) for b in new if b):
                found.add(name)
            continue
        if unit.version == tagged or not (path.name == "VERSION" or check_versions.version_pattern(path)):
            continue
        old_text = git(root, "show", f"{unit.last_tag}:{name}")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if old_text is not None and text.replace(unit.version, tagged) == old_text:
            found.add(name)
    return found


_RELEASE = re.compile(r"^Release (\d+\.\d+\.\d+)\.")


def core_is_current(root: Path, new_files: list[str] | None = None) -> bool:
    """Whether core's VERSION already covers what it ships: nothing under core/bazzite_console_core changed since the commit
    that last changed core/VERSION, or that VERSION is changed and not committed yet (a bump in progress). Then an
    app release carries core as it is, and core needs no new version. *new_files*: untracked(), read already."""
    if git(root, "diff", "--quiet", "HEAD", "--", "core/VERSION") is None:
        return True
    bump = (git(root, "log", "-1", "--format=%H", "--", "core/VERSION") or "").strip()
    return bool(bump) and not changed_since(root, bump, ["core/bazzite_console_core"], new_files)


# --- Edits -----------------------------------------------------------------------------------------------------

def set_version(root: Path, unit: Unit, new: str) -> list[Path]:
    """Writes *new* to the unit's VERSION and to every copy check_versions.py checks; returns the changed files."""
    folder = root / unit.path
    changed = [folder / "VERSION"]
    (folder / "VERSION").write_bytes(f"{new}\n".encode())
    for path in sorted(folder.rglob("*")):
        parts = path.relative_to(folder).parts
        if not path.is_file() or "tests" in parts or "target" in parts:
            continue
        pattern = check_versions.version_pattern(path)       # Cargo.lock too: CI builds Rust with --locked
        if pattern is None:
            continue
        text = path.read_text(encoding="utf-8")
        new_text = pattern.sub(lambda m: m.group(0).replace(f'"{m.group(1)}"', f'"{new}"'), text)
        if new_text != text:
            path.write_bytes(new_text.encode("utf-8"))
            changed.append(path)
    unit.version = new
    return changed


def amsterdam_now(now: datetime.datetime | None = None) -> datetime.datetime:
    """Europe/Amsterdam time without a tz database: CET, CEST from the last Sunday of March to
    the last Sunday of October, switching at 01:00 UTC."""
    utc = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)

    def last_sunday(month: int) -> datetime.datetime:
        day = datetime.datetime(utc.year, month, 31, 1, tzinfo=datetime.timezone.utc)
        return day - datetime.timedelta(days=(day.weekday() + 1) % 7)

    summer = last_sunday(3) <= utc < last_sunday(10)
    return (utc + datetime.timedelta(hours=2 if summer else 1)).replace(tzinfo=None)


def add_changelog_entry(root: Path, unit: Unit, text: str, now: datetime.datetime | None = None,
                        base: str = "origin/main") -> Path:
    """Puts "Changelog: <time>", a blank line and *text* on top of the unit's CHANGELOG. A release entry ("Release
    x.y.z.") replaces the newest entry when that is the same release already, so applying a release again (after a
    check stopped the commit) leaves one entry, with the latest notes (owner, 28-10-2026: "Release 1.3.0." twice).
    Never remove an entry from the CHANGELOG's history (owner, 29-10-2026: the
    portal release replaced the "Release 3.2.0. Pins ..." entry its app release had pushed, and the push failed)."""
    path = root / unit.path / "CHANGELOG"
    stamp = amsterdam_now(now).strftime("%d-%m-%Y %H:%M:%S")
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    release = _RELEASE.match(text.strip())
    if release:
        entries = changelog_entries(old)
        newest = _RELEASE.match(entry_body(entries[0])) if entries else None
        pushed = git(root, "show", f"{base}:{Path(unit.path).as_posix()}/CHANGELOG") if newest else None
        if newest and newest[1] == release[1] and entries[0] not in changelog_entries(pushed or ""):
            old = old[old.index(entries[0]) + len(entries[0]):].lstrip("\n")
    path.write_bytes(f"Changelog: {stamp}\n\n{text.strip()}\n\n{old}".encode("utf-8"))
    return path


def release_text(version: str, notes: str) -> str:
    return f"Release {version}." + (f" {notes.strip()}" if notes.strip() else "")


# --- The kind of change: semantic versioning (owner, 15-10-2026) -----------------------------------------------

# A CHANGELOG entry starts with the kind of change it is; a release takes the highest kind since its last tag.
CHANGE_WORDS = {"Breaking.": "major", "Added.": "minor", "Fixed.": "patch"}
LEVELS = ("patch", "minor", "major")
# Entries the release tools write themselves: they are no change of their own.
TOOL_ENTRIES = ("Release ", "Version ", "Withdrawn: ", "Withdrawal of ")
_ENTRY = re.compile(r"^Changelog: .*$", re.M)


def changelog_entries(text: str) -> list[str]:
    """Each entry of a CHANGELOG, header line included, newest first."""
    starts = [m.start() for m in _ENTRY.finditer(text)]
    return [text[a:b].strip() for a, b in zip(starts, starts[1:] + [len(text)])]


def entry_body(entry: str) -> str:
    return entry.split("\n", 1)[1].strip() if "\n" in entry else ""


def change_word(body: str) -> str:
    """The entry's kind (Breaking., Added., Fixed.), "" when it has none."""
    return next((word for word in CHANGE_WORDS if body.startswith(word + " ") or body == word), "")


def changelog_specs(units: list[Unit]) -> list[str]:
    """The CHANGELOGs new_entries() reads at the units' last tags, as "<tag>:<path>/CHANGELOG": read them all at once
    with read_blobs() and hand that to version_choices() (one git process for the whole table, not one per row)."""
    specs = []
    for unit in units:
        if unit.kind == "core" or not unit.last_tag:
            continue
        specs.append(f"{unit.last_tag}:{unit.path}/CHANGELOG")
        if any(f.startswith("core/") for f in unit.changed or []):
            specs.append(f"{unit.last_tag}:core/CHANGELOG")
    return specs


def new_entries(root: Path, unit: Unit, blobs: dict[str, str | None] | None = None) -> list[str]:
    """The change entries (bodies) since the unit's last tag: its own, and core's when the release carries a core
    change. Core itself, never tagged: its entries since its last "Version x.y.z." entry. *blobs*: the CHANGELOGs at
    the tags, read already (changelog_specs())."""
    def since(path: str, ref: str | None, mark: str = "Version ") -> list[str]:
        file = root / path / "CHANGELOG"
        current = changelog_entries(file.read_text(encoding="utf-8")) if file.is_file() else []
        if ref is None:
            cut = next((i for i, e in enumerate(current) if entry_body(e).startswith(mark)), len(current))
            current = current[:cut]
        else:
            spec = f"{ref}:{path}/CHANGELOG"
            text = blobs[spec] if blobs is not None and spec in blobs else git(root, "show", spec)
            old = set(changelog_entries(text or ""))
            current = [e for e in current if e not in old]
        return [b for b in map(entry_body, current) if b and not b.startswith(TOOL_ENTRIES)]

    if unit.kind == "core":
        return since(unit.path, None)
    entries = since(unit.path, unit.last_tag) if unit.last_tag else []
    if unit.last_tag and any(f.startswith("core/") for f in unit.changed or []):
        entries += since("core", unit.last_tag)
    return entries


def suggested_level(entries: list[str]) -> tuple[str, str]:
    """The release level the entries ask for (patch, minor, major), and why. An entry without a kind counts as a
    fix, and says so."""
    counts = {word: 0 for word in CHANGE_WORDS}
    unmarked = 0
    for body in entries:
        word = change_word(body)
        if word:
            counts[word] += 1
        else:
            unmarked += 1
    level = max((CHANGE_WORDS[w] for w, n in counts.items() if n), key=LEVELS.index, default="patch")
    parts = [f"{n} {w.rstrip('.')}" for w, n in counts.items() if n] + \
            ([f"{unmarked} without Breaking./Added./Fixed. (counted as a fix)"] if unmarked else [])
    return level, ", ".join(parts) or "no CHANGELOG entries"


def _tagged_version(unit: Unit) -> str:
    """The version of the unit's last tag, where the next version counts from; its VERSION without a tag."""
    return unit.last_tag[len(unit.tag_head):] if unit.last_tag else unit.version


def version_choices(root: Path, unit: Unit, blobs: dict[str, str | None] | None = None) -> tuple[list[str], str]:
    """The versions the release offers for the unit, the one semantic versioning gives first, and why. Breaking. ->
    major, Added. -> minor, otherwise patch, counted from the last tag. A VERSION bumped further already, never
    tagged, comes first; a first release is offered as it is."""
    nexts = list(next_versions(unit.version).values())
    if unit.kind == "core" and unit.current:
        return [unit.version] + nexts, f"{unit.version} already holds core's changes"
    if unit.kind != "core" and unit.last_tag is None:
        return [unit.version] + nexts, "the first release"
    level, why = suggested_level(new_entries(root, unit, blobs))
    suggested = next_versions(_tagged_version(unit))[level]
    reason = f"{level}: {why}" + (f" since {unit.last_tag}" if unit.last_tag else "")
    released = unit.released or unit.kind == "core"
    choices = [suggested, unit.version, *nexts]
    if version_tuple(unit.version) > version_tuple(suggested):
        choices.insert(0, unit.version)
    choices = [v for i, v in enumerate(choices) if v not in choices[:i] and not check_new_version(unit.version, v,
                                                                                                    released)]
    return choices, reason


def portal_suggestion(root: Path, portal: Unit) -> tuple[str, str]:
    """The portal's next version by semantic versioning since its last tag, and why: its own CHANGELOG entries, and
    what changed in apps.toml since that tag (an app added or removed: minor; the largest app bump it pins), as
    tools/check_manifest.py counts it. A portal never tagged is offered as it is, as an app's first release is
    (owner, 28-10-2026)."""
    if portal.last_tag is None:
        return portal.version, "the first release"
    level, why = suggested_level(new_entries(root, portal))
    reason = f"{level}: {why}" + (f" since {portal.last_tag}" if portal.last_tag else "")
    old = git(root, "show", f"{portal.last_tag}:portal/apps.toml") \
        if portal.last_tag else None
    if old is not None:
        need, what = check_manifest.required_bump(old, manifest_path(root).read_text(
            encoding="utf-8"))
        if need > LEVELS.index(level) + 1:
            level = LEVELS[need - 1]
            reason = f"{level}: apps.toml changed since {portal.last_tag} ({what})"
    return next_versions(_tagged_version(portal))[level], reason


def write_portal_bump(root: Path, base: str, version: str) -> tuple[list[Path], str]:
    """The portal's version written with its CHANGELOG entry (the pins and the withdrawals that changed since
    *base*): the Commit step's offer writes the version it offers this way.
    The paths changed and the entry's text."""
    portal = next(u for u in load_units(root) if u.kind == "portal")
    changed = set_version(root, portal, version)
    text = portal_text(version, changed_pins(root, base), "", changed_withdrawals(root, base))
    add_changelog_entry(root, portal, text, base=base)
    return changed, text


def portal_offer(root: Path, base: str) -> tuple[str, str, str] | None:
    """What the Commit step offers when its manifest check would refuse the commit (owner, 02-11-2026: it only
    refused): the portal version to write, why that one, and what changed
    in apps.toml. The version is portal_suggestion's (the portal's CHANGELOG entries count: a Breaking entry makes
    it major) or the least the check accepts, whichever is higher. None when no bump is needed."""
    version = (root / "portal" / "VERSION").read_text(encoding="utf-8").strip()
    minimum, why = portal_minimum(root, base, version)
    if not minimum or minimum == version:
        return None
    portal = next(u for u in load_units(root) if u.kind == "portal")
    suggested, reason = portal_suggestion(root, portal)
    if version_tuple(suggested) > version_tuple(minimum):
        return suggested, reason, why
    return minimum, "the least the manifest check accepts", why


def portal_text(version: str, pins: list[str], notes: str, withdrawn: list[tuple[str, str]] = ()) -> str:
    text = f"Release {version}."
    if pins:
        text += " Pins " + ", ".join(pins) + "."
    for tag, reason in withdrawn:
        text += f" Withdraws {tag}: {reason.rstrip('.')}."
    return text + (f" {notes.strip()}" if notes.strip() else "")


# --- Withdrawing a release -------------------------------------------------------------------------------------

_BLOCK = re.compile(r"^\[apps\.(?P<key>[a-z0-9-]+)\]\s*$")


def set_withdrawn(text: str, key: str, reason: str) -> str:
    """apps.toml with [apps.<key>] marked withdrawn for *reason* (after its summary line), or unmarked when
    *reason* is empty; everything else stays as it is."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if (m := _BLOCK.match(line)) and m["key"] == key), None)
    if start is None:
        raise ValueError(f"apps.toml has no [apps.{key}]")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    block = [line for line in lines[start:end] if not line.startswith("withdrawn ")]
    if reason.strip():
        at = next((i + 1 for i, line in enumerate(block) if line.startswith("summary ")), 1)
        block.insert(at, f"withdrawn = {json.dumps(reason.strip(), ensure_ascii=False)}\n")
    return "".join(lines[:start] + block + lines[end:])


def withdrawable(root: Path, units: list[Unit]) -> list[Unit]:
    """The apps a portal pins that can be withdrawn: never the required one (Board Test, always installed)."""
    required = {e.key for e in check_manifest.manifest.load(manifest_path(root)) if e.required}
    return [u for u in units if u.kind == "app" and not u.standalone and u.pinned_tag and u.key not in required]


def withdrawn_reason(root: Path, key: str) -> str:
    entries = check_manifest.manifest.load(manifest_path(root))
    return next((e.withdrawn for e in entries if e.key == key), "")


def withdraw(root: Path, unit: Unit, reason: str, now: datetime.datetime | None = None) -> list[Path]:
    """Marks the app's pinned release withdrawn (or, with no reason, takes that back) in apps.toml, with a CHANGELOG
    entry in the app. Returns the files changed."""
    path = manifest_path(root)
    paths = write_manifest(root, set_withdrawn(path.read_text(encoding="utf-8"), unit.key, reason))
    text = (f"Withdrawn: {unit.pinned_tag}. {reason.strip()}" if reason.strip() else
            f"Withdrawal of {unit.pinned_tag} taken back.")
    return [*paths, add_changelog_entry(root, unit, text, now)]


def changed_withdrawals(root: Path, base: str) -> list[tuple[str, str]]:
    """(tag, reason) of the apps withdrawn since *base*: what the portal release that follows withdraws."""
    old_text = git(root, "show", f"{base}:portal/apps.toml") or ""
    tools = check_manifest
    old = {e.key: e.withdrawn for e in tools.manifest.parse(old_text)} if old_text else {}
    new = tools.manifest.load(manifest_path(root))
    return [(e.tag, e.withdrawn) for e in new if e.withdrawn and not old.get(e.key)]


def withdraw_commands(tag: str, reason: str, now: datetime.datetime | None = None) -> str:
    """What stays the owner's: mark the GitHub release (it stays, as a pre-release, so no update check offers it),
    then the portal release that removes the app from the boards."""
    date = amsterdam_now(now).strftime("%d-%m-%Y")
    notes = f"Withdrawn on {date}: {reason.strip()} Do not install this release."
    test = [
        "# 2. Test it on a PS5 with the app installed: Test withdrawal on this tab (check-release.sh local).",
        "#    The portal must show the app as \"App not available\" and remove it. Take back undoes the mark after",
        "#    a test.",
    ]
    return "\n".join([
        "# 1. Mark the release withdrawn on GitHub (it stays; a pre-release is offered by no update check):",
        f"gh release edit {tag} --prerelease --title {shlex.quote('Withdrawn: ' + tag)} "
        f"--notes {shlex.quote(notes)}",
        "",
        *test,
        "",
        "# 3. Then a portal release (the release tab, from Commit your changes: its Commit bumps the portal): it lists",
        "#    the withdrawal in its CHANGELOG entry.",
    ])


# --- The pins and the portal -----------------------------------------------------------------------------------

def pin(root: Path, unit: Unit, sha256: str) -> None:
    text = manifest_path(root).read_text(encoding="utf-8")
    write_manifest(root, pin_app.pin(text, unit.key, unit.tag, sha256.lower()))
    unit.pinned_tag, unit.pinned_sha = unit.tag, sha256.lower()


def changed_pins(root: Path, base: str) -> list[str]:
    """The pinned tags that differ from *base*: the app releases this portal release brings."""
    old_text = git(root, "show", f"{base}:portal/apps.toml") or ""
    tools = check_manifest
    old = {e.key: e.tag for e in tools.manifest.parse(old_text)} if old_text else {}
    new = tools.manifest.load(manifest_path(root))
    return [e.tag for e in new if old.get(e.key) != e.tag]


def portal_minimum(root: Path, base: str, portal_version: str) -> tuple[str, str]:
    """The lowest portal version CI accepts (tools/check_manifest.py), and why: apps.toml against the last portal
    release (its tag; a version not tagged yet may still change what it pins), or against *base* (the last push)
    while there is no portal tag; ("", "") when apps.toml is unchanged. That release's version is the starting
    point."""
    prefix = tag_prefix(root)
    tools = check_manifest
    tags = tags_of(root, "portal", prefix)
    ref = tags[-1] if tags else base
    old_text = git(root, "show", f"{ref}:portal/apps.toml")
    new_text = manifest_path(root).read_text(encoding="utf-8")
    if old_text is None:
        return "", ""
    need, why = tools.required_bump(old_text, new_text)
    if need <= 0:
        return "", why
    start = ref[len(f"{prefix}portal-v"):] if tags else \
        (git(root, "show", f"{base}:portal/VERSION") or portal_version).strip()
    bumped = next_versions(start)[tools.LEVELS[need]]
    if version_tuple(portal_version) > version_tuple(start) and \
            tools.bump_level(start, portal_version) >= need:
        bumped = portal_version
    return bumped, why


# --- The suite's icon and name ---------------------------------------------------------------------------

_CONSTANT = re.compile(r'^(APP_NAME|APP_ID)\s*=\s*"([^"]+)"', re.M)


def suite_name(root: Path) -> str:
    """The suite's name, as its portal calls itself (APP_NAME in portal/<package>/__init__.py: Bazzite Console Suite);
    the checkout folder's name without one."""
    for init in sorted((root / "portal").glob("*/__init__.py")):
        found = _CONSTANT.search(init.read_text(encoding="utf-8"))
        while found and found.group(1) != "APP_NAME":
            found = _CONSTANT.search(init.read_text(encoding="utf-8"), found.end())
        if found:
            return found.group(2)
    return root.name


def suite_icon(root: Path) -> Path | None:
    """The suite's icon: its portal's (portal/images/bazzite-console-suite.webp); None without one."""
    portal = sorted((root / "portal" / "images").glob("*-suite.webp"))
    return portal[0] if len(portal) == 1 else None


# --- GitHub Actions: did the push build? -----------------------------------------------------------------------

RUNS_URL = "https://api.github.com/repos/{repo}/actions/runs?per_page={page}"
RUNS_PAGE = 30
HEAD_RUNS_URL = "https://api.github.com/repos/{repo}/actions/runs?head_sha={sha}&per_page=100"
ACTIONS_URL = "{repo_url}/actions"
OK_CONCLUSIONS = ("success", "skipped", "neutral")


@dataclass(frozen=True)
class BuildRun:
    """One workflow run on GitHub: CI, Release or Manual, on a branch or a tag."""
    workflow: str                       # "CI"
    ref: str                            # "main", "governor-v0.1.1"
    status: str                         # "queued", "in_progress", "completed", ...
    conclusion: str                     # "success", "failure", "canceled", ...; "" until it is completed
    url: str                            # its page; also what tells two runs apart
    sha: str
    title: str                          # the commit message's first line
    jobs_url: str = ""                  # its jobs on GitHub's API (fetch_jobs)
    started: float = 0.0                # seconds since the epoch; 0 when GitHub does not say
    file: str = ""                      # its workflow's file: "ci.yml", "release.yml"
    attempt: int = 1                    # GitHub's run_attempt: a rerun is the same run, one attempt on

    @property
    def done(self) -> bool:
        return self.status == "completed"

    @property
    def passed(self) -> bool:
        return self.done and self.conclusion in OK_CONCLUSIONS

    @property
    def outcome(self) -> str:
        return ("passed" if self.passed else self.conclusion.replace("_", " ") or "failed") if self.done \
            else self.status.replace("_", " ")

    @property
    def label(self) -> str:
        return f"{self.workflow} on {self.ref}"


def repo_slug() -> str:
    return pin_app.REPO_URL.removeprefix("https://github.com/")


def parse_runs(data: object) -> list[BuildRun]:
    runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
    return [BuildRun(str(r.get("name") or ""), str(r.get("head_branch") or ""), str(r.get("status") or ""),
                     str(r.get("conclusion") or ""), str(r.get("html_url") or ""), str(r.get("head_sha") or ""),
                     str(r.get("display_title") or ""), str(r.get("jobs_url") or ""),
                     epoch(r.get("run_started_at")), str(r.get("path") or "").split("@")[0].rsplit("/", 1)[-1],
                     int(r.get("run_attempt") or 1))
            for r in runs if isinstance(r, dict)]


def epoch(text: object) -> float:
    """GitHub's time ("2026-10-28T09:12:03Z") in seconds since the epoch; 0 without one."""
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


GH_FALLBACK = "/home/linuxbrew/.linuxbrew/bin/gh"   # Homebrew's gh on Bazzite: not on PATH when started from the menu


@dataclass(frozen=True)
class RateInfo:
    """GitHub's hourly limit as its last answer reported it (the X-RateLimit headers, also on unchanged answers)."""
    limit: int
    remaining: int
    reset: float                        # seconds since the epoch
    signed_in: bool

    @classmethod
    def from_headers(cls, headers, signed_in: bool) -> "RateInfo | None":
        try:
            return cls(int(headers.get("X-RateLimit-Limit")), int(headers.get("X-RateLimit-Remaining")),
                       float(headers.get("X-RateLimit-Reset")), signed_in)
        except (TypeError, ValueError, AttributeError):
            return None

    @property
    def until(self) -> str:
        return time.strftime("%H:%M", time.localtime(self.reset))

    @property
    def text(self) -> str:
        who = "signed in" if self.signed_in else "not signed in"
        return f"GitHub API: {self.remaining:,} of {self.limit:,} left until {self.until}, {who}"


class RateLimited(OSError):
    """GitHub refuses until *reset* (seconds since the epoch): the hour's requests are used up."""

    def __init__(self, reset: float, signed_in: bool, rate: RateInfo | None = None):
        super().__init__(f"GitHub's hourly limit is used up until {time.strftime('%H:%M', time.localtime(reset))}")
        self.reset = reset
        self.signed_in = signed_in
        self.rate = rate or RateInfo(60 if not signed_in else 5000, 0, reset, signed_in)


_token: str | None = None               # the token found once per run; "" when there is none
_token_lock = threading.Lock()          # the checks run in worker threads: one asks gh, the others wait for it


def github_token(run=subprocess.run) -> str:
    """GITHUB_TOKEN or GH_TOKEN, else the token of a gh login (gh auth token); "" without one. With a token GitHub
    allows 5,000 requests an hour instead of 60. It is only sent to GitHub's API and never stored here."""
    global _token
    with _token_lock:
        if _token is None:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
            gh = shutil.which("gh") or (GH_FALLBACK if os.access(GH_FALLBACK, os.X_OK) else "")
            if not token and gh:
                try:
                    out = run([gh, "auth", "token"], capture_output=True, text=True, timeout=10)
                    token = out.stdout.strip() if out.returncode == 0 else ""
                except (OSError, subprocess.SubprocessError):
                    token = ""
            _token = token              # only the finished answer: never "" while gh is still being asked
        return _token


def token_warning(token: str) -> str:
    """What push and tag say about the GitHub token on this machine: a gh login (gho_) or a classic token (ghp_)
    reaches every repository of the account, a fine-grained one (github_pat_) only those it names. "" when it is
    fine-grained or there is none."""
    if not token or token.startswith("github_pat_"):
        return ""
    return ("The GitHub token on this machine (a gh login or a classic token) reaches every repository of your "
            "account, not only this one. A fine-grained token for this repository only limits what someone with "
            "this account can do: github.com, Settings, Developer settings, Fine-grained tokens.")


def github_get(url: str, etag: str = "") -> tuple[object | None, str, RateInfo | None]:
    """GitHub's API answer at *url* (parsed JSON), the ETag to send next time and GitHub's hourly limit as it
    stands; the answer None when nothing changed since *etag*. GitHub answers that with 304, which does not count
    against the limit (60 requests without a token, 5,000 with the token of a gh login). Raises RateLimited when
    the limit is used up, OSError offline."""
    global _token
    token = github_token()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "nexus-release-tool"}
    if etag:
        headers["If-None-Match"] = etag
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return (json.load(response), response.headers.get("ETag", ""),
                    RateInfo.from_headers(response.headers, bool(token)))
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return None, etag, RateInfo.from_headers(exc.headers, bool(token))
        if exc.code == 401 and token:            # an expired or revoked login: go on without it
            _token = ""
            return github_get(url, etag)
        if exc.code in (403, 429) and exc.headers.get("X-RateLimit-Remaining") == "0":
            raise RateLimited(float(exc.headers.get("X-RateLimit-Reset") or time.time() + 3600), bool(token),
                              RateInfo.from_headers(exc.headers, bool(token))) from exc
        raise


_pages: dict[str, tuple[str, list[BuildRun]]] = {}     # the runs read last at each url: its ETag and its runs


def runs_at(url: str, etag: str) -> tuple[list[BuildRun], str, bool, RateInfo | None]:
    """The runs at *url*, the ETag to send next time, whether they changed since *etag* and GitHub's limit; when
    GitHub says nothing changed (304, which costs no request), the runs read last at that url."""
    data, etag, rate = github_get(url, etag)
    runs = parse_runs(data) if data is not None else _pages.get(url, ("", []))[1]
    _pages[url] = (etag, runs)
    return runs, etag, data is not None, rate


def fetch_runs(etag: str = "", sha: str = "") -> tuple[list[BuildRun] | None, str, RateInfo | None]:
    """The newest workflow runs (newest first), the ETag to send next time and GitHub's hourly limit as it stands;
    runs None when nothing changed since *etag* (github_get). With *sha*, the checkout's HEAD: when the page is
    full and ends on a run of that commit, its older runs are under the page, so they come from GitHub's list of
    that commit's runs too (one more request, with an ETag of its own). A release of 26 apps started 26 Release runs
    and as many Nexus index runs after the CI runs on its commit, which filled the page, so the CI passes step saw no
    CI run and never lit (owner, 04-11-2026)."""
    repo = repo_slug()
    runs, etag, changed, rate = runs_at(RUNS_URL.format(repo=repo, page=RUNS_PAGE), etag)
    more: list[BuildRun] = []
    if sha and len(runs) >= RUNS_PAGE and runs[-1].sha == sha:
        url = HEAD_RUNS_URL.format(repo=repo, sha=sha)
        more, _etag, found_changed, rate = runs_at(url, _pages.get(url, ("", []))[0])
        changed = changed or found_changed
    if not changed:
        return None, etag, rate
    seen = {r.url for r in runs}
    return runs + [r for r in more if r.url not in seen], etag, rate


def latest_push(runs: list[BuildRun]) -> list[BuildRun]:
    """The runs of the newest commit: a push and its tags start CI, Release and Manual on the same commit."""
    return [r for r in runs if r.sha == runs[0].sha] if runs else []


def superseded(run: BuildRun, runs: list[BuildRun]) -> bool:
    """Whether *run* was canceled for a later run of its workflow on the same commit and ref: GitHub cancels a
    waiting run when a newer one of the same concurrency group comes (nexus-index.yml, which every release run of a
    push starts once), so it was never a failure (owner, 30-10-2026: the pill said Failed for 1759427, whose runs all
    passed but one canceled Nexus index)."""
    return (run.done and run.conclusion in ("cancelled", "canceled")
            and any(r is not run and r.workflow == run.workflow and r.sha == run.sha and r.ref == run.ref
                    and (r.started >= run.started or not r.done) for r in runs))


def build_state(runs: list[BuildRun]) -> str:
    """"running" while one of *runs* has not finished, else "failed" when one did not pass, else "passed"; ""
    without runs. A run canceled for a later one of its workflow on the same commit does not count (superseded)."""
    runs = [r for r in runs if not superseded(r, runs)]
    if not runs:
        return ""
    if not all(r.done for r in runs):
        return "running"
    return "passed" if all(r.passed for r in runs) else "failed"


def just_finished(before: dict[str, BuildRun], runs: list[BuildRun]) -> list[BuildRun]:
    """The runs that were running at the last look (*before*, by url) and have finished now."""
    return [r for r in runs if r.done and r.url in before and not before[r.url].done]


# --- GitHub Actions: the jobs of a run and the step each is at, for the ticker -----------------------------------

@dataclass(frozen=True)
class BuildJob:
    """One job of a workflow run (a CI matrix entry, the release build) and the step it is at."""
    name: str                           # "pytest (core)"
    status: str                         # "queued", "in_progress", "completed"
    conclusion: str                     # "success", "failure", ...; "" until it is completed
    url: str                            # its page, with its log
    step: str = ""                      # the step that runs, else the first that failed, else the next; ""
    step_number: int = 0                # its place among the job's steps, from 1; 0 without one
    steps: int = 0

    @property
    def done(self) -> bool:
        return self.status == "completed"

    @property
    def passed(self) -> bool:
        return self.done and self.conclusion in OK_CONCLUSIONS

    @property
    def outcome(self) -> str:
        return ("passed" if self.passed else self.conclusion.replace("_", " ") or "failed") if self.done \
            else self.status.replace("_", " ")


def current_step(steps: list[dict]) -> tuple[str, int]:
    """The step a job is at, with its place from 1: the one running, else the first that did not pass (a failed
    job's), else the first not finished (between two steps); ("", 0) without one."""
    for pick in (lambda st: st.get("status") == "in_progress",
                 lambda st: st.get("status") == "completed" and (st.get("conclusion") or "") not in OK_CONCLUSIONS,
                 lambda st: st.get("status") != "completed"):
        for i, st in enumerate(steps):
            if pick(st):
                return str(st.get("name") or ""), i + 1
    return "", 0


def parse_jobs(data: object) -> list[BuildJob]:
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    found = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        steps = [st for st in job.get("steps") or [] if isinstance(st, dict)]
        step, number = current_step(steps)
        found.append(BuildJob(str(job.get("name") or ""), str(job.get("status") or ""),
                              str(job.get("conclusion") or ""), str(job.get("html_url") or ""), step, number,
                              len(steps)))
    return found


def fetch_jobs(url: str, etag: str = "") -> tuple[list[BuildJob] | None, str, RateInfo | None]:
    """The jobs of a run (its BuildRun.jobs_url) with the step each is at, read as fetch_runs reads the runs."""
    data, etag, rate = github_get(f"{url}?per_page=100", etag)
    return (None if data is None else parse_jobs(data)), etag, rate


def elapsed(seconds: float) -> str:
    """2:14, or 1:02:03 past an hour."""
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60}:{rest % 60:02d}"


def ticker_runs(runs: list[BuildRun]) -> list[BuildRun]:
    """The ticker's runs in its order: those running, then those that failed, then those that passed."""
    return sorted(runs, key=lambda r: 0 if not r.done else 2 if r.passed else 1)


def run_line(run: BuildRun, jobs: list[BuildJob] | None, now: float) -> str:
    """Where one run stands, for the ticker: "CI on main: 3 of 8 jobs done · pytest (core): Run tests (4/7) ·
    2:14"; a failed run names its job and step; without its jobs (not read), the run's own state."""
    if run.passed:
        return f"{run.label}: passed"
    failed = [j for j in jobs or [] if j.done and not j.passed]
    if run.done:
        where = (f" in {failed[0].name}" + (f", step {failed[0].step}" if failed[0].step else "")) if failed else ""
        return f"{run.label}: {run.outcome}{where}"
    parts = [f"{run.label}: {run.outcome}"]
    if jobs:
        parts = [f"{run.label}: {sum(j.done for j in jobs)} of {len(jobs)} jobs done"]
        if failed:
            parts.append(f"{len(failed)} failed")
        parts += [f"{j.name}: {j.step} ({j.step_number}/{j.steps})" if j.step else j.name
                  for j in jobs if j.status == "in_progress"]
    if run.started:
        parts.append(elapsed(now - run.started))
    return " · ".join(parts)


def ticker_line(runs: list[BuildRun], jobs: dict[str, list[BuildJob]], now: float) -> str:
    """The ticker: every run of the newest push, the running ones first (run_line)."""
    return "   |   ".join(run_line(r, jobs.get(r.url), now) for r in ticker_runs(runs))


def ticker_details(runs: list[BuildRun], jobs: dict[str, list[BuildJob]], now: float) -> str:
    """The ticker's tooltip: the commit, then each run with every job and the step it is at."""
    if not runs:
        return ""
    lines = [f"{runs[0].sha[:7]} {runs[0].title}"]
    for run in ticker_runs(runs):
        lines += ["", f"{run.label}: {run.outcome}"
                  + (f", {elapsed(now - run.started)}" if run.started and not run.done else "")]
        for job in jobs.get(run.url) or []:
            step = f", step {job.step_number} of {job.steps}: {job.step}" if job.step and not job.passed else ""
            lines.append(f"    {job.name}: {job.outcome}{step}")
    return "\n".join(lines)


def ticker_target(runs: list[BuildRun], jobs: dict[str, list[BuildJob]]) -> str:
    """What a click on the ticker opens: the job that runs, else the one that failed, else the run that runs or
    failed, else the newest run; "" without runs."""
    ordered = ticker_runs(runs)
    for run in ordered:
        if run.passed:
            break
        listed = jobs.get(run.url) or []
        pick = next((j for j in listed if j.status == "in_progress"), None) or \
            next((j for j in listed if j.done and not j.passed), None)
        return pick.url if pick and pick.url else run.url
    return ordered[0].url if ordered else ""


# --- GitHub's own status: is GitHub up? ------------------------------------------------------------------------

STATUS_PAGE = "https://www.githubstatus.com/"
STATUS_URL = STATUS_PAGE + "api/v2/summary.json"


@dataclass(frozen=True)
class GitHubStatus:
    """What githubstatus.com reports: up when every part of GitHub works as it should and no incident is open. The
    page's indicator goes back to "none" while an incident is still being monitored (11-11-2026: Actions' backlog
    still queued, the page said All Systems Operational), so an open incident counts as a problem by itself."""
    indicator: str                      # "none", "minor", "major", "critical" (Statuspage's)
    description: str                    # "All Systems Operational", "Partially Degraded Service"
    affected: tuple[str, ...] = ()      # "Actions: degraded performance"
    incidents: tuple[str, ...] = ()     # the open incidents: their names, with their stage ("monitoring")

    @property
    def up(self) -> bool:
        return self.indicator == "none" and not self.incidents


def parse_github_status(data: object) -> GitHubStatus:
    data = data if isinstance(data, dict) else {}
    status = data.get("status") if isinstance(data.get("status"), dict) else {}
    affected = tuple(f"{c.get('name')}: {str(c.get('status')).replace('_', ' ')}" for c in data.get("components") or []
                     if isinstance(c, dict) and c.get("status") not in (None, "operational"))
    incidents = tuple(str(i.get("name")) + (f" ({i.get('status')})" if i.get("status") else "")
                      for i in data.get("incidents") or [] if isinstance(i, dict) and i.get("name"))
    return GitHubStatus(str(status.get("indicator") or ""), str(status.get("description") or ""), affected, incidents)


def fetch_github_status() -> GitHubStatus:
    """githubstatus.com's summary (a public page: no token, no limit to count). Raises OSError offline."""
    request = urllib.request.Request(STATUS_URL, headers={"User-Agent": "nexus-release-tool"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return parse_github_status(json.load(response))


# --- Claude usage: the tokens Claude Code used, from its transcripts on this machine ------------------------------

CLAUDE_USAGE_PAGE = "https://claude.ai/settings/usage"
CLAUDE_WINDOW = 5 * 3600                # Claude's usage limits count in windows of 5 hours


@dataclass(frozen=True)
class ClaudeUsage:
    """The tokens of Claude Code's answers since *since* (seconds since the epoch), by kind and by model."""
    since: float
    messages: int = 0
    input: int = 0
    output: int = 0
    cache_write: int = 0
    cache_read: int = 0
    models: tuple[tuple[str, int], ...] = ()     # (model, tokens), the most first

    @property
    def total(self) -> int:
        return self.input + self.output + self.cache_write + self.cache_read


def claude_dir() -> Path:
    """Claude Code's folder: CLAUDE_CONFIG_DIR, else ~/.claude."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def read_claude_answers(folder: Path, since: float) -> list[tuple[float, str, dict]]:
    """Each answer of Claude since *since* in the transcripts under *folder*/projects (subagents' included), once:
    (time, model, usage). An answer of several parts repeats its usage on every part, so it counts by its ids.
    Only files written since then are read; a line that is not an answer, or not JSON, is skipped."""
    seen: set[tuple[str, str]] = set()
    answers = []
    for path in (folder / "projects").rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < since:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if '"usage"' not in line:
                continue
            try:
                entry = json.loads(line)
                message = entry["message"]
                usage = message["usage"]
                at = datetime.datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).timestamp()
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            key = (str(message.get("id")), str(entry.get("requestId")))
            if entry.get("type") != "assistant" or not isinstance(usage, dict) or at < since or key in seen:
                continue
            seen.add(key)
            answers.append((at, str(message.get("model") or "unknown"), usage))
    return answers


def sum_claude_usage(answers: list[tuple[float, str, dict]], since: float) -> ClaudeUsage:
    def count(usage: dict, name: str) -> int:
        value = usage.get(name)
        return value if isinstance(value, int) else 0

    kinds = {"input": "input_tokens", "output": "output_tokens", "cache_write": "cache_creation_input_tokens",
             "cache_read": "cache_read_input_tokens"}
    totals = dict.fromkeys(kinds, 0)
    models: dict[str, int] = {}
    messages = 0
    for at, model, usage in answers:
        if at < since or model == "<synthetic>":         # Claude Code's own notes, not answers of the model
            continue
        messages += 1
        for kind, name in kinds.items():
            totals[kind] += count(usage, name)
        models[model] = models.get(model, 0) + sum(count(usage, name) for name in kinds.values())
    ranked = tuple(sorted(models.items(), key=lambda m: -m[1]))
    return ClaudeUsage(since, messages, models=ranked, **totals)


def fetch_claude_usage(now: float | None = None, folder: Path | None = None) -> tuple[ClaudeUsage, ClaudeUsage] | None:
    """Claude Code's tokens today (since local midnight) and in the last 5 hours; None without Claude Code here."""
    folder = claude_dir() if folder is None else folder
    if not (folder / "projects").is_dir():
        return None
    now = time.time() if now is None else now
    midnight = datetime.datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    recent = now - CLAUDE_WINDOW
    answers = read_claude_answers(folder, min(midnight, recent))
    return sum_claude_usage(answers, midnight), sum_claude_usage(answers, recent)


def short_count(n: int) -> str:
    """12,345 as 12.3k, 4,567,890 as 4.6M: for a pill."""
    for size, unit in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")):
        if n >= size:
            return f"{n / size:.1f}{unit}"
    return str(n)


# --- The commands for the owner --------------------------------------------------------------------------------

def push_command() -> str:
    """git push, after what GitHub has that this checkout lacks is brought in under its commits (owner, 31-10-2026:
    the release's Pin ... commit made the push fail) and CI's jobs passed here (tools/ci-local.sh)."""
    return f"{pull_command()} && {CI_LOCAL} && git push"


def pull_command() -> str:
    """The git pull button: what was pushed from the other machine, with this checkout's own commits put on top of
    it (--rebase: no merge commit) and its changes not committed yet kept as they are (--autostash)."""
    return "git pull --rebase --autostash"


def behind(root: Path, base: str) -> int:
    """How many commits *base* (the remote's main, as git last fetched it) has that HEAD does not: pushed from the
    other machine. 0 when unknown."""
    out = (git(root, "rev-list", "--count", f"HEAD..{base}") or "0").strip()
    return int(out) if out.isdigit() else 0


def add_command() -> str:
    """The Commit step's git add: the list of the tests written from the tests as they are (ALL-TESTS.md, which CI
    compares with them), then everything, the exec bits CI checks, and what is staged now."""
    return f"python3 {ALL_TESTS} && git add -A && tools/fix-modes.sh && git status --short"


def commit_command(message: str, base: str, amend: bool = False, python: str = "python3") -> str:
    """The Commit step's git commit: the version check and the manifest check first (CI's quick ones), the commit
    only when they pass. *amend*: the staged changes join HEAD, with its message."""
    checks = f"{python} {VERSIONS_CHECK} && {python} {MANIFEST_CHECK} --base {shlex.quote(base)}"
    commit = "git commit --amend --no-edit" if amend else f"git commit -m {shlex.quote(message)}"
    return f"{checks} && {commit}"


def git_state(root: Path, base: str) -> tuple[bool, bool, int]:
    """For the steps and git tag: whether something is not staged (changed or new), whether something is staged, and
    how many commits HEAD has that *base* (the last push) does not."""
    status = git(root, "status", "--porcelain") or ""
    lines = [line for line in status.splitlines() if len(line) > 2]
    unstaged = any(line[1] != " " for line in lines)
    staged = any(line[0] not in " ?" for line in lines)
    ahead = (git(root, "rev-list", "--count", f"{base}..HEAD") or "0").strip()
    return unstaged, staged, int(ahead) if ahead.isdigit() else 0


def main() -> int:
    """The units of the checkout, one line each: tools/nrt.sh --list."""
    list_units(load_units(CHECKOUT))
    return 0


def list_units(units: list[Unit]) -> None:
    for problem in bad_tags(CHECKOUT, units):
        print(f"WARNING: {problem}: delete the tag and tag the commit with the bump ({TAG_SCRIPT})", file=sys.stderr)
    for u in units:
        since = "never released" if u.last_tag is None and u.kind != "core" else \
            f"{u.commits} commits since {u.last_tag}" if u.last_tag else ""
        pinned = f"  pinned {u.pinned_tag}{'' if u.pinned_sha else ' (no sha256)'}" if u.pinned_tag else ""
        needs = f"  needs a release: {u.release_reason}" if u.needs_release else \
            f"  {u.release_reason}: {', '.join(u.in_apps)}" if u.in_apps else ""
        print(f"{u.key:<16} {u.version:<8} {since}{pinned}{needs}")


if __name__ == "__main__":
    sys.exit(main())
