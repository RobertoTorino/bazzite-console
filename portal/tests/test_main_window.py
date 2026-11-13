# SPDX-License-Identifier: GPL-3.0-or-later
"""The portal window, its app tiles, settings page and status header."""

from __future__ import annotations

import pytest

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QMessageBox

from bazzite_console_portal import APP_NAME, CARDS, MANIFEST
from bazzite_console_portal import desktop_icons
from bazzite_console_portal.bigpicture import ICON_PX
from bazzite_console_portal.main_window import DESKTOP_ICONS_KEY, MainWindow, Pending
from bazzite_console_portal.manifest import load, load_cards
from bazzite_console_portal.sources import Records, Sources


@pytest.fixture
def window(qapp, home, settings_dir, tmp_path):
    result = MainWindow(load(MANIFEST), Sources(tmp_path / "work"),
                        Records(tmp_path / "installed.json"), installed=tmp_path / "installed-portal")
    yield result
    result.close()


def test_portal_shows_required_app(window):
    assert window.windowTitle().startswith(APP_NAME)
    assert list(window.states) == [entry.key for entry in window.entries]
    assert [entry.key for entry in window.entries if entry.required] == ["bazzite"]
    assert window.states["bazzite"].title == "Bazzite Test"
    assert [action.text() for action in window.tile_menu(window.entries[0]).actions()][0] == "Open"
    assert window.big.categories == ["sustainable", "gaming", "utilities"]

def test_settings_page_and_clock_menu(window):
    assert not window.big.in_settings()
    window.toggle_settings()
    assert window.big.in_settings()
    assert not window.icons_box.isChecked()

    actions = [action.text() for action in window.clock_menu().actions()]
    assert "12-hour clock (AM/PM)" in actions
    assert "24-hour clock" in actions
    assert "Seconds" in actions
    assert "UTC" in actions

    window.toggle_settings()
    assert not window.big.in_settings()


def test_clock_header_shows_date_and_time(window):
    text = window.big.status.text()
    assert "|" in text
    assert any(day in text for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))


def test_console_release_tags_are_pruned_by_app_key(tmp_path):
    source = Sources(tmp_path / "releases")
    app = load(MANIFEST)[0]
    old = source.work / "ps5-bazzite-v0.0.9"
    current = source.work / app.tag
    other = source.work / "ps5-other-v0.1.0"
    for folder in (old, current, other):
        folder.mkdir(parents=True)

    source.prune(app)

    assert not old.exists()
    assert current.is_dir()
    assert other.is_dir()


def test_desktop_icon_toggle_only_manages_console_apps(tmp_path):
    menu = tmp_path / "applications"
    menu.mkdir()
    (menu / "bazzite-test.desktop").touch()
    (menu / "bazzite-console-suite.desktop").touch()
    (menu / "unrelated-app.desktop").touch()

    assert [path.name for path in desktop_icons.launchers(menu)] == ["bazzite-test.desktop"]


@pytest.mark.parametrize("show", [False, True])
def test_finished_install_respects_desktop_icon_setting(window, tmp_path, desktop, show):
    menu = tmp_path / "applications"
    menu.mkdir()
    name = "ps5-rpcs3-manager.desktop"
    (menu / name).write_text("[Desktop Entry]\n")
    (desktop / name).write_text("[Desktop Entry]\n")
    window.menu = menu
    window.icons_box.setChecked(show)
    window.settings.setValue(DESKTOP_ICONS_KEY, show)
    exit_file = tmp_path / "installer.exit"
    exit_file.write_text("0\n")
    entry = next(entry for entry in window.entries if entry.key == "rpcs3")
    window.pending = Pending(entry, "install", exit_file, entry.tag)

    window._check_pending()

    assert (desktop / name).exists() is show
    assert (menu / name).exists()


def test_start_with_icons_off_removes_existing_console_shortcuts(window, tmp_path, desktop):
    menu = tmp_path / "applications"
    menu.mkdir()
    for name in ("bazzite-test.desktop", "ps5-sftp-tools.desktop", "bazzite-console-suite.desktop"):
        (menu / name).touch()
        (desktop / name).touch()
    window.menu = menu
    window.settings.setValue(DESKTOP_ICONS_KEY, False)
    window.icons_box.setChecked(False)

    window.settle_icons()

    assert sorted(path.name for path in desktop.iterdir()) == ["bazzite-console-suite.desktop"]


def test_first_start_detects_console_shortcuts_and_toggle_restores_them(window, tmp_path, desktop, monkeypatch):
    menu = tmp_path / "applications"
    menu.mkdir()
    name = "ps5-rpcs3-manager.desktop"
    (menu / name).write_text("[Desktop Entry]\n")
    (desktop / name).write_text("[Desktop Entry]\n")
    window.menu = menu
    window.settings.remove(DESKTOP_ICONS_KEY)
    questions = []
    monkeypatch.setattr(QMessageBox, "question", lambda *args: questions.append(args[2]) or
                        QMessageBox.StandardButton.No)
    monkeypatch.setattr(desktop_icons.shutil, "which", lambda _: None)

    window.settle_icons()

    assert len(questions) == 1
    assert not (desktop / name).exists()
    window.icons_box.setChecked(True)
    assert (desktop / name).is_file()
    window.icons_box.setChecked(False)
    assert not (desktop / name).exists()
