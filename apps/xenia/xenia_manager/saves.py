# SPDX-License-Identifier: GPL-3.0-or-later
"""The saves Xenia keeps (owner, 18-11-2026: a Memory cards tab, as PS5 PCSX2 Manager has). Xenia keeps a game's saved
games as folders in its content folder: content/<profile>/<game's code>/00000001/<save's name>, <profile> the 16
hexadecimal digits of a profile's XUID, the game's code its 8 (4D5307E6), 00000001 the console's content type for
a saved game (Xenia Canary's content_manager.cc, ResolvePackageRoot). What Xenia notes of a save beside it, in
<game's code>/Headers/00000001/<save's name>.header, goes with the save.

A save is exported as a .zip with <game's code>/00000001/<save's name> at the top (and its header in its place), so
several fit in one file and a file from here is taken in again as it is. The saves of every profile are listed; one
taken in goes to the first profile's folder, and Xenia has to have a profile for that. Nothing is written outside
it. The caller makes sure Xenia does not run before a save is taken in or deleted."""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SAVED_GAME = "00000001"                 # XContentType::kSavedGame
HEADERS = "Headers"
PROFILE = re.compile(r"^[0-9A-Fa-f]{16}$")
COMMON = "0" * 16                       # the folder of what belongs to no profile (add-ons): no saves
CODE = re.compile(r"^[0-9A-Fa-f]{8}$")


class SaveError(Exception):
    """What went wrong, in words for the window."""


@dataclass(frozen=True)
class Save:
    folder: Path                        # content/<profile>/<game's code>/00000001/<name>
    size: int                           # bytes, all files together
    saved: float                        # when its newest file was written

    @property
    def title_id(self) -> str:
        return self.folder.parent.parent.name.upper()

    @property
    def title(self) -> str:
        return self.folder.name

    @property
    def name(self) -> str:
        """The save's place under a profile's folder, as a .zip holds it: 4D5307E6/00000001/Save1."""
        return f"{self.title_id}/{SAVED_GAME}/{self.folder.name}"

    @property
    def label(self) -> str:
        return f"{self.title_id} · {self.folder.name}"

    @property
    def headers(self) -> list[Path]:
        """What Xenia notes of the save beside it: <game's code>/Headers/00000001/<name>.header."""
        folder = self.folder.parent.parent / HEADERS / SAVED_GAME
        try:
            return sorted(f for f in folder.iterdir() if f.is_file() and f.stem == self.folder.name)
        except OSError:
            return []


def content_folder(home: Path) -> Path:
    """Xenia's content folder, in its own folder."""
    return home / "content"


def profiles(home: Path) -> list[Path]:
    """The folder of every profile Xenia has content for."""
    try:
        return sorted(f for f in content_folder(home).iterdir()
                      if f.is_dir() and PROFILE.match(f.name) and f.name != COMMON)
    except OSError:
        return []


def save_folder(home: Path) -> Path | None:
    """Where a save taken in goes: the first profile's folder; None while Xenia has no profile."""
    return next(iter(profiles(home)), None)


def read_save(folder: Path) -> Save | None:
    """The save in *folder*; None for a folder without files."""
    try:
        stats = [f.stat() for f in folder.rglob("*") if f.is_file()]
    except OSError:
        return None
    if not stats:
        return None
    return Save(folder, sum(s.st_size for s in stats), max(s.st_mtime for s in stats))


def find_saves(home: Path) -> list[Save]:
    """The saves of every profile, by the game's code and then by name."""
    folders = []
    for profile in profiles(home):
        try:
            for game in profile.iterdir():
                if game.is_dir() and CODE.match(game.name) and (game / SAVED_GAME).is_dir():
                    folders += [f for f in (game / SAVED_GAME).iterdir() if f.is_dir()]
        except OSError:
            continue
    saves = [save for save in map(read_save, folders) if save is not None]
    return sorted(saves, key=lambda s: s.name.lower())


def size_text(size: int) -> str:
    """A size in words: "812 B", "24 KB", "1.4 MB"."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{round(size / 1024)} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def export_saves(saves: list[Save], target: Path) -> str:
    """*saves* written to the .zip *target*, each as <game's code>/00000001/<name> with its header; returns what
    happened."""
    work = target.with_name(f".{target.name}.{os.getpid()}")
    try:
        with zipfile.ZipFile(work, "w", zipfile.ZIP_DEFLATED) as archive:
            for save in saves:
                for file in sorted(f for f in save.folder.rglob("*") if f.is_file()):
                    archive.write(file, f"{save.name}/{file.relative_to(save.folder).as_posix()}")
                for header in save.headers:
                    archive.write(header, f"{save.title_id}/{HEADERS}/{SAVED_GAME}/{header.name}")
        work.replace(target)
    except OSError as error:
        work.unlink(missing_ok=True)
        raise SaveError(f"The saves could not be exported: {error}") from error
    return f"Exported {len(saves)} save(s) to {target}."


def _members(archive: zipfile.ZipFile) -> tuple[dict[str, list[tuple[zipfile.ZipInfo, PurePosixPath]]],
                                                 list[tuple[zipfile.ZipInfo, PurePosixPath]]]:
    """The files of a .zip by the save each goes to (<game's code>/00000001/<name>: what is inside it), and the
    headers (<game's code>/Headers/00000001/<file>) with their place. Other files belong to no save. SaveError for
    a path that would leave its folder."""
    found: dict[str, list[tuple[zipfile.ZipInfo, PurePosixPath]]] = {}
    headers: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    for info in archive.infolist():
        if info.is_dir():
            continue
        path = PurePosixPath(info.filename.replace("\\", "/"))
        parts = path.parts
        if path.is_absolute() or ".." in parts or ":" in info.filename:
            raise SaveError(f"The file names a path outside the save folder: {info.filename}")
        if len(parts) > 3 and CODE.match(parts[0]) and parts[1] == SAVED_GAME:
            name = f"{parts[0].upper()}/{SAVED_GAME}/{parts[2]}"
            found.setdefault(name, []).append((info, PurePosixPath(*parts[3:])))
        elif len(parts) == 4 and CODE.match(parts[0]) and parts[1:3] == (HEADERS, SAVED_GAME):
            headers.append((info, PurePosixPath(parts[0].upper(), *parts[1:])))
    return found, headers


def zip_saves(file: Path) -> list[str]:
    """The saves a .zip holds, <game's code>/00000001/<name>. SaveError when it is no .zip or holds none."""
    try:
        with zipfile.ZipFile(file) as archive:
            found, _ = _members(archive)
    except (OSError, zipfile.BadZipFile) as error:
        raise SaveError(f"{file.name} could not be read as a .zip: {error}") from error
    if not found:
        raise SaveError(f"{file.name} holds no XBOX 360 save: no <game's code>/{SAVED_GAME}/<save> folder is in it.")
    return sorted(found)


def import_saves(home: Path, file: Path) -> str:
    """The saves in the .zip *file* put in the first profile's folder, each in place of the save of that name, with
    their headers; returns what happened. A save is unpacked beside its place first, so a file that fails halfway
    leaves the old save."""
    names = zip_saves(file)
    root = save_folder(home)
    if root is None:
        raise SaveError("Xenia has no profile yet to keep a save under: start Xenia once (Xenia settings) and make "
                        "one, then import again.")
    try:
        with zipfile.ZipFile(file) as archive:
            found, headers = _members(archive)
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
            for info, place in headers:
                out_path = root.joinpath(*place.parts)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, open(out_path, "wb") as out:
                    shutil.copyfileobj(source, out)
    except (OSError, zipfile.BadZipFile) as error:
        raise SaveError(f"{file.name} could not be imported: {error}") from error
    return f"Imported {len(names)} save(s) from {file.name}: {', '.join(names)}."


def delete_saves(saves: list[Save]) -> str:
    """*saves* deleted from the disk, each with its header; returns what happened."""
    failed = []
    for save in saves:
        try:
            for header in save.headers:
                header.unlink()
            shutil.rmtree(save.folder)
        except OSError as error:
            failed.append(f"{save.name} ({error})")
    if failed:
        raise SaveError(f"Not deleted: {', '.join(failed)}.")
    return f"Deleted {len(saves)} save(s)."
