# SPDX-License-Identifier: GPL-3.0-or-later
"""What Nexus Garbage Remover finds, when it says so, and how it deletes (owner, 22-11-2026)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from nexus_garbage_remover import garbage


def fill(folder: Path, size: int, name: str = "file") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(b"x" * size)


def test_it_finds_the_full_places_largest_first(tmp_path):
    home, steam, dumps = tmp_path / "home", tmp_path / "home" / "Steam", tmp_path / "dumps"
    fill(steam / "config" / "htmlcache" / "BrowserMetrics", 3 << 20)
    fill(home / ".local" / "share" / "Trash" / "files", 2 << 20)
    fill(dumps, 1 << 10)                                            # under a MB: left out
    found = garbage.find(home, steam, dumps, which=lambda _name: None)
    assert [place.key for place in found] == ["steam-reports", "trash"]
    assert found[0].size == 3 << 20 and found[0].files == 1 and not found[0].root
    assert found[1].command == ["find", str(home / ".local" / "share" / "Trash"), "-mindepth", "2", "-delete"]


def test_the_crash_dumps_take_root(tmp_path):
    dumps = garbage.places(tmp_path, tmp_path, tmp_path / "dumps", which=lambda _name: None)[0]
    assert dumps.key == "dumps" and dumps.root and dumps.command_text.startswith("sudo find ")


def test_homebrew_only_where_it_is_installed(tmp_path):
    keys = [place.key for place in garbage.places(tmp_path, None, tmp_path, which=lambda name: "/bin/" + name)]
    assert "homebrew" in keys
    assert "homebrew" not in [place.key for place in garbage.places(tmp_path, None, tmp_path, which=lambda _: None)]



def test_homebrews_own_cache_is_not_garbage(tmp_path):
    cache = tmp_path / ".cache" / "Homebrew"
    fill(cache / "api", 3 << 20)                                    # what brew cleanup keeps: never counted
    fill(cache / "bootsnap" / "key", 2 << 20)
    assert garbage.find(tmp_path, None, tmp_path / "dumps", which=lambda name: "/bin/" + name) == []
    fill(cache / "downloads", 2 << 20)
    found = garbage.find(tmp_path, None, tmp_path / "dumps", which=lambda name: "/bin/" + name)
    assert [(place.key, place.size) for place in found] == [("homebrew", 2 << 20)]

def test_it_tells_from_a_gigabyte_once_a_day():
    gb = garbage.NOTIFY_FROM
    assert not garbage.should_notify(gb - 1, 1000.0, {})
    assert garbage.should_notify(gb, 1000.0, {})
    assert not garbage.should_notify(gb, 1000.0 + 3600, {"time": 1000.0, "size": gb})
    assert garbage.should_notify(2 * gb, 1000.0 + 3600, {"time": 1000.0, "size": gb})       # it grew by a GB
    assert garbage.should_notify(gb, 1000.0 + garbage.NOTIFY_AGAIN, {"time": 1000.0, "size": gb})


def test_the_users_places_go_alone_and_the_systems_with_one_password(tmp_path):
    places = garbage.places(tmp_path, tmp_path, tmp_path / "dumps", which=lambda _name: None)
    calls = []

    def run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")
    assert garbage.remove(places, run, which=lambda name: "/usr/bin/" + name) == []
    assert calls[-1][:3] == ["pkexec", "sh", "-c"] and len([c for c in calls if c[0] == "pkexec"]) == 1
    refused = garbage.remove(places[:1], lambda argv, **_k: subprocess.CompletedProcess(argv, 126, "", ""),
                             which=lambda name: "/usr/bin/" + name)
    assert refused == ["Not authorized: the password dialog was canceled or refused."]


def test_the_window_lists_the_places_checked(qapp, tmp_path):
    from nexus_garbage_remover.main_window import MainWindow
    place = garbage.Garbage("trash", "Trash", tmp_path, "why", ["true"], size=2 << 30, files=3)
    window = MainWindow(finder=lambda: [place], remover=lambda chosen: [])
    while window.worker.running:
        qapp.processEvents()
    assert window.table.rowCount() == 1 and window.chosen() == [place]
    assert window.total_box.value.text() == "2.0 GB" and window.state.text() == "2.0 GB found"
    assert window.delete_pill.isEnabled()
    from PyQt6.QtCore import Qt
    window.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    assert window.chosen() == [] and not window.delete_pill.isEnabled()
    window.close()
