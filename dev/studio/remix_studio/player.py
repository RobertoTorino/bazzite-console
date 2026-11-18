# SPDX-License-Identifier: GPL-3.0-or-later
"""Playing a mix or a background: its samples go to the audio output (Qt's QAudioSink, 16-bit stereo at the mix's
rate) as the output has room for them. Without an audio output, or without Qt's multimedia, nothing plays and
available() says so; the mix can still be saved."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .pad import RATE


class Player(QObject):
    """play(pcm) plays a sound from its start, ending the one before (finished comes once the last of it played);
    stop() ends it at once."""

    finished = pyqtSignal()

    def __init__(self, rate: int = RATE, parent: QObject | None = None):
        super().__init__(parent)
        self.rate = rate
        self.sink = None
        self.device = None                      # the sink's input
        self.waiting = bytearray()              # what the sink had no room for yet
        self.ended = False
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._pump)

    def available(self) -> bool:
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            return bool(QMediaDevices.audioOutputs())
        except Exception:  # noqa: BLE001  (any failure of the multimedia stack: no sound)
            return False

    def output_name(self) -> str:
        """The default output's name, "" without one."""
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            return QMediaDevices.defaultAudioOutput().description() if self.available() else ""
        except Exception:  # noqa: BLE001
            return ""

    def playing(self) -> bool:
        return self.sink is not None

    def start(self) -> bool:
        """Open the output for a new sound, ending the one before; False when nothing can play."""
        self.stop()
        if not self.available():
            return False
        try:
            from PyQt6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
            wanted = QAudioFormat()
            wanted.setSampleRate(self.rate)
            wanted.setChannelCount(2)
            wanted.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            self.sink = QAudioSink(QMediaDevices.defaultAudioOutput(), wanted, self)
            self.device = self.sink.start()
        except Exception:  # noqa: BLE001  (a sound that cannot play never gets in the way)
            self.sink = self.device = None
            return False
        self.ended = False
        self.timer.start()
        return True

    def feed(self, pcm: bytes) -> None:
        if self.sink is not None:
            self.waiting += pcm
            self._pump()

    def end(self) -> None:
        self.ended = True
        if self.sink is None:
            self.finished.emit()

    def _pump(self) -> None:
        """Give the sink what it has room for; after the last of it, wait until it played."""
        if self.sink is None or self.device is None:
            return
        from PyQt6.QtMultimedia import QAudio
        room = self.sink.bytesFree() & ~3       # whole frames
        if self.waiting and room > 0:
            written = self.device.write(bytes(self.waiting[:room]))
            if written > 0:
                del self.waiting[:written]
        if self.ended and not self.waiting and self.sink.state() == QAudio.State.IdleState:
            self.stop()
            self.finished.emit()

    def play(self, pcm: bytes) -> bool:
        """Play *pcm* (16-bit stereo) from its start; False when nothing can play."""
        if not self.start():
            return False
        self.feed(pcm)
        self.end()
        return True

    def stop(self) -> None:
        self.timer.stop()
        self.waiting.clear()
        sink, self.sink, self.device = self.sink, None, None
        if sink is not None:
            sink.stop()
            sink.deleteLater()

    def close(self) -> None:
        self.stop()


__all__ = ["Player"]
