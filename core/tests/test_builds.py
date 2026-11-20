# SPDX-License-Identifier: GPL-3.0-or-later
"""Several builds of an emulator side by side (builds.py; owner, 20-11-2026): installed beside each other and checked
against their SHA-256, one in use through "current", switched and deleted, a custom file added, a replaced member
seen by its size; the list from GitHub with its digests. The version manager's window (builds_dialog.py) over it."""

from __future__ import annotations

import hashlib
import io
import urllib.error
import zipfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QMenu, QMessageBox

from bazzite_console_core import builds
from bazzite_console_core.builds import Build
from bazzite_console_core.builds_dialog import BuildsDialog, fill_menu

MEMBER = "emu.AppImage"


def _build(version: str, payload: bytes, **extra) -> Build:
    return Build(version, f"Build {version}", extra.pop("published", "2026-11-19"), url=f"https://example/{version}",
                 asset=f"emu-{version}.AppImage", sha256=hashlib.sha256(payload).hexdigest(), size=len(payload),
                 **extra)


def _fetch(payload: bytes, calls: list | None = None):
    def fetch(url: str, dest: Path, progress=None) -> None:
        if calls is not None:
            calls.append(url)
        dest.write_bytes(payload)
    return fetch


def test_builds_side_by_side(tmp_path):
    home = tmp_path / "emulator"
    assert builds.installed(home, MEMBER) == [] and builds.current(home, MEMBER) == ""
    calls = []
    builds.install(home, _build("1.0", b"one", published="2026-10-01"), MEMBER, _fetch(b"one", calls))
    assert calls == ["https://example/1.0"] and builds.current(home, MEMBER) == "1.0"
    builds.install(home, _build("2.0", b"two"), MEMBER, _fetch(b"two"), use_it=False)
    assert builds.current(home, MEMBER) == "1.0"                                 # not in use until Use
    assert [b.version for b in builds.installed(home, MEMBER)] == ["2.0", "1.0"]  # newest first
    image = home / "2.0" / MEMBER
    assert image.read_bytes() == b"two" and image.stat().st_mode & 0o777 == 0o755
    assert sorted(p.name for p in home.iterdir()) == ["1.0", "2.0", "current"]   # no download left behind
    builds.use(home, "2.0", MEMBER)
    assert builds.current(home, MEMBER) == "2.0" and builds.info(home, MEMBER).name == "Build 2.0"
    with pytest.raises(builds.BuildError, match="in use"):
        builds.delete(home, "2.0", MEMBER)
    builds.delete(home, "1.0", MEMBER)
    assert [b.version for b in builds.installed(home, MEMBER)] == ["2.0"]
    with pytest.raises(builds.BuildError, match="not installed"):
        builds.use(home, "1.0", MEMBER)
    for bad in ("", ".", "..", "current", "../x"):
        with pytest.raises(builds.BuildError):
            builds.delete(home, bad, MEMBER)


def test_a_build_older_than_build_json(tmp_path):
    """A folder an earlier version of a manager installed, without build.json: a build all the same."""
    home = tmp_path / "emulator"
    (home / "4377").mkdir(parents=True)
    (home / "4377" / MEMBER).write_text("old")
    (home / "current").symlink_to("4377")
    assert [(b.version, b.name) for b in builds.installed(home, MEMBER)] == [("4377", "")]
    assert not builds.replaced(home, MEMBER) and builds.replaced(home, MEMBER, fallback=10)
    assert not builds.replaced(home, MEMBER, fallback=3)
    builds.remember(home, "4377", Build("4377", "Build: 4377"), MEMBER)
    assert builds.info(home, MEMBER).member_size == 3 and not builds.replaced(home, MEMBER, fallback=10)


def test_a_different_file_changes_nothing(tmp_path):
    home = tmp_path / "emulator"
    builds.install(home, _build("1.0", b"one"), MEMBER, _fetch(b"one"))
    with pytest.raises(builds.BuildError, match="not the file GitHub published .its SHA-256 differs"):
        builds.install(home, _build("2.0", b"two"), MEMBER, _fetch(b"tampered"))
    with pytest.raises(builds.BuildError, match="the file this app was tested with"):
        builds.install(home, _build("2.0", b"two"), MEMBER, _fetch(b"x"), refused="this app was tested with")
    with pytest.raises(builds.BuildError, match="no SHA-256"):
        builds.install(home, Build("3.0", url="https://example/3.0"), MEMBER, _fetch(b"three"))
    assert [b.version for b in builds.installed(home, MEMBER)] == ["1.0"] and builds.current(home, MEMBER) == "1.0"
    assert sorted(p.name for p in home.iterdir()) == ["1.0", "current"]


def test_download_errors(tmp_path):
    def http(url, dest, progress=None):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    def offline(url, dest, progress=None):
        raise urllib.error.URLError("Name or service not known")
    with pytest.raises(builds.BuildError, match="GitHub answered 404 for emu-1.0.AppImage"):
        builds.install(tmp_path, _build("1.0", b"one"), MEMBER, http)
    with pytest.raises(builds.BuildError, match="download failed: Name or service not known"):
        builds.install(tmp_path, _build("1.0", b"one"), MEMBER, offline)


def test_a_zip_unpacked(tmp_path):
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w") as archive:
        archive.writestr("Emu.AppImage", b"inside")
    payload = packed.getvalue()

    def unpack(archive: Path, member: Path) -> None:
        with zipfile.ZipFile(archive) as opened:
            member.write_bytes(opened.read("Emu.AppImage"))
    home = tmp_path / "emulator"
    builds.install(home, _build("1.0", payload), MEMBER, _fetch(payload), unpack=unpack)
    assert (home / "1.0" / MEMBER).read_bytes() == b"inside" and builds.info(home, MEMBER).member_size == 6


def test_replaced_by_its_own_size(tmp_path):
    home = tmp_path / "emulator"
    builds.install(home, _build("1.0", b"one"), MEMBER, _fetch(b"one"))
    assert not builds.replaced(home, MEMBER, fallback=999)                      # build.json knows better
    (home / "1.0" / MEMBER).write_bytes(b"another build written over it")
    assert builds.replaced(home, MEMBER)
    assert not builds.replaced(tmp_path / "nothing", MEMBER, fallback=1)


def test_a_custom_build(tmp_path):
    home = tmp_path / "emulator"
    own = tmp_path / "My Emu (fixed).AppImage"
    own.write_bytes(b"mine")
    first = builds.add_custom(home, own, MEMBER)
    second = builds.add_custom(home, own, MEMBER)
    assert (first.version, second.version) == ("custom-My-Emu-fixed", "custom-My-Emu-fixed-2")
    assert first.kind == builds.CUSTOM and first.name == own.name and builds.current(home, MEMBER) == ""
    assert (home / first.folder / MEMBER).read_bytes() == b"mine" and own.is_file()       # a copy
    with pytest.raises(builds.BuildError, match="not a file"):
        builds.add_custom(home, tmp_path / "missing", MEMBER)


def _release(tag: str, asset: str, digest: str = "sha256:" + "ab" * 32, **extra) -> dict:
    return {"tag_name": tag, "name": f"emu {tag}", "published_at": "2026-11-19T20:05:38Z",
            "html_url": f"https://github.com/o/emu/releases/tag/{tag}", "prerelease": extra.get("prerelease", False),
            "draft": extra.get("draft", False),
            "assets": [{"name": "emu-windows.zip", "digest": "sha256:" + "00" * 32},
                       {"name": asset, "digest": digest, "size": 1234,
                        "browser_download_url": f"https://github.com/o/emu/releases/download/{tag}/{asset}"}]}


def _pick(release: dict, asset: dict) -> str | None:
    return str(release["tag_name"]).lstrip("v") if str(asset.get("name", "")).endswith("-linux.AppImage") else None


def test_the_list_from_github():
    def fetch(url: str):
        assert url == "https://api.github.com/repos/o/emu/releases?per_page=30"
        return [_release("v3.0", "emu-3.0-linux.AppImage", prerelease=True),
                _release("v2.9", "emu-2.9-linux.AppImage", draft=True),
                _release("v2.8", "emu-2.8-linux.AppImage", digest=""),          # no SHA-256 from GitHub
                _release("v2.7", "emu-2.7-mac.dmg"),
                _release("v2.6", "emu-2.6-linux.AppImage")]
    found = builds.github_builds("o/emu", _pick, fetch)
    assert [(b.version, b.kind) for b in found] == [("3.0", builds.PRERELEASE), ("2.6", builds.RELEASE)]
    six = found[1]
    assert (six.name, six.published, six.size, six.sha256) == ("emu v2.6", "2026-11-19", 1234, "ab" * 32)
    assert six.url.endswith("/download/v2.6/emu-2.6-linux.AppImage") and six.page.endswith("/tag/v2.6")

    def offline(url: str):
        raise urllib.error.URLError("no network")
    with pytest.raises(builds.BuildError, match="could not be asked: no network"):
        builds.github_builds("o/emu", _pick, offline)
    with pytest.raises(builds.BuildError, match="not a release list"):
        builds.github_builds("o/emu", _pick, lambda url: {"message": "rate limited"})


def test_the_latest_release_and_merging():
    def fetch(url: str):
        assert url == "https://api.github.com/repos/o/emu/releases/latest"
        return _release("v2.6", "emu-2.6-linux.AppImage")
    latest = builds.github_latest("o/emu", _pick, fetch)
    assert latest.version == "2.6"
    assert builds.github_latest("o/emu", _pick, lambda url: _release("v2.6", "emu.dmg")) is None
    tested = Build("2.5", "tested", "2026-09-01")
    merged = builds.merged([tested], [latest, Build("2.5", "from GitHub", "2026-09-01")])
    assert [(b.version, b.name) for b in merged] == [("2.6", "emu v2.6"), ("2.5", "tested")]


def test_the_version_pill_menu(qapp, tmp_path):
    home = tmp_path / "emulator"
    builds.install(home, _build("1.0", b"one"), MEMBER, _fetch(b"one"))
    builds.install(home, _build("2.0", b"two", published="2026-11-20"), MEMBER, _fetch(b"two"), use_it=False)
    used, managed = [], []
    menu = QMenu()
    fill_menu(menu, home, MEMBER, "1.0", used.append, lambda: managed.append(True))
    actions = [a for a in menu.actions() if not a.isSeparator()]
    assert [(a.text(), a.isChecked()) for a in actions] == [("2.0", False), ("1.0 (tested)", True),
                                                            ("Manage versions…", False)]
    actions[0].trigger()
    actions[2].trigger()
    assert used == ["2.0"] and managed == [True]


def _dialog(home: Path, tested: Build, available, install, **extra) -> BuildsDialog:
    return BuildsDialog("Emu", home, MEMBER, tested, available, install, **extra)


def _wait(dialog, qapp) -> None:
    while dialog.worker.running:
        qapp.processEvents()


def test_the_version_manager(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    home = tmp_path / "emulator"
    tested = _build("1.0", b"one", published="2026-10-01")
    builds.install(home, tested, MEMBER, _fetch(b"one"))
    newer = _build("2.0", b"two", published="2026-11-20", kind=builds.PRERELEASE)
    dialog = _dialog(home, tested, lambda: [newer, _build("1.0", b"one", published="2026-10-01")],
                     lambda build: builds.install(home, build, MEMBER, _fetch(b"two"), use_it=False))
    changed = []
    dialog.changed.connect(lambda: changed.append(True))
    table = dialog.installed_table
    assert table.rowCount() == 1 and table.item(0, 0).text() == "✓" and table.item(0, 4).text() == "Tested"
    assert dialog.remote_table.rowCount() == 1                                  # the tested build, before Refresh
    assert dialog.remote_table.item(0, 3).text() == "Tested, installed"
    dialog.on_refresh()
    _wait(dialog, qapp)
    assert [dialog.remote_table.item(r, 0).text() for r in range(2)] == ["2.0", "1.0"]
    assert dialog.remote_table.item(0, 3).text() == "Pre-release" and dialog.status.text().startswith("2 Emu")
    dialog.remote_table.selectRow(1)
    assert not dialog.download_pill.isEnabled()                                 # installed already
    dialog.remote_table.selectRow(0)
    assert dialog.download_pill.isEnabled()
    dialog.on_download()
    _wait(dialog, qapp)
    assert dialog.status.text() == "Emu 2.0 is installed; Use puts it in use." and changed == [True]
    assert dialog.chosen().version == "2.0" and builds.current(home, MEMBER) == "1.0"
    assert dialog.use_pill.isEnabled() and dialog.delete_pill.isEnabled()
    dialog.on_use()
    assert builds.current(home, MEMBER) == "2.0" and "not tried on the board" in dialog.status.text()
    dialog.installed_table.selectRow([b.version for b in dialog.builds].index("2.0"))
    assert not dialog.use_pill.isEnabled() and not dialog.delete_pill.isEnabled()   # the one in use
    dialog.installed_table.selectRow([b.version for b in dialog.builds].index("1.0"))
    dialog.on_delete()
    assert [b.version for b in dialog.builds] == ["2.0"] and len(changed) == 3


def test_the_version_manager_says_what_went_wrong(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    home = tmp_path / "emulator"
    tested = _build("1.0", b"one")

    def offline():
        raise builds.BuildError("GitHub could not be asked: no network.")

    def broken(build):
        raise builds.BuildError(f"{build.asset} is not the file GitHub published (its SHA-256 differs)")
    dialog = _dialog(home, tested, offline, broken)
    dialog.on_refresh()
    _wait(dialog, qapp)
    assert dialog.status.text() == "The list could not be read: GitHub could not be asked: no network."
    dialog.remote_table.selectRow(0)
    dialog.on_download()
    _wait(dialog, qapp)
    assert "was not installed: emu-1.0.AppImage is not the file" in dialog.status.text()
    assert dialog.builds == []


def test_a_custom_build_in_the_version_manager(qapp, tmp_path):
    home = tmp_path / "emulator"
    own = tmp_path / "emu-dev.AppImage"
    own.write_bytes(b"mine")
    dialog = _dialog(home, _build("1.0", b"one"), list, lambda build: None, pick_file=lambda: str(own))
    dialog.on_custom()
    assert [b.version for b in dialog.builds] == ["custom-emu-dev"] and "was not checked" in dialog.status.text()
    assert dialog.installed_table.item(0, 4).text() == builds.CUSTOM and dialog.use_pill.isEnabled()
    dialog.on_use()
    assert builds.current(home, MEMBER) == "custom-emu-dev"
