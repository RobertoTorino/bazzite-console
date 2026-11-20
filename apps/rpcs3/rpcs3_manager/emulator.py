# SPDX-License-Identifier: GPL-3.0-or-later
"""The RPCS3 build this version of the app pins: the Linux AppImage of one build on GitHub, checked against its
SHA-256 before it is installed. RPCS3 has no stable releases: it publishes a build for every change
(RPCS3/rpcs3-binaries-linux, one release "build-<commit>" each) and now and then tags a version as a landmark
(v0.0.43). The app pins a landmark build and tells the user when a newer one is available. RPCS3's newest build is
downloaded beside it in the version manager (owner, 20-11-2026: as shadPS4's own launcher; core's builds), checked
against the SHA-256 GitHub publishes; it was not tried on the board.

Each build goes to ~/.local/share/ps5-rpcs3-manager/emulator/<version>/rpcs3.AppImage, with "current" pointing to
the one in use. The
run wrapper (~/.local/bin/ps5-rpcs3-run) starts "current", so the Steam shortcuts keep working when the version
changes. RPCS3's own window offers its newest build when it opens, and replaces the AppImage with it when asked to;
the app then says so (replaced()), and Install puts the pinned build back."""

from __future__ import annotations

import hashlib
import re
import shutil
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from bazzite_console_core import builds
from bazzite_console_core.builds import Build
from bazzite_console_core.platform import data_home
from bazzite_console_core.updates import Fetch, ReleaseInfo, github_fetch, latest_release, version_tuple

from . import APP_ID, __version__

LANDMARK = "0.0.43"                     # the tagged version (v0.0.43) the build is of
BUILD = 20395                           # RPCS3's build number, counted over its whole history (24-10-2026: the
#                                         first pin after 19-10-2026, when RPCS3 began to re-attach a controller
#                                         that reconnects with a new device path; owner)
VERSION = f"{LANDMARK}-{BUILD}"         # as RPCS3 names its builds; also the folder it is installed in
COMMIT = "46b7fb670b280d08036c7670270b713daef912c2"
ASSET = f"rpcs3-v{VERSION}-{COMMIT[:8]}_linux64.AppImage"
SHA256 = "9df18bd0af25e94c5a03936b04b3e5a332a5c22e6fa61e6ab93376b027817a5c"
SIZE = 83180532                         # bytes: how the app tells that RPCS3 replaced it with another build
SIZE_MB = round(SIZE / (1 << 20))       # for the question before downloading
MEMBER = "rpcs3.AppImage"               # the name it is installed under, the same for every version
REPO = "RPCS3/rpcs3"
BUILDS = "RPCS3/rpcs3-binaries-linux"
URL = f"https://github.com/{BUILDS}/releases/download/build-{COMMIT}/{ASSET}"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/tag/v{LANDMARK}"
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
    """The installed RPCS3 build ("0.0.43-20133"), "" when none is."""
    current = home / "current"
    if not (current / MEMBER).is_file():
        return ""
    return current.resolve().name


def replaced(home: Path) -> bool:
    """Whether the AppImage in use is no longer the build installed: RPCS3 updated itself in its own window (it
    writes the new build over the AppImage it runs from). The pinned build's size for one installed before the size
    was kept."""
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
    return Build(VERSION, VERSION, "2026-10-24", builds.RELEASE, URL, ASSET, SHA256, SIZE, RELEASE_PAGE)


def install(home: Path, fetch: Download = download, progress: Progress | None = None) -> str:
    """Puts the pinned build in use: from its folder when it is there unchanged, else downloaded and checked. Other
    builds stay. Returns what was done. Nothing changes when a step fails (EmulatorError)."""
    image = home / VERSION / MEMBER
    try:
        if image.is_file() and sha256(image) == SHA256:
            builds.remember(home, VERSION, tested(), MEMBER)
            builds.use(home, VERSION, MEMBER)
            return f"RPCS3 {VERSION} is in use."
        builds.install(home, tested(), MEMBER, fetch, progress, refused="pinned by this app")
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    return f"RPCS3 {VERSION} is installed."


_ASSET = re.compile(r"rpcs3-v(.+)-[0-9a-f]{8}_linux64\.AppImage")


def _pick(release: dict, asset: dict) -> str | None:
    match = _ASSET.fullmatch(str(asset.get("name", "")))
    return match.group(1) if match else None


def available(fetch: Fetch | None = None) -> list[Build]:
    """RPCS3's newest build, the one that can be downloaded beside the pinned one (builds.BuildError when GitHub
    cannot be asked). Only the newest: RPCS3/rpcs3-binaries-linux holds a release for each of its thousands of
    builds, and GitHub lists them by their tag, not by date."""
    latest = builds.github_latest(BUILDS, _pick, fetch or github_fetch(f"{APP_ID}/{__version__}"))
    return [latest] if latest is not None else []


def install_build(home: Path, build: Build, fetch: Download = download, progress: Progress | None = None) -> None:
    """Downloads *build* beside the others, checked against its SHA-256; not in use yet."""
    builds.install(home, build, MEMBER, fetch, progress, use_it=False)


def remove(home: Path) -> None:
    """Every installed RPCS3 build goes; RPCS3's own folder (firmware, saves, settings, installed games) stays."""
    shutil.rmtree(home, ignore_errors=True)


def newer_release(fetch: Fetch | None = None) -> ReleaseInfo | None:
    """RPCS3's newest landmark when it is newer than the one this app brings; None when it is not, or when GitHub
    cannot be asked (nothing to say then)."""
    latest = latest_release(REPO, fetch=fetch, user_agent=f"{APP_ID}/{__version__}")
    if latest.error or version_tuple(latest.version) <= version_tuple(LANDMARK):
        return None
    return latest
