# SPDX-License-Identifier: GPL-3.0-or-later
"""apps.toml: the apps of this portal release, each pinned to one release tag (see the comment in apps.toml)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

TAG_PREFIX = "ps5-"                             # the suite's tags (TAG_PREFIX at the repository's root)
_TAG = re.compile(r"^ps5-(?P<app>[a-z0-9-]+)-v(?P<version>\d+\.\d+\.\d+)$")
_SHA256 = re.compile(r"^([0-9a-f]{64})?$")
_QUICKFIX = re.compile(r"^[a-z][a-z0-9-]*$")
# category = "<key>": the app's category (its icon, icons/categories.toml) and the portal's tab for it, in this order.
CATEGORIES = {"sustainable": "Sustainable", "graphics": "Graphics", "gaming": "Gaming", "utilities": "Utilities"}
# Categories of earlier portal releases, still read in their manifests (the tools compare with the last portal
# release): none in this suite.
LEGACY_CATEGORIES: tuple[str, ...] = ()
# Apps renamed in the suite (old key: new key), for the record of a copy installed under the old key: Board Test
# and Bluetooth got their keys on 15-11-2026.
RENAMED = {"bazzite": "board", "btpair": "bluetooth"}


REQUIRED_FIRST = "board"                        # Board Test: always installed, the first tile


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Quickfix:
    """One quickfix of an app made of small quickfixes ([[apps.<key>.quickfixes]]): a tile of its own in the app's category,
    which opens that quickfix's window. Installed, updated and removed with its app."""
    key: str                                    # "tools": the tile is <app>/<key>
    name: str                                   # on its tile
    summary: str
    launch: str                                 # the command that opens it
    changes_board: bool = False
    board_change: str = ""                      # with changes_board: as an app's, in its own box of the wiki chapter


@dataclass(frozen=True)
class AppEntry:
    key: str                                    # "compute": folder under apps/, tag prefix
    name: str
    summary: str
    tag: str
    sha256: str = ""
    required: bool = False
    changes_board: bool = False
    # board_change: for an app that changes the board, what it touches, what stays after a reboot or a power off,
    # what it never touches (the BIOS, the firmware) and how it is undone, in a few plain sentences: the tile's
    # tooltip shows it under "Changes the board", and the app's wiki chapter opens with the same text in a box
    # (tools/check_manifest.py keeps the two the same). "" in a manifest from before it (owner, 03-11-2026).
    board_change: str = ""
    category: str = ""                          # a key of CATEGORIES; "" only in a manifest from before categories
    install: tuple[str, ...] = ()
    uninstall: tuple[str, ...] = ()
    detect: tuple[str, ...] = ()
    launch: tuple[tuple[str, str], ...] = ()
    short: str = ""                             # the name on its tile; "": the name without the suite prefix
    # withdrawn = "<reason>" in apps.toml: the release was withdrawn (privacy, security or another problem). The
    # portal shows the app as not available, offers no install, and removes it from a board that has it; the GitHub
    # release stays, marked withdrawn (a pre-release named "Withdrawn: ...", which no update check offers). Not for
    # the required app. "": not withdrawn.
    withdrawn: str = ""
    # quickfixes: an app made of small quickfixes shows each as a tile of its own (owner, 15-11-2026), not one of its own.
    quickfixes: tuple[Quickfix, ...] = ()
    # On the tile of one quickfix (tiles()): its key, and the app's own name; "" on an app's entry.
    quickfix: str = ""
    app_name: str = ""

    @property
    def tile(self) -> str:
        """The key of its tile: the app's key, or <app>/<quickfix> for one quickfix of it."""
        return f"{self.key}/{self.quickfix}" if self.quickfix else self.key

    @property
    def release_name(self) -> str:
        """The name of what is installed: the app's, also on a quickfix's tile."""
        return self.app_name or self.name

    def tiles(self) -> tuple["AppEntry", ...]:
        """What the portal shows of it: the app's tile, or a tile per quickfix. A quickfix's is the app's entry with the
        quickfix's name, summary, launch command and board change, so installing, updating and the records stay the
        app's (its key and tag)."""
        if not self.quickfixes:
            return (self,)
        return tuple(replace(self, name=h.name, short=h.name, summary=h.summary, launch=(("Open", h.launch),),
                             changes_board=h.changes_board, board_change=h.board_change, quickfixes=(),
                             quickfix=h.key, app_name=self.name) for h in self.quickfixes)

    @property
    def version(self) -> str:
        return self.tag.rsplit("-v", 1)[1] if self.tag else ""

    @property
    def asset(self) -> str:
        """The release asset: <tag>.tar.gz, which unpacks into a folder named <tag>."""
        return f"{self.tag}.tar.gz"


def version_tuple(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(p) for p in version.split("."))
    return major, minor, patch


def _strings(key: str, field: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ManifestError(f"[apps.{key}] {field} must be a list of non-empty strings")
    return tuple(value)


def _entry(key: str, raw: dict) -> AppEntry:
    table = "apps"
    for field in ("name", "summary", "tag"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            raise ManifestError(f"[{table}.{key}] needs a non-empty {field}")
    match = _TAG.match(raw["tag"])
    if not match or match["app"] != key:
        raise ManifestError(f"[{table}.{key}] tag {raw['tag']!r} is not ps5-{key}-v<x.y.z>")
    sha = str(raw.get("sha256", "")).lower()
    if not _SHA256.match(sha):
        raise ManifestError(f"[{table}.{key}] sha256 must be empty or 64 hex digits")
    short = raw.get("short", "")
    if not isinstance(short, str):
        raise ManifestError(f"[{table}.{key}] short must be a string")
    board_change = raw.get("board_change", "")
    if not isinstance(board_change, str):
        raise ManifestError(f"[{table}.{key}] board_change must be a string")
    withdrawn = raw.get("withdrawn", "")
    if "withdrawn" in raw and (not isinstance(withdrawn, str) or not withdrawn.strip()):
        raise ManifestError(f"[{table}.{key}] withdrawn must say why the release was withdrawn")
    category = raw.get("category", "")
    if category not in ("", *CATEGORIES, *LEGACY_CATEGORIES):
        raise ManifestError(f"[{table}.{key}] category must be one of {', '.join(CATEGORIES)}")
    launch = raw.get("launch", [])
    if not isinstance(launch, list) or not all(isinstance(item, list) and len(item) == 2 and
                                               all(isinstance(s, str) and s for s in item) for item in launch):
        raise ManifestError(f"[{table}.{key}] launch must be a list of [label, command] pairs")
    entry = AppEntry(key=key, name=raw["name"], summary=raw["summary"], tag=raw["tag"], sha256=sha,
                     required=bool(raw.get("required", False)), changes_board=bool(raw.get("changes_board", False)),
                     board_change=" ".join(board_change.split()), category=category,
                     install=_strings(key, "install", raw.get("install")),
                     uninstall=_strings(key, "uninstall", raw.get("uninstall")),
                     detect=_strings(key, "detect", raw.get("detect")),
                     launch=tuple((label, command) for label, command in launch), short=short.strip(),
                     withdrawn=withdrawn.strip(),
                     quickfixes=_quickfixes(key, raw["quickfixes"]) if "quickfixes" in raw else ())
    if not entry.install or not entry.uninstall or not entry.detect:
        raise ManifestError(f"[{table}.{key}] install, uninstall and detect must not be empty")
    if entry.required and entry.withdrawn:
        raise ManifestError(f"[{table}.{key}] a required app cannot be withdrawn: pin a release that works")
    return entry


def _quickfixes(key: str, value: object) -> tuple[Quickfix, ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ManifestError(f"[apps.{key}] quickfixes must be [[apps.{key}.quickfixes]] tables")
    quickfixes = []
    for raw in value:
        for field in ("key", "name", "summary", "launch"):
            if not isinstance(raw.get(field), str) or not raw[field].strip():
                raise ManifestError(f"[[apps.{key}.quickfixes]] needs a non-empty {field}")
        if not _QUICKFIX.match(raw["key"]):
            raise ManifestError(f"[[apps.{key}.quickfixes]] key {raw['key']!r} is not lowercase letters, digits, -")
        board_change = raw.get("board_change", "")
        if not isinstance(board_change, str):
            raise ManifestError(f"[[apps.{key}.quickfixes]] {raw['key']}: board_change must be a string")
        quickfixes.append(Quickfix(raw["key"], raw["name"], raw["summary"], raw["launch"],
                              bool(raw.get("changes_board", False)), " ".join(board_change.split())))
    if len({h.key for h in quickfixes}) != len(quickfixes):
        raise ManifestError(f"[apps.{key}] two quickfixes have the same key")
    return tuple(quickfixes)


def _load_toml(text: str) -> dict:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"apps.toml is not valid TOML: {exc}") from exc


def parse(text: str) -> list[AppEntry]:
    """The pinned apps in display order: the required ones first (Board Test, board, before the others; owner,
    15-11-2026: PS5 Quickfix is required too), the rest in file order. The [checkout.*] tables of an earlier portal
    release's manifest (apps that ran from a checkout) are not read."""
    apps = _load_toml(text).get("apps")
    if not isinstance(apps, dict) or not apps:
        raise ManifestError("apps.toml has no [apps.<name>] tables")
    entries = [_entry(key, raw) for key, raw in apps.items()]
    if not any(e.required for e in entries):
        raise ManifestError(f"apps.toml must have a required app ({REQUIRED_FIRST})")
    return sorted(entries, key=lambda e: (not e.required, e.key != REQUIRED_FIRST))   # stable: file order within


def load(path: Path) -> list[AppEntry]:
    return parse(path.read_text(encoding="utf-8"))
