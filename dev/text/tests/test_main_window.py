# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: the voices the engine has, Speak plays the parts as they arrive, Stop, Save as with and without
making the speech again, what a failure and a stopped engine show, the settings, and Set up the speech engine where
the engine is not on the machine; the icons are Nexus's."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QFileDialog

from textspeech import APP_NAME, LOGO_PATH, ROOT, engine_setup, main_window
from textspeech.main_window import NO_TEXT, MainWindow

VOICES = ["af_heart", "bf_emma", "af_bella", "bf_lily", "bm_george", "ef_dora"]    # the last two are never listed


class FakeSpeech(QObject):
    """The engine as the window sees it: records what is asked, and the test emits what comes back."""

    ready = pyqtSignal(list)
    chunk = pyqtSignal(int, int, int, bytes)
    done = pyqtSignal(int, float, float)
    canceled = pyqtSignal(int)
    saved = pyqtSignal(int, str)
    failed = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.count = 0
        self.is_ready = False
        self.started = 0
        self.alive = False
        self.asked: list[tuple] = []

    def running(self) -> bool:
        return self.alive

    def start(self) -> None:
        self.started += 1
        self.alive = True

    def load(self) -> None:
        self.is_ready = True
        self.ready.emit(list(VOICES))

    def die(self) -> None:
        self.alive = self.is_ready = False
        self.stopped.emit()

    def speak(self, text: str, voice: str, speed: float) -> int:
        self.count += 1
        self.asked.append(("speak", self.count, text, voice, speed))
        return self.count

    def cancel(self) -> None:
        self.asked.append(("cancel",))

    def save(self, ident: int, path: Path) -> None:
        self.asked.append(("save", ident, Path(path)))

    def close(self) -> None:
        self.asked.append(("close",))


class FakePlayer(QObject):
    finished = pyqtSignal()

    def __init__(self, output: str = "Test output"):
        super().__init__()
        self.output = output
        self.open = False
        self.calls: list = []

    def output_name(self) -> str:
        return self.output

    def playing(self) -> bool:
        return self.open

    def start(self) -> bool:
        self.calls.append("start")
        self.open = True
        return True

    def feed(self, pcm: bytes) -> None:
        self.calls.append(pcm)

    def end(self) -> None:
        self.calls.append("end")

    def play_out(self) -> None:
        self.open = False
        self.finished.emit()

    def stop(self) -> None:
        self.calls.append("stop")
        self.open = False

    def close(self) -> None:
        self.calls.append("close")


@pytest.fixture
def installed(monkeypatch):
    monkeypatch.setattr(engine_setup, "installed", lambda root=None: True)


def _window(settings: QSettings | None = None, tmp_path: Path | None = None) -> MainWindow:
    """A window on a loaded engine."""
    window = MainWindow(settings=settings, speech=FakeSpeech(), player=FakePlayer(),
                        engine_dir=tmp_path or Path("/nonexistent/engine"))
    window.speech.load()
    return window


def test_the_info_text_links_to_the_apps_place_in_the_wiki():
    assert main_window.WIKI.endswith("/development/dashboard/#nexus-tts")
    assert "//development" not in main_window.WIKI
    assert f"<a href='{main_window.WIKI}'>the wiki</a>" in main_window.ABOUT


def test_the_icons_are_nexus_at_512_and_128_px():
    assert LOGO_PATH == ROOT / "images" / "nexus-text-to-speech.webp"
    assert QImage(str(LOGO_PATH)).size().width() == 512
    assert QImage(str(LOGO_PATH.with_name("nexus-text-to-speech-128.png"))).size().width() == 128


def test_the_window_opens_on_the_engine_and_lists_its_voices(qapp, installed):
    window = MainWindow(speech=FakeSpeech(), player=FakePlayer())
    assert window.windowTitle() == APP_NAME == "Nexus TTS"
    assert window.pages.currentIndex() == 0 and window.speech.started == 1
    assert window.state.text() == "Starting" and not window.speak_button.isEnabled()
    assert not window.voice_box.isEnabled() and not window.save_button.isEnabled()

    window.speech.load()
    assert window.state.text() == "Ready" and window.statusBar().currentMessage() == "Playing on: Test output."
    labels = [window.voice_box.itemText(i) for i in range(window.voice_box.count())]
    assert labels == ["Bella · American English", "Heart · American English", "Emma · British English",
                      "Lily · British English"]
    assert window.voice() == "af_heart" and window.speed() == 0.85 and window.speed_value.text() == "0.85"
    assert window.text() == "Good morning!"
    assert window.speak_button.isEnabled() and window.save_button.isEnabled() and not window.stop_button.isEnabled()
    window.close()
    assert window.speech.asked == [("close",)] and window.player.calls[-1] == "close"


def test_without_an_audio_output_the_window_says_so(qapp, installed):
    window = MainWindow(speech=FakeSpeech(), player=FakePlayer(output=""))
    window.speech.load()
    assert window.statusBar().currentMessage() == main_window.NO_OUTPUT
    window.close()


def test_speak_plays_the_parts_as_they_arrive(qapp, installed):
    window = _window()
    window.text_edit.setPlainText("  One. Two.  ")
    window.speed_slider.setValue(120)

    assert window.speak()
    assert window.speech.asked == [("speak", 1, "One. Two.", "af_heart", 1.2)]
    assert window.player.calls == ["stop", "start"] and window.state.text() == "Speaking"
    assert window.stop_button.isEnabled() and window.busy()

    window.speech.chunk.emit(1, 0, 2, b"one")
    assert window.statusBar().currentMessage() == "Sentence 1 of 2…"
    window.speech.chunk.emit(9, 0, 1, b"stale")             # of a speak that was given up: not played
    window.speech.chunk.emit(1, 1, 2, b"two")
    window.speech.done.emit(1, 3.44, 1.21)
    assert window.player.calls == ["stop", "start", b"one", b"two", "end"]
    assert window.statusBar().currentMessage() == "3.4 s of speech, made in 1.2 s."
    assert not window.busy() and window.state.text() == "Speaking" and window.stop_button.isEnabled()   # still heard

    window.player.play_out()
    assert window.state.text() == "Ready" and not window.stop_button.isEnabled()
    window.close()


def test_nothing_is_spoken_without_a_text(qapp, installed):
    window = _window()
    window.text_edit.setPlainText("   \n ")
    assert not window.speak() and window.save(Path("/tmp/x.ogg")) is None
    assert window.speech.asked == [] and window.statusBar().currentMessage() == NO_TEXT
    window.close()


def test_a_text_in_another_script_is_not_spoken_or_saved(qapp, installed, tmp_path):
    window = _window()
    window.text_edit.setPlainText("Hello. Привет.")
    assert not window.speak() and window.statusBar().currentMessage() == main_window.NOT_ENGLISH
    window.statusBar().clearMessage()
    assert window.save(tmp_path / "x.ogg") is None and window.statusBar().currentMessage() == main_window.NOT_ENGLISH
    assert window.speech.asked == [] and window.player.calls == []
    assert window.voice_box.findData("ef_dora") == -1          # no voice of another language to choose
    assert window.voice_box.findData("bm_george") == -1        # and no male voice
    window.close()


def test_stop_cancels_the_speech_and_the_sound(qapp, installed):
    window = _window()
    window.speak()
    window.speech.chunk.emit(1, 0, 3, b"one")
    window.stop()
    assert window.speech.asked[-1] == ("cancel",) and window.player.calls[-1] == "stop"
    assert not window.busy() and window.state.text() == "Ready" and not window.stop_button.isEnabled()
    window.speech.chunk.emit(1, 1, 3, b"late")              # made before the engine saw the cancel
    window.speech.canceled.emit(1)
    assert b"late" not in window.player.calls

    window.speak()                                          # stopped while only the sound was left
    window.speech.done.emit(2, 1.0, 0.5)
    window.stop()
    assert window.speech.asked.count(("cancel",)) == 1 and not window.player.playing()
    window.close()


def test_a_spoken_text_is_saved_without_making_it_again(qapp, installed, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = _window(settings)
    window.speak()
    window.speech.done.emit(1, 1.0, 0.5)

    assert window.save(tmp_path / "out" / "hello.mp3") == tmp_path / "out" / "hello.mp3"
    assert window.speech.asked[-1] == ("save", 1, tmp_path / "out" / "hello.mp3")
    assert [a[0] for a in window.speech.asked] == ["speak", "save"]
    window.speech.saved.emit(1, str(tmp_path / "out" / "hello.mp3"))
    assert window.statusBar().currentMessage() == f"Saved {tmp_path / 'out' / 'hello.mp3'}"
    assert window.save_dir() == tmp_path / "out" and window.save_format() == ".mp3"

    assert window.save(tmp_path / "hello.txt") is None      # no format of the engine's
    assert "Unknown format .txt" in window.statusBar().currentMessage()
    window.close()


@pytest.mark.parametrize("change", ["nothing spoken", "text", "voice", "speed"])
def test_an_unspoken_or_changed_text_is_made_first_without_playing(qapp, installed, tmp_path, change):
    window = _window()
    if change != "nothing spoken":
        window.speak()
        window.speech.done.emit(1, 1.0, 0.5)
        window.player.play_out()
        if change == "text":
            window.text_edit.setPlainText("Something else.")
        elif change == "voice":
            window.voice_box.setCurrentIndex(window.voice_box.findData("bf_emma"))
        else:
            window.speed_slider.setValue(150)
    before, ident = len(window.player.calls), window.speech.count + 1

    assert window.save(tmp_path / "speech.flac") == tmp_path / "speech.flac"
    assert window.speech.asked[-1][:2] == ("speak", ident) and window.state.text() == "Making the speech"
    window.speech.chunk.emit(ident, 0, 1, b"quiet")
    assert window.speech.asked[-1][0] == "speak"            # not saved before it is made
    window.speech.done.emit(ident, 1.0, 0.5)
    assert window.speech.asked[-1] == ("save", ident, tmp_path / "speech.flac")
    assert window.player.calls[before:] == ["stop"]         # never opened, fed or ended
    assert window.state.text() == "Ready"

    window.save(tmp_path / "again.ogg")                     # now it is in memory
    assert window.speech.asked[-1] == ("save", ident, tmp_path / "again.ogg")
    window.close()


def test_save_as_asks_for_the_file_and_adds_the_suffix_of_the_chosen_format(qapp, installed, tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue(main_window.SAVE_DIR_KEY, str(tmp_path))
    window = _window(settings)
    asked = []

    def choose(_parent, _title, start, filters):
        asked.append((start, filters))
        return str(tmp_path / "my speech"), "FLAC (*.flac)"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", choose)
    assert window.save() == tmp_path / "my speech.flac"
    assert asked == [(str(tmp_path / "speech.ogg"), "Ogg Vorbis (*.ogg);;MP3 (*.mp3);;FLAC (*.flac);;WAV (*.wav)")]
    assert window.save_format() == ".flac"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: ("", ""))
    count = len(window.speech.asked)
    assert window.save() is None and len(window.speech.asked) == count      # canceled: nothing asked
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda _p, _t, start, filters: asked.append((start, filters))
                        or (str(tmp_path / "typed.wav"), "FLAC (*.flac)"))
    assert window.save() == tmp_path / "typed.wav"          # a typed suffix wins
    assert asked[-1] == (str(tmp_path / "speech.flac"), "FLAC (*.flac);;Ogg Vorbis (*.ogg);;MP3 (*.mp3);;WAV (*.wav)")
    window.close()


def test_a_failure_is_shown_and_the_next_speak_clears_it(qapp, installed):
    window = _window()
    window.speak()
    window.speech.failed.emit("No words were found in this text.")
    assert window.state.text() == "Failed" and window.state.kind == "bad" and not window.busy()
    assert window.statusBar().currentMessage() == "No words were found in this text."
    assert window.player.calls[-1] == "stop" and window.speak_button.isEnabled()
    window.speak()
    assert window.state.text() == "Speaking" and window.state.kind == "info"
    window.close()


def test_speak_starts_an_engine_that_stopped_and_then_speaks(qapp, installed):
    window = _window()
    window.speak()
    window.speech.die()
    assert window.state.text() == "Stopped" and not window.busy() and not window.save_button.isEnabled()
    assert window.speak_button.isEnabled() and "Speak starts it again" in window.statusBar().currentMessage()

    window.voice_box.setCurrentIndex(window.voice_box.findData("bf_emma"))
    assert not window.speak()                               # not yet: the engine is starting
    assert window.speech.started == 2 and window.state.text() == "Starting"
    window.speech.load()
    assert window.speech.asked[-1] == ("speak", 2, "Good morning!", "bf_emma", 0.85)    # the chosen voice stays
    window.close()


def test_the_text_and_the_choices_are_remembered(qapp, installed, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = _window(settings)
    window.text_edit.setPlainText("Remember me.")
    window.voice_box.setCurrentIndex(window.voice_box.findData("bf_lily"))
    window.speed_slider.setValue(135)
    window.close()

    again = _window(settings)
    assert (again.text(), again.voice(), again.speed()) == ("Remember me.", "bf_lily", 1.35)
    again.close()

    settings.setValue(main_window.VOICE_KEY, "xx_gone")     # a voice the engine no longer has
    settings.setValue(main_window.SPEED_KEY, "fast")
    other = _window(settings)
    assert (other.voice(), other.speed()) == ("af_heart", 0.85)
    other.close()


def _wait(condition, seconds: float = 20.0) -> bool:
    end = time.monotonic() + seconds
    while not condition() and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)
    return condition()


def test_without_the_engine_the_window_sets_it_up(qapp, tmp_path, monkeypatch):
    done = tmp_path / "done"
    monkeypatch.setattr(engine_setup, "installed", lambda root=None: done.is_file())
    monkeypatch.setattr(engine_setup, "steps", lambda root: [
        [sys.executable, "-c", "print('making the venv')"],
        [sys.executable, "-c", f"import pathlib; pathlib.Path({str(done)!r}).touch(); print('fetched')"]])
    window = MainWindow(speech=FakeSpeech(), player=FakePlayer(), engine_dir=tmp_path / "engine")
    assert window.pages.currentIndex() == 1 and window.state.text() == "Not set up" and window.speech.started == 0
    assert not window.speak_button.isEnabled() and not window.save_button.isEnabled() and not window.speak()

    window.setup_button.click()
    assert window.state.text() == "Setting up" and not window.setup_button.isEnabled()
    assert _wait(lambda: window.speech.started == 1)
    said = window.setup_output.toPlainText()
    assert said.index("making the venv") < said.index("fetched") < said.index("The speech engine is set up.")
    assert f"$ {sys.executable} -c print('making the venv')" in said
    assert window.pages.currentIndex() == 0 and window.state.text() == "Starting" and (tmp_path / "engine").is_dir()
    window.speech.load()
    assert window.speak()
    window.close()


def test_a_setup_step_that_fails_ends_the_setup_and_can_be_tried_again(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(engine_setup, "installed", lambda root=None: False)
    monkeypatch.setattr(engine_setup, "steps", lambda root: [
        [sys.executable, "-c", "import sys; print('no network'); sys.exit(4)"],
        [sys.executable, "-c", "print('never')"]])
    window = MainWindow(speech=FakeSpeech(), player=FakePlayer(), engine_dir=tmp_path / "engine")
    window.set_up()
    assert _wait(lambda: window.setup_button.isEnabled())
    said = window.setup_output.toPlainText()
    assert "no network" in said and "exit code 4" in said and "never" not in said
    assert window.state.text() == "Not set up" and window.pages.currentIndex() == 1 and window.speech.started == 0

    monkeypatch.setattr(engine_setup, "steps", lambda root: [[str(tmp_path / "no-such-program")]])
    window.set_up()
    assert _wait(lambda: "exit code -1" in window.setup_output.toPlainText()) and window.setup_button.isEnabled()

    def nothing(root):
        raise engine_setup.SetupError(engine_setup.NO_PYTHON)

    monkeypatch.setattr(engine_setup, "steps", nothing)
    window.set_up()
    assert "brew install uv" in window.setup_output.toPlainText() and window.setup_button.isEnabled()
    window.close()
