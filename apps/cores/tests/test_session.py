# SPDX-License-Identifier: GPL-3.0-or-later
"""The window runs the script in a terminal of its own: lines for people and "@@" events arrive apart, a carriage
return ends a line, the answers reach the script's questions, sudo's prompt asks the window for the password, and
the exit code comes back."""

from __future__ import annotations

import sys

import pytest
from PyQt6.QtCore import QEventLoop, QTimer

from cores_bisect.session import ScriptSession

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs a pseudo-terminal and bash")

FAKE = r"""
echo "plain line"
printf 'progress 1\rprogress 2\n'
echo "@@ phase load"
echo "@@ ask crash" >&2
echo "Did the system freeze? [Y/n]"
read -r a
echo "answer=$a"
printf '%s' "$SUDO_PROMPT"
read -rs pw
echo "password=$pw"
[ -t 0 ] && echo "has a terminal"
exit 3
"""


def _run(tmp_path, answers):
    script = tmp_path / "fake.sh"
    script.write_text(FAKE)
    session = ScriptSession(str(script))
    lines, events, codes = [], [], []
    session.line.connect(lines.append)
    session.notice.connect(events.append)
    session.notice.connect(lambda e: e[0] == "ask" and session.send(answers["ask"]))
    session.password.connect(lambda: session.send(answers["password"]))
    loop = QEventLoop()
    session.finished.connect(lambda code: (codes.append(code), loop.quit()))
    session.start([])
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    return lines, events, codes, session


def test_a_session(qapp, tmp_path):
    lines, events, codes, session = _run(tmp_path, {"ask": "n", "password": "secret"})
    assert codes == [3] and not session.busy
    assert "plain line" in lines and "progress 1" in lines and "progress 2" in lines
    assert ["phase", "load"] in events and ["ask", "crash"] in events
    assert "answer=n" in lines and "password=secret" in lines and "has a terminal" in lines
    assert not any("secret" in line and "password=" not in line for line in lines)   # no echo of the answer
    session.close()


def test_one_terminal_for_every_run(qapp, tmp_path):
    """The second run uses the same shell and terminal, so sudo, which remembers per terminal, asks only once."""
    script = tmp_path / "tty.sh"
    script.write_text('echo "tty=$(tty)"\nexit "${1:-0}"\n')
    session = ScriptSession(str(script))
    lines, codes = [], []
    session.line.connect(lines.append)
    loop = QEventLoop()
    session.finished.connect(lambda code: (codes.append(code), loop.quit()))
    session.start(["0"])
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    shell = session._proc.pid
    session.start(["4"])
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    ttys = [line for line in lines if line.startswith("tty=")]
    assert codes == [0, 4] and len(ttys) == 2 and ttys[0] == ttys[1] and session._proc.pid == shell
    session.close()


def test_stop_ends_the_script_and_keeps_the_terminal(qapp, tmp_path):
    script = tmp_path / "slow.sh"
    script.write_text("trap 'echo stopped; exit 130' INT\necho started\nsleep 30 & wait\n")
    session = ScriptSession(str(script))
    lines, codes = [], []
    session.line.connect(lines.append)
    loop = QEventLoop()
    session.line.connect(lambda line: line == "started" and session.stop())
    session.finished.connect(lambda code: (codes.append(code), loop.quit()))
    session.start([])
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    assert codes == [130] and "stopped" in lines and session._proc is not None and session._proc.poll() is None
    session.close()


def test_a_test_run_blocks_sleep_until_it_ends(qapp, tmp_path, monkeypatch):
    """With block_sleep the script runs under systemd-inhibit; its exit code comes through."""
    from cores_bisect import session as session_module
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "systemd-inhibit").write_text('#!/bin/sh\necho "inhibit: $1 $2"\nshift 4\nexec "$@"\n')
    (fake / "systemd-inhibit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake}:{session_module.os.environ['PATH']}")
    script = tmp_path / "x.sh"
    script.write_text("echo ran\nexit 5\n")
    session = ScriptSession(str(script))
    lines, codes = [], []
    session.line.connect(lines.append)
    loop = QEventLoop()
    session.finished.connect(lambda code: (codes.append(code), loop.quit()))
    session.start([], block_sleep=True)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    assert lines[:2] == ["inhibit: --what=sleep --mode=block", "ran"] and codes == [5]
    session.close()
