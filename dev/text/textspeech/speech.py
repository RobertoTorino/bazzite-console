# SPDX-License-Identifier: GPL-3.0-or-later
"""The window's side of the speech engine: engine.py as a process that stays (the model loads once, about a second),
its commands written as JSON lines and its events read as signals. The engine's own output (stderr) goes to this
app's, so it is in the log Nexus Dashboard for PS5 keeps."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from . import engine_setup


class Speech(QObject):
    ready = pyqtSignal(list)                    # the engine loaded its model: the voices it has
    chunk = pyqtSignal(int, int, int, bytes)    # a speak's id, the part's index, the number of parts, 16-bit mono PCM
    done = pyqtSignal(int, float, float)        # a speak's id, the seconds of speech, the seconds it took
    canceled = pyqtSignal(int)
    saved = pyqtSignal(int, str)                # a speak's id, the file written
    failed = pyqtSignal(str)                    # what went wrong, as the engine says it
    stopped = pyqtSignal()                      # the engine ended by itself

    def __init__(self, command: list[str] | None = None, parent: QObject | None = None):
        """*command* starts the engine (the installed one by default; a test gives its own)."""
        super().__init__(parent)
        self.command = command
        self.process: QProcess | None = None
        self.count = 0                          # the last speak's id
        self.is_ready = False

    def running(self) -> bool:
        return self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning

    def start(self) -> None:
        if self.running():
            return
        command = self.command or engine_setup.serve_command()
        process = self.process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.ForwardedErrorChannel)
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(lambda *_: self._ended(process))
        process.errorOccurred.connect(
            lambda error: error == QProcess.ProcessError.FailedToStart and self._ended(process))
        process.start(command[0], command[1:])

    def _send(self, **command) -> None:
        if self.running():
            self.process.write((json.dumps(command) + "\n").encode("utf-8"))

    def speak(self, text: str, voice: str, speed: float) -> int:
        """Ask for *text*; its id comes back with every chunk and with done. A speak before it is given up."""
        self.count += 1
        self._send(cmd="speak", id=self.count, text=text, voice=voice, speed=speed)
        return self.count

    def cancel(self) -> None:
        self._send(cmd="cancel")

    def save(self, ident: int, path: Path) -> None:
        self._send(cmd="save", id=ident, path=str(path))

    def _read(self) -> None:
        process = self.sender()
        while process is not None and process.canReadLine():
            try:
                event = json.loads(bytes(process.readLine()).decode("utf-8"))
                self._handle(event)
            except (ValueError, KeyError, TypeError):
                continue                        # not a line of the protocol

    def _handle(self, event: dict) -> None:
        kind = event["event"]
        if kind == "ready":
            self.is_ready = True
            self.ready.emit(list(event["voices"]))
        elif kind == "chunk":
            self.chunk.emit(event["id"], event["index"], event["count"], base64.b64decode(event["pcm"]))
        elif kind == "done":
            self.done.emit(event["id"], float(event["seconds"]), float(event["took"]))
        elif kind == "canceled":
            self.canceled.emit(event["id"])
        elif kind == "saved":
            self.saved.emit(event["id"], event["path"])
        elif kind == "error":
            self.failed.emit(str(event["message"]))

    def _ended(self, process: QProcess) -> None:
        if process is not self.process:
            return                              # closed by close(): nothing to say
        self.process = None
        self.is_ready = False
        process.deleteLater()
        self.stopped.emit()

    def close(self) -> None:
        """Ask the engine to quit and wait a moment; kill it when it does not."""
        process, self.process, self.is_ready = self.process, None, False
        if process is None:
            return
        if process.state() != QProcess.ProcessState.NotRunning:
            process.write(b'{"cmd": "quit"}\n')
            process.closeWriteChannel()
            if not process.waitForFinished(2000):
                process.kill()
                process.waitForFinished(1000)
        process.deleteLater()


__all__ = ["Speech"]
