# SPDX-License-Identifier: GPL-3.0-or-later

"""The GPU sweep window as a program of its own: python -m gpu_governor --sweep [--script PATH] [--resume]. GPU
Manager's Safe points page starts it, and the autostart entry of a sweep with one boot per attempt (resume.py). Its own
process, so a freeze or a restart during a sweep leaves GPU Manager alone."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from .. import exit_keys
from ..theme import HOVER_STYLESHEET, apply_theme
from . import APP_ID, APP_NAME, ROOT, SCRIPT, WINDOW_ICON_PATH, __version__, instance
from .main_window import MainWindow
from .widgets import RoundedToolTip, WheelGuard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gpu_governor --sweep", description=f"{APP_NAME} {__version__}")
    parser.add_argument("--script", default=str(ROOT / SCRIPT), help=f"path to {SCRIPT}")
    parser.add_argument("--resume", action="store_true",
                        help="go on with a running sweep after a login (the autostart entry passes it)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args, qt_args = parser.parse_known_args(argv)

    app = QApplication([sys.argv[0], *qt_args])
    exit_keys.install(app)                  # Escape and a controller's B close the window
    app.setOrganizationName(APP_ID)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(f"{APP_NAME} {__version__}")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("ps5-governor-manager")
    app.setStyle("Fusion")
    apply_theme(app, HOVER_STYLESHEET)     # GPU Manager's theme, the outline on hover
    RoundedToolTip.install(app)            # the tooltips as the suite's other apps show them
    WheelGuard.install(app)                 # the wheel changes a value only after a click on it
    if WINDOW_ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(WINDOW_ICON_PATH)))

    script = Path(args.script).resolve()
    if not script.is_file():
        QMessageBox.critical(None, APP_NAME, f"{script.name} not found:\n{script}")
        return 1

    # One instance: a second launch brings the running window to the front and exits.
    if instance.already_running(APP_ID):
        return 0
    window = MainWindow(str(script), resume_run=args.resume)
    window.show()
    server = instance.serve(APP_ID, window)  # noqa: F841 (kept alive while the app runs)
    return app.exec()

