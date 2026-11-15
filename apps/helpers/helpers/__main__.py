# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point: python -m helpers [HELPER]: the list of helpers, or one helper's window (the portal's tiles)."""

from __future__ import annotations

import argparse
import sys

from bazzite_console_core import __version__ as CORE_VERSION, instance
from bazzite_console_core.app import create_app, exec_app
from bazzite_console_core import exit_keys

from . import APP_NAME, INFO, __version__
from .catalog import BY_KEY


def main() -> int:
    parser = argparse.ArgumentParser(prog="helpers", description=f"{APP_NAME} {__version__}")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__} (core {CORE_VERSION})")
    parser.add_argument("helper", nargs="?", choices=sorted(BY_KEY), help="open this helper's window")
    args, qt_args = parser.parse_known_args()

    app = create_app(INFO, qt_args)
    exit_keys.install(app)                  # Escape and a controller's B close the window
    # One window per helper: a second launch of the same one brings its window to the front.
    name = f"{INFO.app_id}-{args.helper}" if args.helper else INFO.app_id
    if instance.already_running(name):
        return 0
    if args.helper:
        from .windows import WINDOWS
        window = WINDOWS[args.helper]()
    else:
        from .main_window import MainWindow
        window = MainWindow()
    window.show()
    server = instance.serve(name, window)  # noqa: F841 (kept alive while the app runs)
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
