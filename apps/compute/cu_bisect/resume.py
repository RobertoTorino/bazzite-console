# SPDX-License-Identifier: GPL-3.0-or-later

"""Going on after a restart: while a CU test runs, an autostart entry opens the window again after every login, with
--resume, and the window then goes on with the next attempt. The entry goes when the test is done, paused or
started over, and with the app's uninstall. restart() restarts the board as the script's do_reboot does: no
password dialog, sudo -n as the fallback."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

ENTRY_NAME = "ps5-cu-tools-resume.desktop"


def entry_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "autostart" / ENTRY_NAME


def launcher(script: str = "", unlock_script: str = "") -> list[str]:
    """This Python with this package and these scripts: the window that armed the entry opens again, installed or
    from a checkout. The entry's Path= is the package's folder, so -m finds it."""
    from . import ROOT
    return [sys.executable, "-m", "cu_bisect", "--script", script or str(ROOT / "ps5-cu-bisect.sh"),
            "--unlock-script", unlock_script or str(ROOT / "ps5-cu-unlock.sh")]


def armed() -> bool:
    return entry_path().is_file()


def arm(script: str = "", unlock_script: str = "") -> None:
    from . import ROOT
    path = entry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[Desktop Entry]\nType=Application\nName=PS5 CU Unlock, going on with the CU test\n"
                    f"Exec={shlex.join([*launcher(script, unlock_script), '--resume'])}\nPath={ROOT}\n"
                    "X-GNOME-Autostart-enabled=true\n")


def disarm() -> None:
    entry_path().unlink(missing_ok=True)


def restart() -> bool:
    """Restarts the board. False when neither systemctl nor sudo -n may."""
    for argv in (["systemctl", "reboot", "--no-ask-password"], ["sudo", "-n", "systemctl", "reboot"]):
        try:
            if subprocess.run(argv, capture_output=True).returncode == 0:
                return True
        except OSError:
            continue
    return False
