# SPDX-License-Identifier: GPL-3.0-or-later
"""The header's shortcuts: what each one starts, from what the machine has."""

import subprocess
from pathlib import Path

import pytest

from bazzite_console_portal import shortcuts


def has(*programs):
    return lambda name: f"/usr/bin/{name}" if name in programs else None


def flatpak(code=0, error=None):
    def run(argv, **kwargs):
        assert argv == ["flatpak", "info", "com.brave.Browser"] and kwargs["timeout"] == 5
        if error is not None:
            raise error
        return subprocess.CompletedProcess(argv, code, "", "")
    return run


def test_steam_and_the_file_manager():
    assert shortcuts.steam(has("steam")).argv == ["steam"]
    with pytest.raises(shortcuts.Missing, match="Steam is not installed"):
        shortcuts.steam(has())
    assert shortcuts.files(has("xdg-open"), Path("/home/someone")).argv == ["xdg-open", "/home/someone"]
    with pytest.raises(shortcuts.Missing, match="xdg-open"):
        shortcuts.files(has())


def test_youtube_needs_brave_browsers_flatpak():
    start = shortcuts.youtube(flatpak())
    assert start.argv == ["flatpak", "run", "com.brave.Browser", "--start-maximized", "https://www.youtube.com/"]
    assert "com.brave.Browser" in start.app_ids
    with pytest.raises(shortcuts.Missing, match="Brave Browser is required"):
        shortcuts.youtube(flatpak(1))
    with pytest.raises(shortcuts.Missing, match="Flatpak is not available"):
        shortcuts.youtube(flatpak(error=FileNotFoundError()))
    with pytest.raises(shortcuts.Missing, match="could not be asked"):
        shortcuts.youtube(flatpak(error=subprocess.TimeoutExpired("flatpak", 5)))


def test_discord_opens_in_brave():
    """Discord (owner, 25-11-2026): its web app in a maximized window of Brave Browser, and a message while it is missing."""
    start = shortcuts.discord(flatpak())
    assert start.argv == ["flatpak", "run", "com.brave.Browser", "--start-maximized", "https://discord.com/app"]
    assert "com.brave.Browser" in start.app_ids
    with pytest.raises(shortcuts.Missing, match="Brave Browser is required.*to open Discord"):
        shortcuts.discord(flatpak(1))


def test_the_weather_opens_its_forecast_in_brave():
    """A click on the weather (owner, 24-11-2026): the place's forecast at wttr.in, a page without ads, by its
    coordinates, in a window of Brave Browser."""
    start = shortcuts.weather(52.37, 4.89, flatpak())
    assert start.argv == ["flatpak", "run", "com.brave.Browser", "https://wttr.in/52.3700,4.8900"]
    assert "com.brave.Browser" in start.app_ids
    with pytest.raises(shortcuts.Missing, match="Brave Browser is required.*to open the weather"):
        shortcuts.weather(52.37, 4.89, flatpak(1))


def test_github_opens_in_the_desktops_own_browser():
    """github.com with xdg-open; the browser's window is the one KWin brings to the front, when it can be asked."""
    def browser(code=0, out="org.mozilla.firefox.desktop\n", error=None):
        def run(argv, **kwargs):
            assert argv == ["xdg-settings", "get", "default-web-browser"] and kwargs["timeout"] == 5
            if error is not None:
                raise error
            return subprocess.CompletedProcess(argv, code, out, "")
        return run
    start = shortcuts.github(has("xdg-open"), browser())
    assert start.argv == ["xdg-open", "https://github.com/"] and start.app_ids == ("org.mozilla.firefox",)
    for unknown in (browser(1), browser(out=""), browser(error=FileNotFoundError()),
                    browser(error=subprocess.TimeoutExpired("xdg-settings", 5))):
        assert shortcuts.github(has("xdg-open"), unknown) == shortcuts.Start(["xdg-open", "https://github.com/"], ())
    with pytest.raises(shortcuts.Missing, match="GitHub could not be opened"):
        shortcuts.github(has())


@pytest.mark.parametrize("page, kcm, panel", [("bluetooth", "kcm_bluetooth", "bluetooth"),
                                              ("network", "kcm_networkmanagement", "network"),
                                              ("sound", "kcm_pulseaudio", "sound"),
                                              ("display", "kcm_kscreen", "display")])
def test_the_settings_of_the_desktop_that_is_there(page, kcm, panel):
    """KDE Plasma's System Settings, else the module alone, else GNOME's Settings (not only the owner's desktop)."""
    assert shortcuts.settings(page, has("systemsettings", "kcmshell6")).argv == ["systemsettings", kcm]
    assert shortcuts.settings(page, has("kcmshell6")).argv == ["kcmshell6", kcm]
    assert shortcuts.settings(page, has("gnome-control-center")).argv == ["gnome-control-center", panel]
    with pytest.raises(shortcuts.Missing, match="settings of this desktop"):
        shortcuts.settings(page, has())
