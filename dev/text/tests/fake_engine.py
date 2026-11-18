# SPDX-License-Identifier: GPL-3.0-or-later
"""A model that makes a tone for the tests, and, run as a program, the engine's loop on it: the protocol of
engine.py serve without the Kokoro model (test_speech.py starts it as the window starts the real engine)."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
for path in (APP.parents[1] / "core", APP):         # as run.sh and conftest.py have them
    sys.path.insert(0, str(path))

from textspeech import engine  # noqa: E402

VOICES = ["bf_emma", "af_heart", "ef_dora", "af_bella", "zf_xiaobei", "bm_george"]  # as the model: not all offered


class FakeKokoro:
    """create() as kokoro-onnx has it: a tenth of a second of tone per call, and its two ValueErrors."""

    def __init__(self, during=None):
        self.asked: list[tuple[str, str, float, str]] = []
        self.during = during                    # called in each create(), with the text

    def get_voices(self) -> list[str]:
        return sorted(VOICES)

    def create(self, text: str, voice: str, speed: float = 1.0, lang: str = "en-us"):
        import numpy as np
        if voice not in VOICES:
            raise ValueError(f"Voice {voice} not found in available voices")
        if not any(letter.isalnum() for letter in text):
            raise ValueError(f"Nothing to synthesize, {text!r} produced no phonemes")
        self.asked.append((text, voice, speed, lang))
        if self.during is not None:
            self.during(text)
        tone = np.sin(np.arange(engine.RATE // 10) * 2 * np.pi * 440 / engine.RATE) * 0.5
        return tone.astype(np.float32), engine.RATE


if __name__ == "__main__":
    if "--fail" in sys.argv:
        sys.exit(3)
    server = engine.Server(FakeKokoro(), sys.stdout)
    threading.Thread(target=server.read, args=(sys.stdin,), daemon=True).start()
    sys.exit(server.run())
