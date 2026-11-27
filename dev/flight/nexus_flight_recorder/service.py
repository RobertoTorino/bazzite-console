# SPDX-License-Identifier: GPL-3.0-or-later
"""The recorder's service: its state, read without a password, and the commands that change it through pkexec
(helper.py as root, the system Python)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bazzite_console_core import sensors

from .helper import LIB, UNIT

HELPER = Path(__file__).resolve().parent / "helper.py"
RECORDER = Path(__file__).resolve().parent / "recorder.py"
SYSTEM_PYTHON = "/usr/bin/python3"


@dataclass
class State:
    installed: bool = False
    running: bool = False
    at_boot: bool = False
    since: str = ""                             # "17:34", "" when not running
    current: bool = True                        # the installed recorder is this checkout's


def _out(argv: list[str]) -> str:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def state(root: Path = Path("/"), out=_out) -> State:
    installed = (root / LIB / "recorder.py").is_file()
    if not installed:
        return State()
    running = out(["systemctl", "is-active", UNIT]) == "active"
    since = ""
    if running:
        stamp = out(["systemctl", "show", "-p", "ActiveEnterTimestamp", "--value", UNIT]).split()
        since = stamp[2][:5] if len(stamp) >= 3 else ""
    try:
        current = (root / LIB / "recorder.py").read_bytes() == RECORDER.read_bytes()
    except OSError:
        current = True
    return State(True, running, out(["systemctl", "is-enabled", UNIT]) == "enabled", since, current)


def command(action: str) -> list[str]:
    extra = [str(RECORDER), sensors.__file__] if action == "install" else []
    return ["pkexec", SYSTEM_PYTHON, "-I", str(HELPER), action, *extra]


def run(action: str) -> str:
    """Runs one helper action; "" when it worked, else why not ("Canceled." when the password was not given)."""
    try:
        done = subprocess.run(command(action), capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        return str(exc)
    if done.returncode in (126, 127):
        return "Canceled."
    try:
        answer = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return (done.stderr or done.stdout).strip() or "The helper gave no answer."
    return "" if answer.get("ok") else str(answer.get("error", "It failed."))
