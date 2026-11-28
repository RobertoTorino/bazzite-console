# SPDX-License-Identifier: GPL-3.0-or-later
"""The saves Vita3K keeps (owner, 18-11-2026: a Memory cards tab, as PS5 PCSX2 Manager has). A PS Vita game keeps its
save as a folder in ux0/user/<user>/savedata on Vita3K's storage, <user> a number of two digits (00 for the first
one), named after the game's code (PCSB00001). A save that came from a PS Vita has sce_sys/param.sfo, which may
name it; one a game made in Vita3K is the game's own files alone, so the tab names the game by its code.

A save is exported as a .zip with its folder at the top, so several fit in one file and a file from here is taken in
again as it is. The saves of every user are listed; one taken in goes to the first user's folder. Nothing is written
outside it. The caller makes sure Vita3K does not run before a save is taken in or deleted. (Vita3K's own window
takes in and writes the encrypted saves of a real PS Vita; this is for the saves as Vita3K keeps them.)"""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .games import read_sfo

SFO = "sce_sys/param.sfo"
ICON = "sce_sys/icon0.png"
CODE = re.compile(r"^[A-Z]{4}[0-9]{5}")     # a save folder is named after its game: PCSB00001


class SaveError(Exception):
    """What went wrong, in words for the window."""


@dataclass(frozen=True)
class Save:
    folder: Path                        # ux0/user/<user>/savedata/<name>
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


FIRST_USER = "00"


def save_folders(vita_fs: Path) -> list[Path]:
    """The save folder of every user Vita3K has: ux0/user/<user>/savedata."""
    try:
        return sorted(user / "savedata" for user in (vita_fs / "ux0" / "user").iterdir()
                      if (user / "savedata").is_dir())
    except OSError:
        return []


def save_folder(vita_fs: Path) -> Path:
    """Where a save taken in goes: the first user's save folder (00's when Vita3K has none yet)."""
    return next(iter(save_folders(vita_fs)), vita_fs / "ux0" / "user" / FIRST_USER / "savedata")


def _text(value) -> str:
    return " ".join(str(value or "").split())           # the texts may hold line breaks


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
    return Save(folder, _text(sfo.get("TITLE")), _text(sfo.get("SUB_TITLE") or sfo.get("SAVEDATA_TITLE")),
                _text(sfo.get("DETAIL") or sfo.get("SAVEDATA_DETAIL")),
                sum(s.st_size for s in stats), max(s.st_mtime for s in stats))


def find_saves(vita_fs: Path) -> list[Save]:
    """The saves of every user, by folder: the game's code."""
    folders = []
    for root in save_folders(vita_fs):
        try:
            folders += [f for f in root.iterdir() if f.is_dir()]
        except OSError:
            continue
    saves = [save for save in map(read_save, folders) if save is not None]
    return sorted(saves, key=lambda s: s.name.lower())


def icon(save: Save) -> bytes | None:
    """The save's picture (sce_sys/icon0.png), None when it has none."""
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


def _members(archive: zipfile.ZipFile) -> dict[str, list[tuple[zipfile.ZipInfo, PurePosixPath]]]:
    """The files of a .zip by the save folder each goes to: its top folder. Files at the top belong to no save.
    SaveError for a path that would leave its folder."""
    found: dict[str, list[tuple[zipfile.ZipInfo, PurePosixPath]]] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or ":" in info.filename:
            raise SaveError(f"The file names a path outside the save folder: {info.filename}")
        if len(path.parts) > 1:
            found.setdefault(path.parts[0], []).append((info, PurePosixPath(*path.parts[1:])))
    return found


def zip_saves(file: Path) -> list[str]:
    """The save folders a .zip holds: the top folders named after a game's code (a save Vita3K made has no
    param.sfo to know it by). SaveError when it is no .zip or holds none."""
    try:
        with zipfile.ZipFile(file) as archive:
            found = _members(archive)
    except (OSError, zipfile.BadZipFile) as error:
        raise SaveError(f"{file.name} could not be read as a .zip: {error}") from error
    names = sorted(name for name in found if CODE.match(name))
    if not names:
        raise SaveError(f"{file.name} holds no PS Vita save: no folder in it is named after a game's code, such as "
                        "PCSB00001.")
    return names


def import_saves(vita_fs: Path, file: Path) -> str:
    """The saves in the .zip *file* put in the save folder, each in place of the save of that name; returns what
    happened. A save is unpacked beside its place first, so a file that fails halfway leaves the old save."""
    names = zip_saves(file)
    root = save_folder(vita_fs)
    try:
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(file) as archive:
            found = _members(archive)
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
    """*saves* deleted from the disk; returns what happened."""
    failed = []
    for save in saves:
        try:
            shutil.rmtree(save.folder)
        except OSError as error:
            failed.append(f"{save.name} ({error})")
    if failed:
        raise SaveError(f"Not deleted: {', '.join(failed)}.")
    return f"Deleted {len(saves)} save(s)."
