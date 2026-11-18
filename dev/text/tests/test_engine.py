# SPDX-License-Identifier: GPL-3.0-or-later
"""The speech engine without its model: the text cut into sentences, the voices' names and languages, the model
files downloaded and checked, and the loop that speaks, cancels and saves, on a model that makes a tone."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import queue

import pytest

from fake_engine import FakeKokoro
from textspeech import engine
from textspeech.engine import PARAGRAPH_PAUSE as PARAGRAPH, SENTENCE_PAUSE as SENTENCE, split_text


def test_a_text_is_cut_after_each_sentence():
    assert split_text("Good morning! How are you? Fine.") == [("Good morning!", SENTENCE), ("How are you?", SENTENCE),
                                                              ("Fine.", 0.0)]
    assert split_text("One sentence without a stop") == [("One sentence without a stop", 0.0)]
    assert split_text('"Go!" she said. (He went.) Done...  Really') == [
        ('"Go!" she said.', SENTENCE), ("(He went.)", SENTENCE), ("Done...", SENTENCE), ("Really", 0.0)]
    assert split_text("") == [] and split_text("  \n\n  ") == []


def test_an_abbreviation_an_initial_and_a_lower_case_word_end_no_sentence():
    assert split_text("Dr. Smith is here at 3 p.m. sharp. He waits.") == [
        ("Dr. Smith is here at 3 p.m. sharp.", SENTENCE), ("He waits.", 0.0)]
    assert split_text("See J. R. Smith, e.g. Monday. Version 2.5 is out.") == [
        ("See J. R. Smith, e.g. Monday.", SENTENCE), ("Version 2.5 is out.", 0.0)]


def test_an_empty_line_is_a_paragraph_and_a_line_break_a_space():
    assert split_text("First line\nstill the first. Second.\n\n\nNew paragraph.") == [
        ("First line still the first.", SENTENCE), ("Second.", PARAGRAPH), ("New paragraph.", 0.0)]


def test_only_the_english_female_voices_are_offered_american_first():
    assert set(engine.LANGUAGES) == {"a", "b"}
    assert engine.language("af_heart") == ("American English", "en-us") and engine.language("bf_emma")[1] == "en-gb"
    assert engine.voice_label("af_heart") == "Heart · American English"
    assert engine.voice_label("bf_isabella") == "Isabella · British English"
    model = ["zf_xiaobei", "bf_emma", "af_heart", "ef_dora", "am_adam", "af_bella", "jm_kumo", "pm_alex", "bm_lewis",
             "hf_alpha", "if_sara", "ff_siwis", "xx_new", "a", "bx_odd"]
    assert engine.offered_voices(model) == ["af_bella", "af_heart", "bf_emma"]
    assert engine.DEFAULT_VOICE in engine.offered_voices(model)


def test_a_text_with_letters_of_another_script_is_not_english():
    for text in ("Good morning!", "A café, a naïve façade: 100 % – “fine”… £5 & 3 °C 🙂", "", "1, 2, 3."):
        assert engine.is_english(text), text
    for text in ("你好。", "Привет, world", "नमस्ते", "こんにちは", "Καλημέρα", "مرحبا"):
        assert not engine.is_english(text), text


def test_the_pinned_files_are_the_half_precision_model_and_the_voices():
    assert set(engine.FILES) == {engine.MODEL, engine.VOICES} and engine.MODEL.endswith(".fp16.onnx")
    assert all(size > 1e6 and len(digest) == 64 for size, digest in engine.FILES.values())
    assert engine.BASE_URL.startswith("https://github.com/thewh1teagle/kokoro-onnx/releases/download/")


def _published(folder, **files: bytes) -> tuple[str, dict]:
    folder.mkdir()
    for name, data in files.items():
        (folder / name).write_bytes(data)
    return folder.as_uri() + "/", {name: (len(data), hashlib.sha256(data).hexdigest()) for name, data in files.items()}


def test_fetch_downloads_what_is_missing_and_checks_it(tmp_path):
    base, files = _published(tmp_path / "site", **{"model.onnx": b"m" * 5000, "voices.bin": b"v" * 300})
    models, said = tmp_path / "models", []
    assert engine.missing_files(models) == list(engine.FILES)

    assert engine.fetch(models, base, files, say=said.append)
    assert (models / "model.onnx").read_bytes() == b"m" * 5000 and (models / "voices.bin").read_bytes() == b"v" * 300
    assert not list(models.glob("*.part")) and "model.onnx is done." in said

    (models / "voices.bin").write_bytes(b"v" * 299 + b"x")       # damaged: fetched again; the model is kept
    said.clear()
    assert engine.fetch(models, base, files, say=said.append)
    assert "model.onnx is here already." in said and (models / "voices.bin").read_bytes() == b"v" * 300


def test_fetch_keeps_no_file_that_is_not_the_pinned_one(tmp_path):
    base, files = _published(tmp_path / "site", **{"model.onnx": b"m" * 5000})
    wrong = {"model.onnx": (5000, "0" * 64)}
    said = []
    assert not engine.fetch(tmp_path / "models", base, wrong, say=said.append)
    assert list((tmp_path / "models").iterdir()) == [] and "SHA-256 differs" in said[-1]
    assert not engine.fetch(tmp_path / "models", base, {"gone.onnx": (10, "0" * 64)}, say=said.append)
    assert "The download of gone.onnx failed." in said[-1] and list((tmp_path / "models").iterdir()) == []


# --- the loop --------------------------------------------------------------------------------------------------------
class Commands(queue.Queue):
    """The commands of a test, each taken when the one before is over, as a window sends them; what arrives while a
    text is being spoken goes in *meanwhile*."""

    def __init__(self):
        super().__init__()
        self.meanwhile: list[dict] = []

    def get_nowait(self) -> dict:
        if not self.meanwhile:
            raise queue.Empty
        return self.meanwhile.pop(0)


def _server(kokoro=None) -> tuple[engine.Server, io.StringIO]:
    out = io.StringIO()
    return engine.Server(kokoro or FakeKokoro(), out, Commands()), out


def _events(out: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in out.getvalue().splitlines()]


def _run(server: engine.Server, *commands: dict) -> int:
    for command in (*commands, {"cmd": "quit"}):
        server.commands.put(command)
    return server.run()


def test_a_text_is_spoken_a_sentence_at_a_time():
    server, out = _server()
    assert _run(server, {"cmd": "speak", "id": 7, "text": "One. Two.\n\nThree.", "voice": "bf_emma", "speed": 1.2}) == 0
    ready, *chunks, done = _events(out)
    assert ready == {"event": "ready", "voices": ["af_bella", "af_heart", "bf_emma"], "rate": 24000}
    assert [(c["event"], c["id"], c["index"], c["count"]) for c in chunks] == [("chunk", 7, i, 3) for i in range(3)]
    # 16-bit mono: a tenth of a second of tone, and the pause after it (a sentence, a paragraph, none)
    assert [len(base64.b64decode(c["pcm"])) for c in chunks] == [2 * (2400 + 6000), 2 * (2400 + 14400), 2 * 2400]
    assert done["event"] == "done" and done["id"] == 7 and done["seconds"] == pytest.approx(1.15)
    assert server.kokoro.asked == [("One.", "bf_emma", 1.2, "en-gb"), ("Two.", "bf_emma", 1.2, "en-gb"),
                                   ("Three.", "bf_emma", 1.2, "en-gb")]


def test_the_voice_and_the_speed_have_defaults_and_limits():
    server, _out = _server()
    _run(server, {"cmd": "speak", "id": 1, "text": "Hi."}, {"cmd": "speak", "id": 2, "text": "Hi.", "speed": 9})
    assert server.kokoro.asked == [("Hi.", "af_heart", 0.85, "en-us"), ("Hi.", "af_heart", 2.0, "en-us")]


def test_a_cancel_ends_a_speech_at_the_next_sentence():
    server, out = _server()
    server.kokoro.during = lambda text: text == "One." and server.commands.meanwhile.append({"cmd": "cancel"})
    _run(server, {"cmd": "speak", "id": 1, "text": "One. Two. Three.", "voice": "af_heart"})
    assert [e["event"] for e in _events(out)] == ["ready", "chunk", "canceled"]
    assert server.spoken is None                # nothing to save of a canceled speech


def test_a_new_speak_takes_the_place_of_the_one_being_made():
    server, out = _server()
    server.kokoro.during = lambda text: text == "One." and server.commands.meanwhile.append(
        {"cmd": "speak", "id": 2, "text": "Other.", "voice": "af_heart"})
    _run(server, {"cmd": "speak", "id": 1, "text": "One. Two.", "voice": "af_heart"})
    assert [(e["event"], e.get("id")) for e in _events(out)] == [
        ("ready", None), ("chunk", 1), ("canceled", 1), ("chunk", 2), ("done", 2)]


def test_what_cannot_be_spoken_is_said_and_the_loop_goes_on():
    server, out = _server()
    _run(server, {"cmd": "speak", "id": 1, "text": "---", "voice": "af_heart"},
         {"cmd": "speak", "id": 2, "text": "Hi.", "voice": "xx_none"},
         {"cmd": "speak", "id": 3, "text": "--- Hi. ***", "voice": "af_heart"})
    events = _events(out)[1:]
    assert events[0] == {"event": "error", "id": 1, "message": "No words were found in this text."}
    assert events[1] == {"event": "error", "id": 2, "message": "xx_none is not one of the English female voices."}
    assert [e["event"] for e in events[2:]] == ["chunk", "done"]        # the part with words is spoken


def test_only_english_is_spoken():
    """A voice of another language and a male voice, though the model has them, and a text in another script are
    all refused."""
    server, out = _server()
    _run(server, {"cmd": "speak", "id": 1, "text": "Buenos días.", "voice": "ef_dora"},
         {"cmd": "speak", "id": 2, "text": "Hello. 你好。", "voice": "af_heart"},
         {"cmd": "speak", "id": 3, "text": "Hello.", "voice": "bm_george"},
         {"cmd": "speak", "id": 4, "text": "Hello.", "voice": "bf_emma"})
    events = _events(out)[1:]
    assert events[0] == {"event": "error", "id": 1, "message": "ef_dora is not one of the English female voices."}
    assert events[1] == {"event": "error", "id": 2, "message": engine.NOT_ENGLISH}
    assert events[2] == {"event": "error", "id": 3, "message": "bm_george is not one of the English female voices."}
    assert [e["event"] for e in events[3:]] == ["chunk", "done"] and server.kokoro.asked == [
        ("Hello.", "bf_emma", 0.85, "en-gb")]


@pytest.mark.parametrize("suffix", sorted(engine.FORMATS))
def test_the_last_speech_is_saved_in_each_format(tmp_path, suffix):
    import soundfile
    server, out = _server()
    path = tmp_path / "new folder" / f"speech{suffix}"
    _run(server, {"cmd": "speak", "id": 4, "text": "One. Two.", "voice": "af_heart"},
         {"cmd": "save", "id": 4, "path": str(path)})
    assert _events(out)[-1] == {"event": "saved", "id": 4, "path": str(path)}
    info = soundfile.info(str(path))
    assert info.samplerate == 24000 and info.channels == 1 and info.duration == pytest.approx(0.45, abs=0.06)
    assert [p.name for p in path.parent.iterdir()] == [path.name]       # no .part left


def test_a_long_speech_is_written_a_second_at_a_time(tmp_path):
    import numpy as np
    import soundfile
    server, out = _server()
    server.spoken = (1, np.zeros(engine.RATE * 5 + 123, dtype=np.float32))
    _run(server, {"cmd": "save", "id": 1, "path": str(tmp_path / "long.ogg")})
    assert _events(out)[-1]["event"] == "saved"
    assert soundfile.info(str(tmp_path / "long.ogg")).frames == engine.RATE * 5 + 123


def test_a_save_that_cannot_be_done_is_said(tmp_path):
    server, out = _server()
    _run(server, {"cmd": "save", "id": 1, "path": str(tmp_path / "a.ogg")},
         {"cmd": "speak", "id": 1, "text": "Hi.", "voice": "af_heart"},
         {"cmd": "save", "id": 1, "path": str(tmp_path / "a.xyz")},
         {"cmd": "save", "id": 9, "path": str(tmp_path / "a.ogg")})
    errors = [e["message"] for e in _events(out) if e["event"] == "error"]
    assert errors == ["This speech is no longer in memory. Speak the text again.",
                      "Unknown format .xyz. Use .ogg, .wav, .flac, .mp3.",
                      "This speech is no longer in memory. Speak the text again."]
    assert list(tmp_path.iterdir()) == []


def test_the_reader_takes_commands_and_ends_with_a_quit():
    server = engine.Server(FakeKokoro(), io.StringIO(), queue.Queue())
    server.read(io.StringIO('{"cmd": "cancel"}\nnot json\n[1]\n{"cmd": "speak", "id": 1}\n'))
    taken = [server.commands.get_nowait() for _ in range(3)]
    assert taken == [{"cmd": "cancel"}, {"cmd": "speak", "id": 1}, {"cmd": "quit"}]


def test_a_save_while_a_text_is_spoken_is_refused_and_the_speech_goes_on():
    server, out = _server()
    server.kokoro.during = lambda text: text == "One." and server.commands.meanwhile.append(
        {"cmd": "save", "id": 1, "path": "/nowhere/a.ogg"})
    _run(server, {"cmd": "speak", "id": 1, "text": "One. Two.", "voice": "af_heart"})
    assert [e["event"] for e in _events(out)] == ["ready", "chunk", "error", "chunk", "done"]
