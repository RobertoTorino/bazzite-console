# SPDX-License-Identifier: GPL-3.0-or-later
"""A voice track from a text: a small dialog that has Nexus TTS's engine speak a text and write it as a sound
file, which the window then takes as its voice. The engine is Nexus TTS's own (dev/text in this checkout, its
venv and model outside it); nothing of it is copied here. Where Nexus TTS or its engine is not there, the dialog
says so and makes nothing."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bazzite_console_core.widgets import accent_button, hint_label

from . import CHECKOUT

TEXT_KEY = "speak/text"                 # the settings
VOICE_KEY = "speak/voice"
SPEED_KEY = "speak/speed"
NO_TEXT_APP = "Nexus TTS is not in this checkout, so a text cannot be spoken here. Open a sound file instead."
NOT_SET_UP = ("The speech engine is not on this machine yet. Open Nexus TTS from Nexus Dashboard and set it up "
              "there. Then come back.")
NO_TEXT = "Type a text first."


def text_to_speech(checkout: Path = CHECKOUT) -> SimpleNamespace | None:
    """Nexus TTS's engine, its setup and its Speech from *checkout* (dev/text), or None without it."""
    folder = checkout / "dev" / "text"
    if not (folder / "textspeech" / "engine.py").is_file():
        return None
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    try:
        from textspeech import engine, engine_setup
        from textspeech.speech import Speech
    except ImportError:
        return None
    return SimpleNamespace(engine=engine, engine_setup=engine_setup, Speech=Speech)


class SpeakDialog(QDialog):
    """Accepted once *target* holds the spoken text."""

    def __init__(self, target: Path, settings: QSettings | None = None, parent: QWidget | None = None,
                 parts: SimpleNamespace | None = None, speech=None, installed: bool | None = None):
        """*parts* is Nexus TTS (found in the checkout by default), *speech* its engine and *installed* whether
        that engine is on the machine; a test passes its own."""
        super().__init__(parent)
        self.setWindowTitle("Voice from a text")
        self.resize(640, 420)
        self.target = target
        self.settings = settings
        self.parts = parts if parts is not None else text_to_speech()
        self.speech = speech
        self.making: int | None = None          # the id of the speak the engine is making

        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type or paste the English text to speak")
        self.text_edit.setTabChangesFocus(True)
        layout.addWidget(self.text_edit, 1)
        row = QHBoxLayout()
        self.voice_box = QComboBox()
        self.voice_box.setToolTip("The voice, American or British English")
        self.voice_box.setMinimumContentsLength(26)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setFixedWidth(150)
        self.speed_slider.setToolTip("How fast the voice speaks. 1.00 is the voice's own pace")
        self.speed_value = QLabel()
        self.speed_value.setMinimumWidth(36)
        self.speed_slider.valueChanged.connect(lambda value: self.speed_value.setText(f"{value / 100:.2f}"))
        self.make_button = accent_button("Make the voice", "Speak the text and use it as the voice track")
        self.make_button.clicked.connect(self.make)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        row.addWidget(QLabel("Voice:"))
        row.addWidget(self.voice_box)
        row.addWidget(QLabel("Speed:"))
        row.addWidget(self.speed_slider)
        row.addWidget(self.speed_value)
        row.addStretch(1)
        row.addWidget(self.make_button)
        row.addWidget(self.cancel_button)
        layout.addLayout(row)
        self.message = hint_label("")
        layout.addWidget(self.message)

        self.make_button.setEnabled(False)
        self.voice_box.setEnabled(False)
        if self.parts is None:
            self.message.setText(NO_TEXT_APP)
            return
        engine = self.parts.engine
        self.speed_slider.setRange(round(engine.SPEED_RANGE[0] * 100), round(engine.SPEED_RANGE[1] * 100))
        text, speed = "", engine.DEFAULT_SPEED
        if settings is not None:
            text = str(settings.value(TEXT_KEY, text))
            try:
                speed = float(settings.value(SPEED_KEY, speed))
            except (TypeError, ValueError):
                pass
        self.text_edit.setPlainText(text)
        self.speed_slider.setValue(round(speed * 100))
        if not (self.parts.engine_setup.installed() if installed is None else installed):
            self.message.setText(NOT_SET_UP)
            return
        if self.speech is None:
            self.speech = self.parts.Speech(parent=self)
        self.speech.ready.connect(self.engine_ready)
        self.speech.done.connect(self.on_done)
        self.speech.saved.connect(self.on_saved)
        self.speech.failed.connect(self.on_failed)
        self.speech.stopped.connect(lambda: self.on_failed("The speech engine stopped."))
        self.message.setText("The speech engine is loading its model…")
        self.speech.start()

    def engine_ready(self, voices: list) -> None:
        engine = self.parts.engine
        wanted = engine.DEFAULT_VOICE
        if self.settings is not None:
            wanted = str(self.settings.value(VOICE_KEY, wanted))
        self.voice_box.clear()
        for voice in engine.offered_voices([str(v) for v in voices]):
            self.voice_box.addItem(engine.voice_label(voice), voice)
        self.voice_box.setCurrentIndex(max(self.voice_box.findData(wanted),
                                           self.voice_box.findData(engine.DEFAULT_VOICE), 0))
        self.voice_box.setEnabled(True)
        self.make_button.setEnabled(True)
        self.message.setText("")

    def make(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.message.setText(NO_TEXT)
            return
        voice, speed = str(self.voice_box.currentData() or ""), self.speed_slider.value() / 100
        if self.settings is not None:
            self.settings.setValue(TEXT_KEY, text)
            self.settings.setValue(VOICE_KEY, voice)
            self.settings.setValue(SPEED_KEY, speed)
        self.make_button.setEnabled(False)
        self.message.setText("Making the voice…")
        self.making = self.speech.speak(text, voice, speed)

    def on_done(self, ident: int, _seconds: float, _took: float) -> None:
        if ident == self.making:
            self.target.parent.mkdir(parents=True, exist_ok=True)
            self.speech.save(ident, self.target)

    def on_saved(self, ident: int, _path: str) -> None:
        if ident == self.making:
            self.accept()

    def on_failed(self, message: str) -> None:
        self.making = None
        self.message.setText(message)
        self.make_button.setEnabled(self.speech is not None and self.speech.is_ready)

    def done(self, result: int) -> None:
        if self.speech is not None:
            self.speech.close()
        super().done(result)


__all__ = ["NOT_SET_UP", "NO_TEXT", "NO_TEXT_APP", "SPEED_KEY", "TEXT_KEY", "VOICE_KEY", "SpeakDialog",
           "text_to_speech"]
