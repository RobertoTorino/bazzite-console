# SPDX-License-Identifier: GPL-3.0-or-later
"""Installing the pinned Xenia build (emulator.py) from a file made here instead of the download: checked against
its SHA-256 first, "current" switched, other builds kept beside it, nothing changed when a step fails, and a newer build
found on GitHub by when it was published."""

from __future__ import annotations

import hashlib
import urllib.error
from pathlib import Path

import pytest

from xenia_manager import emulator

APPIMAGE = b"#!/bin/sh\necho Xenia\n"


def _fetch(payload: bytes, calls: list | None = None):
    def fetch(url: str, dest: Path, progress=None) -> None:
        if calls is not None:
            calls.append(url)
        dest.write_bytes(payload)
    return fetch


@pytest.fixture
def pinned(monkeypatch):
    """The file the tests use, pinned as the release."""
    monkeypatch.setattr(emulator, "SHA256", hashlib.sha256(APPIMAGE).hexdigest())
    return APPIMAGE


def test_the_pin_points_at_the_release():
    assert emulator.URL == ("https://github.com/xenia-canary/xenia-canary/releases/download/54386cb/"
                            "xenia_canary_linux.AppImage")
    assert emulator.VERSION == "54386cb" and emulator.COMMIT.startswith("54386cb") and len(emulator.SHA256) == 64
    assert emulator.RELEASE_PAGE == "https://github.com/xenia-canary/xenia-canary/releases/tag/54386cb"
    assert emulator.SIZE_MB == 16


def test_install_and_remove(tmp_path, pinned):
    home = tmp_path / "emulator"
    assert emulator.installed_version(home) == ""
    calls = []
    assert emulator.install(home, _fetch(pinned, calls)) == f"Xenia {emulator.VERSION} is installed."
    assert calls == [emulator.URL]
    image = emulator.appimage(home)
    assert image.read_bytes() == APPIMAGE and image.stat().st_mode & 0o777 == 0o755
    assert image.name == "xenia.AppImage"                                        # the same name for every build
    assert (home / "current").is_symlink() and emulator.installed_version(home) == emulator.VERSION
    assert sorted(p.name for p in home.iterdir()) == ["54386cb", "current"]       # no download left behind
    emulator.remove(home)
    assert not home.exists() and emulator.installed_version(home) == ""


def test_an_older_version_stays_beside_it(tmp_path, pinned):
    home = tmp_path / "emulator"
    (home / "f42147a").mkdir(parents=True)
    (home / "f42147a" / emulator.MEMBER).write_text("old")
    (home / "current").symlink_to("f42147a")
    assert emulator.installed_version(home) == "f42147a"
    emulator.install(home, _fetch(pinned))
    assert emulator.installed_version(home) == emulator.VERSION
    assert (home / "f42147a" / emulator.MEMBER).read_text() == "old"           # one click away


def test_a_different_file_is_refused(tmp_path, pinned):
    home = tmp_path / "emulator"
    with pytest.raises(emulator.EmulatorError, match="SHA-256 differs"):
        emulator.install(home, _fetch(b"something else"))
    assert emulator.installed_version(home) == "" and not list(home.iterdir())


def test_a_failed_install_keeps_the_installed_one(tmp_path, pinned):
    home = tmp_path / "emulator"
    emulator.install(home, _fetch(pinned))
    emulator.appimage(home).write_bytes(b"changed")                             # so Install downloads it again
    with pytest.raises(emulator.EmulatorError):
        emulator.install(home, _fetch(b"broken"))
    assert emulator.installed_version(home) == emulator.VERSION and emulator.appimage(home).read_bytes() == b"changed"


def test_the_pinned_build_back_in_use_without_a_download(tmp_path, pinned):
    home = tmp_path / "emulator"
    emulator.install(home, _fetch(pinned))
    (home / "other").mkdir()
    (home / "other" / emulator.MEMBER).write_text("another build")
    (home / "current").unlink()
    (home / "current").symlink_to("other")
    calls = []
    assert emulator.install(home, _fetch(pinned, calls)).endswith(" is in use.")
    assert calls == [] and emulator.installed_version(home) == emulator.VERSION


def test_download_errors_say_what_happened(tmp_path):
    def http(url, dest, progress=None):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    def offline(url, dest, progress=None):
        raise urllib.error.URLError("Name or service not known")
    with pytest.raises(emulator.EmulatorError, match="GitHub answered 404"):
        emulator.install(tmp_path, http)
    with pytest.raises(emulator.EmulatorError, match="download failed: Name or service not known"):
        emulator.install(tmp_path, offline)


def _releases(tag: str, published: str = "2026-11-30T22:00:00Z"):
    """GitHub's answer for Xenia Canary's /releases/latest."""
    def fetch(url: str):
        assert url == "https://api.github.com/repos/xenia-canary/xenia-canary/releases/latest"
        return {"tag_name": tag, "html_url": f"https://github.com/xenia-canary/xenia-canary/releases/tag/{tag}",
                "published_at": published, "assets": []}
    return fetch


def test_a_newer_xenia():
    newer = emulator.newer_release(_releases("0a1b2c3"))
    assert (newer.version, newer.published) == ("0a1b2c3", "2026-11-30") and newer.url.endswith("/0a1b2c3")
    assert emulator.newer_release(_releases("54386cb", emulator.PUBLISHED)) is None  # the one the app brings
    assert emulator.newer_release(_releases("f42147a", "2026-10-20T09:40:37Z")) is None   # an older build
    assert emulator.newer_release(lambda url: ["not a release"]) is None

    def offline(url: str):
        raise urllib.error.URLError("no network")
    assert emulator.newer_release(offline) is None                                 # nothing to say then


def test_xenia_running_sees_the_appimages_process(tmp_path):
    proc = tmp_path / "proc"
    for pid, comm, state in (("10", "steam", "S"), ("11", "xenia.AppImage", "Z")):
        (proc / pid).mkdir(parents=True)
        (proc / pid / "comm").write_text(comm + "\n")
        (proc / pid / "stat").write_text(f"{pid} ({comm}) {state} 1 1 1\n")
    assert not emulator.running(proc)                                                # a zombie does not count
    (proc / "11" / "stat").write_text("11 (xenia.AppImage) S 1 1 1\n")
    assert emulator.running(proc)
    assert not emulator.running(Path("/nonexistent"))


def test_the_builds_on_github():
    """The version manager's list: the Linux AppImage of each Canary build, with GitHub's SHA-256."""
    def release(tag: str, digest: str = "sha256:" + "ab" * 32) -> dict:
        return {"tag_name": tag, "name": f"{tag}_canary_experimental", "published_at": "2026-11-18T10:00:00Z",
                "assets": [{"name": "xenia_canary_windows.zip", "digest": "sha256:" + "cd" * 32},
                           {"name": "xenia_canary_linux.AppImage", "digest": digest, "size": 16546296,
                            "browser_download_url": f"https://github.com/xenia-canary/xenia-canary/releases/download/"
                                                    f"{tag}/xenia_canary_linux.AppImage"}]}

    def fetch(url: str):
        assert url == "https://api.github.com/repos/xenia-canary/xenia-canary/releases?per_page=30"
        return [release("79aee12"), release("f9431eb", digest="")]
    found = emulator.available(fetch)
    assert [(b.version, b.name, b.published) for b in found] == [("79aee12", "79aee12_canary_experimental",
                                                                    "2026-11-18")]
    assert found[0].url.endswith("/download/79aee12/xenia_canary_linux.AppImage") and found[0].sha256 == "ab" * 32
    assert emulator.tested().version == emulator.BUILD and emulator.tested().sha256 == emulator.SHA256
