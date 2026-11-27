# SPDX-License-Identifier: GPL-3.0-or-later
"""Installing the pinned KytyPS5-Native (emulator.py) from a release archive made here: the whole release in the
build's folder, the SHA-256 check, an archive that reaches outside its folder, and what a failed step leaves."""

from __future__ import annotations

import hashlib
import io
import tarfile
import urllib.error

import pytest

from bazzite_console_core import builds, processes
from bazzite_console_core.updates import ReleaseInfo
from kytyps5_manager import emulator


def archive(files: dict[str, str]) -> bytes:
    """A release as KytyPS5-Native packs it: a .tar.gz with its files under "./"."""
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as packed:
        for name, text in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(text), 0o755
            packed.addfile(info, io.BytesIO(text.encode()))
    return data.getvalue()


RELEASE = {"./kyty_emulator": "#!/bin/sh\n", "./kyty_launcher": "#!/bin/sh\n", "./install-helper.sh": "#!/bin/sh\n",
           "./lib/libQt6Core.so.6": "lib"}


def fetch_of(payload: bytes):
    return lambda url, dest, progress=None: dest.write_bytes(payload)


def test_install_puts_the_whole_release_in_use(tmp_path, monkeypatch):
    payload = archive(RELEASE)
    monkeypatch.setattr(emulator, "SHA256", hashlib.sha256(payload).hexdigest())
    home = tmp_path / "emulator"
    assert emulator.installed_version(home) == ""
    assert emulator.install(home, fetch_of(payload)) == f"KytyPS5-Native {emulator.VERSION} is installed."
    assert emulator.installed_version(home) == emulator.VERSION
    build = home / "current"
    assert all((build / name).is_file() for name in ("kyty_emulator", "kyty_launcher", "install-helper.sh",
                                                     "lib/libQt6Core.so.6"))
    assert (build / "kyty_emulator").stat().st_mode & 0o111
    assert builds.info(home, emulator.MEMBER).sha256 == emulator.SHA256
    assert not [p for p in home.iterdir() if p.name.startswith(".download")]

    def no_fetch(url, dest, progress=None):
        raise AssertionError("downloaded again")
    (home / "current").unlink()
    assert emulator.install(home, no_fetch) == f"KytyPS5-Native {emulator.VERSION} is in use."
    emulator.remove(home)
    assert not home.exists()


def test_another_file_is_refused_and_nothing_changes(tmp_path):
    home = tmp_path / "emulator"
    with pytest.raises(emulator.EmulatorError, match="SHA-256 differs"):
        emulator.install(home, fetch_of(archive(RELEASE)))          # not the pinned file
    assert emulator.installed_version(home) == "" and list(home.iterdir()) == []


@pytest.mark.parametrize(("payload", "words"), [
    (b"not an archive", "could not be unpacked"),
    (archive({"./kyty_launcher": "x"}), "has no kyty_emulator"),
    (archive({"../outside": "x", "./kyty_emulator": "x"}), "could not be unpacked")])
def test_a_bad_archive(tmp_path, monkeypatch, payload, words):
    monkeypatch.setattr(emulator, "SHA256", hashlib.sha256(payload).hexdigest())
    home = tmp_path / "home" / "emulator"
    with pytest.raises(emulator.EmulatorError, match=words):
        emulator.install(home, fetch_of(payload))
    assert emulator.installed_version(home) == "" and not (tmp_path / "home" / "outside").exists()
    assert not (tmp_path / "outside").exists()


def test_a_failed_download(tmp_path):
    def gone(url, dest, progress=None):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    def offline(url, dest, progress=None):
        raise urllib.error.URLError("no route")
    with pytest.raises(emulator.EmulatorError, match="GitHub answered 404"):
        emulator.install(tmp_path / "e", gone)
    with pytest.raises(emulator.EmulatorError, match="The download failed: no route"):
        emulator.install(tmp_path / "e", offline)


def test_the_pin_names_one_release():
    assert emulator.URL == (f"https://github.com/superkeka/KytyPS5-Native/releases/download/"
                            f"KytyPS5-Native-{emulator.VERSION}/KytyPS5-Native-{emulator.VERSION}-Linux-x86_64.tar.gz")
    assert len(emulator.SHA256) == 64 and emulator.SHA256 == emulator.SHA256.lower()
    assert emulator.VERSION.startswith(emulator.PUBLISHED)


def test_a_newer_release(monkeypatch):
    def latest(tag: str, published: str, error: str = ""):
        monkeypatch.setattr(emulator, "latest_release", lambda repo, **kwargs: ReleaseInfo(
            version=tag, tag=tag, published=published, error=error))
        return emulator.newer_release()
    assert latest(emulator.TAG, emulator.PUBLISHED) is None                     # the pinned one itself
    assert latest("KytyPS5-Native-2026-11-18-a5e09ee", "2026-11-18") is None    # an older one
    assert latest("KytyPS5-Native-2099-01-01-abcdef0", "2099-01-01").tag == "KytyPS5-Native-2099-01-01-abcdef0"
    assert latest("", "", error="offline") is None


def test_the_emulators_processes_are_found_and_ended_with_what_they_started(tmp_path):
    proc = tmp_path / "proc"
    for pid, name, parent in ((10, "kyty_emulator", 1), (20, "child", 10), (30, "bash", 1), (40, "kyty_launcher", 1)):
        (proc / str(pid)).mkdir(parents=True)
        (proc / str(pid) / "comm").write_text(name + "\n")
        (proc / str(pid) / "stat").write_text(f"{pid} ({name}) S {parent} 0\n")
    assert emulator.running(proc) and sorted(processes.find(emulator.is_kyty, proc)) == [10, 40]
    sent: list[int] = []
    assert processes.end([10, 40], proc, kill=lambda pid, sig: sent.append(pid))
    assert sent == [20, 10, 40]
    assert not emulator.running(tmp_path / "none")
