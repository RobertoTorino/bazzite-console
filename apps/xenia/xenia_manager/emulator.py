# SPDX-License-Identifier: GPL-3.0-or-later
"""The Xenia build this version of the app pins: the Linux AppImage of one Xenia Canary build on GitHub, checked
against its SHA-256 before it is installed. Xenia has no stable releases: Xenia Canary publishes a build for almost
every change, a release of xenia-canary/xenia-canary tagged with the commit it was built from (838850f), all of them
marked experimental, the Linux build more so than the Windows one. The app reports when a newer build is available.
A tag is a commit, not a number, so "newer" is the latest release published after the pinned one. Another build is
downloaded beside it in the version manager (owner, 20-11-2026: as shadPS4's own launcher; core's builds), checked
against the SHA-256 GitHub publishes; it was not tried on the board.

Each build goes to ~/.local/share/ps5-xenia-manager/emulator/<build>/xenia.AppImage, with "current" pointing to the
one in use. The
run wrapper (~/.local/bin/ps5-xenia-run) starts "current", so the Steam shortcuts keep working when the build
changes. The AppImage does not update itself (its AppRun is the program).

Xenia keeps its settings (CONFIG, xenia-canary.config.toml), saves and installed content in $XDG_DATA_HOME/Xenia,
~/.local/share/Xenia by default. running() says whether the installed Xenia runs (the app's Settings window leaves
its settings alone then; owner, 03-11-2026)."""

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

BUILD = "54386cb"                       # the build's tag: the commit it was built from
COMMIT = "54386cbbd36b1e5b9e3c8ea8616f4c7c8f0c56b6"
PUBLISHED = "2026-11-19T20:05:38Z"      # when GitHub published it: a later release is a newer build
VERSION = BUILD                         # how the app names it; also the folder it is installed in
ASSET = "xenia_canary_linux.AppImage"   # the same name in every build's release
SHA256 = "fbd24aa75b09b2d808526b70616c092e89d9c8655becbb2d3b561cf48835e4b6"
SIZE = 16546296                         # bytes of the AppImage
SIZE_MB = round(SIZE / (1 << 20))       # for the question before downloading
MEMBER = "xenia.AppImage"               # the name it is installed under, the same for every build
CONFIG = "xenia-canary.config.toml"     # Xenia's settings file, in xenia_home()
REPO = "xenia-canary/xenia-canary"
URL = f"https://github.com/{REPO}/releases/download/{BUILD}/{ASSET}"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/tag/{BUILD}"
CHUNK = 1 << 20
TIMEOUT = 30

Progress = Callable[[int, int], None]                   # bytes so far, total (0 when unknown)
Download = Callable[[str, Path, Progress | None], None]


class EmulatorError(Exception):
    pass


def emulator_home() -> Path:
    return data_home() / APP_ID / "emulator"


def xenia_home() -> Path:
    """Xenia's own folder: its settings, saves and installed content."""
    return data_home() / "Xenia"


def is_xenia(comm: str, _folder: Path) -> bool:
    """Whether a process is the installed Xenia: the AppImage's own process, named after the file (comm holds the
    first 15 characters: "xenia.AppImage")."""
    return comm == MEMBER[:15]


def running(proc: Path = Path("/proc")) -> bool:
    """Whether the installed Xenia runs. A finished one not collected yet (a zombie) does not count. Xenia writes its settings when it starts and keeps them while it runs, so nothing in them is written then."""
    return bool(processes.find(is_xenia, proc))


def end(proc: Path = Path("/proc")) -> list[int]:
    """Ends Xenia at once, with everything it started (Exit Xenia); the processes it was sent to."""
    return processes.end(processes.find(is_xenia, proc), proc)


def appimage(home: Path) -> Path:
    """The AppImage the run wrapper starts."""
    return home / "current" / MEMBER


def installed_version(home: Path) -> str:
    """The installed Xenia build ("838850f"), "" when none is."""
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


def tested() -> Build:
    """The build this version of the app was tried with."""
    return Build(VERSION, f"{BUILD}_canary_experimental", PUBLISHED[:10], builds.RELEASE, URL, ASSET, SHA256, SIZE,
                 RELEASE_PAGE)


def install(home: Path, fetch: Download = download, progress: Progress | None = None) -> str:
    """Puts the pinned build in use: from its folder when it is there unchanged, else downloaded and checked. Other
    builds stay. Returns what was done. Nothing changes when a step fails (EmulatorError)."""
    image = home / VERSION / MEMBER
    try:
        if image.is_file() and sha256(image) == SHA256:
            builds.remember(home, VERSION, tested(), MEMBER)
            builds.use(home, VERSION, MEMBER)
            return f"Xenia {BUILD} is in use."
        builds.install(home, tested(), MEMBER, fetch, progress, refused="pinned by this app")
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    return f"Xenia {BUILD} is installed."


def _pick(release: dict, asset: dict) -> str | None:
    tag = str(release.get("tag_name", "")).strip()
    return tag if tag and asset.get("name") == ASSET else None


def available(fetch: Fetch | None = None) -> list[Build]:
    """The Xenia Canary builds that can be downloaded, newest first (builds.BuildError when GitHub cannot be
    asked)."""
    return builds.github_builds(REPO, _pick, fetch or github_fetch(f"{APP_ID}/{__version__}"))


def install_build(home: Path, build: Build, fetch: Download = download, progress: Progress | None = None) -> None:
    """Downloads *build* beside the others, checked against its SHA-256; not in use yet."""
    builds.install(home, build, MEMBER, fetch, progress, use_it=False)


def remove(home: Path) -> None:
    """Every installed Xenia build goes; Xenia's own folder (settings, saves, installed content) stays."""
    shutil.rmtree(home, ignore_errors=True)


def newer_release(fetch: Fetch | None = None) -> ReleaseInfo | None:
    """Xenia's newest build when it was published after the one this app brings; None when it was not, or when
    GitHub cannot be asked (nothing to say then). The builds are tagged with a commit, which core's latest_release
    does not read as a version, so the app reads the release itself."""
    fetch = fetch or github_fetch(f"{APP_ID}/{__version__}")
    try:
        data = fetch(f"https://api.github.com/repos/{REPO}/releases/latest")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    tag = str(data.get("tag_name", "")).strip()
    published = str(data.get("published_at", ""))
    if not tag or tag == BUILD or published <= PUBLISHED:          # ISO 8601 in UTC: compared as text
        return None
    return ReleaseInfo(tag, tag, str(data.get("html_url") or f"https://github.com/{REPO}/releases/tag/{tag}"),
                       published[:10])
