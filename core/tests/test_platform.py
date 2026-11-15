# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from bazzite_console_core import platform, steam


def _working_bash() -> bool:
    """A bash that runs a command."""
    if shutil.which("bash") is None:
        return False
    try:
        result = subprocess.run(["bash", "-c", "echo ok"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "ok"


NEEDS_BASH = pytest.mark.skipif(not _working_bash(), reason="needs a bash that runs")


def test_terminal_command_plain_keeps_window_open():
    assert platform.terminal_command("bash x.sh") == "bash x.sh; echo; read -rp 'Press Enter to close... ' _"
    assert platform.terminal_command("bash x.sh", keep_open=False) == "bash x.sh"


def test_terminal_command_exit_file_covers_whole_command():
    line = platform.terminal_command("cd /a && bash x.sh", keep_open=False, exit_file=PurePosixPath("/tmp/st 1"))
    assert line == "( cd /a && bash x.sh ); echo $? > '/tmp/st 1'"


def test_terminal_command_on_error_pauses_only_after_a_failure():
    """keep_open="on_error" (owner, 26-10-2026): the window of a command that ended well closes by itself, one with
    an error waits for Enter; the exit file gets the status either way."""
    pause = "echo; read -rp 'Press Enter to close... ' _"
    line = platform.terminal_command("cd /a && bash x.sh", keep_open="on_error", exit_file=PurePosixPath("/tmp/st 1"))
    assert line == "( cd /a && bash x.sh ); s=$?; echo $s > '/tmp/st 1'; [ \"$s\" = 0 ] || { " + pause + "; }"
    assert platform.terminal_command("bash x.sh", keep_open="on_error") == \
        "( bash x.sh ); s=$?; [ \"$s\" = 0 ] || { " + pause + "; }"


@NEEDS_BASH
@pytest.mark.parametrize("command, status, paused", [("true", "0", False), ("true && false", "1", True),
                                                      ("exit 3", "3", True)])
def test_on_error_runs_the_pause_only_on_a_failure(tmp_path, command, status, paused):
    exit_file = tmp_path / "status"
    line = platform.terminal_command(command, keep_open="on_error", exit_file=Path(exit_file.as_posix()))
    # Without a terminal "read" shows no prompt and ends at once; the pause's echo leaves its blank line.
    result = subprocess.run(["bash", "-c", line.replace(str(exit_file.as_posix()), "status")], cwd=tmp_path,
                            check=False, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert (tmp_path / "status").read_text().strip() == status
    assert (result.stdout == "\n") is paused


@NEEDS_BASH
@pytest.mark.parametrize("command, status", [("true", "0"), ("true && false", "1"), ("exit 3", "3")])
def test_exit_file_gets_the_status(tmp_path, command, status):
    exit_file = tmp_path / "status"
    line = platform.terminal_command(command, keep_open=False, exit_file=Path(exit_file.as_posix()))
    subprocess.run(["bash", "-c", line.replace(str(exit_file.as_posix()), "status")], cwd=tmp_path, check=False)
    assert (tmp_path / "status").read_text().strip() == status


def test_no_terminal_raises(monkeypatch):
    monkeypatch.delenv("TERMINAL", raising=False)
    monkeypatch.setattr(platform.shutil, "which", lambda name: None)
    assert platform.find_terminal() is None
    with pytest.raises(RuntimeError, match="No terminal emulator found"):
        platform.launch_in_terminal("true")


def test_terminal_preference_and_argv(monkeypatch):
    started = []
    monkeypatch.delenv("TERMINAL", raising=False)
    monkeypatch.setattr(platform.shutil, "which", lambda name: f"/usr/bin/{name}" if name in ("ptyxis", "xterm") else None)
    monkeypatch.setattr(platform.subprocess, "Popen", lambda argv, **kw: started.append((argv, kw)))
    platform.launch_in_terminal("bash x.sh", keep_open=False)
    argv, kw = started[0]
    assert argv == ["ptyxis", "--", "bash", "-lc", "bash x.sh"]           # ptyxis comes before xterm
    assert kw["start_new_session"] is True


def test_expand_and_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert platform.data_home() == tmp_path / "data"
    monkeypatch.setenv("PS5_X", "abc")
    assert platform.expand("$PS5_X/y").as_posix().endswith("abc/y")


def test_show_in_folder(monkeypatch, tmp_path):
    """A saved screenshot shows itself (owner, 06-11-2026): the file manager over D-Bus, else the folder with
    xdg-open."""
    shot = tmp_path / "it's a shot.png"
    ran, opened = [], []

    class Done:
        returncode = 0
    monkeypatch.setattr(platform.shutil, "which", lambda name: "/usr/bin/gdbus" if name == "gdbus" else None)
    monkeypatch.setattr(platform.subprocess, "run", lambda command, **kw: ran.append(command) or Done())
    monkeypatch.setattr(platform, "xdg_open", lambda target: opened.append(target) or True)
    assert platform.show_in_folder(shot) and opened == []
    assert ran[0][-2] == f"['{shot.resolve().as_uri()}']" and "%27" in ran[0][-2]   # the quote cannot end the list
    Done.returncode = 1                                                         # no FileManager1 on the bus
    assert platform.show_in_folder(shot) and opened == [shot.parent]


def test_private_writes_the_home_folder_as_a_tilde(monkeypatch):
    """The privacy rule (owner, 29-10-2026: a folder on the screen showed the user's name): the home folder as ~,
    wherever it is in the text."""
    monkeypatch.setattr(Path, "home", lambda: Path("/home/someone"))
    assert platform.private("/home/someone/Games and /home/someone2") == "~/Games and /home/someone2"
