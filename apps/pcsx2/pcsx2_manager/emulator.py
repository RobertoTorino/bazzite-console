# SPDX-License-Identifier: GPL-3.0-or-later
"""The PCSX2 this version of the app pins: the Linux AppImage of one stable GitHub release, checked against its
SHA-256. A newer stable comes with a new version of the app; the app reports when one is available. Another build,
a stable release or a nightly, is downloaded beside it in the version manager (owner, 20-11-2026: as shadPS4's own
launcher; core's builds), checked against the SHA-256 GitHub publishes; it was not tried on the board.

Each build goes to ~/.local/share/ps5-pcsx2-manager/emulator/<version>/pcsx2.AppImage, with "current" pointing to
the one in use and the build's size in its build.json (.size before it), so replaced() knows the expected size. The
run wrapper (~/.local/bin/ps5-pcsx2-run) starts "current", so the Steam shortcuts keep working when the version
changes. Installing a build also takes PCSX2's catalog out of its AppImage, beside it (catalogue.py). PCSX2's own
window offers its updates when it opens, and replaces the AppImage with another build when asked to; the app then
says so (replaced()), and Install puts the pinned release back."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from bazzite_console_core import builds
from bazzite_console_core.builds import Build
from bazzite_console_core.platform import data_home
from bazzite_console_core.updates import Fetch, ReleaseInfo, github_fetch, latest_release, version_tuple

from . import APP_ID, __version__, catalogue

VERSION = "2.8.2"
TAG = f"v{VERSION}"
ASSET = f"pcsx2-{TAG}-linux-appimage-x64-Qt.AppImage"
SHA256 = "0c46bb6a88aa2782b10853a7b07cf3387ba99cbef2b966372cd2315b8571abea"
SIZE = 60119544                         # bytes: how the app tells that PCSX2 replaced itself with another build
SIZE_MB = round(SIZE / (1 << 20))       # for the question before downloading
MEMBER = "pcsx2.AppImage"               # the name it is installed under, the same for every version
REPO = "PCSX2/pcsx2"
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
    """The installed PCSX2 version ("2.8.2"), "" when none is."""
    current = home / "current"
    if not (current / MEMBER).is_file():
        return ""
    return current.resolve().name


def replaced(home: Path) -> bool:
    """Whether the AppImage in use is no longer the build installed: PCSX2 updated itself in its own window (it
    writes the new build over the AppImage it runs from). The expected size is in the build's build.json (core's
    builds); for an install from before it, the .size written then, else the pinned release's."""
    try:
        fallback: int | None = int((home / "current" / ".size").read_text())
    except (OSError, ValueError):
        fallback = SIZE if installed_version(home) == VERSION else None
    return builds.replaced(home, MEMBER, fallback)


def take_catalogue(home: Path) -> bool:
    """PCSX2's catalog (game titles, patches) out of the installed AppImage, beside it (catalogue.py); whether it
    is there afterwards. Without it the app goes on with the files' names."""
    image = appimage(home)
    try:
        catalogue.extract(image)
    except (OSError, subprocess.SubprocessError):
        pass
    return not catalogue.missing(image.parent)


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


def tested() -> Build:
    """The build this version of the app was tried with."""
    return Build(VERSION, TAG, "2026-09-04", builds.RELEASE, URL, ASSET, SHA256, SIZE, RELEASE_PAGE)


def install(home: Path, fetch: Download = download, progress: Progress | None = None) -> str:
    """Puts the pinned build in use: from its folder when it is there unchanged, else downloaded and checked. Other
    builds stay. Returns what was done. Nothing changes when a step fails (EmulatorError)."""
    image = home / VERSION / MEMBER
    try:
        if image.is_file() and sha256(image) == SHA256:
            builds.remember(home, VERSION, tested(), MEMBER)
            builds.use(home, VERSION, MEMBER)
            return f"PCSX2 {VERSION} is in use."
        builds.install(home, tested(), MEMBER, fetch, progress, refused="pinned by this app")
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    take_catalogue(home)
    return f"PCSX2 {VERSION} is installed."


_ASSET = re.compile(r"pcsx2-v(.+)-linux-appimage-x64-Qt\.AppImage")


def _pick(release: dict, asset: dict) -> str | None:
    match = _ASSET.fullmatch(str(asset.get("name", "")))
    return match.group(1) if match else None


def available(fetch: Fetch | None = None) -> list[Build]:
    """The PCSX2 builds that can be downloaded, newest first: the nightlies on the first page of GitHub's list and
    the newest stable release, which the nightlies push off that page (builds.BuildError when GitHub cannot be
    asked)."""
    fetch = fetch or github_fetch(f"{APP_ID}/{__version__}")
    stable = builds.github_latest(REPO, _pick, fetch)
    return builds.merged([stable] if stable is not None else [], builds.github_builds(REPO, _pick, fetch))


def install_build(home: Path, build: Build, fetch: Download = download, progress: Progress | None = None) -> None:
    """Downloads *build* beside the others, checked against its SHA-256; not in use yet."""
    builds.install(home, build, MEMBER, fetch, progress, use_it=False)
    try:
        catalogue.extract(home / build.folder / MEMBER)         # its own catalog, beside it
    except (OSError, subprocess.SubprocessError):
        pass


def remove(home: Path) -> None:
    """Every installed PCSX2 build goes; PCSX2's own folder (BIOS, memory cards, saves, settings) stays."""
    shutil.rmtree(home, ignore_errors=True)


def newer_release(fetch: Fetch | None = None) -> ReleaseInfo | None:
    """PCSX2's newest stable release when it is newer than the one this app brings; None when it is not, or when
    GitHub cannot be asked (nothing to say then). GitHub's "latest" is the newest release not marked as a
    pre-release, which leaves PCSX2's nightlies out."""
    latest = latest_release(REPO, fetch=fetch, user_agent=f"{APP_ID}/{__version__}")
    if latest.error or version_tuple(latest.version) <= version_tuple(VERSION):
        return None
    return latest
