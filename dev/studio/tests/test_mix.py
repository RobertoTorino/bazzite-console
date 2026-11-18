# SPDX-License-Identifier: GPL-3.0-or-later
"""The mix: how long it is with and without a voice, where the voice sits, the background's fades, the volumes, a
mix too loud turned down as a whole, and settings of another version made safe."""

from __future__ import annotations

import numpy as np
import pytest

from remix_studio import mix as mixer
from remix_studio.mix import CEILING, Mix
from remix_studio.pad import LEVEL, RATE, Pad

QUIET = Pad(chord="Single note", movement=0, space=0)


def voice(seconds: float = 1.0, level: float = 0.25) -> np.ndarray:
    return np.full((int(seconds * RATE), 2), level, dtype=np.float32)


def test_without_a_voice_the_background_lasts_the_length_set():
    found = mixer.render(QUIET, Mix(length=6, fade=0, background_volume=100))
    assert found.seconds == 6.0 and found.sound.shape == (6 * RATE, 2) and found.sound.dtype == np.float32
    assert float(np.abs(found.sound).max()) == pytest.approx(LEVEL, rel=1e-3) and found.turned_down == 0.0


def test_with_a_voice_it_is_the_lead_in_the_voice_and_the_tail():
    settings = Mix(lead=2, tail=3, fade=0, background_volume=0, voice_volume=100)
    assert mixer.seconds(settings, voice(1.5)) == 6.5
    found = mixer.render(QUIET, settings, voice(1.5)).sound
    assert len(found) == int(6.5 * RATE)
    assert not found[:2 * RATE].any() and not found[int(3.5 * RATE):].any()     # only the voice, where it sits
    assert np.allclose(found[2 * RATE:int(3.5 * RATE)], 0.25)


def test_the_volumes_scale_each_track():
    half = mixer.render(QUIET, Mix(lead=0, tail=0, fade=0, background_volume=0, voice_volume=50), voice()).sound
    assert np.allclose(half, 0.125)
    loud = mixer.render(QUIET, Mix(length=5, fade=0, background_volume=100)).sound
    soft = mixer.render(QUIET, Mix(length=5, fade=0, background_volume=50)).sound
    assert np.allclose(soft, loud / 2, atol=1e-6)


def test_the_background_fades_in_and_out():
    curve = mixer.fades(10 * RATE, 2.0)
    assert curve[0] == 0.0 and curve[-1] == 0.0 and np.all(curve[2 * RATE:8 * RATE] == 1.0)
    assert np.all(np.diff(curve[:2 * RATE]) >= 0) and np.allclose(curve[:2 * RATE], curve[::-1][:2 * RATE])
    assert np.all(mixer.fades(RATE, 0.0) == 1.0)
    short = mixer.fades(RATE, 5.0)                          # each fade is half the sound at most
    assert short[RATE // 2 - 1] > 0.99 and short[0] == 0.0 and short[-1] == 0.0
    found = mixer.render(QUIET, Mix(length=6, fade=2)).sound
    assert float(np.abs(found[:RATE // 10]).max()) < 0.1 * float(np.abs(found[2 * RATE:4 * RATE]).max())


def test_a_mix_too_loud_is_turned_down_as_a_whole():
    found = mixer.render(QUIET, Mix(lead=0, tail=0, fade=0, background_volume=0, voice_volume=150), voice(1.0, 0.98))
    assert float(np.abs(found.sound).max()) == pytest.approx(CEILING, rel=1e-4)
    assert found.turned_down == pytest.approx(20 * np.log10(1.5), abs=0.01)


def test_values_of_another_version_become_valid():
    found = mixer.from_values({"voice_volume": "999", "background_volume": "x", "lead": -3, "length": "1",
                               "unknown": 1})
    assert found == Mix(voice_volume=150, lead=0, length=5)
    assert mixer.from_values({k: str(v) for k, v in mixer.to_values(Mix(tail=9)).items()}) == Mix(tail=9)
