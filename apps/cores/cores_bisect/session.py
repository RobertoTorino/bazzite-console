# SPDX-License-Identifier: GPL-3.0-or-later

"""Runs ps5-cores-bisect.sh inside the window, in a pseudo-terminal of its own. sudo needs a terminal to ask for the
password and to remember it, and the script's questions read from it. One shell keeps that terminal for the window's
whole life and runs each script in it, so sudo asks once for a test, not once per run (owner, 23-11-2026: no password
for every attempt). With PS5_GUI=1 the script
prints "@@ <event> <args>" lines for the window beside its text for people (see ev() in the script); its questions
come as "@@ ask <name>" before the prompt. SUDO_PROMPT marks sudo's password prompt, so the window asks for the
password in its own masked field and writes it to the terminal. The password is never stored."""

from __future__ import annotations

import fcntl
import os
import pty
import shlex
import shutil
import signal
import subprocess
import termios

from PyQt6.QtCore import QObject, QSocketNotifier, QTimer, pyqtSignal

PASSWORD_PROMPT = "@@password@@"
# The shell that keeps the terminal: it runs each command line it reads. Its trap keeps it alive on Ctrl+C, while
# the script it runs gets the default handling back, so the script's own INT trap works.
SHELL = 'trap : INT; while IFS= read -r line; do eval "$line"; done'
# A test blocks sleep while it runs (owner, 23-11-2026), with logind's standard lock. It ends with the script, and an
# active session takes it without a password. It waits for the script's own Ctrl+C handling and passes its exit code.
NO_SLEEP = ["systemd-inhibit", "--what=sleep", "--mode=block", "--who=PS5 Core Unlock",
            "--why=A core test is running"]


def _controlling_tty() -> None:  # pragma: no cover - runs in the child
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)


class ScriptSession(QObject):
    line = pyqtSignal(str)          # a line for people
    notice = pyqtSignal(list)       # "@@ load 40 180 61 1500 99" -> ["load", "40", "180", "61", "1500", "99"]
    password = pyqtSignal()         # sudo asks for the password: answer with send() or cancel()
    finished = pyqtSignal(int)      # the exit code

    def __init__(self, script: str, parent: QObject | None = None):
        super().__init__(parent)
        self.script = script
        self.args: list[str] = []
        self._proc: subprocess.Popen | None = None      # the shell
        self._running = False                           # a script runs in it now
        self._fd = -1
        self._notifier: QSocketNotifier | None = None
        self._buf = ""
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._poll)

    @property
    def busy(self) -> bool:
        return self._running

    def start(self, args: list[str], block_sleep: bool = False) -> None:
        """Runs the script with *args*; *block_sleep* keeps the board from sleeping until it ends."""
        if self.busy:
            raise RuntimeError("The script is already running.")
        self.args = list(args)
        if self._proc is None:
            self._open()
        self._running = True
        prefix = NO_SLEEP if block_sleep and shutil.which("systemd-inhibit") else []
        command = shlex.join([*prefix, "bash", self.script, *self.args]) + "; printf '\\n@@ exit %d\\n' \"$?\""
        os.write(self._fd, (command + "\n").encode())

    def close(self) -> None:
        """Ends the shell and its terminal, when the window closes."""
        if self._proc is not None:
            try:
                os.killpg(self._proc.pid, signal.SIGHUP)
            except OSError:
                pass

    def _open(self) -> None:
        master, slave = pty.openpty()
        attrs = termios.tcgetattr(slave)
        attrs[3] &= ~termios.ECHO                       # the answers are not printed back
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        env = dict(os.environ, PS5_GUI="1", NO_COLOR="1", TERM="dumb", SUDO_PROMPT=PASSWORD_PROMPT)
        try:
            self._proc = subprocess.Popen(["bash", "-c", SHELL], stdin=slave, stdout=slave, stderr=slave, env=env,
                                          start_new_session=True, preexec_fn=_controlling_tty, close_fds=True)
        finally:
            os.close(slave)
        self._fd = master
        os.set_blocking(master, False)
        self._buf = ""
        self._notifier = QSocketNotifier(master, QSocketNotifier.Type.Read, self)
        self._notifier.activated.connect(self._read)
        self._timer.start()

    def send(self, text: str) -> None:
        """Writes an answer and Enter to the script's terminal."""
        if self._fd >= 0:
            os.write(self._fd, (text + "\n").encode())

    def cancel(self) -> None:
        """Ctrl+C in the terminal: sudo's prompt gives up, and the script stops as it does on Ctrl+C."""
        if self._fd >= 0:
            os.write(self._fd, b"\x03")

    def stop(self) -> None:
        """Stops the script as Ctrl+C does: it records the attempt as stopped (ABORTED) and says to restart."""
        if self._proc is not None:
            try:
                os.killpg(self._proc.pid, signal.SIGINT)
            except OSError:
                pass

    def _read(self) -> None:
        try:
            data = os.read(self._fd, 65536)
        except BlockingIOError:
            return
        except OSError:                                 # EIO: every writer closed the terminal
            data = b""
        if not data:
            if self._notifier is not None:
                self._notifier.setEnabled(False)
            return
        self._feed(data.decode(errors="replace"))

    def _feed(self, text: str) -> None:
        """Splits the output first and emits after, so a slot that answers right away finds the buffer in order."""
        self._buf += text.replace("\r\n", "\n")
        out: list[tuple[str, object]] = []
        while PASSWORD_PROMPT in self._buf:
            before, self._buf = self._buf.split(PASSWORD_PROMPT, 1)
            out += self._split(before + "\n")[0]
            out.append(("password", None))
        items, self._buf = self._split(self._buf)
        for kind, value in [*out, *items]:
            if kind == "password":
                self.password.emit()
            elif kind == "notice" and value[:1] == ["exit"] and self._running:
                self._running = False
                self.finished.emit(int(value[1]) if len(value) > 1 and value[1].isdigit() else 1)
            elif kind == "notice":
                self.notice.emit(value)
            else:
                self.line.emit(value)

    @staticmethod
    def _split(text: str) -> tuple[list[tuple[str, object]], str]:
        """The whole lines of *text* (a carriage return ends one too) as lines and notices, and the rest."""
        *whole, rest = text.replace("\r", "\n").split("\n")
        items: list[tuple[str, object]] = []
        for raw in whole:
            line = raw.rstrip()
            if line.startswith("@@ "):
                items.append(("notice", line[3:].split()))
            elif line:
                items.append(("line", line))
        return items, rest

    def _poll(self) -> None:
        """The shell ended, by a Ctrl+C that also ended it or with the window: a running script counts as stopped."""
        if self._proc is None or self._proc.poll() is None:
            return
        self._timer.stop()
        self._read_rest()
        code = self._proc.returncode
        self._proc = None
        if self._notifier is not None:
            self._notifier.setEnabled(False)
            self._notifier.deleteLater()
            self._notifier = None
        os.close(self._fd)
        self._fd = -1
        rest = self._buf.strip()
        self._buf = ""
        if rest:
            self._feed(rest + "\n")
        if self._running:
            self._running = False
            self.finished.emit(code if code > 0 else 130)

    def _read_rest(self) -> None:
        while True:
            try:
                data = os.read(self._fd, 65536)
            except OSError:
                return
            if not data:
                return
            self._feed(data.decode(errors="replace"))
