# SPDX-License-Identifier: GPL-3.0-or-later
"""Several builds of an emulator side by side, one of them in use (owner, 20-11-2026: the version manager of
shadPS4's own launcher, for every emulator manager). The build a manager was tried with is one of them; any other
build its upstream publishes on GitHub can be downloaded beside it, and one click switches back.

The builds sit in the manager's emulator folder, one folder each, named after the build ("4377", "0.21.0"), with the
emulator's file under one name in all of them (the member, "vita3k.AppImage") and what is known about the build
beside it (build.json). "current" points to the one in use: the run wrapper starts it, so the Steam shortcuts keep
working whichever build is in use. Switching changes only that link.

A download is checked against the SHA-256 GitHub publishes for the file (its digest; owner, 20-11-2026: GitHub is
enough), or the one the manager pins for the build it was tried with. A file without one is not offered. A build
added by hand (Add custom) has no check: it is the user's own file.

Nothing here touches Qt; the list from GitHub takes a fetch function, so it is tested without a network."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import urllib.error
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .updates import Fetch

INFO = "build.json"                     # what is known about a build, in its folder
CURRENT = "current"                     # the link to the build in use
RELEASE, PRERELEASE, CUSTOM = "Release", "Pre-release", "Custom"
TESTED = "Tested"                       # the kind shown for the build the manager was tried with
PER_PAGE = 30                           # releases asked from GitHub for the list
CUSTOM_PREFIX = "custom-"
CHUNK = 1 << 20
_FOLDER_RE = re.compile(r"[^A-Za-z0-9._-]+")

Progress = Callable[[int, int], None]                   # bytes so far, total (0 when unknown)
Download = Callable[[str, Path, Progress | None], None]
Unpack = Callable[[Path, Path], None]                   # the downloaded file, the member to write from it


class BuildError(Exception):
    pass


@dataclass
class Build:
    version: str                        # as the emulator names it; also its folder
    name: str = ""                      # the release's name or codename
    published: str = ""                 # YYYY-MM-DD
    kind: str = RELEASE                 # RELEASE, PRERELEASE or CUSTOM
    url: str = ""                       # the file to download
    asset: str = ""                     # its name
    sha256: str = ""                    # what the file must hash to
    size: int = 0                       # bytes of the download
    page: str = ""                      # the release's page
    member_size: int = 0                # bytes of the installed member: how a manager tells it was replaced

    @property
    def folder(self) -> str:
        return folder_name(self.version)


def folder_name(version: str) -> str:
    """A version as a folder name: no slashes, no spaces, never hidden."""
    name = _FOLDER_RE.sub("-", version).strip("-.")
    return name or "build"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _read_info(folder: Path) -> Build:
    try:
        data = json.loads((folder / INFO).read_text())
    except (OSError, ValueError):
        data = {}
    known = {f.name for f in fields(Build)}
    values = {k: v for k, v in data.items() if k in known} if isinstance(data, dict) else {}
    values["version"] = str(values.get("version") or folder.name)
    return Build(**values)


def _write_info(folder: Path, build: Build) -> None:
    (folder / INFO).write_text(json.dumps(asdict(build), indent=1) + "\n")


def current(home: Path, member: str) -> str:
    """The folder of the build in use, "" when none is."""
    link = home / CURRENT
    if not (link / member).is_file():
        return ""
    return link.resolve().name


def installed(home: Path, member: str) -> list[Build]:
    """The builds in *home*, newest first (by the date they were published, the folder's name next). A folder
    from before build.json was written is a build all the same, named after its folder."""
    try:
        folders = [f for f in home.iterdir()
                   if f.is_dir() and not f.is_symlink() and not f.name.startswith(".") and (f / member).is_file()]
    except OSError:
        return []
    builds = []
    for folder in folders:
        build = _read_info(folder)
        if build.version != folder.name and build.folder != folder.name:
            build.version = folder.name
        builds.append(build)
    return sorted(builds, key=lambda b: (b.published, b.version), reverse=True)


def info(home: Path, member: str) -> Build | None:
    """What is known about the build in use."""
    folder = current(home, member)
    return _read_info(home / folder) if folder else None


def use(home: Path, folder: str, member: str) -> None:
    """Puts the build in *folder* in use: "current" points to it (swapped in one step)."""
    if not (home / folder / member).is_file():
        raise BuildError(f"Build {folder} is not installed.")
    link = home / ".current-new"
    link.unlink(missing_ok=True)
    link.symlink_to(folder)
    link.replace(home / CURRENT)


def delete(home: Path, folder: str, member: str) -> None:
    """Deletes a build that is not in use."""
    if folder == current(home, member):
        raise BuildError(f"Build {folder} is in use: put another build in use first.")
    target = home / folder
    if not folder or folder.startswith(".") or folder == CURRENT or target.parent != home or not target.is_dir():
        raise BuildError(f"Build {folder} is not installed.")
    shutil.rmtree(target)


def _place(home: Path, build: Build, source: Path, member: str, use_it: bool) -> None:
    """*source* (the member, checked) into the build's folder, with its build.json; in use when *use_it*."""
    source.chmod(0o755)
    build.member_size = source.stat().st_size
    target = home / build.folder
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir()
    _write_info(target, build)
    source.replace(target / member)
    if use_it:
        use(home, build.folder, member)


def install(home: Path, build: Build, member: str, fetch: Download, progress: Progress | None = None,
            unpack: Unpack | None = None, use_it: bool = True, refused: str = "GitHub published") -> None:
    """Downloads *build*, checks it against its SHA-256 and puts it beside the others; in use when *use_it*. The
    downloaded file is the member itself, or *unpack* writes the member from it (a zip). Nothing changes when a
    step fails (BuildError). *refused* says whose file it should have been."""
    if not build.sha256:
        raise BuildError(f"{build.asset or build.version} has no SHA-256 to check it against; nothing was installed.")
    home.mkdir(parents=True, exist_ok=True)
    work = home / f".download-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    try:
        archive = work / (build.asset or member)
        try:
            fetch(build.url, archive, progress)
        except urllib.error.HTTPError as error:
            raise BuildError(f"GitHub answered {error.code} for {build.asset}.") from error
        except (urllib.error.URLError, OSError) as error:
            reason = str(getattr(error, "reason", error))
            raise BuildError(f"The download failed: {reason}.") from error
        if sha256(archive).lower() != build.sha256.lower():
            raise BuildError(f"{build.asset} is not the file {refused} (its SHA-256 differs); nothing was "
                             "installed.")
        image = work / f".{member}"
        if unpack is None:
            archive.replace(image)
        else:
            unpack(archive, image)
        _place(home, build, image, member, use_it)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def add_custom(home: Path, source: Path, member: str, name: str = "") -> Build:
    """The user's own file (an AppImage they built or downloaded) as a build beside the others, not in use yet.
    Its folder is "custom-" and the file's name; a second one with that name gets a number."""
    if not source.is_file():
        raise BuildError(f"{source} is not a file.")
    home.mkdir(parents=True, exist_ok=True)
    base = CUSTOM_PREFIX + folder_name(source.stem)
    version, number = base, 2
    while (home / version).exists():
        version, number = f"{base}-{number}", number + 1
    work = home / f".custom-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    try:
        copy = work / member
        shutil.copyfile(source, copy)
        build = Build(version, name or source.name, kind=CUSTOM, asset=source.name, sha256=sha256(copy),
                      size=copy.stat().st_size)
        _place(home, build, copy, member, use_it=False)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return build


def replaced(home: Path, member: str, fallback: int | None = None) -> bool:
    """Whether the member in use is no longer the file installed: the emulator wrote another build over itself.
    The size installed is in build.json; *fallback* for a build installed before that file was written (None: not
    known, so not replaced)."""
    try:
        size = (home / CURRENT / member).stat().st_size
    except OSError:
        return False
    expected = fallback
    if (home / CURRENT / INFO).is_file():
        build = _read_info(home / CURRENT)
        expected = build.member_size if build.member_size else fallback
    return expected is not None and size != expected


def remember(home: Path, folder: str, build: Build, member: str) -> None:
    """build.json for a build already in place (installed by an earlier version of the manager)."""
    image = home / folder / member
    if image.is_file() and not (home / folder / INFO).is_file():
        build.member_size = build.member_size or image.stat().st_size
        _write_info(home / folder, build)


def digest(asset: dict) -> str:
    """The SHA-256 GitHub publishes for a release's file ("sha256:…"), "" when it has none."""
    value = str(asset.get("digest") or "")
    return value.split(":", 1)[1] if value.startswith("sha256:") else ""


def github_builds(repo: str, pick: Callable[[dict, dict], str | None], fetch: Fetch,
                  per_page: int = PER_PAGE) -> list[Build]:
    """The builds on *repo*'s release list (GitHub's newest first, one page): for each release the file *pick*
    (release, asset) answers a version for, with GitHub's SHA-256. A release without such a file, or whose file
    has no SHA-256, is left out. Raises BuildError when GitHub cannot be asked."""
    try:
        data = fetch(f"https://api.github.com/repos/{repo}/releases?per_page={per_page}")
    except urllib.error.HTTPError as error:
        raise BuildError(f"GitHub answered {error.code}.") from error
    except (urllib.error.URLError, OSError, ValueError) as error:
        reason = str(getattr(error, "reason", error))
        raise BuildError(f"GitHub could not be asked: {reason}.") from error
    if not isinstance(data, list):
        raise BuildError("GitHub's answer was not a release list.")
    builds = []
    for release in data:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        for asset in release.get("assets") or []:
            version = pick(release, asset)
            checksum = digest(asset)
            if not version or not checksum:
                continue
            builds.append(Build(version, str(release.get("name") or release.get("tag_name") or ""),
                                str(release.get("published_at") or "")[:10],
                                PRERELEASE if release.get("prerelease") else RELEASE,
                                str(asset.get("browser_download_url") or ""), str(asset.get("name") or ""),
                                checksum, int(asset.get("size") or 0), str(release.get("html_url") or "")))
            break
    return builds


def github_latest(repo: str, pick: Callable[[dict, dict], str | None], fetch: Fetch) -> Build | None:
    """The build of *repo*'s latest release (GitHub's newest not marked as a pre-release), as github_builds reads
    one; None when it has no such file. For a list whose first page is all pre-releases (nightlies), or one GitHub
    does not keep in date order. Raises BuildError when GitHub cannot be asked."""
    try:
        data = fetch(f"https://api.github.com/repos/{repo}/releases/latest")
    except urllib.error.HTTPError as error:
        raise BuildError(f"GitHub answered {error.code}.") from error
    except (urllib.error.URLError, OSError, ValueError) as error:
        reason = str(getattr(error, "reason", error))
        raise BuildError(f"GitHub could not be asked: {reason}.") from error
    found = github_builds(repo, pick, lambda _url: [data]) if isinstance(data, dict) else []
    return found[0] if found else None


def merged(*lists: list[Build]) -> list[Build]:
    """Builds from several lists, each version once (the first list that has it wins), newest first."""
    seen: dict[str, Build] = {}
    for builds in lists:
        for build in builds:
            seen.setdefault(build.version, build)
    return sorted(seen.values(), key=lambda b: (b.published, b.version), reverse=True)
