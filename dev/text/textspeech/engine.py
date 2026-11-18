# SPDX-License-Identifier: GPL-3.0-or-later
"""The speech engine: a program of its own, run with the engine's Python (engine_setup.py), never with the
checkout's dev venv, since onnxruntime has no wheel for that venv's Python. It stands alone: only the standard
library at import time, so the window imports its names (the voices' languages, the text's parts) too.

    python engine.py fetch --models DIR     download the model and the voices, each checked against its SHA-256
    python engine.py serve --models DIR     load the model once, then speak on request

serve reads one JSON command per line on stdin and writes one JSON event per line on stdout:

    {"cmd": "speak", "id": 1, "text": "...", "voice": "af_heart", "speed": 0.85}
    {"cmd": "save", "id": 1, "path": "/home/me/Music/speech.ogg"}       the format follows the suffix
    {"cmd": "cancel"}    {"cmd": "quit"}

    {"event": "ready", "voices": [...], "rate": 24000}          the English female voices: no other is offered
    {"event": "chunk", "id": 1, "index": 0, "count": 3, "pcm": "<base64, 16-bit mono>"}     one part of the text
    {"event": "done", "id": 1, "seconds": 13.1, "took": 4.2}
    {"event": "canceled", "id": 1}    {"event": "saved", "id": 1, "path": "..."}
    {"event": "error", "id": 1, "message": "..."}

The text is spoken a sentence at a time, so the first one plays while the next is made, and a cancel or a new speak
takes effect at the next sentence. The last finished speech stays in memory: save writes it in any format without
making it again."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import queue
import re
import sys
import threading
import time
import unicodedata
import urllib.request
from pathlib import Path

RATE = 24000                            # Kokoro's sample rate
BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
# The half-precision model: as fast as the full one on a CPU (measured on the test machine: 13 s of speech in 4.3 s, both)
# at half the download; the 8-bit one is smaller still and 2.3 times slower. name: (bytes, SHA-256)
MODEL = "kokoro-v1.0.fp16.onnx"
VOICES = "voices-v1.0.bin"
FILES = {
    MODEL: (163527961, "f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96"),
    VOICES: (28214398, "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"),
}

# English female voices only (owner, 18-11-2026): the model has male voices and voices in seven more languages, and
# none of them is offered. A voice's first letter is its language: (the name shown, eSpeak NG's code for the
# phonemes); its second is f for a female voice.
LANGUAGES = {
    "a": ("American English", "en-us"),
    "b": ("British English", "en-gb"),
}
DEFAULT_VOICE = "af_heart"
DEFAULT_SPEED = 0.85
SPEED_RANGE = (0.5, 2.0)                # what the model takes
FORMATS = {".ogg": "OGG", ".wav": "WAV", ".flac": "FLAC", ".mp3": "MP3"}   # a saved file's suffix: libsndfile's name

NOT_ENGLISH = "Only English text can be spoken. This text has letters of another script."
NOT_OFFERED = "{voice} is not one of the English female voices."

SENTENCE_PAUSE = 0.25                   # seconds of silence after a sentence, and after a paragraph
PARAGRAPH_PAUSE = 0.6
ABBREVIATIONS = frozenset({"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "no", "e.g", "i.e",
                           "fig", "approx", "inc", "ltd", "mt"})
# A sentence ends at . ! ? … (with the quotes and brackets that close it) before white space
_END = re.compile(r"[.!?…]+[\"'”’»)\]]*(?=\s)")


def language(voice: str) -> tuple[str, str]:
    """The language of *voice* ("af_heart"): its name and eSpeak NG's code."""
    return LANGUAGES.get(voice[:1], LANGUAGES["a"])


def voice_label(voice: str) -> str:
    """"af_heart" as the window shows it: "Heart · American English"."""
    name = voice.split("_", 1)[-1].replace("_", " ").title()
    return f"{name} · {language(voice)[0]}"


def offered_voices(voices: list[str]) -> list[str]:
    """The voices of *voices* that are offered, the English female ones ("af_", "bf_"), in the order of the window's
    list: American, then British, by name."""
    order = list(LANGUAGES)
    return sorted((v for v in voices if v[:1] in order and v[1:3] == "f_"), key=lambda v: (order.index(v[:1]), v))


def is_english(text: str) -> bool:
    """False for a text with a letter of another script (Cyrillic, Greek, Chinese): that is no English text. A text
    in another language written in Latin letters cannot be told apart here, and is read as English."""
    return all(unicodedata.name(letter, "").startswith("LATIN") for letter in text if letter.isalpha())


def _sentences(paragraph: str) -> list[str]:
    """*paragraph* cut after each sentence. A stop is no end after an abbreviation or an initial (Dr. Smith,
    J. Smith), and nothing is one before a lower-case letter (3 p.m. sharp; "Go!" she said)."""
    found, start = [], 0
    for match in _END.finditer(paragraph):
        rest = paragraph[match.end():].lstrip()
        if not rest:
            break
        if rest[0].islower():
            continue
        if match.group().startswith("."):
            word = re.split(r"[\s(\[\"'“‘]", paragraph[start:match.start()])[-1].lower()
            if word in ABBREVIATIONS or len(word) == 1 and word.isalpha():
                continue
        found.append(paragraph[start:match.end()].strip())
        start = match.end()
    return [*found, paragraph[start:].strip()]


def split_text(text: str) -> list[tuple[str, float]]:
    """*text* as the parts spoken one at a time: each sentence with the silence after it in seconds (a longer one
    at the end of a paragraph, none after the last). A paragraph ends at an empty line; a single line break is a
    space."""
    parts: list[tuple[str, float]] = []
    for paragraph in re.split(r"\n\s*\n", text):
        sentences = [s for s in _sentences(" ".join(paragraph.split())) if s]
        parts += [(sentence, SENTENCE_PAUSE) for sentence in sentences]
        if sentences:
            parts[-1] = (parts[-1][0], PARAGRAPH_PAUSE)
    if parts:
        parts[-1] = (parts[-1][0], 0.0)
    return parts


# --- the model files -------------------------------------------------------------------------------------------------
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def missing_files(models: Path) -> list[str]:
    """The model files not in *models* yet, or not at their full size (a quick look: fetch checks the SHA-256)."""
    return [name for name, (size, _digest) in FILES.items()
            if not (models / name).is_file() or (models / name).stat().st_size != size]


def fetch(models: Path, base_url: str = BASE_URL, files: dict[str, tuple[int, str]] = FILES, say=print) -> bool:
    """Download each of *files* that *models* lacks, to a .part beside it first; a file is kept only when its
    SHA-256 is the pinned one. False when one failed."""
    models.mkdir(parents=True, exist_ok=True)
    for name, (size, digest) in files.items():
        path, part = models / name, models / f"{name}.part"
        if path.is_file() and path.stat().st_size == size and sha256(path) == digest:
            say(f"{name} is here already.")
            continue
        say(f"Downloading {name}, {size / 1e6:.0f} MB, from {base_url}")
        try:
            request = urllib.request.Request(base_url + name, headers={"User-Agent": "python-urllib"})
            with urllib.request.urlopen(request, timeout=60) as response, open(part, "wb") as out:
                got, shown = 0, 0
                while block := response.read(1 << 20):
                    out.write(block)
                    got += len(block)
                    if size and got * 10 // size > shown:
                        shown = got * 10 // size
                        say(f"  {min(shown * 10, 100)} %")
        except OSError as error:
            part.unlink(missing_ok=True)
            say(f"The download of {name} failed. {error}")
            return False
        if sha256(part) != digest:
            part.unlink(missing_ok=True)
            say(f"The download of {name} is not the expected file, so it was removed. Its SHA-256 differs.")
            return False
        part.replace(path)
        say(f"{name} is done.")
    return True


# --- speaking --------------------------------------------------------------------------------------------------------
class Server:
    """serve's loop: the commands arrive on a thread, so a cancel or a new speak is seen between two sentences."""

    def __init__(self, kokoro, out, commands: queue.Queue | None = None):
        self.kokoro = kokoro
        self.out = out
        self.commands: queue.Queue = commands if commands is not None else queue.Queue()
        self.spoken: tuple[int, object] | None = None   # the last finished speech: its id and its samples

    def emit(self, event: str, **fields) -> None:
        self.out.write(json.dumps({"event": event, **fields}) + "\n")
        self.out.flush()

    def read(self, stream) -> None:
        """The reader thread: every line of *stream* a command; its end is a quit."""
        for line in stream:
            try:
                command = json.loads(line)
            except ValueError:
                continue
            if isinstance(command, dict):
                self.commands.put(command)
        self.commands.put({"cmd": "quit"})

    def run(self) -> int:
        self.emit("ready", voices=offered_voices(self.kokoro.get_voices()), rate=RATE)
        while True:
            command = self.commands.get()
            while command is not None:              # a speak hands back the command that interrupted it
                kind = command.get("cmd")
                if kind == "quit":
                    return 0
                following = None
                try:
                    if kind == "speak":
                        following = self.speak(command)
                    elif kind == "save":
                        self.save(command)
                except Exception as error:  # noqa: BLE001  (whatever the model or the file raises: said, not fatal)
                    self.emit("error", id=command.get("id"), message=str(error))
                command = following

    def speak(self, command: dict) -> dict | None:
        """Speak the command's text a part at a time; the command that interrupted it, or None when it finished."""
        import numpy as np
        ident, voice = command.get("id"), str(command.get("voice") or DEFAULT_VOICE)
        speed = min(max(float(command.get("speed") or DEFAULT_SPEED), SPEED_RANGE[0]), SPEED_RANGE[1])
        text = str(command.get("text") or "")
        if voice not in offered_voices(self.kokoro.get_voices()):
            raise ValueError(NOT_OFFERED.format(voice=voice))
        if not is_english(text):
            raise ValueError(NOT_ENGLISH)
        parts = split_text(text)
        started, made = time.monotonic(), []
        for index, (sentence, pause) in enumerate(parts):
            try:
                interrupt = self.commands.get_nowait()
            except queue.Empty:
                interrupt = None
            if interrupt is not None and interrupt.get("cmd") == "save":
                self.emit("error", id=interrupt.get("id"), message="Nothing can be saved while a text is spoken.")
            elif interrupt is not None:
                self.emit("canceled", id=ident)
                return None if interrupt.get("cmd") == "cancel" else interrupt
            try:
                audio, _rate = self.kokoro.create(sentence, voice=voice, speed=speed, lang=language(voice)[1])
            except ValueError:
                continue                            # a part without anything to say (a row of dashes)
            if pause:
                audio = np.concatenate([audio, np.zeros(int(pause * RATE), dtype=audio.dtype)])
            made.append(audio)
            pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2").tobytes()
            self.emit("chunk", id=ident, index=index, count=len(parts), pcm=base64.b64encode(pcm).decode("ascii"))
        if not made:
            self.emit("error", id=ident, message="No words were found in this text.")
            return None
        samples = np.concatenate(made)
        self.spoken = (ident, samples)
        self.emit("done", id=ident, seconds=round(len(samples) / RATE, 2), took=round(time.monotonic() - started, 2))
        return None

    def save(self, command: dict) -> None:
        import soundfile
        ident, path = command.get("id"), Path(str(command.get("path") or ""))
        if self.spoken is None or self.spoken[0] != ident:
            raise ValueError("This speech is no longer in memory. Speak the text again.")
        if path.suffix.lower() not in FORMATS:
            raise ValueError(f"Unknown format {path.suffix or path.name}. Use {', '.join(FORMATS)}.")
        path.parent.mkdir(parents=True, exist_ok=True)
        samples, part = self.spoken[1], path.with_name(f".{path.name}.part")
        try:
            # A second at a time: libsndfile's Ogg writer crashes on a long speech handed over in one piece
            with soundfile.SoundFile(str(part), "w", samplerate=RATE, channels=1,
                                     format=FORMATS[path.suffix.lower()]) as out:
                for start in range(0, len(samples), RATE):
                    out.write(samples[start:start + RATE])
            part.replace(path)
        finally:
            part.unlink(missing_ok=True)
        self.emit("saved", id=ident, path=str(path))


def serve(models: Path) -> int:
    # The protocol keeps the real stdout; whatever a library prints goes to stderr, the window's log
    out = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    try:
        import onnxruntime
        from kokoro_onnx import Kokoro
        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3              # errors only: the model's load warns about every folded node
        session = onnxruntime.InferenceSession(str(models / MODEL), options, providers=["CPUExecutionProvider"])
        kokoro = Kokoro.from_session(session, str(models / VOICES))
    except Exception as error:  # noqa: BLE001  (a missing package or model file: said, then over)
        out.write(json.dumps({"event": "error", "id": None, "message": f"The engine could not start: {error}"}) + "\n")
        out.flush()
        return 1
    server = Server(kokoro, out)
    threading.Thread(target=server.read, args=(sys.stdin,), daemon=True).start()
    return server.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine", description="The speech engine of Text to Speech.")
    parser.add_argument("action", choices=("fetch", "serve"))
    parser.add_argument("--models", type=Path, required=True, help="the folder of the model files")
    args = parser.parse_args(argv)
    if args.action == "fetch":
        return 0 if fetch(args.models, say=lambda line: print(line, flush=True)) else 1
    return serve(args.models)


if __name__ == "__main__":
    sys.exit(main())
