# SPDX-License-Identifier: GPL-3.0-or-later
"""The shadPS4 Linux build this version of the app pins from a tagged GitHub release (an AppImage in a zip), checked
against its SHA-256. A newer stable comes with a new version of the app; the app reports when one is available.
Another build, a stable release or the pre-release (a nightly), is downloaded beside it in the version manager
(owner, 20-11-2026: as shadPS4's own launcher; core's builds), checked against the SHA-256 GitHub publishes; it was
not tried on the board.

Each build goes to ~/.local/share/ps5-shadps4-manager/emulator/<version>/, with "current" pointing to the one in
use. The run wrapper (~/.local/bin/ps5-shadps4-run) starts "current", so the Steam shortcuts keep working when the
version changes."""

from __future__ import annotations

import hashlib
import re
import shutil
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from bazzite_console_core import builds
from bazzite_console_core.builds import Build
from bazzite_console_core.platform import data_home
from bazzite_console_core.updates import Fetch, ReleaseInfo, github_fetch, latest_release, version_tuple

from . import APP_ID, __version__

VERSION = "0.21.0"
TAG = "v.0.21.0"                        # shadPS4 tags its releases "v.0.21.0"
ASSET = "shadps4-linux-sdl-0.21.0.zip"
SHA256 = "7c41c58254461d742b5edf564e23795697b63e9e46de11d0e1ed67bd2cbaae68"
SIZE_MB = 32                            # the zip, for the question before downloading
NAME = "shadps4 v0.21.0 - codename Until Mavethee Dawn"     # the release's name on GitHub
PUBLISHED = "2026-10-30"
MEMBER = "Shadps4-sdl.AppImage"         # the only file in the zip
REPO = "shadps4-emu/shadPS4"
URL = f"https://github.com/{REPO}/releases/download/{TAG}/{ASSET}"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/tag/{TAG}"
CHUNK = 1 << 20
TIMEOUT = 30

Progress = Callable[[int, int], None]                   # bytes so far, total (0 when unknown)
Download = Callable[[str, Path, Progress | None], None]


class EmulatorError(Exception):
    pass


def emulator_home() -> Path:
    return data_home() / APP_ID / "emulator"


def appimage(home: Path) -> Path:
    """The AppImage the run wrapper starts."""
    return home / "current" / MEMBER


def installed_version(home: Path) -> str:
    """The installed shadPS4 version ("0.21.0"), "" when none is."""
    current = home / "current"
    if not (current / MEMBER).is_file():
        return ""
    return current.resolve().name


def download(url: str, dest: Path, progress: Progress | None = None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": f"{APP_ID}/{__version__}"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response, dest.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while chunk := response.read(CHUNK):
            out.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def unpack(archive: Path, member: Path) -> None:
    """The AppImage out of a release's zip (core's builds.install calls it on the checked download)."""
    try:
        with zipfile.ZipFile(archive) as packed:
            if MEMBER not in packed.namelist():
                raise builds.BuildError(f"{archive.name} has no {MEMBER}.")
            with packed.open(MEMBER) as source, member.open("wb") as out:
                shutil.copyfileobj(source, out, CHUNK)
    except zipfile.BadZipFile as error:
        raise builds.BuildError(f"{archive.name} is damaged.") from error


def tested() -> Build:
    """The release this version of the app was tried with."""
    return Build(VERSION, NAME, PUBLISHED, builds.RELEASE, URL, ASSET, SHA256, SIZE_MB << 20, RELEASE_PAGE)


def install(home: Path, fetch: Download = download, progress: Progress | None = None) -> str:
    """Puts the pinned stable release in use: from its folder when it is there, else downloaded, checked against
    its SHA-256 and unpacked. Other builds stay. Returns what was done. Nothing changes when a step fails
    (EmulatorError)."""
    try:
        if (home / VERSION / MEMBER).is_file() and (home / VERSION / builds.INFO).is_file():
            builds.use(home, VERSION, MEMBER)
            return f"shadPS4 {VERSION} is in use."
        builds.install(home, tested(), MEMBER, fetch, progress, unpack, refused="pinned by this app")
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    return f"shadPS4 {VERSION} is installed."


_ASSET = re.compile(r"shadps4-linux-sdl-(.+)\.zip")


def _pick(release: dict, asset: dict) -> str | None:
    match = _ASSET.fullmatch(str(asset.get("name", "")))
    return match.group(1) if match else None


def available(fetch: Fetch | None = None) -> list[Build]:
    """The shadPS4 builds that can be downloaded, newest first: the stable releases and the pre-release (a nightly,
    named after its date and commit), each the Linux SDL zip (builds.BuildError when GitHub cannot be asked)."""
    return builds.github_builds(REPO, _pick, fetch or github_fetch(f"{APP_ID}/{__version__}"))


def install_build(home: Path, build: Build, fetch: Download = download, progress: Progress | None = None) -> None:
    """Downloads *build* beside the others, checked against its SHA-256 and unpacked; not in use yet."""
    builds.install(home, build, MEMBER, fetch, progress, unpack, use_it=False)


def remove(home: Path) -> None:
    """Every installed shadPS4 build goes; shadPS4's own folder (saves, system modules, settings) stays."""
    shutil.rmtree(home, ignore_errors=True)


def newer_release(fetch: Fetch | None = None) -> ReleaseInfo | None:
    """shadPS4's newest stable release when it is newer than the one this app brings; None when it is not, or when
    GitHub cannot be asked (nothing to say then)."""
    latest = latest_release(REPO, fetch=fetch, user_agent=f"{APP_ID}/{__version__}")
    if latest.error or version_tuple(latest.version) <= version_tuple(VERSION):
        return None
    return latest
