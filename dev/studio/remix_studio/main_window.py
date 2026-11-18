# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: the pills Play, Stop, Save as and Reset in the header, then the three parts of a remix from top to bottom. Voice takes
a sound file or a text spoken by Text to Speech's engine. Background is a preset, a chord and three sliders, with Try
background to hear it alone. Mix sets the volumes, the lead-in, the tail and the fade, and draws the result. The mix
is made in a thread, so the window never waits on it; a mix that was just played is saved as it was heard. The
voice file, the background, the mix and the save folder are remembered in the settings."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QSettings, QStandardPaths, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor, QKeySequence, QPainter, QPen, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bazzite_console_core import SUITE_MANUAL_URL
from bazzite_console_core.nexus import EDGE, MAIN, TEAL, header as nexus_header
from bazzite_console_core.widgets import ActionPill, InfoButton, StatusText, hint_label, same_width

from . import APP_ID, APP_NAME, CHECKOUT, LOGO_PATH, audio, mix as mixer, pad as synth
from .audio import FORMATS, OPEN_FILTER, AudioError
from .mix import Mix, Result
from .pad import RATE, Pad
from .player import Player
from .speak_dialog import SpeakDialog

PAD_GROUP = "pad"                       # the settings: the background's and the mix's fields under their group
MIX_GROUP = "mix"
VOICE_KEY = "voice_file"
OPEN_DIR_KEY = "open_dir"
SAVE_DIR_KEY = "save_dir"
FORMAT_KEY = "format"
DEFAULT_FORMAT = ".ogg"
FILTERS = {".ogg": "Ogg Vorbis (*.ogg)", ".mp3": "MP3 (*.mp3)", ".flac": "FLAC (*.flac)", ".wav": "WAV (*.wav)"}
CUSTOM = "Custom"                       # the preset box once a control left the preset
TRY_SECONDS = 12
# Where a spoken text is kept as the voice
SPOKEN = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / APP_ID / "voice-from-text.wav"
NO_VOICE = "No voice yet. The mix is the background alone."
NO_OUTPUT = "No audio output was found, so the mix is not heard. Save as… still writes it."
WIKI = f"{SUITE_MANUAL_URL}development/dashboard/#remix-studio"
ABOUT = ("A remix has two tracks, a voice and a background.<br><br><b>Voice</b> is a sound file, or a text that "
         "Text to Speech speaks for you. <b>Background</b> is a sustained sound made here. Choose a preset, a key "
         "and a chord, and shape it with the sliders. <b>Try background</b> plays it alone.<br><br><b>Mix</b> sets "
         "how loud each track is. The background starts before the voice by the lead-in and goes on after it by the "
         "tail. It fades in and out. <b>Length</b> is how long the mix lasts. With a voice, moving it changes the "
         "tail.<br><br><b>Play</b> (Ctrl+Enter) makes the mix and plays it, and <b>Stop</b> "
         "(Esc) ends it. <b>Save as…</b> writes it as an Ogg Vorbis, MP3, FLAC or WAV file. <b>Reset</b> puts the "
         "background and the mix back on their default values.<br><br>"
         f"More in <a href='{WIKI}'>the wiki</a>.")


class Job(QThread):
    """One piece of work off the window's thread; ended tells what it returned, or what went wrong."""

    ended = pyqtSignal(object, object)

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self.work = work

    def run(self) -> None:
        try:
            self.ended.emit(self.work(), None)
        except Exception as error:  # noqa: BLE001  (whatever it is goes to the status line)
            self.ended.emit(None, error)


class WaveView(QWidget):
    """A track drawn: its loudest and softest sample per pixel, in the accent on the field color."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.sound: np.ndarray | None = None
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_sound(self, sound: np.ndarray | None) -> None:
        self.sound = sound
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setPen(QPen(QColor(EDGE), 1))
        painter.setBrush(QColor(MAIN))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        width, height = self.width() - 2, self.height() - 2
        middle = height / 2 + 1
        painter.drawLine(1, int(middle), width, int(middle))
        if self.sound is None or width < 2:
            return
        painter.setPen(QPen(QColor(TEAL), 1))
        for x, (low, high) in enumerate(audio.peaks(self.sound, width)):
            painter.drawLine(x + 1, int(middle - high * (height / 2 - 2)), x + 1,
                             int(middle - low * (height / 2 - 2)) + 1)


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None, player: Player | None = None, threads: bool = True):
        """*settings* remembers the remix (None: this session only); *player* is the audio output (the real one by
        default; a test passes its own); with *threads* off the work is done at once, in the caller's thread."""
        super().__init__()
        self.settings = settings
        self.player = player if player is not None else Player(parent=self)
        self.threads = threads
        self.setWindowTitle(APP_NAME)
        self.resize(980, 760)
        self.voice: np.ndarray | None = None    # float32 stereo at RATE
        self.voice_path: Path | None = None
        self.voice_count = 0                    # goes up with every voice: part of what a mix was made from
        self.result: Result | None = None       # the last mix made
        self.result_of: tuple | None = None     # what it was made from
        self.job: Job | None = None
        self.sound_of = Pad().preset            # the preset whose sound the background has
        self._filling = False

        central = QWidget()
        layout = QVBoxLayout(central)
        header = nexus_header(LOGO_PATH, APP_NAME, CHECKOUT)  # the checkout's commit, never a version
        self.state = StatusText()
        header.add_state(self.state)
        header.add_action(InfoButton(ABOUT, "What this app does"))
        self.play_button = ActionPill("Play", "The mix", "Make the mix and play it (Ctrl+Enter)")
        self.play_button.clicked.connect(lambda: self.play())
        self.stop_button = ActionPill("Stop", "Playing", "Stop playing (Esc)")
        self.stop_button.clicked.connect(self.stop)
        self.save_button = ActionPill("Save as…", "A sound file", "Write the mix as an Ogg Vorbis, MP3, FLAC or WAV "
                                                                  "file")
        self.save_button.clicked.connect(lambda: self.save())
        self.reset_button = ActionPill("Reset", "Default values", "Put the background and the mix back on the values "
                                                                  "the app starts with. The voice stays")
        self.reset_button.clicked.connect(self.reset)
        pills = [self.play_button, self.stop_button, self.save_button, self.reset_button]
        same_width(pills)
        for button in pills:
            header.add_second(button)
        header.second_row.addStretch(1)
        layout.addLayout(header)

        voice_box = QGroupBox("Voice")
        voice_layout = QVBoxLayout(voice_box)
        voice_row = QHBoxLayout()
        self.open_button = QPushButton("Open a sound file…")
        self.open_button.setToolTip("Use a WAV, Ogg Vorbis, FLAC or MP3 file as the voice")
        self.open_button.clicked.connect(lambda: self.open_voice())
        self.speak_button = QPushButton("From a text…")
        self.speak_button.setToolTip("Have Text to Speech speak a text, and use that as the voice")
        self.speak_button.clicked.connect(lambda: self.speak_text())
        self.remove_button = QPushButton("Remove")
        self.remove_button.setToolTip("Take the voice out. The mix is then the background alone")
        self.remove_button.clicked.connect(self.remove_voice)
        self.voice_label = hint_label(NO_VOICE)
        for button in (self.open_button, self.speak_button, self.remove_button):
            voice_row.addWidget(button)
        voice_row.addWidget(self.voice_label, 1)
        voice_layout.addLayout(voice_row)
        self.voice_view = WaveView()
        voice_layout.addWidget(self.voice_view, 1)
        layout.addWidget(voice_box, 2)

        pad_box = QGroupBox("Background")
        pad_layout = QVBoxLayout(pad_box)
        pad_row = QHBoxLayout()
        self.preset_box = self._combo([*synth.PRESETS, CUSTOM], "A sound to start from. The box says Custom once a "
                                                                "control has left it")
        self.preset_box.currentTextChanged.connect(self.choose_preset)
        self.key_box = self._combo(synth.KEYS, "The note the chord is built on")
        self.octave_box = self._combo(synth.OCTAVES, "How low or high the chord sits")
        self.chord_box = self._combo(synth.CHORDS, "The notes that sound together")
        for box in (self.key_box, self.octave_box, self.chord_box):
            box.currentTextChanged.connect(self.pad_changed)
        self.try_button = QPushButton("Try background")
        self.try_button.setToolTip(f"Play {TRY_SECONDS} seconds of the background alone")
        self.try_button.clicked.connect(self.try_background)
        for label, box in (("Preset:", self.preset_box), ("Key:", self.key_box), ("Octave:", self.octave_box),
                           ("Chord:", self.chord_box)):
            pad_row.addWidget(QLabel(label))
            pad_row.addWidget(box)
        pad_row.addStretch(1)
        pad_row.addWidget(self.try_button)
        pad_layout.addLayout(pad_row)
        self.sliders: dict[str, QSlider] = {}
        self.values: dict[str, QLabel] = {}
        pad_grid = QGridLayout()
        pad_grid.setHorizontalSpacing(12)
        for column, (name, (label, tip)) in enumerate(synth.SLIDERS.items()):
            self._slider(pad_grid, 0, column, name, label, tip, 0, 100, "")
            self.sliders[name].valueChanged.connect(self.pad_changed)
        pad_layout.addLayout(pad_grid)
        layout.addWidget(pad_box)

        mix_box = QGroupBox("Mix")
        mix_layout = QVBoxLayout(mix_box)
        mix_grid = QGridLayout()
        mix_grid.setHorizontalSpacing(12)
        for index, (name, (least, most, label, unit, tip)) in enumerate(mixer.RANGES.items()):
            self._slider(mix_grid, index // 2, index % 2, name, label, tip, least, most, unit)
        mix_layout.addLayout(mix_grid)
        self.free_length = Mix().length         # the length set for a mix without a voice
        for name in ("lead", "tail"):
            self.sliders[name].valueChanged.connect(self.show_length)
        self.sliders["length"].valueChanged.connect(self.length_moved)
        self.mix_view = WaveView()
        mix_layout.addWidget(self.mix_view, 1)
        self.mix_label = hint_label("")
        mix_layout.addWidget(self.mix_label)
        layout.addWidget(mix_box, 3)
        self.setCentralWidget(central)

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.play)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.play)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.stop)
        self.player.finished.connect(self.update_controls)

        self.restore()
        output = self.player.output_name()
        self.statusBar().showMessage(f"Playing on: {output}." if output else NO_OUTPUT)
        self.update_controls()

    # --- building the controls -----------------------------------------------------------------------------------
    @staticmethod
    def _combo(items, tip: str) -> QComboBox:
        box = QComboBox()
        box.addItems(list(items))
        box.setToolTip(tip)
        return box

    def _slider(self, grid: QGridLayout, row: int, column: int, name: str, label: str, tip: str, least: int,
                most: int, unit: str) -> None:
        """A labeled slider with its value in *grid*, three cells wide."""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(least, most)
        slider.setToolTip(tip)
        value = QLabel()
        value.setMinimumWidth(52)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda number: value.setText(f"{number} {unit}".rstrip()))
        grid.addWidget(QLabel(label), row, column * 3)
        grid.addWidget(slider, row, column * 3 + 1)
        grid.addWidget(value, row, column * 3 + 2)
        grid.setColumnStretch(column * 3 + 1, 1)
        value.setText(f"{slider.value()} {unit}".rstrip())
        self.sliders[name], self.values[name] = slider, value

    # --- the settings --------------------------------------------------------------------------------------------
    def _group(self, group: str) -> dict[str, object]:
        if self.settings is None:
            return {}
        self.settings.beginGroup(group)
        values = {key: self.settings.value(key) for key in self.settings.childKeys()}
        self.settings.endGroup()
        return values

    def restore(self) -> None:
        """The last background, mix and voice file from the settings; the Warm pad preset without any."""
        self.show_pad(synth.from_values(self._group(PAD_GROUP)))
        self.show_mix(mixer.from_values(self._group(MIX_GROUP)))
        if self.settings is not None:
            path = str(self.settings.value(VOICE_KEY, ""))
            if path and Path(path).is_file():
                self.open_voice(Path(path))

    def remember(self) -> None:
        if self.settings is None:
            return
        for group, values in ((PAD_GROUP, synth.to_values(self.read_pad())),
                              (MIX_GROUP, mixer.to_values(self.read_mix()))):
            self.settings.beginGroup(group)
            for key, value in values.items():
                self.settings.setValue(key, value)
            self.settings.endGroup()
        self.settings.setValue(VOICE_KEY, str(self.voice_path) if self.voice_path is not None else "")

    # --- the background and the mix ------------------------------------------------------------------------------
    def show_pad(self, pad: Pad) -> None:
        """Put *pad* in the controls; the preset box says its preset while its numbers are that preset's."""
        self._filling = True
        self.key_box.setCurrentText(pad.key)
        self.octave_box.setCurrentText(pad.octave)
        self.chord_box.setCurrentText(pad.chord)
        for name in synth.SLIDERS:
            self.sliders[name].setValue(getattr(pad, name))
        self.sound_of = pad.preset
        self.preset_box.setCurrentText(pad.preset if synth.PRESETS.get(pad.preset) == pad else CUSTOM)
        self._filling = False

    def read_pad(self) -> Pad:
        return Pad(self.sound_of, self.key_box.currentText(), self.octave_box.currentText(),
                   self.chord_box.currentText(), *(self.sliders[name].value() for name in synth.SLIDERS))

    def choose_preset(self, name: str) -> None:
        if not self._filling and name in synth.PRESETS:
            self.show_pad(synth.PRESETS[name])

    def pad_changed(self, *_args) -> None:
        """A control moved: the preset box says Custom unless the numbers are still the preset's."""
        if self._filling:
            return
        self._filling = True
        pad = self.read_pad()
        self.preset_box.setCurrentText(pad.preset if synth.PRESETS.get(pad.preset) == pad else CUSTOM)
        self._filling = False

    def show_mix(self, mix: Mix) -> None:
        self.free_length = mix.length
        for name, value in mixer.to_values(mix).items():
            if name != "length":
                self.sliders[name].setValue(int(value))
        self.show_length()

    def read_mix(self) -> Mix:
        values = {name: self.sliders[name].value() for name in mixer.RANGES}
        return Mix(**{**values, "length": self.free_length})

    def voice_seconds(self) -> int:
        """The voice's length in whole seconds, as the Length slider counts it."""
        return round(len(self.voice) / RATE) if self.voice is not None else 0

    def show_length(self, *_args) -> None:
        """Put the Length slider on the mix's length. Without a voice that is the length set, from 5 s to 600 s.
        With a voice it is the lead-in, the voice and the tail, and the slider reaches as far as the tail can."""
        slider = self.sliders["length"]
        least, most = mixer.RANGES["length"][:2]
        value = self.free_length
        if self.voice is not None:
            least = self.sliders["lead"].value() + self.voice_seconds() + mixer.RANGES["tail"][0]
            most = self.sliders["lead"].value() + self.voice_seconds() + mixer.RANGES["tail"][1]
            value = least + self.sliders["tail"].value()
        self._filling, before = True, self._filling
        slider.setRange(least, most)
        slider.setValue(value)
        self._filling = before
        self.values["length"].setText(f"{slider.value()} s")
        slider.setToolTip(mixer.RANGES["length"][4] if self.voice is None else
                          "How long the mix lasts. That is the lead-in, the voice and the tail. Moving it changes the tail")

    def length_moved(self, value: int) -> None:
        """The Length slider was moved by hand: without a voice it is the length, with one it sets the tail."""
        if self._filling:
            return
        if self.voice is None:
            self.free_length = value
        else:
            self.sliders["tail"].setValue(value - self.sliders["lead"].value() - self.voice_seconds())

    def reset(self) -> None:
        """The background and the mix back on the values the app starts with; the voice stays."""
        self.show_pad(Pad())
        self.show_mix(Mix())
        self.statusBar().showMessage("The background and the mix are back on their default values.")

    # --- the voice -----------------------------------------------------------------------------------------------
    def open_dir(self) -> Path:
        default = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation) or Path.home())
        if self.settings is not None:
            return Path(str(self.settings.value(OPEN_DIR_KEY, str(default))))
        return default

    def open_voice(self, path: Path | None = None) -> bool:
        """Take the sound file *path*, or the one chosen in the dialog, as the voice. False when none was taken."""
        if path is None:
            chosen, _used = QFileDialog.getOpenFileName(self, "Open the voice", str(self.open_dir()), OPEN_FILTER)
            if not chosen:
                return False
            path = Path(chosen)
            if self.settings is not None:
                self.settings.setValue(OPEN_DIR_KEY, str(path.parent))
        try:
            voice = audio.load(path)
        except AudioError as error:
            self.statusBar().showMessage(str(error))
            return False
        self.voice, self.voice_path = voice, path
        self.voice_count += 1
        name = "A spoken text" if path == SPOKEN else path.name
        self.voice_label.setText(f"{name}, {len(voice) / RATE:.1f} s")
        self.voice_view.set_sound(voice)
        self.show_length()
        self.statusBar().showMessage(f"The voice is {name}.")
        self.update_controls()
        return True

    def speak_text(self, dialog: SpeakDialog | None = None) -> bool:
        """Have Text to Speech speak a text (in *dialog*; a test passes its own) and take it as the voice."""
        dialog = dialog if dialog is not None else SpeakDialog(SPOKEN, self.settings, self)
        if not dialog.exec():
            return False
        return self.open_voice(dialog.target)

    def remove_voice(self) -> None:
        self.voice = self.voice_path = None
        self.voice_count += 1
        self.voice_label.setText(NO_VOICE)
        self.voice_view.set_sound(None)
        self.show_length()
        self.update_controls()

    # --- making, playing and saving ------------------------------------------------------------------------------
    def busy(self) -> bool:
        return self.job is not None

    def update_controls(self) -> None:
        free = not self.busy()
        for widget in (self.play_button, self.save_button, self.reset_button, self.try_button, self.open_button,
                       self.speak_button):
            widget.setEnabled(free)
        self.remove_button.setEnabled(free and self.voice is not None)
        self.sliders["voice_volume"].setEnabled(self.voice is not None)
        self.sliders["lead"].setEnabled(self.voice is not None)
        self.sliders["tail"].setEnabled(self.voice is not None)
        self.stop_button.setEnabled(self.player.playing())
        if free:
            playing = self.player.playing()
            self.state.set_status("Playing" if playing else "Ready", "info" if playing else "ok")

    def run(self, work, then, status: str) -> None:
        """Do *work* off the window's thread, then call *then* with what it returned. One at a time: the buttons
        that start work are off meanwhile. A failure goes to the status line."""
        def ended(result, error, job=None):
            if job is not None:
                job.wait()
                job.deleteLater()
            self.job = None
            self.update_controls()
            if error is not None:
                self.state.set_status("Failed", "bad", str(error))
                self.statusBar().showMessage(str(error))
            else:
                then(result)
        self.state.set_status(status, "info")
        if not self.threads:
            try:
                result, error = work(), None
            except Exception as failure:  # noqa: BLE001  (as Job does)
                result, error = None, failure
            ended(result, error)
            return
        job = self.job = Job(work, self)
        job.ended.connect(lambda result, error: ended(result, error, job))
        self.update_controls()
        job.start()

    def with_mix(self, then, status: str) -> None:
        """Call *then* with the mix of the window as it is now, made first when it is not the last one made."""
        pad, mix, voice = self.read_pad(), self.read_mix(), self.voice
        made_of = (self.voice_count, pad, mix)
        if self.result is not None and self.result_of == made_of:
            then(self.result)
            return
        def made(result: Result) -> None:
            self.result, self.result_of = result, made_of
            self.mix_view.set_sound(result.sound)
            turned = (f" It was turned down by {result.turned_down:.1f} dB, so nothing clips."
                      if result.turned_down else "")
            self.mix_label.setText(f"{result.seconds:.1f} s.{turned}")
            then(result)
        self.statusBar().showMessage("Making the mix…")
        self.run(lambda: mixer.render(pad, mix, voice), made, status)

    def play(self) -> None:
        if self.busy():
            return
        self.remember()
        self.player.stop()
        def play(result: Result) -> None:
            heard = self.player.play(audio.pcm(result.sound))
            self.statusBar().showMessage(f"Playing {result.seconds:.1f} s." if heard else NO_OUTPUT)
            self.update_controls()
        self.with_mix(play, "Making the mix")

    def try_background(self) -> None:
        """Play a few seconds of the background alone, at full volume."""
        if self.busy():
            return
        self.remember()
        self.player.stop()
        pad = self.read_pad()
        def play(sound: np.ndarray) -> None:
            heard = self.player.play(audio.pcm(sound))
            self.statusBar().showMessage(f"Playing {TRY_SECONDS} s of the background." if heard else NO_OUTPUT)
            self.update_controls()
        self.statusBar().showMessage("Making the background…")
        self.run(lambda: synth.render(pad, TRY_SECONDS) * mixer.fades(TRY_SECONDS * RATE, 1.0)[:, None], play,
                 "Making the background")

    def stop(self) -> None:
        self.player.stop()
        self.update_controls()

    def save_dir(self) -> Path:
        default = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation) or Path.home())
        if self.settings is not None:
            return Path(str(self.settings.value(SAVE_DIR_KEY, str(default))))
        return default

    def save_format(self) -> str:
        chosen = str(self.settings.value(FORMAT_KEY, DEFAULT_FORMAT)) if self.settings is not None else DEFAULT_FORMAT
        return chosen if chosen in FILTERS else DEFAULT_FORMAT

    def save(self, path: Path | None = None) -> Path | None:
        """Write the mix as it is now to *path*, or to the file chosen in the dialog; None when canceled. The file
        is there once the status line says Saved."""
        if self.busy():
            return None
        if path is None:
            suffix = self.save_format()
            filters = ";;".join([FILTERS[suffix], *(f for s, f in FILTERS.items() if s != suffix)])
            chosen, used = QFileDialog.getSaveFileName(self, "Save the mix", str(self.save_dir() / f"remix{suffix}"),
                                                       filters)
            if not chosen:
                return None
            path = Path(chosen)
            if path.suffix.lower() not in FORMATS:  # no suffix typed: the one of the chosen filter
                path = path.with_name(path.name + next((s for s, f in FILTERS.items() if f == used), suffix))
        if path.suffix.lower() not in FORMATS:
            self.statusBar().showMessage(f"Unknown format {path.suffix}. Use {', '.join(FORMATS)}.")
            return None
        if self.settings is not None:
            self.settings.setValue(SAVE_DIR_KEY, str(path.parent))
            self.settings.setValue(FORMAT_KEY, path.suffix.lower())
        self.remember()
        def write(result: Result) -> None:
            self.statusBar().showMessage(f"Saving {path.name}…")
            self.run(lambda: audio.save(path, result.sound), lambda _none: self.statusBar().showMessage(
                f"Saved {path}"), "Saving")
        self.with_mix(write, "Making the mix")
        return path

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        self.remember()
        self.player.close()
        if self.job is not None:
            self.job.wait()
        event.accept()


__all__ = ["ABOUT", "CUSTOM", "DEFAULT_FORMAT", "FILTERS", "FORMAT_KEY", "MIX_GROUP", "NO_OUTPUT", "NO_VOICE",
           "OPEN_DIR_KEY", "PAD_GROUP", "SAVE_DIR_KEY", "SPOKEN", "TRY_SECONDS", "VOICE_KEY", "Job", "MainWindow",
           "WaveView"]
