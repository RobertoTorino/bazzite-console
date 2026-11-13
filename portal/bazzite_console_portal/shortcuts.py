# SPDX-License-Identifier: GPL-3.0-or-later
"""Programs outside the suite that the portal can open from its header."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

BRAVE_ID, BRAVE_NAME = "com.brave.Browser", "Brave Browser"
YOUTUBE_URL = "https://www.youtube.com/"
SETTINGS = {
    "bluetooth": (("systemsettings", ("kcm_bluetooth",), "systemsettings"),
                  ("kcmshell6", ("kcm_bluetooth",), "kcmshell6"),
                  ("gnome-control-center", ("bluetooth",), "org.gnome.Settings")),
    "network": (("systemsettings", ("kcm_networkmanagement",), "systemsettings"),
                ("kcmshell6", ("kcm_networkmanagement",), "kcmshell6"),
                ("gnome-control-center", ("network",), "org.gnome.Settings")),
    "sound": (("systemsettings", ("kcm_pulseaudio",), "systemsettings"),
              ("kcmshell6", ("kcm_pulseaudio",), "kcmshell6"),
              ("gnome-control-center", ("sound",), "org.gnome.Settings")),
    "display": (("systemsettings", ("kcm_kscreen",), "systemsettings"),
                ("kcmshell6", ("kcm_kscreen",), "kcmshell6"),
                ("gnome-control-center", ("display",), "org.gnome.Settings")),
}

Which = Callable[[str], str | None]
Run = Callable[..., subprocess.CompletedProcess]


class Missing(RuntimeError):
    """The shortcut's program is not available on this system."""


@dataclass(frozen=True)
class Start:
    argv: list[str]
    app_ids: tuple[str, ...]


def steam(which: Which | None = None) -> Start:
    if (which or shutil.which)("steam") is None:
        raise Missing("Steam is not installed on this system.")
    return Start(["steam"], ("steam",))


def files(which: Which | None = None, home: Path | None = None) -> Start:
    """Open the desktop's file manager on the home folder."""
    if (which or shutil.which)("xdg-open") is None:
        raise Missing("No file manager could be opened: xdg-open is not on this system.")
    return Start(["xdg-open", str(home or Path.home())], ("org.kde.dolphin", "org.gnome.Nautilus"))


def flatpak_installed(app_id: str, run: Run | None = None) -> bool:
    """Whether a Flatpak is installed; raise Missing when Flatpak cannot report."""
    try:
        result = (run or subprocess.run)(["flatpak", "info", app_id], capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        raise Missing("Flatpak is not available on this system.") from None
    except (OSError, subprocess.SubprocessError) as exc:
        raise Missing(f"Flatpak could not be asked what is installed:\n\n{exc}") from None
    return result.returncode == 0


def youtube(run: Run | None = None) -> Start:
    """Open YouTube fullscreen in Brave Browser's kiosk mode."""
    if not flatpak_installed(BRAVE_ID, run):
        raise Missing(f"{BRAVE_NAME} is required. Install its Flatpak ({BRAVE_ID}) to open YouTube.")
    return Start(["flatpak", "run", BRAVE_ID, "--kiosk", YOUTUBE_URL], (BRAVE_ID, "brave-browser"))


def settings(page: str, which: Which | None = None) -> Start:
    """Open a Bluetooth, network, sound, or display settings page."""
    for program, arguments, app_id in SETTINGS[page]:
        if (which or shutil.which)(program) is not None:
            return Start([program, *arguments], (app_id,))
    label = "Bluetooth" if page == "bluetooth" else page
    raise Missing(f"The {label} settings of this desktop could not be found "
                  "(KDE Plasma's System Settings or GNOME's Settings).")


def bluetooth_settings() -> Start:
    return settings("bluetooth")


def network_settings() -> Start:
    return settings("network")


def sound_settings() -> Start:
    return settings("sound")


def display_settings() -> Start:
    return settings("display")
