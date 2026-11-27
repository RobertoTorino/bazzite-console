# SPDX-License-Identifier: GPL-3.0-or-later
"""The KytyPS5-Native this version of the app installs: the Linux build of a tagged release on GitHub (a .tar.gz
with the emulator, its launcher, its libraries and its GPU helper), pinned and checked against the SHA-256 this
version of the app was tried with. A newer release comes with a new version of the app, so the launch line and the
advice in the app are tried with the release they are for; the app says when there is a newer one.

The build goes to ~/.local/share/ps5-kytyps5/emulator/<version>/, the whole release in it, with "current"
pointing to the one in use (core's builds). The run wrapper (~/.local/bin/ps5-kytyps5-run) starts "current", so
the Steam shortcuts keep working when the version changes.

KytyPS5-Native keeps what it writes (saves, trophies, its shader cache) in the folder it is started from. The app
starts it from ~/.local/share/KytyPS5-Native/data, the folder the emulator's own run script uses, so nothing of
yours sits in a build's folder and Uninstall never takes it."""

from __future__ import annotations

import os
import shutil
import tarfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from bazzite_console_core import builds, processes
from bazzite_console_core.builds import Build
from bazzite_console_core.platform import data_home
from bazzite_console_core.updates import Fetch, ReleaseInfo, latest_release

from . import APP_ID, __version__

VERSION = "2026-11-27-8278d03"          # KytyPS5-Native names a release after its date and commit
TAG = f"KytyPS5-Native-{VERSION}"
ASSET = f"{TAG}-Linux-x86_64.tar.gz"
SHA256 = "3398587acb4641aecb30a8f704181736e7149f145a2d5a864f21f5333558ecd5"
SIZE_MB = 41                            # the archive, for the question before downloading
NAME = TAG                              # the release's name on GitHub
PUBLISHED = "2026-11-27"
MEMBER = "kyty_emulator"                # the emulator in a build's folder
LAUNCHER = "kyty_launcher"              # its own window, beside it
HELPER_INSTALL = "install-helper.sh"    # installs the GPU helper kyty-lodhw as a system service (root)
REPO = "superkeka/KytyPS5-Native"
URL = f"https://github.com/{REPO}/releases/download/{TAG}/{ASSET}"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/tag/{TAG}"
PROGRAMS = (MEMBER, LAUNCHER)           # what runs while the emulator runs, by the kernel's names
CHUNK = 1 << 20
TIMEOUT = 30

Progress = Callable[[int, int], None]                   # bytes so far, total (0 when unknown)
Download = Callable[[str, Path, Progress | None], None]


class EmulatorError(Exception):
    pass


def emulator_home() -> Path:
    return data_home() / APP_ID / "emulator"


def kyty_data() -> Path:
    """The folder KytyPS5-Native is started from, where it keeps its saves: its own, as its run script's."""
    return data_home() / "KytyPS5-Native" / "data"


def installed_version(home: Path) -> str:
    """The installed KytyPS5-Native version ("2026-11-27-8278d03"), "" when none is."""
    return builds.current(home, MEMBER)


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


def unpack(archive: Path, folder: Path) -> None:
    """The release's files into *folder*. A member that would land outside it, or is no plain file, folder or
    link inside it, is refused by tarfile's data filter."""
    try:
        with tarfile.open(archive, "r:gz") as packed:
            packed.extractall(folder, filter="data")
    except (tarfile.TarError, EOFError) as error:
        raise EmulatorError(f"{archive.name} could not be unpacked: {error}") from error
    if not (folder / MEMBER).is_file():
        raise EmulatorError(f"{archive.name} has no {MEMBER}.")


def tested() -> Build:
    """The release this version of the app was tried with."""
    return Build(VERSION, NAME, PUBLISHED, builds.RELEASE, URL, ASSET, SHA256, SIZE_MB << 20, RELEASE_PAGE)


def install(home: Path, fetch: Download = download, progress: Progress | None = None) -> str:
    """Puts the pinned release in use: from its folder when it is there, else downloaded, checked against the
    SHA-256 this app was tried with and unpacked. Returns what was done. Nothing changes when a step fails
    (EmulatorError)."""
    try:
        if (home / VERSION / MEMBER).is_file():
            builds.remember(home, VERSION, tested(), MEMBER)
            builds.use(home, VERSION, MEMBER)
            return f"KytyPS5-Native {VERSION} is in use."
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    home.mkdir(parents=True, exist_ok=True)
    work = home / f".download-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    try:
        archive = work / ASSET
        try:
            fetch(URL, archive, progress)
        except urllib.error.HTTPError as error:
            raise EmulatorError(f"GitHub answered {error.code} for {ASSET}.") from error
        except (urllib.error.URLError, OSError) as error:
            raise EmulatorError(f"The download failed: {getattr(error, 'reason', error)}.") from error
        if builds.sha256(archive).lower() != SHA256:
            raise EmulatorError(f"{ASSET} is not the file this app was tested with (its SHA-256 differs); nothing "
                                "was installed.")
        tree = work / "tree"
        tree.mkdir()
        unpack(archive, tree)
        shutil.rmtree(home / VERSION, ignore_errors=True)
        tree.replace(home / VERSION)
        builds.remember(home, VERSION, tested(), MEMBER)
        builds.use(home, VERSION, MEMBER)
    except builds.BuildError as error:
        raise EmulatorError(str(error)) from error
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return f"KytyPS5-Native {VERSION} is installed."


def remove(home: Path) -> None:
    """The installed KytyPS5-Native goes; its own folders (saves, settings) stay."""
    shutil.rmtree(home, ignore_errors=True)


def newer_release(fetch: Fetch | None = None) -> ReleaseInfo | None:
    """KytyPS5-Native's newest release when it is another one than this app brings and published later; None when
    it is not, or when GitHub cannot be asked (nothing to say then)."""
    latest = latest_release(REPO, fetch=fetch, user_agent=f"{APP_ID}/{__version__}")
    if latest.error or not latest.version or VERSION in latest.version:
        return None
    return latest if (latest.published or "")[:10] > PUBLISHED else None


def is_kyty(comm: str, _folder: Path) -> bool:
    """Whether a process is KytyPS5-Native: the emulator or its own window."""
    return comm in PROGRAMS


def running(proc: Path = Path("/proc")) -> bool:
    """Whether KytyPS5-Native runs."""
    return bool(processes.find(is_kyty, proc))


def end(proc: Path = Path("/proc")) -> list[int]:
    """Ends KytyPS5-Native at once, with everything it started (Exit KytyPS5); the processes it was sent to."""
    return processes.end(processes.find(is_kyty, proc), proc)
