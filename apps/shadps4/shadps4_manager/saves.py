# SPDX-License-Identifier: GPL-3.0-or-later
"""The saves shadPS4 keeps (owner, 18-11-2026: a Memory cards tab, as PS5 PCSX2 Manager has). A PS4 game keeps each save
as a folder: home/<user>/savedata/<game's code>/<save's name> in shadPS4's own folder, <user> a number (1000 for the
first one), with sce_sys/param.sfo that names the save (MAINTITLE), its line under it (SUBTITLE) and what is in it
(DETAIL), a picture (sce_sys/icon0.png) and the data itself (seen in shadPS4 0.20's folder on the board).

A save is exported as a .zip with <game's code>/<save's name> at the top, so several fit in one file and a file from
here is taken in again as it is. The saves of every user are listed; one taken in goes to the first user's folder.
Nothing is written outside it. The caller makes sure shadPS4 does not run before a save is taken in or deleted."""

from __future__ import annotations

import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .games import read_sfo

SFO = "sce_sys/param.sfo"
ICON = "sce_sys/icon0.png"
FIRST_USER = "1000"


class SaveError(Exception):
    """What went wrong, in words for the window."""


@dataclass(frozen=True)
class Save:
    folder: Path                        # home/<user>/savedata/<game's code>/<name>
    title: str                          # the save's own title (MAINTITLE)
    subtitle: str                       # its line under it
    detail: str                         # what is in it, in the game's words
    size: int                           # bytes, all files together
    saved: float                        # when its newest file was written

    @property
    def title_id(self) -> str:
        return self.folder.parent.name

    @property
    def name(self) -> str:
        """The save's place under the save folder, as a .zip holds it: CUSA00001/SAVE00."""
        return f"{self.title_id}/{self.folder.name}"

    @property
    def label(self) -> str:
        return " · ".join(part for part in (self.title, self.subtitle) if part) or self.name


def save_folders(home: Path) -> list[Path]:
    """The save folder of every user shadPS4 has: home/<user>/savedata."""
    try:
        return sorted(user / "savedata" for user in (home / "home").iterdir() if (user / "savedata").is_dir())
    except OSError:
        return []


def save_folder(home: Path) -> Path:
    """Where a save taken in goes: the first user's save folder (1000's when shadPS4 has none yet)."""
    return next(iter(save_folders(home)), home / "home" / FIRST_USER / "savedata")


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
    return Save(folder, _text(sfo.get("MAINTITLE")), _text(sfo.get("SUBTITLE")), _text(sfo.get("DETAIL")),
                sum(s.st_size for s in stats), max(s.st_mtime for s in stats))


def find_saves(home: Path) -> list[Save]:
    """The saves of every user, by the game's code and then by folder."""
    folders = []
    for root in save_folders(home):
        try:
            folders += [f for game in root.iterdir() if game.is_dir() for f in game.iterdir() if f.is_dir()]
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
    """*saves* written to the .zip *target*, each as <game's code>/<name>; returns what happened."""
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
    """The files of a .zip by the save each goes to, <game's code>/<name>: its two top folders. Files higher up
    belong to no save. SaveError for a path that would leave its folder."""
    found: dict[str, list[tuple[zipfile.ZipInfo, PurePosixPath]]] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or ":" in info.filename:
            raise SaveError(f"The file names a path outside the save folder: {info.filename}")
        if len(path.parts) > 2:
            found.setdefault("/".join(path.parts[:2]), []).append((info, PurePosixPath(*path.parts[2:])))
    return found


def zip_saves(file: Path) -> list[str]:
    """The saves a .zip holds, <game's code>/<name>: those with a sce_sys/param.sfo. SaveError when it is no .zip
    or holds none."""
    try:
        with zipfile.ZipFile(file) as archive:
            found = _members(archive)
    except (OSError, zipfile.BadZipFile) as error:
        raise SaveError(f"{file.name} could not be read as a .zip: {error}") from error
    names = sorted(name for name, files in found.items() if any(inside.as_posix() == SFO for _, inside in files))
    if not names:
        raise SaveError(f"{file.name} holds no PS4 save: no <game's code>/<save> folder in it has a "
                        "sce_sys/param.sfo.")
    return names


def import_saves(home: Path, file: Path) -> str:
    """The saves in the .zip *file* put in the save folder, each in place of the save of that name; returns what
    happened. A save is unpacked beside its place first, so a file that fails halfway leaves the old save."""
    names = zip_saves(file)
    root = save_folder(home)
    try:
        with zipfile.ZipFile(file) as archive:
            found = _members(archive)
            for name in names:
                target = root.joinpath(*name.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                work = target.with_name(f".{target.name}.{os.getpid()}")
                shutil.rmtree(work, ignore_errors=True)
                try:
                    for info, inside in found[name]:
                        out_path = work.joinpath(*inside.parts)
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(info) as source, open(out_path, "wb") as out:
                            shutil.copyfileobj(source, out)
                    shutil.rmtree(target, ignore_errors=True)
                    work.replace(target)
                finally:
                    shutil.rmtree(work, ignore_errors=True)
    except (OSError, zipfile.BadZipFile) as error:
        raise SaveError(f"{file.name} could not be imported: {error}") from error
    return f"Imported {len(names)} save(s) from {file.name}: {', '.join(names)}."


def delete_saves(saves: list[Save]) -> str:
    """*saves* deleted from the disk, and a game's folder with its last save; returns what happened."""
    failed = []
    for save in saves:
        try:
            shutil.rmtree(save.folder)
            if not any(save.folder.parent.iterdir()):
                save.folder.parent.rmdir()
        except OSError as error:
            failed.append(f"{save.name} ({error})")
    if failed:
        raise SaveError(f"Not deleted: {', '.join(failed)}.")
    return f"Deleted {len(saves)} save(s)."
