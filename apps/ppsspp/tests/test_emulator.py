# SPDX-License-Identifier: GPL-3.0-or-later
"""Installing the pinned PPSSPP release (emulator.py) from a file made here instead of the download: checked against
its SHA-256 first, "current" switched, other versions kept beside it, nothing changed when a step fails, and PPSSPP's two-
or three-number release tags read right."""

from __future__ import annotations

import hashlib
import urllib.error
from pathlib import Path

import pytest

from ppsspp_manager import emulator

APPIMAGE = b"#!/bin/sh\necho PPSSPP\n"


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
    assert emulator.URL == ("https://github.com/hrydgard/ppsspp/releases/download/v1.20.4/"
                            "PPSSPP-v1.20.4-anylinux-x86_64.AppImage")
    assert emulator.VERSION == "1.20.4" and len(emulator.SHA256) == 64
    assert emulator.RELEASE_PAGE == "https://github.com/hrydgard/ppsspp/releases/tag/v1.20.4"
    assert emulator.SIZE_MB == 48


def test_install_and_remove(tmp_path, pinned):
    home = tmp_path / "emulator"
    assert emulator.installed_version(home) == ""
    calls = []
    assert emulator.install(home, _fetch(pinned, calls)) == f"PPSSPP {emulator.VERSION} is installed."
    assert calls == [emulator.URL]
    image = emulator.appimage(home)
    assert image.read_bytes() == APPIMAGE and image.stat().st_mode & 0o777 == 0o755
    assert image.name == "ppsspp.AppImage"                                       # the same name for every version
    assert (home / "current").is_symlink() and emulator.installed_version(home) == emulator.VERSION
    assert sorted(p.name for p in home.iterdir()) == ["1.20.4", "current"]       # no download left behind
    emulator.remove(home)
    assert not home.exists() and emulator.installed_version(home) == ""


def test_an_older_version_stays_beside_it(tmp_path, pinned):
    home = tmp_path / "emulator"
    (home / "1.19.3").mkdir(parents=True)
    (home / "1.19.3" / emulator.MEMBER).write_text("old")
    (home / "current").symlink_to("1.19.3")
    assert emulator.installed_version(home) == "1.19.3"
    emulator.install(home, _fetch(pinned))
    assert emulator.installed_version(home) == emulator.VERSION
    assert (home / "1.19.3" / emulator.MEMBER).read_text() == "old"           # one click away


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


def _releases(tag: str):
    """GitHub's answer for PPSSPP's /releases/latest."""
    def fetch(url: str):
        assert url == "https://api.github.com/repos/hrydgard/ppsspp/releases/latest"
        return {"tag_name": tag, "html_url": f"https://github.com/hrydgard/ppsspp/releases/tag/{tag}",
                "published_at": "2026-11-30T22:00:00Z", "assets": []}
    return fetch


def test_ppsspp_tags_with_two_or_three_numbers():
    assert emulator.version_tuple("v1.20.4") == (1, 20, 4)
    assert emulator.version_tuple("v1.21") == (1, 21, 0)                        # the first release of a series
    assert emulator.version_tuple("nothing") == ()


def test_a_newer_ppsspp_release():
    newer = emulator.newer_release(_releases("v1.21"))
    assert (newer.version, newer.tag, newer.published) == ("1.21.0", "v1.21", "2026-11-30")
    assert newer.url.endswith("/v1.21")
    assert emulator.newer_release(_releases("v1.20.5")).version == "1.20.5"
    assert emulator.newer_release(_releases("v1.20.4")) is None                 # the one the app brings
    assert emulator.newer_release(_releases("v1.19.3")) is None
    assert emulator.newer_release(_releases("not a version")) is None

    def offline(url: str):
        raise urllib.error.URLError("no network")
    assert emulator.newer_release(offline) is None                              # nothing to say then


def test_the_releases_on_github():
    """The version manager's list: the x86_64 AppImage of each release, with GitHub's SHA-256; a release without one
    (an older one, named otherwise) is left out."""
    def release(tag: str, assets: list[str]) -> dict:
        return {"tag_name": tag, "name": tag, "published_at": "2026-03-15T10:00:00Z",
                "assets": [{"name": name, "digest": "sha256:" + "ab" * 32, "size": 50000000,
                            "browser_download_url": f"https://github.com/hrydgard/ppsspp/releases/download/{tag}/{name}"}
                           for name in assets]}

    def fetch(url: str):
        assert url == "https://api.github.com/repos/hrydgard/ppsspp/releases?per_page=30"
        return [release("v1.20.3", ["PPSSPP-v1.20.3-anylinux-aarch64.AppImage",
                                    "PPSSPP-v1.20.3-anylinux-x86_64.AppImage.zsync",
                                    "PPSSPP-v1.20.3-anylinux-x86_64.AppImage"]),
                release("v1.20", ["PPSSPP-v1.20-anylinux-x86_64.AppImage"]),
                release("v1.17", ["PPSSPP-v1.17-x86_64.AppImage"])]
    found = emulator.available(fetch)
    assert [b.version for b in found] == ["1.20.3", "1.20"]
    assert found[0].asset == "PPSSPP-v1.20.3-anylinux-x86_64.AppImage" and found[0].sha256 == "ab" * 32
