# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point: python -m demo_recorder (run.sh starts it with the checkout's dev venv)."""

from __future__ import annotations

import argparse
import sys

from bazzite_console_core import __version__ as CORE_VERSION, instance
from bazzite_console_core.app import create_app, exec_app
from bazzite_console_core.nexus import NEXUS, checkout_stamp
from bazzite_console_core.platform import data_home

from . import APP_ID, APP_NAME, CHECKOUT, INFO


def main() -> int:
    stamp = checkout_stamp(CHECKOUT)  # never released: the commit says which code runs
    parser = argparse.ArgumentParser(prog="demo_recorder", description=f"{APP_NAME} {stamp}".strip())
    parser.add_argument("--version", action="version", version=f"%(prog)s {stamp} (core {CORE_VERSION})")
    _args, qt_args = parser.parse_known_args()

    app = create_app(INFO, qt_args, theme=NEXUS)           # Nexus's design, not a suite's theme
    # One instance: a second launch (a double-click on the Desktop icon) brings the running window to the front.
    if instance.already_running(INFO.app_id):
        return 0
    # With the menu entry of install.sh, the desktop file name gives the window its icon in the task bar. Without
    # it, no name: Qt would try to register it with the desktop portal, which only logs "App info not found".
    if not (data_home() / "applications" / f"{APP_ID}.desktop").is_file():
        app.setDesktopFileName("")
    from .main_window import MainWindow
    window = MainWindow()
    window.show()
    server = instance.serve(INFO.app_id, window)  # noqa: F841 (kept alive while the app runs)
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
