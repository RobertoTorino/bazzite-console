# SPDX-License-Identifier: GPL-3.0-or-later
"""While a core test runs, an autostart entry opens the window with --resume after a login; it goes again on its own."""

from __future__ import annotations

import shlex

from cores_bisect import resume


def test_arm_and_disarm(home):
    assert not resume.armed()
    resume.arm()
    path = home / ".config" / "autostart" / "ps5-core-unlock-resume.desktop"
    assert resume.armed() and resume.entry_path() == path
    exec_line = next(line for line in path.read_text().splitlines() if line.startswith("Exec="))
    assert shlex.split(exec_line[5:])[-1] == "--resume"
    resume.disarm()
    assert not path.exists()
    resume.disarm()                                     # nothing there: no error


def test_the_entry_opens_the_same_code_and_scripts(home):
    """Installed or from a checkout: this Python, this package's folder and the window's own scripts."""
    from cores_bisect import ROOT
    resume.arm("/x/ps5-cores-bisect.sh", "/x/ps5-cores-unlock.sh")
    lines = resume.entry_path().read_text().splitlines()
    argv = shlex.split(next(line for line in lines if line.startswith("Exec="))[5:])
    assert argv == [resume.sys.executable, "-m", "cores_bisect", "--script", "/x/ps5-cores-bisect.sh",
                    "--unlock-script", "/x/ps5-cores-unlock.sh", "--resume"]
    assert f"Path={ROOT}" in lines


def test_restart_reports_when_it_may_not(monkeypatch):
    calls = []

    class Done:
        def __init__(self, code):
            self.returncode = code
    monkeypatch.setattr(resume.subprocess, "run", lambda argv, **k: (calls.append(argv), Done(1))[1])
    assert resume.restart() is False
    assert calls == [["systemctl", "reboot", "--no-ask-password"], ["sudo", "-n", "systemctl", "reboot"]]
