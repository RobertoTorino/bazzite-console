# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point: python -m nexus_garbage_remover [--remind] (run.sh starts it with the checkout's dev venv).

--remind shows no window: it measures the garbage and, when there is much of it, says so in a desktop notification
with a button that opens the app. The hourly systemd user timer that install.sh writes runs it."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from bazzite_console_core import __version__ as CORE_VERSION, instance
from bazzite_console_core.nexus import checkout_stamp

from . import APP_ID, APP_NAME, CHECKOUT, INFO, LOGO_PATH, ROOT
from .garbage import find, notify_text, read_state, should_notify, write_state


def notify(text: str) -> str:
    """A desktop notification with an Open button; the button's key when it was clicked, else ""."""
    try:
        done = subprocess.run(["notify-send", "--app-name", APP_NAME, "--icon", str(LOGO_PATH), "--wait",
                               "--action=open=Open", APP_NAME, text], capture_output=True, text=True, timeout=3600)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (done.stdout or "").strip()


def remind() -> int:
    """The hourly check: a notification when there is much garbage; its Open button starts the app."""
    found = find()
    total = sum(place.size for place in found)
    now = time.time()
    if not should_notify(total, now, read_state()):
        return 0
    write_state(total, now)
    text = notify_text(found)
    print(text)
    if notify(text) == "open":
        subprocess.Popen([str(ROOT / "run.sh")], start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


def main() -> int:
    stamp = checkout_stamp(CHECKOUT)  # never released: the commit says which code runs
    parser = argparse.ArgumentParser(prog="nexus_garbage_remover", description=f"{APP_NAME} {stamp}".strip())
    parser.add_argument("--version", action="version", version=f"%(prog)s {stamp} (core {CORE_VERSION})")
    parser.add_argument("--remind", action="store_true", help="no window: a desktop notification when there is much "
                                                              "garbage (the hourly timer runs this)")
    args, qt_args = parser.parse_known_args()
    if args.remind:
        return remind()

    from bazzite_console_core.app import create_app, exec_app
    from bazzite_console_core.nexus import NEXUS
    from bazzite_console_core.platform import data_home

    app = create_app(INFO, qt_args, theme=NEXUS)           # Nexus's design, not a suite's theme
    if instance.already_running(INFO.app_id):              # a second launch brings the running window to the front
        return 0
    if not (data_home() / "applications" / f"{APP_ID}.desktop").is_file():
        app.setDesktopFileName("")              # no menu entry: no desktop file name for Qt to look up
    from .main_window import MainWindow
    window = MainWindow()
    window.show()
    server = instance.serve(INFO.app_id, window)  # noqa: F841 (kept alive while the app runs)
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
