# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point: python -m nexus_release_tool (run.sh starts it with the checkout's dev venv)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from nexus_core import __version__ as CORE_VERSION, instance
from nexus_core.app import create_app, exec_app
from nexus_core.platform import data_home
from nexus_core.settings import open_settings
from PyQt6.QtCore import QSettings

from . import APP_ID, APP_NAME, INFO, __version__
from .style import NEXUS

# The app's id as Nexus Releases (dev/releases, until 30-10-2026): its settings are taken over once.
EARLIER_ID = "nexus-releases"


def settings_file() -> Path:
    """Where open_settings(INFO) keeps the settings: <id>/<id>.ini in ~/.config."""
    return Path(QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, INFO.org,
                          INFO.settings_name).fileName())


def take_earlier_settings(new: Path) -> bool:
    """The settings of Nexus Releases, the app's earlier name, become this app's when it has none yet: the file
    moves to *new* and the earlier folder goes. True when they were taken over."""
    old = new.parent.parent / EARLIER_ID / f"{EARLIER_ID}.ini"
    if new.exists() or not old.is_file():
        return False
    new.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old, new)
    shutil.rmtree(old.parent, ignore_errors=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(prog="nexus_release_tool", description=f"{APP_NAME} {__version__}")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__} (core {CORE_VERSION})")
    _args, qt_args = parser.parse_known_args()

    take_earlier_settings(settings_file())          # before open_settings() reads them
    app = create_app(INFO, qt_args, theme=NEXUS)           # Nexus's design, not a suite's theme
    if instance.already_running(INFO.app_id):       # a double-click on the Desktop icon starts it twice
        return 0
    # With the menu entry of install.sh, the desktop file name gives the window its icon in the task bar. Without
    # it, no name: Qt would try to register it with the desktop portal, which only logs "App info not found".
    if not (data_home() / "applications" / f"{APP_ID}.desktop").is_file():
        app.setDesktopFileName("")
    from .main_window import ReleaseWindow
    window = ReleaseWindow(settings=open_settings(INFO))
    window.show()
    server = instance.serve(INFO.app_id, window)  # noqa: F841 (kept alive while the app runs)
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
