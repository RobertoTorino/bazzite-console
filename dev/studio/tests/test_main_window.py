# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: the presets and Custom, a voice from a file and from a text, Play making the mix once and playing it,
Try background, Save as in the format of the suffix, what a failure shows, the settings, and the work done in a
thread; the icons are Nexus's."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest
import soundfile
from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QFileDialog

from remix_studio import APP_NAME, LOGO_PATH, ROOT, main_window, mix as mixer, pad as synth
from remix_studio.main_window import CUSTOM, NO_OUTPUT, NO_VOICE, TRY_SECONDS, MainWindow
from remix_studio.mix import Mix
from remix_studio.pad import PRESETS, RATE, Pad


class FakePlayer(QObject):
    """The audio output as the window sees it: keeps what it was given to play."""

    finished = pyqtSignal()

    def __init__(self, output: str = "Speakers"):
        super().__init__()
        self.output = output
        self.played: list[bytes] = []
        self.on = False

    def output_name(self) -> str:
        return self.output

    def playing(self) -> bool:
        return self.on

    def play(self, pcm: bytes) -> bool:
        self.played.append(pcm)
        self.on = bool(self.output)
        return self.on

    def stop(self) -> None:
        self.on = False

    def close(self) -> None:
        self.on = False


class FakeDialog:
    """Voice from a text, answered: the file it wrote, or canceled."""

    def __init__(self, target: Path | None):
        self.target = target

    def exec(self) -> bool:
        return self.target is not None


def settings_in(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "studio.ini"), QSettings.Format.IniFormat)


def voice_file(tmp_path, seconds: float = 1.0, name: str = "voice.wav") -> Path:
    path = tmp_path / name
    tone = 0.3 * np.sin(2 * np.pi * 300 * np.arange(int(24000 * seconds)) / 24000)
    soundfile.write(str(path), tone.astype(np.float32), 24000)
    return path


@pytest.fixture
def window(qapp, tmp_path):
    found = MainWindow(settings=settings_in(tmp_path), player=FakePlayer(), threads=False)
    for name in ("lead", "tail", "fade"):           # short mixes: the tests stay quick
        found.sliders[name].setValue(1)
    found.sliders["length"].setValue(5)
    yield found
    found.close()


def test_the_icons_are_nexus_at_512_and_128_px():
    assert LOGO_PATH.is_file() and QImage(str(LOGO_PATH)).width() == 512
    assert QImage(str(ROOT / "images" / "nexus-remix-studio-128.png")).width() == 128


def test_the_window_opens_on_the_warm_pad_without_a_voice(qapp):
    window = MainWindow(player=FakePlayer(), threads=False)
    assert window.windowTitle() == APP_NAME
    assert window.read_pad() == Pad() and window.preset_box.currentText() == "Warm pad"
    assert window.read_mix() == Mix()
    assert window.voice is None and window.voice_label.text() == NO_VOICE
    assert window.statusBar().currentMessage() == "Playing on: Speakers."
    assert window.state.text() == "Ready"
    assert not window.remove_button.isEnabled() and not window.stop_button.isEnabled()
    assert not window.sliders["lead"].isEnabled() and not window.sliders["tail"].isEnabled()
    assert window.sliders["length"].isEnabled() and window.values["length"].text() == "30 s"
    assert not window.sliders["voice_volume"].isEnabled()
    window.close()


def test_without_an_output_the_status_line_says_so(qapp):
    window = MainWindow(player=FakePlayer(output=""), threads=False)
    assert window.statusBar().currentMessage() == NO_OUTPUT
    window.sliders["length"].setValue(5)
    window.play()
    assert window.statusBar().currentMessage() == NO_OUTPUT and window.result is not None
    window.close()


def test_a_preset_fills_the_controls_and_a_moved_control_says_custom(window):
    window.preset_box.setCurrentText("Drone")
    assert window.read_pad() == PRESETS["Drone"]
    assert (window.key_box.currentText(), window.octave_box.currentText()) == ("D", "Low")
    assert window.values["tone"].text() == "35"

    window.sliders["tone"].setValue(80)
    assert window.preset_box.currentText() == CUSTOM
    assert window.read_pad() == Pad("Drone", "D", "Low", "Fifth", 80, 60, 60)      # still the drone's sound
    window.chord_box.setCurrentText("Minor")
    window.sliders["tone"].setValue(35)
    assert window.preset_box.currentText() == CUSTOM
    window.chord_box.setCurrentText("Fifth")
    assert window.preset_box.currentText() == "Drone"                              # back on its numbers
    window.preset_box.setCurrentText(CUSTOM)                                       # chosen by hand: nothing moves
    assert window.read_pad() == PRESETS["Drone"]


def test_the_sliders_show_their_value_with_its_unit(window):
    window.sliders["voice_volume"].setValue(120)
    window.sliders["lead"].setValue(7)
    assert window.values["voice_volume"].text() == "120 %" and window.values["lead"].text() == "7 s"


def test_a_sound_file_becomes_the_voice(window, tmp_path):
    assert window.open_voice(voice_file(tmp_path, 1.5))
    assert window.voice.shape == (int(1.5 * RATE), 2)
    assert window.voice_label.text() == "voice.wav, 1.5 s"
    assert window.voice_view.sound is window.voice
    assert window.remove_button.isEnabled() and window.sliders["lead"].isEnabled()

    window.remove_voice()
    assert window.voice is None and window.voice_label.text() == NO_VOICE and window.voice_view.sound is None
    assert not window.remove_button.isEnabled() and not window.sliders["lead"].isEnabled()


def test_the_top_row_is_four_pills_of_one_width(window):
    pills = [window.play_button, window.stop_button, window.save_button, window.reset_button]
    assert [pill.text() for pill in pills] == ["Play", "Stop", "Save as…", "Reset"]
    assert all(type(pill).__name__ == "ActionPill" for pill in pills)
    assert len({pill.minimumWidth() for pill in pills}) == 1


def test_without_a_voice_length_sets_how_long_the_mix_lasts(window):
    slider = window.sliders["length"]
    assert (slider.minimum(), slider.maximum(), slider.value()) == (5, 600, 5)
    slider.setValue(90)
    assert window.read_mix().length == 90 and window.values["length"].text() == "90 s"
    window.play()
    assert window.result.seconds == 90.0


def test_with_a_voice_length_is_lead_in_voice_and_tail_and_moving_it_sets_the_tail(window, tmp_path):
    window.sliders["length"].setValue(90)
    window.open_voice(voice_file(tmp_path, 4.0))
    slider = window.sliders["length"]
    assert (slider.minimum(), slider.maximum(), slider.value()) == (5, 35, 6)      # a second of lead-in and of tail
    assert window.values["length"].text() == "6 s" and slider.isEnabled()

    slider.setValue(15)
    assert window.sliders["tail"].value() == 10 and window.values["tail"].text() == "10 s"
    window.play()
    assert window.result.seconds == 15.0
    window.sliders["lead"].setValue(5)
    assert (slider.minimum(), slider.maximum(), slider.value()) == (9, 39, 19)
    window.sliders["tail"].setValue(0)
    assert slider.value() == 9

    window.remove_voice()                                           # the length set without a voice comes back
    assert (slider.minimum(), slider.maximum(), slider.value()) == (5, 600, 90)
    assert window.read_mix().length == 90


def test_reset_puts_the_background_and_the_mix_on_their_defaults_and_keeps_the_voice(window, tmp_path):
    window.open_voice(voice_file(tmp_path, 2.0))
    window.preset_box.setCurrentText("Dark")
    window.sliders["tone"].setValue(90)
    window.sliders["background_volume"].setValue(120)
    window.sliders["length"].setValue(20)
    window.reset_button.click()
    assert window.read_pad() == Pad() and window.preset_box.currentText() == "Warm pad"
    assert window.read_mix() == Mix() and window.voice is not None
    assert window.sliders["length"].value() == Mix().lead + 2 + Mix().tail
    assert window.statusBar().currentMessage() == "The background and the mix are back on their default values."
    window.remove_voice()
    assert window.sliders["length"].value() == Mix().length


def test_the_open_dialog_remembers_its_folder_and_cancel_changes_nothing(window, tmp_path, monkeypatch):
    path = voice_file(tmp_path)
    asked = []
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        lambda _parent, _title, folder, _filter: (asked.append(folder), (str(path), ""))[1])
    assert window.open_voice() and window.voice_path == path
    assert window.open_voice() and asked[1] == str(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: ("", ""))
    assert not window.open_voice() and window.voice_path == path


def test_what_is_no_sound_file_is_said_and_the_voice_stays(window, tmp_path):
    window.open_voice(voice_file(tmp_path))
    notes = tmp_path / "notes.txt"
    notes.write_text("not a sound")
    assert not window.open_voice(notes)
    assert window.statusBar().currentMessage() == "notes.txt is not a sound file this app can read."
    assert window.voice_path.name == "voice.wav"


def test_a_spoken_text_becomes_the_voice_and_cancel_changes_nothing(window, tmp_path, monkeypatch):
    spoken = voice_file(tmp_path, 2.0, "voice-from-text.wav")
    monkeypatch.setattr(main_window, "SPOKEN", spoken)
    assert not window.speak_text(FakeDialog(None)) and window.voice is None
    assert window.speak_text(FakeDialog(spoken))
    assert window.voice_label.text() == "A spoken text, 2.0 s"
    assert window.statusBar().currentMessage() == "The voice is A spoken text."


def test_play_makes_the_mix_draws_it_and_plays_it(window, tmp_path):
    window.open_voice(voice_file(tmp_path, 1.0))
    window.play()
    assert window.result.seconds == 3.0                             # lead-in, voice and tail of a second each
    assert len(window.player.played) == 1 and len(window.player.played[0]) == 3 * RATE * 4
    assert window.mix_view.sound is window.result.sound and window.mix_label.text() == "3.0 s."
    assert window.statusBar().currentMessage() == "Playing 3.0 s."
    assert window.state.text() == "Playing" and window.stop_button.isEnabled()

    window.stop()
    assert window.state.text() == "Ready" and not window.stop_button.isEnabled()


def test_a_mix_is_made_again_only_after_a_change(window, tmp_path, monkeypatch):
    made = []
    render = mixer.render
    monkeypatch.setattr(mixer, "render", lambda *args: (made.append(args), render(*args))[1])
    window.play()
    window.play()
    assert len(made) == 1 and len(window.player.played) == 2
    window.sliders["background_volume"].setValue(80)
    window.play()
    window.chord_box.setCurrentText("Minor")
    window.play()
    window.open_voice(voice_file(tmp_path))
    window.play()
    window.open_voice(voice_file(tmp_path))                         # the same file again may hold another sound
    window.play()
    assert len(made) == 5
    assert made[-1][0].chord == "Minor" and made[-1][1].background_volume == 80 and made[-1][2] is window.voice


def test_a_mix_too_loud_says_it_was_turned_down(window, tmp_path):
    window.open_voice(voice_file(tmp_path))
    window.sliders["voice_volume"].setValue(150)
    window.sliders["background_volume"].setValue(150)
    window.play()
    assert window.result.turned_down > 0
    assert window.mix_label.text() == (f"3.0 s. It was turned down by {window.result.turned_down:.1f} dB, so "
                                       "nothing clips.")


def test_try_background_plays_it_alone_and_leaves_the_mix(window):
    window.try_background()
    assert len(window.player.played[0]) == TRY_SECONDS * RATE * 4 and window.result is None
    assert window.statusBar().currentMessage() == f"Playing {TRY_SECONDS} s of the background."


def test_save_writes_the_mix_that_was_heard_without_making_it_again(window, tmp_path, monkeypatch):
    window.play()
    monkeypatch.setattr(mixer, "render", lambda *_: pytest.fail("made again"))
    path = tmp_path / "out" / "remix.flac"
    path.parent.mkdir()
    assert window.save(path) == path
    sound, rate = soundfile.read(str(path), dtype="float32")
    assert rate == RATE and np.allclose(sound, window.result.sound, atol=1e-4)
    assert window.statusBar().currentMessage() == f"Saved {path}"
    assert window.settings.value("save_dir") == str(path.parent) and window.settings.value("format") == ".flac"


def test_save_makes_the_mix_first_when_it_was_not_played(window, tmp_path):
    path = tmp_path / "remix.wav"
    window.save(path)
    assert soundfile.info(str(path)).duration == pytest.approx(5.0) and not window.player.played


def test_the_save_dialog_offers_the_last_format_and_adds_the_suffix(window, tmp_path, monkeypatch):
    asked = []
    def dialog(_parent, _title, start, filters):
        asked.append((start, filters))
        return str(tmp_path / "evening"), "MP3 (*.mp3)"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", dialog)
    window.settings.setValue("save_dir", str(tmp_path))
    assert window.save() == tmp_path / "evening.mp3" and (tmp_path / "evening.mp3").is_file()
    assert asked[0] == (str(tmp_path / "remix.ogg"), "Ogg Vorbis (*.ogg);;MP3 (*.mp3);;FLAC (*.flac);;WAV (*.wav)")
    window.save()
    assert asked[1][0] == str(tmp_path / "remix.mp3") and asked[1][1].startswith("MP3 (*.mp3);;")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: ("", ""))
    assert window.save() is None


def test_an_unknown_format_and_a_failed_write_are_said(window, tmp_path):
    assert window.save(tmp_path / "remix.txt") is None
    assert window.statusBar().currentMessage() == "Unknown format .txt. Use .ogg, .mp3, .flac, .wav."
    window.save(tmp_path / "missing" / "remix.wav")
    assert window.statusBar().currentMessage().startswith("remix.wav could not be written")
    assert window.state.text() == "Failed"
    window.play()                                                   # the next thing that works clears it
    assert window.state.text() == "Playing"


def test_the_remix_is_remembered(qapp, tmp_path):
    first = MainWindow(settings=settings_in(tmp_path), player=FakePlayer(), threads=False)
    first.preset_box.setCurrentText("Glass")
    first.sliders["space"].setValue(20)
    first.sliders["tail"].setValue(9)
    first.sliders["background_volume"].setValue(65)
    first.open_voice(voice_file(tmp_path))
    first.close()

    again = MainWindow(settings=settings_in(tmp_path), player=FakePlayer(), threads=False)
    assert again.read_pad() == Pad("Glass", "A", "High", "Open (sus2)", 60, 50, 20)
    assert again.preset_box.currentText() == CUSTOM
    assert again.read_mix() == Mix(tail=9, background_volume=65)
    assert again.sliders["length"].value() == 3 + 1 + 9             # with the voice: lead-in, voice and tail
    assert again.voice_path == tmp_path / "voice.wav" and again.voice is not None
    again.remove_voice()
    again.close()

    third = MainWindow(settings=settings_in(tmp_path), player=FakePlayer(), threads=False)
    assert third.voice is None
    third.close()


def test_a_voice_file_that_is_gone_is_left_out(qapp, tmp_path):
    settings = settings_in(tmp_path)
    settings.setValue("voice_file", str(tmp_path / "gone.wav"))
    window = MainWindow(settings=settings, player=FakePlayer(), threads=False)
    assert window.voice is None and window.voice_label.text() == NO_VOICE
    window.close()


def test_in_a_thread_the_buttons_wait_and_the_mix_arrives(qapp, tmp_path):
    window = MainWindow(player=FakePlayer())
    window.sliders["length"].setValue(5)
    window.play()
    assert window.busy() and not window.play_button.isEnabled() and not window.save_button.isEnabled()
    assert window.state.text() == "Making the mix"
    window.play()                                                   # a second click while it is made: nothing
    path = tmp_path / "remix.wav"
    assert window.save(path) is None
    deadline = time.monotonic() + 30
    while window.busy() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    assert not window.busy() and len(window.player.played) == 1 and window.play_button.isEnabled()

    window.save(path)
    while window.busy() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    assert soundfile.info(str(path)).duration == pytest.approx(5.0)
    window.close()
