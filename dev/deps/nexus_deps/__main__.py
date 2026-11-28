# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point: python -m nexus_deps [--fix | --remind] (run.sh starts it with the checkout's dev venv).

--fix opens the window and offers Fix as soon as the check is done (the hourly notification's Fix… button).
--sync-upstreams writes catalogs/upstreams.json again from the portal's apps.toml (upstreams.py).
--remind shows no window: it checks the suite's dependencies, reads Bazzite's update state, looks for the machine's
updates (Flatpaks, Homebrew, Rust, the development venv), the PlayStation firmware and the emulators
(each new version once) and, when something needs the user, says so in a desktop notification with buttons to open the
app or fix what is missing or newer. The hourly systemd user timer that install.sh writes runs it."""

from __future__ import annotations

import argparse
import subprocess
import sys

from bazzite_console_core import __version__ as CORE_VERSION, instance
from bazzite_console_core.nexus import checkout_stamp

from . import APP_ID, APP_NAME, CATALOG, CHECKOUT, INFO, LOGO_PATH, ROOT
from .bazzite import read_state
from .dependencies import DependencyCatalogError, DependencyCheckError, check_all, load_apps, load_catalog, load_tools
from .fixes import notify, reminder_text
from .system import read_sources
from .upstreams import read as read_upstreams


def remind() -> int:
    """The hourly check: a notification when something needs the user; a click on a button opens the app."""
    path = CATALOG
    try:
        result = check_all(load_catalog(path), load_tools(path), load_apps(path), INFO.user_agent)
    except (DependencyCatalogError, DependencyCheckError, OSError) as exc:
        print(f"{APP_NAME}: the dependency check failed: {exc}", file=sys.stderr)
        result = None
    sources = read_sources() + read_upstreams("notified")
    note = reminder_text(read_state(), result, sources=sources)
    if not note.text:
        return 0
    print(note.text)
    answer = notify(APP_NAME, note.text, str(LOGO_PATH), note.actions)
    if answer in ("fix", "open"):
        argv = [str(ROOT / "run.sh"), *(["--fix"] if answer == "fix" else [])]
        subprocess.Popen(argv, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    return 0


def main() -> int:
    stamp = checkout_stamp(CHECKOUT)  # never released: the commit says which code runs
    parser = argparse.ArgumentParser(prog="nexus_deps", description=f"{APP_NAME} {stamp}".strip())
    parser.add_argument("--version", action="version", version=f"%(prog)s {stamp} (core {CORE_VERSION})")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fix", action="store_true", help="offer Fix as soon as the check is done")
    mode.add_argument("--remind", action="store_true", help="no window: a desktop notification when something "
                                                            "needs you (the hourly timer runs this)")
    mode.add_argument("--sync-upstreams", action="store_true", help="no window: bring catalogs/upstreams.json in "
                                                                    "line with the portal's apps.toml")
    args, qt_args = parser.parse_known_args()
    if args.remind:
        return remind()
    if args.sync_upstreams:
        from .upstreams import write
        print(f"{APP_NAME}: upstreams.json " + ("updated." if write() else "was in sync."))
        return 0

    from bazzite_console_core.app import create_app, exec_app
    from bazzite_console_core.nexus import NEXUS
    from bazzite_console_core.platform import data_home
    from PyQt6.QtWidgets import QMessageBox

    app = create_app(INFO, qt_args, theme=NEXUS)           # Nexus's design, not a suite's theme
    path = CATALOG
    try:
        apps = load_apps(path)
        dependencies = load_catalog(path)
        tools = load_tools(path)
    except DependencyCatalogError as exc:
        QMessageBox.critical(None, APP_NAME, f"The dependency catalog could not be read:\n\n{exc}")
        return 1
    # One instance: a second launch (a double-click on the Desktop icon) brings the running window to the front.
    if instance.already_running(INFO.app_id):
        return 0
    if not (data_home() / "applications" / f"{APP_ID}.desktop").is_file():
        app.setDesktopFileName("")              # no menu entry: no desktop file name for Qt to look up
    from .main_window import DependencyWindow
    window = DependencyWindow(dependencies, tools, apps, offer_fix=args.fix)
    window.show()
    server = instance.serve(INFO.app_id, window)  # noqa: F841 (kept alive while the app runs)
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
