# SPDX-License-Identifier: GPL-3.0-or-later
"""The Vita3K build this version of the app pins: the Linux AppImage of one GitHub build, checked against its
SHA-256 before it is installed. Vita3K has no stable releases: it publishes a build for every change, the newest
under the rolling "continuous" tag of Vita3K/Vita3K and each one kept in Vita3K/Vita3K-builds (a release per build,
tagged with its number, 4269). The app reports when a newer build is available. Another build is downloaded beside
it in the version manager (owner, 20-11-2026: as shadPS4's own launcher; core's builds), checked against the
SHA-256 GitHub publishes; it was not tried on the board.

Each build goes to ~/.local/share/ps5-vita3k-manager/emulator/<build>/vita3k.AppImage, with "current" pointing to
the one in use. The
run wrapper (~/.local/bin/ps5-vita3k-run) starts "current", so the Steam shortcuts keep working when the build
changes. The AppImage can update itself in place (its 10-self-updater.hook: it asks on its second start, then
writes the newest continuous build over itself); the run wrapper turns that off, and should it happen all the same
(the AppImage started some other way) the app sees it by the file's size (replaced()) and Install puts the pinned
build back. Vita3K's own window only says when a newer build is out, with a link."""

from __future__ import annotations

import hashlib
import shutil
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from bazzite_console_core import builds, processes
from bazzite_console_core.builds import Build
from bazzite_console_core.platform import data_home
from bazzite_console_core.updates import Fetch, ReleaseInfo, github_fetch

from . import APP_ID, __version__

BUILD = 4377                            # Vita3K's build number, counted over its whole history
VERSION = str(BUILD)                    # how the app names it; also the folder it is installed in
SEMVER = "0.2.1"                        # what it calls itself (Vita3K --version: v0.2.1 4377-685b80a6)
COMMIT = "685b80a6acc93b9014b702c753d3698ec5287b24"
ASSET = "Vita3K-x86_64.AppImage"        # the same name in every build's release
SHA256 = "de1ddd4b5ae61a0f4f92f153dc4fa9752239a7a48c7ffcee663c84e932a09db2"
SIZE = 89794395                         # bytes: how the app tells that the AppImage was replaced by another build
SIZE_MB = round(SIZE / (1 << 20))       # for the question before downloading
MEMBER = "vita3k.AppImage"              # the name it is installed under, the same for every build
REPO = "Vita3K/Vita3K"
BUILDS = "Vita3K/Vita3K-builds"
URL = f"https://github.com/{BUILDS}/releases/download/{VERSION}/{ASSET}"
RELEASE_PAGE = f"https://github.com/{BUILDS}/releases/tag/{VERSION}"
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
    """The installed Vita3K build ("4269"), "" when none is."""
    current = home / "current"
    if not (current / MEMBER).is_file():
        return ""
    return current.resolve().name


def replaced(home: Path) -> bool:
    """Whether the AppImage in use is no longer the build installed: it updated itself (it writes the new build
    over the AppImage it runs from). The pinned build's size for one installed before the size was kept."""
    return builds.replaced(home, MEMBER, SIZE if installed_version(home) == VERSION else None)


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
    return Build(VERSION, f"Build: {VERSION}", "2026-11-17", builds.RELEASE, URL, ASSET, SHA256, SIZE, RELEASE_PAGE)


def install(home: Path, fetch: Download = download, progress: Progress | None = None) -> str:
    """Puts the pinned build in use: from its folder when it is there unchanged, else downloaded and checked. Other
    builds stay. Returns what was done. Nothing changes when a step fails (EmulatorError)."""
    image = home / VERSION / MEMBER
    try:
        if image.is_file() and sha256(image) == SHA256:
            builds.remember(home, VERSION, tested(), MEMBER)
            builds.use(home, VERSION, MEMBER)
            return f"Vita3K build {VERSION} is in use."
        builds.install(home, tested(), MEMBER, fetch, progress, refused="pinned by this app")
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    return f"Vita3K build {VERSION} is installed."


def _pick(release: dict, asset: dict) -> str | None:
    tag = str(release.get("tag_name", "")).strip()
    return tag if tag.isdigit() and asset.get("name") == ASSET else None


def available(fetch: Fetch | None = None) -> list[Build]:
    """The builds on Vita3K/Vita3K-builds that can be downloaded, newest first (builds.BuildError when GitHub cannot
    be asked)."""
    return builds.github_builds(BUILDS, _pick, fetch or github_fetch(f"{APP_ID}/{__version__}"))


def install_build(home: Path, build: Build, fetch: Download = download, progress: Progress | None = None) -> None:
    """Downloads *build* beside the others, checked against its SHA-256; not in use yet."""
    builds.install(home, build, MEMBER, fetch, progress, use_it=False)


def remove(home: Path) -> None:
    """Every installed Vita3K build goes; Vita3K's own folders (firmware, games, saves, settings) stay."""
    shutil.rmtree(home, ignore_errors=True)


def newer_release(fetch: Fetch | None = None) -> ReleaseInfo | None:
    """Vita3K's newest build when it is newer than the one this app brings; None when it is not, or when GitHub
    cannot be asked (nothing to say then). The builds are tagged with their number alone, which core's
    latest_release does not read as a version, so the app reads the tag itself."""
    fetch = fetch or github_fetch(f"{APP_ID}/{__version__}")
    try:
        data = fetch(f"https://api.github.com/repos/{BUILDS}/releases/latest")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    tag = str(data.get("tag_name", "")).strip()
    if not tag.isdigit() or int(tag) <= BUILD:
        return None
    return ReleaseInfo(tag, tag, str(data.get("html_url") or f"https://github.com/{BUILDS}/releases/tag/{tag}"),
                       str(data.get("published_at", ""))[:10])


def is_vita3k(comm: str, _folder: Path) -> bool:
    """Whether a process is the installed Vita3K: the AppImage's own process, named after the file (comm holds the
    first 15 characters: "vita3k.AppImage"), stays while the program it unpacked runs."""
    return comm == MEMBER[:15]


def running(proc: Path = Path("/proc")) -> bool:
    """Whether the installed Vita3K runs. A finished one not collected yet (a zombie) does not count. Vita3K writes its settings back when it closes, so nothing in them is written while it runs."""
    return bool(processes.find(is_vita3k, proc))


def end(proc: Path = Path("/proc")) -> list[int]:
    """Ends Vita3K at once, with everything it started (Exit Vita3K); the processes it was sent to."""
    return processes.end(processes.find(is_vita3k, proc), proc)
