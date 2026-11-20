# SPDX-License-Identifier: GPL-3.0-or-later
"""Voice from a text: Nexus TTS found in the checkout, its voices listed, the text spoken and saved to the
target, a failure shown, and what the dialog says without Nexus TTS or without its engine."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtWidgets import QDialog

from remix_studio import CHECKOUT
from remix_studio.speak_dialog import NO_TEXT, NO_TEXT_APP, NOT_SET_UP, SpeakDialog, text_to_speech

VOICES = ["af_heart", "bf_emma", "bm_george"]       # the last one is never listed


class FakeSpeech(QObject):
    """The engine as the dialog sees it: records what is asked, and the test emits what comes back."""

    ready = pyqtSignal(list)
    done = pyqtSignal(int, float, float)
    saved = pyqtSignal(int, str)
    failed = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_ready = False
        self.asked: list[tuple] = []

    def start(self) -> None:
        self.asked.append(("start",))

    def load(self) -> None:
        self.is_ready = True
        self.ready.emit(list(VOICES))

    def speak(self, text: str, voice: str, speed: float) -> int:
        self.asked.append(("speak", text, voice, speed))
        return 7

    def save(self, ident: int, path) -> None:
        self.asked.append(("save", ident, path))

    def close(self) -> None:
        self.asked.append(("close",))


def settings_in(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "studio.ini"), QSettings.Format.IniFormat)


def test_text_to_speech_is_found_in_the_checkout_and_missed_elsewhere(tmp_path):
    parts = text_to_speech(CHECKOUT)
    assert parts.engine.DEFAULT_VOICE == "af_heart" and parts.Speech.__name__ == "Speech"
    assert parts.engine_setup.ENGINE_DIR.name == "nexus-text-to-speech"
    assert text_to_speech(tmp_path) is None


def test_a_text_is_spoken_saved_and_the_dialog_accepts(qapp, tmp_path):
    speech, target = FakeSpeech(), tmp_path / "cache" / "voice.wav"
    dialog = SpeakDialog(target, settings_in(tmp_path), speech=speech, installed=True)
    assert speech.asked == [("start",)] and not dialog.make_button.isEnabled()
    assert dialog.message.text() == "The speech engine is loading its model…"

    speech.load()
    assert [dialog.voice_box.itemData(i) for i in range(dialog.voice_box.count())] == ["af_heart", "bf_emma"]
    assert dialog.make_button.isEnabled() and dialog.message.text() == ""
    assert dialog.speed_slider.value() == 85 and dialog.speed_value.text() == "0.85"

    dialog.make()
    assert dialog.message.text() == NO_TEXT and len(speech.asked) == 1
    dialog.text_edit.setPlainText("  Good evening.  ")
    dialog.voice_box.setCurrentIndex(1)
    dialog.speed_slider.setValue(110)
    dialog.make()
    assert speech.asked[-1] == ("speak", "Good evening.", "bf_emma", 1.1)
    assert not dialog.make_button.isEnabled() and dialog.message.text() == "Making the voice…"

    speech.done.emit(3, 1.0, 0.2)                           # of another speak: nothing
    assert speech.asked[-1][0] == "speak"
    speech.done.emit(7, 1.0, 0.2)
    assert speech.asked[-1] == ("save", 7, target) and target.parent.is_dir()
    speech.saved.emit(7, str(target))
    assert dialog.result() == QDialog.DialogCode.Accepted and speech.asked[-1] == ("close",)

    again = SpeakDialog(target, settings_in(tmp_path), speech=FakeSpeech(), installed=True)
    assert again.text_edit.toPlainText() == "Good evening." and again.speed_slider.value() == 110
    again.speech.load()
    assert again.voice_box.currentData() == "bf_emma"
    again.reject()


def test_a_failure_is_shown_and_make_works_again(qapp, tmp_path):
    speech = FakeSpeech()
    dialog = SpeakDialog(tmp_path / "voice.wav", speech=speech, installed=True)
    speech.load()
    dialog.text_edit.setPlainText("Привет")
    dialog.make()
    speech.failed.emit("Only English text can be spoken. This text has letters of another script.")
    assert dialog.message.text().startswith("Only English text") and dialog.make_button.isEnabled()
    speech.done.emit(7, 1.0, 0.2)                           # the failed one is over
    assert speech.asked[-1][0] == "speak"

    speech.is_ready = False
    speech.stopped.emit()
    assert dialog.message.text() == "The speech engine stopped." and not dialog.make_button.isEnabled()
    dialog.reject()


def test_without_the_engine_the_dialog_says_where_to_set_it_up(qapp, tmp_path):
    speech = FakeSpeech()
    dialog = SpeakDialog(tmp_path / "voice.wav", speech=speech, installed=False)
    assert dialog.message.text() == NOT_SET_UP and not dialog.make_button.isEnabled() and speech.asked == []
    dialog.reject()


def test_without_text_to_speech_the_dialog_says_so(qapp, tmp_path, monkeypatch):
    from remix_studio import speak_dialog
    monkeypatch.setattr(speak_dialog, "text_to_speech", lambda: None)
    dialog = SpeakDialog(tmp_path / "voice.wav")
    assert dialog.message.text() == NO_TEXT_APP and not dialog.make_button.isEnabled() and dialog.speech is None
    dialog.reject()
