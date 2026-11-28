# SPDX-License-Identifier: GPL-3.0-or-later
"""The saves on PPSSPP's memory stick (owner, 18-11-2026: a Memory cards tab, as PS5 PCSX2 Manager has). A PSP has no
memory card files: a game keeps each save as a folder in PSP/SAVEDATA on the memory stick, named after the game's
code and the save's own name (ULUS10521DATA00), with a PARAM.SFO that names the game (TITLE), the save
(SAVEDATA_TITLE) and what is in it (SAVEDATA_DETAIL), a picture (ICON0.PNG) and the data itself.

A save is exported as a .zip with its folder at the top, so several fit in one file and a file from here is taken in
again as it is; a .zip with a save's files at the top (no folder) is taken in under the .zip's own name. Nothing is
written outside PSP/SAVEDATA. The caller makes sure PPSSPP does not run before a save is taken in or deleted."""

from __future__ import annotations

import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .games import read_sfo

SFO = "PARAM.SFO"
ICON = "ICON0.PNG"


class SaveError(Exception):
    """What went wrong, in words for the window."""


@dataclass(frozen=True)
class Save:
    folder: Path                        # PSP/SAVEDATA/<name>
    game: str                           # the game's title, "" when the save does not name it
    title: str                          # the save's own title
    detail: str                         # what is in it, in the game's words
    size: int                           # bytes, all files together
    saved: float                        # when its newest file was written

    @property
    def name(self) -> str:
        return self.folder.name

    @property
    def label(self) -> str:
        return " · ".join(part for part in (self.game, self.title) if part) or self.name


def save_folder(memstick: Path) -> Path:
    """Where PPSSPP keeps the saves: PSP/SAVEDATA on its memory stick."""
    return memstick / "PSP" / "SAVEDATA"


def _text(value) -> str:
    return " ".join(str(value or "").split())           # PSP texts may hold line breaks


def read_save(folder: Path) -> Save | None:
    """The save in *folder*; None for a folder without files."""
    try:
        files = [f for f in folder.rglob("*") if f.is_file()]
        if not files:
            return None
        stats = [f.stat() for f in files]
        sfo = read_sfo((folder / SFO).read_bytes()) if (folder / SFO).is_file() else {}
    except OSError:
        return None
    return Save(folder, _text(sfo.get("TITLE")), _text(sfo.get("SAVEDATA_TITLE")), _text(sfo.get("SAVEDATA_DETAIL")),
                sum(s.st_size for s in stats), max(s.st_mtime for s in stats))


def find_saves(memstick: Path) -> list[Save]:
    """The saves on the memory stick, by game and then by folder."""
    try:
        folders = [f for f in save_folder(memstick).iterdir() if f.is_dir()]
    except OSError:
        return []
    saves = [save for save in map(read_save, folders) if save is not None]
    return sorted(saves, key=lambda s: (s.game.lower(), s.name.lower()))


def icon(save: Save) -> bytes | None:
    """The save's picture (ICON0.PNG), None when it has none."""
    try:
        return (save.folder / ICON).read_bytes()
    except OSError:
        return None


def size_text(size: int) -> str:
    """A size in words: "812 B", "24 KB", "1.4 MB"."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{round(size / 1024)} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def export_saves(saves: list[Save], target: Path) -> str:
    """*saves* written to the .zip *target*, each as its folder; returns what happened."""
    work = target.with_name(f".{target.name}.{os.getpid()}")
    try:
        with zipfile.ZipFile(work, "w", zipfile.ZIP_DEFLATED) as archive:
            for save in saves:
                for file in sorted(f for f in save.folder.rglob("*") if f.is_file()):
                    archive.write(file, f"{save.name}/{file.relative_to(save.folder).as_posix()}")
        work.replace(target)
    except OSError as error:
        work.unlink(missing_ok=True)
        raise SaveError(f"The saves could not be exported: {error}") from error
    return f"Exported {len(saves)} save(s) to {target}."


def _members(archive: zipfile.ZipFile, fallback: str) -> dict[str, list[tuple[zipfile.ZipInfo, PurePosixPath]]]:
    """The files of a .zip by the save folder each goes to: its top folder, or *fallback* for files at the top.
    SaveError for a path that would leave its folder."""
    found: dict[str, list[tuple[zipfile.ZipInfo, PurePosixPath]]] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or ":" in info.filename:
            raise SaveError(f"The file names a path outside the save folder: {info.filename}")
        name, inside = (path.parts[0], PurePosixPath(*path.parts[1:])) if len(path.parts) > 1 else (fallback, path)
        found.setdefault(name, []).append((info, inside))
    return found


def zip_saves(file: Path) -> list[str]:
    """The save folders a .zip holds: those with a PARAM.SFO. SaveError when it is no .zip or holds none."""
    try:
        with zipfile.ZipFile(file) as archive:
            found = _members(archive, file.stem)
    except (OSError, zipfile.BadZipFile) as error:
        raise SaveError(f"{file.name} could not be read as a .zip: {error}") from error
    names = sorted(name for name, files in found.items() if any(str(inside) == SFO for _, inside in files))
    if not names:
        raise SaveError(f"{file.name} holds no PSP save: no folder in it has a PARAM.SFO.")
    return names


def import_saves(memstick: Path, file: Path) -> str:
    """The saves in the .zip *file* put in PSP/SAVEDATA, each in place of the save of that name; returns what
    happened. A save is unpacked beside its place first, so a file that fails halfway leaves the old save."""
    names = zip_saves(file)
    root = save_folder(memstick)
    try:
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(file) as archive:
            found = _members(archive, file.stem)
            for name in names:
                work = root / f".{name}.{os.getpid()}"
                shutil.rmtree(work, ignore_errors=True)
                try:
                    for info, inside in found[name]:
                        target = work.joinpath(*inside.parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(info) as source, open(target, "wb") as out:
                            shutil.copyfileobj(source, out)
                    shutil.rmtree(root / name, ignore_errors=True)
                    work.replace(root / name)
                finally:
                    shutil.rmtree(work, ignore_errors=True)
    except (OSError, zipfile.BadZipFile) as error:
        raise SaveError(f"{file.name} could not be imported: {error}") from error
    return f"Imported {len(names)} save(s) from {file.name}: {', '.join(names)}."


def delete_saves(saves: list[Save]) -> str:
    """*saves* deleted from the memory stick; returns what happened."""
    failed = []
    for save in saves:
        try:
            shutil.rmtree(save.folder)
        except OSError as error:
            failed.append(f"{save.name} ({error})")
    if failed:
        raise SaveError(f"Not deleted: {', '.join(failed)}.")
    return f"Deleted {len(saves)} save(s)."
