# SPDX-License-Identifier: GPL-3.0-or-later
import re
from pathlib import Path

from bazzite_console_portal import desktop_icons

APPS = Path(__file__).resolve().parents[2] / "apps"


def menu_with(tmp_path, *names):
    menu = tmp_path / "applications"
    menu.mkdir()
    for name in names:
        (menu / name).write_text(f"[Desktop Entry]\nName={name}\n")
    return menu


def test_add_and_remove_only_the_apps_icons(tmp_path, desktop):
    menu = menu_with(tmp_path, "bazzite-console-suite.desktop", "ps5-hdmi-cec.desktop", "ps5-cu-unlock.desktop",
                     "firefox.desktop")
    (desktop / "bazzite-console-suite.desktop").write_text("portal")
    (desktop / "notes.desktop").write_text("mine")
    assert desktop_icons.add(desktop, menu) == ["ps5-cu-unlock.desktop", "ps5-hdmi-cec.desktop"]
    icon = desktop / "ps5-hdmi-cec.desktop"
    assert icon.read_text() == (menu / "ps5-hdmi-cec.desktop").read_text() and icon.stat().st_mode & 0o111
    assert desktop_icons.add(desktop, menu) == []                                   # already there
    assert desktop_icons.remove(desktop, menu) == ["ps5-cu-unlock.desktop", "ps5-hdmi-cec.desktop"]
    assert sorted(p.name for p in desktop.iterdir()) == ["bazzite-console-suite.desktop", "notes.desktop"]


def test_an_icon_without_a_menu_entry_is_not_the_suites(tmp_path, desktop):
    menu = menu_with(tmp_path)
    (desktop / "ps5-something-else.desktop").write_text("not installed by the suite")
    assert desktop_icons.remove(desktop, menu) == [] and (desktop / "ps5-something-else.desktop").exists()


def test_no_menu_or_desktop_folder(tmp_path):
    assert desktop_icons.launchers(tmp_path / "none") == []
    assert desktop_icons.add(tmp_path / "no-desktop", menu_with(tmp_path, "ps5-hdmi-cec.desktop")) == []


def test_every_installers_menu_entry_is_known():
    """A new app whose menu entry is not ps5-*.desktop needs adding to OTHERS, or its Desktop icon stays."""
    for installer in sorted(APPS.glob("*/install.sh")):
        app_id = re.search(r'^APP_ID="([^"]+)"', installer.read_text(encoding="utf-8"), re.M)
        if app_id is None:
            continue
        name = f"{app_id[1]}.desktop"
        assert Path(name).match(desktop_icons.PATTERN) or name in desktop_icons.OTHERS, installer
