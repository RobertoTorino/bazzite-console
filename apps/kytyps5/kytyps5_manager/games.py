# SPDX-License-Identifier: GPL-3.0-or-later
"""The PS5 games in the chosen folders: an installed game is a folder with eboot.bin and, beside it,
sce_sys/param.json with its title, title ID (PPSA00001) and version.

The scan is shadPS4 Manager's (an eboot.bin found below a folder, a path found twice counted once). The title comes
from param.json: localizedParameters holds a titleName per language, and defaultLanguage names the one to take.
Without param.json the folder's name is the title. KytyPS5-Native starts the game's folder (--game <folder>)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

MAX_DEPTH = 5                           # as deep as shadPS4 Manager looks for a game in a game folder


def is_file(path: Path) -> bool:
    """path.is_file(), False when it cannot be asked: a failing or half-mounted SD card answers with an error (EIO)
    instead of no, which ended the scan (the Windows suite's empty card slot, 29-10-2026)."""
    try:
        return path.is_file()
    except OSError:
        return False


@dataclass(frozen=True)
class Game:
    eboot: Path
    title: str
    title_id: str = ""
    version: str = ""

    @property
    def folder(self) -> Path:
        return self.eboot.parent

    def picture(self, name: str) -> Path | None:
        """One of the game's own pictures in sce_sys (icon0.png, pic1.png), if it has it."""
        path = self.folder / "sce_sys" / name
        return path if is_file(path) else None


def read_param(text: str) -> dict:
    """The entries of a param.json; {} for anything that is not one."""
    try:
        found = json.loads(text)
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def title_of(param: dict) -> str:
    """The game's title in its default language, else in any language it names; "" when it names none."""
    localized = param.get("localizedParameters")
    if not isinstance(localized, dict):
        return ""
    names = [localized.get(str(localized.get("defaultLanguage")))]
    names += [value for key, value in sorted(localized.items()) if key != "defaultLanguage"]
    for entry in names:
        if isinstance(entry, dict) and str(entry.get("titleName") or "").strip():
            return str(entry["titleName"]).strip()
    return ""


def read_game(eboot: Path) -> Game:
    """The game in eboot's folder."""
    try:
        param = read_param((eboot.parent / "sce_sys" / "param.json").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        param = {}
    return Game(eboot, title_of(param) or eboot.parent.name, str(param.get("titleId") or ""),
                str(param.get("contentVersion") or ""))


def _eboots(root: Path, depth: int = MAX_DEPTH):
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    folders = []
    for entry in entries:
        try:
            plain = entry.is_file()
            folder = not plain and depth > 0 and entry.is_dir(follow_symlinks=False)
        except OSError:                                 # a failing card: skipped, the scan goes on
            continue
        if plain and entry.name.lower() == "eboot.bin":
            yield Path(entry.path)
        elif folder:
            folders.append(entry)
    for entry in folders:
        if not entry.name.startswith(".") and entry.name != "sce_sys":
            yield from _eboots(Path(entry.path), depth - 1)


def scan(folders: list[Path]) -> list[Game]:
    """Every game below the folders (a game found twice counted once), sorted by title."""
    seen: set[Path] = set()
    games = []
    for folder in folders:
        for eboot in _eboots(folder):
            key = eboot.resolve()
            if key in seen:
                continue
            seen.add(key)
            games.append(read_game(eboot))
    return sorted(games, key=lambda g: (g.title.casefold(), g.title_id, str(g.eboot)))
