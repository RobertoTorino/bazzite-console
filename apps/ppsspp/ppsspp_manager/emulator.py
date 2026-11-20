# SPDX-License-Identifier: GPL-3.0-or-later
"""The PPSSPP release this version of the app pins: the Linux AppImage of a tagged GitHub release, checked against
its SHA-256 before it is installed. A newer PPSSPP comes with a new version of the app. The app reports when a newer
release is available. Another release is downloaded beside it in the version manager (owner, 20-11-2026: as
shadPS4's own launcher; core's builds), checked against the SHA-256 GitHub publishes; it was not tried on the board.

Each release goes to ~/.local/share/ps5-ppsspp-manager/emulator/<version>/ppsspp.AppImage, with "current" pointing
to the one in use.
The run wrapper (~/.local/bin/ps5-ppsspp-run) starts "current", so the Steam shortcuts keep working when the
version changes. PPSSPP does not update itself on Linux: its own window only says when a new release is out."""

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
from bazzite_console_core.updates import Fetch, ReleaseInfo, github_fetch

from . import APP_ID, __version__

VERSION = "1.20.4"
TAG = f"v{VERSION}"
ASSET = f"PPSSPP-{TAG}-anylinux-x86_64.AppImage"
SHA256 = "661c098e6b7f7610171a57b7c533ce8bba6f2312b71e76d61e850461973eba21"
SIZE = 50689748                         # bytes of the AppImage
SIZE_MB = round(SIZE / (1 << 20))       # for the question before downloading
MEMBER = "ppsspp.AppImage"              # the name it is installed under, the same for every version
REPO = "hrydgard/ppsspp"
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
    """The installed PPSSPP version ("1.20.4"), "" when none is."""
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
    return Build(VERSION, TAG, "2026-05-16", builds.RELEASE, URL, ASSET, SHA256, SIZE, RELEASE_PAGE)


def install(home: Path, fetch: Download = download, progress: Progress | None = None) -> str:
    """Puts the pinned build in use: from its folder when it is there unchanged, else downloaded and checked. Other
    builds stay. Returns what was done. Nothing changes when a step fails (EmulatorError)."""
    image = home / VERSION / MEMBER
    try:
        if image.is_file() and sha256(image) == SHA256:
            builds.remember(home, VERSION, tested(), MEMBER)
            builds.use(home, VERSION, MEMBER)
            return f"PPSSPP {VERSION} is in use."
        builds.install(home, tested(), MEMBER, fetch, progress, refused="pinned by this app")
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    return f"PPSSPP {VERSION} is installed."


_ASSET = re.compile(r"PPSSPP-v(.+)-anylinux-x86_64\.AppImage")


def _pick(release: dict, asset: dict) -> str | None:
    match = _ASSET.fullmatch(str(asset.get("name", "")))
    return match.group(1) if match else None


def available(fetch: Fetch | None = None) -> list[Build]:
    """The PPSSPP releases that can be downloaded, newest first: those with an x86_64 AppImage (builds.BuildError
    when GitHub cannot be asked)."""
    return builds.github_builds(REPO, _pick, fetch or github_fetch(f"{APP_ID}/{__version__}"))


def install_build(home: Path, build: Build, fetch: Download = download, progress: Progress | None = None) -> None:
    """Downloads *build* beside the others, checked against its SHA-256; not in use yet."""
    builds.install(home, build, MEMBER, fetch, progress, use_it=False)


def remove(home: Path) -> None:
    """Every installed PPSSPP build goes; PPSSPP's own folder (saves, settings, memory stick games) stays."""
    shutil.rmtree(home, ignore_errors=True)


# PPSSPP numbers the first release of a series 1.20 and its fixes 1.20.4: two or three numbers (core's
# version_tuple wants three, so the app reads the tag itself).
_VERSION = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def version_tuple(version: str) -> tuple[int, ...]:
    match = _VERSION.search(version or "")
    return tuple(int(part or 0) for part in match.groups()) if match else ()


def newer_release(fetch: Fetch | None = None) -> ReleaseInfo | None:
    """PPSSPP's newest release when it is newer than the one this app brings; None when it is not, or when GitHub
    cannot be asked (nothing to say then)."""
    fetch = fetch or github_fetch(f"{APP_ID}/{__version__}")
    try:
        data = fetch(f"https://api.github.com/repos/{REPO}/releases/latest")
        tag = str(data.get("tag_name", ""))
        url = str(data.get("html_url", "")) or f"https://github.com/{REPO}/releases"
        published = str(data.get("published_at", ""))[:10]
    except (urllib.error.URLError, OSError, ValueError, AttributeError):
        return None
    found = version_tuple(tag)
    if not found or found <= version_tuple(VERSION):
        return None
    return ReleaseInfo(".".join(map(str, found)), tag, url, published)


def running(proc: Path = Path("/proc")) -> bool:
    """Whether the installed PPSSPP runs: the AppImage's own process, named after the file (comm holds the first 15
    characters: "ppsspp.AppImage"), stays while the program it unpacked runs. A finished one not collected yet (a zombie)
    does not count. PPSSPP writes its settings back when it closes, so nothing in them is written while it runs."""
    for folder in proc.glob("[0-9]*"):
        try:
            if (folder / "comm").read_text().strip() != MEMBER[:15]:
                continue
            state = (folder / "stat").read_text().rsplit(")", 1)[1].split()[0]
        except (OSError, IndexError):
            continue
        if state not in ("Z", "X"):
            return True
    return False
