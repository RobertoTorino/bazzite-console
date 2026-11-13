# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

import pytest

from bazzite_console_portal import shortcuts


def test_files_uses_the_desktop_file_manager():
    result = shortcuts.files(lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None, Path("/home/test"))

    assert result.argv == ["xdg-open", "/home/test"]
    assert result.app_ids == ("org.kde.dolphin", "org.gnome.Nautilus")


def test_steam_requires_its_launcher():
    assert shortcuts.steam(lambda _: "/usr/bin/steam").argv == ["steam"]
    with pytest.raises(shortcuts.Missing, match="Steam is not installed"):
        shortcuts.steam(lambda _: None)


def test_youtube_opens_brave_in_kiosk_mode():
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return type("Result", (), {"returncode": 0})()

    result = shortcuts.youtube(run)

    assert result.argv == ["flatpak", "run", shortcuts.BRAVE_ID, "--kiosk", shortcuts.YOUTUBE_URL]
    assert calls[0][0] == ["flatpak", "info", shortcuts.BRAVE_ID]
    assert calls[0][1] == {"capture_output": True, "text": True, "timeout": 5}


def test_settings_choose_the_first_available_desktop_handler():
    result = shortcuts.settings("network", lambda name: "/usr/bin/kcmshell6" if name == "kcmshell6" else None)

    assert result.argv == ["kcmshell6", "kcm_networkmanagement"]
    assert result.app_ids == ("kcmshell6",)
