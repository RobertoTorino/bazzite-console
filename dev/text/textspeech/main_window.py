# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: the voice, the speed and the actions in the header, the text below. Speak plays the text while the
engine makes it, a sentence at a time; Stop ends it; Save as writes the speech as OGG, MP3, FLAC or WAV, without
making it again when the text, the voice and the speed are still the ones spoken. Where the speech engine is not on
the machine yet, the window shows Set up the speech engine and the output of its steps instead of the text. The
text, the voice, the speed and the save folder are remembered in the settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QProcess, QSettings, QStandardPaths, Qt
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bazzite_console_core import SUITE_MANUAL_URL
from bazzite_console_core.nexus import header as nexus_header
from bazzite_console_core.widgets import InfoButton, StatusText, Terminal, accent_button, hint_label

from . import APP_NAME, CHECKOUT, LOGO_PATH, engine_setup
from .engine import (DEFAULT_SPEED, DEFAULT_VOICE, FORMATS, NOT_ENGLISH, SPEED_RANGE, offered_voices, is_english,
                     voice_label)
from .player import Player
from .speech import Speech

TEXT_KEY = "text"                       # the settings
VOICE_KEY = "voice"
SPEED_KEY = "speed"
SAVE_DIR_KEY = "save_dir"
FORMAT_KEY = "format"
DEFAULT_TEXT = "Good morning!"
DEFAULT_FORMAT = ".ogg"
FILTERS = {".ogg": "Ogg Vorbis (*.ogg)", ".mp3": "MP3 (*.mp3)", ".flac": "FLAC (*.flac)", ".wav": "WAV (*.wav)"}
NO_OUTPUT = "No audio output was found, so the speech is not heard. Save as… still writes it."
NO_TEXT = "Type a text first."
WIKI = f"{SUITE_MANUAL_URL}development/dashboard/#text-to-speech"
SETUP_HINT = ("The speech engine is not on this machine yet. Setting it up downloads about 350 MB into {folder}. "
              "Nothing else on the machine changes.")
ABOUT = ("Type or paste a text, choose a voice and a speed, and click <b>Speak</b> (Ctrl+Enter). <b>Stop</b> (Esc) "
         "ends it. The first sentence plays while the next ones are made. An empty line in the text gives a longer "
         "pause.<br><br><b>Save as…</b> writes the speech as an Ogg Vorbis, MP3, FLAC or WAV file. You do not have "
         "to click Speak first.<br><br>The voices are female and English, American or British, and the text must "
         "be English too. They run on this machine, and nothing of your text leaves it.<br><br>"
         f"More in <a href='{WIKI}'>the wiki</a>.")


@dataclass(frozen=True)
class Spoken:
    """One speak: its id at the engine, and what was asked."""

    ident: int
    text: str
    voice: str
    speed: float

    def same(self, text: str, voice: str, speed: float) -> bool:
        return (self.text, self.voice, self.speed) == (text, voice, speed)


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None, speech: Speech | None = None,
                 player: Player | None = None, engine_dir: Path = engine_setup.ENGINE_DIR):
        """*settings* remembers the text and the choices (None: this session only); *speech* is the engine and
        *player* the audio output (the real ones by default; a test passes its own); *engine_dir* is where the
        engine is, or will be set up."""
        super().__init__()
        self.settings = settings
        self.engine_dir = engine_dir
        self.speech = speech if speech is not None else Speech(engine_setup.serve_command(engine_dir), self)
        self.player = player if player is not None else Player(parent=self)
        self.setWindowTitle(APP_NAME)
        self.resize(900, 560)
        self.current: Spoken | None = None      # the speak the engine is making
        self.finished: Spoken | None = None     # the last one it made in full: what Save as can write at once
        self.save_after: Path | None = None     # the file to write once the current speak is made
        self.speak_when_ready = False           # Speak was clicked while the engine was starting again
        self.setup_steps: list[list[str]] = []
        self.setup_process: QProcess | None = None

        central = QWidget()
        layout = QVBoxLayout(central)
        header = nexus_header(LOGO_PATH, APP_NAME, CHECKOUT)  # the checkout's commit, never a version
        self.state = StatusText()
        header.add_state(self.state)
        header.add_action(InfoButton(ABOUT, "What this app does"))
        self.voice_box = QComboBox()
        self.voice_box.setToolTip("The voice, American or British English")
        self.voice_box.setMinimumContentsLength(30)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(round(SPEED_RANGE[0] * 100), round(SPEED_RANGE[1] * 100))
        self.speed_slider.setSingleStep(5)
        self.speed_slider.setPageStep(10)
        self.speed_slider.setFixedWidth(160)
        self.speed_slider.setToolTip("How fast the voice speaks. 1.00 is the voice's own pace")
        self.speed_slider.valueChanged.connect(self.show_speed)
        self.speed_value = QLabel()
        self.speed_value.setMinimumWidth(36)
        self.speak_button = accent_button("Speak", "Speak the text (Ctrl+Enter)")
        self.speak_button.clicked.connect(lambda: self.speak())
        self.stop_button = QPushButton("Stop")
        self.stop_button.setToolTip("Stop speaking (Esc)")
        self.stop_button.clicked.connect(self.stop)
        self.save_button = QPushButton("Save as…")
        self.save_button.setToolTip("Write the speech as an Ogg Vorbis, MP3, FLAC or WAV file")
        self.save_button.clicked.connect(lambda: self.save())
        header.add_second(QLabel("Voice:"))
        header.add_second(self.voice_box)
        header.add_second(QLabel("Speed:"))
        header.add_second(self.speed_slider)
        header.add_second(self.speed_value)
        header.add_second(self.speak_button)
        header.add_second(self.stop_button)
        header.add_second(self.save_button)
        header.second_row.addStretch(1)
        layout.addLayout(header)

        self.pages = QStackedWidget()
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type or paste the text to speak")
        self.text_edit.setTabChangesFocus(True)
        self.pages.addWidget(self.text_edit)
        setup_page = QWidget()
        setup_layout = QVBoxLayout(setup_page)
        setup_layout.setContentsMargins(0, 0, 0, 0)
        setup_layout.addWidget(hint_label(SETUP_HINT.format(folder=engine_dir)))
        self.setup_button = accent_button("Set up the speech engine", "Download the speech engine and the voice model")
        self.setup_button.clicked.connect(self.set_up)
        setup_layout.addWidget(self.setup_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.setup_output = Terminal()
        setup_layout.addWidget(self.setup_output, 1)
        self.pages.addWidget(setup_page)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(central)

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.speak)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.speak)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.stop)

        self.speech.ready.connect(self.engine_ready)
        self.speech.chunk.connect(self.on_chunk)
        self.speech.done.connect(self.on_done)
        self.speech.canceled.connect(self.on_canceled)
        self.speech.saved.connect(self.on_saved)
        self.speech.failed.connect(self.on_failed)
        self.speech.stopped.connect(self.engine_stopped)
        self.player.finished.connect(self.update_controls)

        self.restore()
        if engine_setup.installed(engine_dir):
            self.start_engine()
        else:
            self.pages.setCurrentIndex(1)
            self.state.set_status("Not set up", "warn", "The speech engine is not on this machine yet")
        self.update_controls()

    # --- the settings --------------------------------------------------------------------------------------------
    def restore(self) -> None:
        text, speed = DEFAULT_TEXT, DEFAULT_SPEED
        if self.settings is not None:
            text = str(self.settings.value(TEXT_KEY, text))
            try:
                speed = float(self.settings.value(SPEED_KEY, speed))
            except (TypeError, ValueError):
                pass
        self.text_edit.setPlainText(text)
        self.speed_slider.setValue(round(speed * 100))
        self.show_speed(self.speed_slider.value())

    def remember(self) -> None:
        if self.settings is None:
            return
        self.settings.setValue(TEXT_KEY, self.text())
        self.settings.setValue(SPEED_KEY, self.speed())
        if self.voice():
            self.settings.setValue(VOICE_KEY, self.voice())

    def text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def voice(self) -> str:
        return str(self.voice_box.currentData() or "")

    def speed(self) -> float:
        return self.speed_slider.value() / 100

    def show_speed(self, value: int) -> None:
        self.speed_value.setText(f"{value / 100:.2f}")

    # --- the engine ----------------------------------------------------------------------------------------------
    def start_engine(self) -> None:
        self.pages.setCurrentIndex(0)
        self.state.set_status("Starting", "info", "The speech engine is loading its model")
        self.speech.start()
        self.update_controls()

    def engine_ready(self, voices: list) -> None:
        wanted = DEFAULT_VOICE
        if self.settings is not None:
            wanted = str(self.settings.value(VOICE_KEY, wanted))
        wanted = self.voice() or wanted         # the engine started again: the choice stays
        self.voice_box.clear()
        for voice in offered_voices([str(v) for v in voices]):
            self.voice_box.addItem(voice_label(voice), voice)
        index = max(self.voice_box.findData(wanted), self.voice_box.findData(DEFAULT_VOICE), 0)
        self.voice_box.setCurrentIndex(index)
        self.state.set_status("Ready", "ok")
        output = self.player.output_name()
        self.statusBar().showMessage(f"Playing on: {output}." if output else NO_OUTPUT)
        self.update_controls()
        if self.speak_when_ready:
            self.speak_when_ready = False
            self.speak()

    def engine_stopped(self) -> None:
        """The engine ended by itself: said, and Speak starts it again."""
        self.current = self.finished = self.save_after = None
        self.player.stop()
        self.state.set_status("Stopped", "bad", "The speech engine ended. Speak starts it again")
        self.statusBar().showMessage("The speech engine stopped. Speak starts it again.")
        self.update_controls()

    def busy(self) -> bool:
        return self.current is not None

    def update_controls(self) -> None:
        installed = self.pages.currentIndex() == 0
        ready = installed and self.speech.is_ready
        self.voice_box.setEnabled(ready)
        self.speed_slider.setEnabled(installed)
        self.speak_button.setEnabled(installed and (ready or not self.speech.running()))
        self.save_button.setEnabled(ready)
        self.stop_button.setEnabled(self.busy() or self.player.playing())
        if ready and self.state.kind in ("ok", "info"):
            if self.busy():
                self.state.set_status("Speaking" if self.save_after is None else "Making the speech", "info")
            else:
                self.state.set_status("Speaking" if self.player.playing() else "Ready",
                                      "info" if self.player.playing() else "ok")

    # --- speaking ------------------------------------------------------------------------------------------------
    def speak(self, play: bool = True) -> bool:
        """Speak the text as it is now; with *play* off it is only made (for Save as). False when nothing was
        asked of the engine."""
        if self.pages.currentIndex() != 0:
            return False
        if not self.speech.running():           # it ended by itself: start it, then speak
            self.speak_when_ready = play
            self.start_engine()
            return False
        if not self.speech.is_ready:
            return False
        text = self.text()
        if not text or not is_english(text):
            self.statusBar().showMessage(NOT_ENGLISH if text else NO_TEXT)
            return False
        self.remember()
        self.state.set_status("Ready", "ok")    # a failure before this one is over
        self.player.stop()
        if play:
            self.save_after = None
            self.player.start()
        self.current = Spoken(self.speech.speak(text, self.voice(), self.speed()), text, self.voice(), self.speed())
        self.statusBar().showMessage("Making the speech…")
        self.update_controls()
        return True

    def stop(self) -> None:
        if self.busy():
            self.speech.cancel()
        self.current = self.save_after = None
        self.player.stop()
        self.update_controls()

    def on_chunk(self, ident: int, index: int, count: int, pcm: bytes) -> None:
        if self.current is None or ident != self.current.ident:
            return                              # of a speak that was given up
        if self.save_after is None:
            self.player.feed(pcm)
        self.statusBar().showMessage(f"Sentence {index + 1} of {count}…")

    def on_done(self, ident: int, seconds: float, took: float) -> None:
        if self.current is None or ident != self.current.ident:
            return
        self.finished, self.current = self.current, None
        self.statusBar().showMessage(f"{seconds:.1f} s of speech, made in {took:.1f} s.")
        if self.save_after is not None:
            path, self.save_after = self.save_after, None
            self.speech.save(ident, path)
        else:
            self.player.end()
        self.update_controls()

    def on_canceled(self, ident: int) -> None:
        if self.current is not None and ident == self.current.ident:
            self.current = self.save_after = None
            self.update_controls()

    def on_failed(self, message: str) -> None:
        self.current = self.save_after = None
        self.player.stop()
        self.state.set_status("Failed", "bad", message)
        self.statusBar().showMessage(message)
        self.update_controls()

    # --- saving --------------------------------------------------------------------------------------------------
    def save_dir(self) -> Path:
        default = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation) or Path.home())
        if self.settings is not None:
            return Path(str(self.settings.value(SAVE_DIR_KEY, str(default))))
        return default

    def save_format(self) -> str:
        chosen = str(self.settings.value(FORMAT_KEY, DEFAULT_FORMAT)) if self.settings is not None else DEFAULT_FORMAT
        return chosen if chosen in FILTERS else DEFAULT_FORMAT

    def save(self, path: Path | None = None) -> Path | None:
        """Write the speech of the text as it is now to *path*, or to the file chosen in the dialog; None when
        canceled or when there is nothing to speak. The file is there once the status line says Saved."""
        if not self.speech.is_ready:
            return None
        if not self.text() or not is_english(self.text()):
            self.statusBar().showMessage(NOT_ENGLISH if self.text() else NO_TEXT)
            return None
        if path is None:
            suffix = self.save_format()
            filters = ";;".join([FILTERS[suffix], *(f for s, f in FILTERS.items() if s != suffix)])
            chosen, used = QFileDialog.getSaveFileName(self, "Save the speech",
                                                       str(self.save_dir() / f"speech{suffix}"), filters)
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
        spoken = self.finished if not self.busy() else None
        if spoken is not None and spoken.same(self.text(), self.voice(), self.speed()):
            self.speech.save(spoken.ident, path)
        else:                                   # not spoken yet, or changed since: made first, without playing
            if not self.speak(play=False):
                return None
            self.save_after = path
            self.update_controls()
        return path

    def on_saved(self, _ident: int, path: str) -> None:
        self.statusBar().showMessage(f"Saved {path}")

    # --- setting the engine up -----------------------------------------------------------------------------------
    def set_up(self) -> None:
        """Run the steps of engine_setup one after the other, their output in the window; then start the engine."""
        try:
            self.setup_steps = engine_setup.steps(self.engine_dir)
        except engine_setup.SetupError as error:
            self.setup_output.appendPlainText(str(error))
            return
        self.setup_button.setEnabled(False)
        self.state.set_status("Setting up", "info")
        self.engine_dir.mkdir(parents=True, exist_ok=True)
        self._next_step()

    def _next_step(self) -> None:
        if not self.setup_steps:
            self.setup_process = None
            self.setup_button.setEnabled(True)
            if engine_setup.installed(self.engine_dir):
                self.setup_output.appendPlainText("The speech engine is set up.")
                self.start_engine()
            else:
                self._setup_failed("The speech engine is still not complete.")
            return
        command = self.setup_steps.pop(0)
        self.setup_output.appendPlainText("$ " + " ".join(command))
        process = self.setup_process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda: self._setup_said(process))
        process.finished.connect(lambda code, _status: self._step_ended(process, code))
        process.errorOccurred.connect(
            lambda error: error == QProcess.ProcessError.FailedToStart and self._step_ended(process, -1))
        process.start(command[0], command[1:])

    def _setup_said(self, process: QProcess) -> None:
        text = bytes(process.readAllStandardOutput()).decode("utf-8", "replace").rstrip()
        if text:
            self.setup_output.appendPlainText(text)

    def _step_ended(self, process: QProcess, code: int) -> None:
        if process is not self.setup_process:
            return
        self._setup_said(process)
        process.deleteLater()
        if code != 0:
            self.setup_steps = []
            self.setup_process = None
            self.setup_button.setEnabled(True)
            self._setup_failed(f"This step failed (exit code {code}). Click Set up the speech engine to try again.")
        else:
            self._next_step()

    def _setup_failed(self, message: str) -> None:
        self.setup_output.appendPlainText(message)
        self.state.set_status("Not set up", "warn", message)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        self.remember()
        if self.setup_process is not None:
            process, self.setup_process = self.setup_process, None
            process.kill()
            process.waitForFinished(1000)
        self.player.close()
        self.speech.close()
        event.accept()


__all__ = ["ABOUT", "DEFAULT_FORMAT", "DEFAULT_TEXT", "FILTERS", "FORMAT_KEY", "NO_OUTPUT", "NO_TEXT", "SAVE_DIR_KEY",
           "SETUP_HINT", "SPEED_KEY", "TEXT_KEY", "VOICE_KEY", "MainWindow", "Spoken"]
