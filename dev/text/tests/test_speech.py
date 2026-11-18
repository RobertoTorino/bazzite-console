# SPDX-License-Identifier: GPL-3.0-or-later
"""The window's side of the engine, on a real process: tests/fake_engine.py speaks the engine's protocol with a
model that makes a tone."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from textspeech.speech import Speech

FAKE = [sys.executable, str(Path(__file__).with_name("fake_engine.py"))]


def _wait(condition, seconds: float = 20.0) -> bool:
    end = time.monotonic() + seconds
    while not condition() and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)
    return condition()


def _listening(speech: Speech) -> list[tuple]:
    seen: list[tuple] = []
    for name in ("ready", "chunk", "done", "canceled", "saved", "failed", "stopped"):
        getattr(speech, name).connect(lambda *args, n=name: seen.append((n, *args)))
    return seen


def test_the_engine_starts_speaks_saves_and_quits(qapp, tmp_path):
    speech = Speech(FAKE)
    seen = _listening(speech)
    assert not speech.running() and not speech.is_ready

    speech.start()
    speech.start()                              # a second start changes nothing
    assert _wait(lambda: speech.is_ready)
    assert seen == [("ready", ["af_bella", "af_heart", "bf_emma"])]

    ident = speech.speak("One. Two.", "af_heart", 1.0)
    assert ident == 1 and _wait(lambda: seen[-1][0] == "done")
    chunks = [event for event in seen if event[0] == "chunk"]
    assert [(c[1], c[2], c[3]) for c in chunks] == [(1, 0, 2), (1, 1, 2)]
    assert isinstance(chunks[0][4], bytes) and len(chunks[0][4]) == 2 * (2400 + 6000)
    assert seen[-1][:2] == ("done", 1) and seen[-1][2] > 0.3

    speech.save(ident, tmp_path / "speech.wav")
    assert _wait(lambda: seen[-1][0] == "saved")
    assert seen[-1] == ("saved", 1, str(tmp_path / "speech.wav")) and (tmp_path / "speech.wav").stat().st_size > 1000

    speech.save(5, tmp_path / "other.wav")
    assert _wait(lambda: seen[-1][0] == "failed") and "no longer in memory" in seen[-1][1]
    assert speech.speak("More.", "af_heart", 1.0) == 2

    process = speech.process
    speech.close()
    assert not speech.running() and not speech.is_ready and process.exitCode() == 0
    assert ("stopped",) not in seen             # closed on purpose: nothing to say


def test_an_engine_that_ends_by_itself_is_said(qapp):
    speech = Speech([*FAKE, "--fail"])
    seen = _listening(speech)
    speech.start()
    assert _wait(lambda: ("stopped",) in seen)
    assert not speech.running() and not speech.is_ready
    speech.speak("Unheard.", "af_heart", 1.0)   # nothing to write to: no error
    speech.close()


def test_an_engine_that_cannot_start_is_said(qapp, tmp_path):
    speech = Speech([str(tmp_path / "no-python"), "engine.py"])
    seen = _listening(speech)
    speech.start()
    assert _wait(lambda: ("stopped",) in seen) and seen.count(("stopped",)) == 1
