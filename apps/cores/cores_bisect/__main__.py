# SPDX-License-Identifier: GPL-3.0-or-later

"""Entry point: python -m cores_bisect [--script PATH] [--unlock-script PATH] [--resume]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from . import APP_ID, APP_NAME, ROOT, WINDOW_ICON_PATH, __version__
from .main_window import MainWindow
from . import exit_keys, instance
from .theme import HOVER_STYLESHEET, apply_theme
from .widgets import RoundedToolTip

DEFAULT_SCRIPT = ROOT / "ps5-cores-bisect.sh"
DEFAULT_UNLOCK_SCRIPT = ROOT / "ps5-cores-unlock.sh"


def main() -> int:
    parser = argparse.ArgumentParser(prog="cores_bisect", description=f"{APP_NAME} {__version__}")
    parser.add_argument("--script", default=str(DEFAULT_SCRIPT), help="path to ps5-cores-bisect.sh")
    parser.add_argument("--unlock-script", default=str(DEFAULT_UNLOCK_SCRIPT), help="path to ps5-cores-unlock.sh")
    parser.add_argument("--resume", action="store_true",
                        help="go on with a running core test after a login (the autostart entry passes it)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args, qt_args = parser.parse_known_args()

    app = QApplication([sys.argv[0], *qt_args])
    exit_keys.install(app)                  # Escape and a controller's B close the window
    app.setOrganizationName("ps5-cores-bisect")
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(f"{APP_NAME} {__version__}")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    app.setStyle("Fusion")
    apply_theme(app, HOVER_STYLESHEET)     # the suite's theme, the accent outline on hover
    RoundedToolTip.install(app)            # the tooltips as the suite's other apps show them
    if WINDOW_ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(WINDOW_ICON_PATH)))

    script = Path(args.script).resolve()
    unlock_script = Path(args.unlock_script).resolve()
    for path in (script, unlock_script):
        if not path.is_file():
            QMessageBox.critical(None, APP_NAME, f"{path.name} not found:\n{path}")
            return 1

    # One instance: a second launch brings the running window to the front and exits.
    if instance.already_running(APP_ID):
        return 0
    window = MainWindow(str(script), str(unlock_script), resume_run=args.resume)
    window.show()
    server = instance.serve(APP_ID, window)  # noqa: F841 (kept alive while the app runs)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
