# SPDX-License-Identifier: GPL-3.0-or-later
"""Sound files: another rate and one channel become the mix's rate in stereo, each format is written and read back,
a failed write leaves nothing, and a drawing gets its peaks."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile

from remix_studio import audio
from remix_studio.audio import FORMATS, AudioError
from remix_studio.pad import RATE


def tone(hz: float, rate: int, seconds: float = 1.0) -> np.ndarray:
    return (0.5 * np.sin(2 * np.pi * hz * np.arange(int(rate * seconds)) / rate)).astype(np.float32)[:, None]


@pytest.mark.parametrize("rate", [24000, 44100, 96000])
def test_another_rate_becomes_the_mixes_rate_with_the_same_sound(rate):
    found = audio.resample(tone(440.0, rate), rate)
    assert found.shape == (RATE, 1) and found.dtype == np.float32
    assert np.allclose(found[1000:-1000], tone(440.0, RATE)[1000:-1000], atol=2e-3)


def test_going_down_drops_what_the_new_rate_cannot_hold():
    found = audio.resample(tone(30000.0, 96000), 96000)     # 30 kHz cannot be in a 48 kHz sound
    assert float(np.abs(found[1000:-1000]).max()) < 0.01


def test_the_same_rate_and_an_empty_sound_stay_as_they_are():
    sound = tone(440.0, RATE)
    assert audio.resample(sound, RATE) is sound
    assert audio.resample(np.zeros((0, 1), np.float32), 24000).shape == (0, 1)


def test_one_channel_goes_to_both_sides_and_more_than_two_lose_the_rest():
    mono = tone(440.0, RATE)
    assert np.array_equal(audio.stereo(mono), np.hstack([mono, mono]))
    many = np.hstack([mono, mono * 2, mono * 3])
    assert np.array_equal(audio.stereo(many), many[:, :2])


def test_a_voice_file_loads_as_stereo_at_the_mixes_rate(tmp_path):
    path = tmp_path / "voice.wav"
    soundfile.write(str(path), tone(440.0, 24000, 2.0), 24000)
    found = audio.load(path)
    assert found.shape == (2 * RATE, 2) and found.dtype == np.float32 and found.flags["C_CONTIGUOUS"]


def test_what_is_no_sound_file_says_so(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not a sound")
    with pytest.raises(AudioError, match="notes.txt is not a sound file"):
        audio.load(path)
    empty = tmp_path / "empty.wav"
    soundfile.write(str(empty), np.zeros((0, 1), np.float32), 24000)
    with pytest.raises(AudioError, match="no sound in it"):
        audio.load(empty)


@pytest.mark.parametrize("suffix", list(FORMATS))
def test_every_format_is_written_and_read_back(tmp_path, suffix):
    sound = audio.stereo(tone(440.0, RATE, 2.5))
    path = tmp_path / f"mix{suffix}"
    audio.save(path, sound)
    assert not list(tmp_path.glob("*.part"))
    info = soundfile.info(str(path))
    assert (info.samplerate, info.channels) == (RATE, 2)
    assert info.duration == pytest.approx(2.5, abs=0.1)


def test_an_unknown_format_and_a_failed_write_leave_nothing(tmp_path):
    sound = audio.stereo(tone(440.0, RATE, 0.1))
    with pytest.raises(AudioError, match="Unknown format .txt"):
        audio.save(tmp_path / "mix.txt", sound)
    with pytest.raises(AudioError, match="could not be written"):
        audio.save(tmp_path / "missing" / "mix.wav", sound)
    assert not list(tmp_path.iterdir())


def test_the_output_gets_16_bit_samples_that_never_wrap():
    found = np.frombuffer(audio.pcm(np.array([[0.0, 1.0], [-1.0, 2.5]], dtype=np.float32)), dtype="<i2")
    assert found.tolist() == [0, 32767, -32767, 32767]


def test_a_drawing_gets_the_lowest_and_highest_sample_of_each_part():
    sound = np.array([[0.1, 0.1], [0.5, 0.5], [-0.3, -0.3], [0.2, 0.2]], dtype=np.float32)
    found = audio.peaks(sound, 2)
    assert found == [pytest.approx((0.1, 0.5)), pytest.approx((-0.3, 0.2))]
    assert len(audio.peaks(sound, 9)) == 9                  # more columns than samples: each still has one
    assert audio.peaks(sound, 0) == [] and audio.peaks(np.zeros((0, 2), np.float32), 5) == []
