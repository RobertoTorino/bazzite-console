# SPDX-License-Identifier: GPL-3.0-or-later
"""The background: the chord's notes, a cycle built from harmonics, the same numbers giving the same sound, what
Tone, Movement and Space change, and values of another version made safe."""

from __future__ import annotations

import numpy as np
import pytest

from remix_studio import pad
from remix_studio.pad import LEVEL, PRESETS, RATE, TIMBRES, Pad


def spectrum(sound: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mono = sound.mean(axis=1) * np.hanning(len(sound))
    return np.fft.rfftfreq(len(mono), 1 / RATE), np.abs(np.fft.rfft(mono))


def brightness(sound: np.ndarray) -> float:
    """The frequency its energy centers on."""
    hz, level = spectrum(sound)
    return float(np.sum(hz * level ** 2) / np.sum(level ** 2))


def test_every_preset_has_its_sound_and_starts_from_valid_numbers():
    assert set(PRESETS) == set(TIMBRES)
    for name, preset in PRESETS.items():
        assert preset.preset == name and pad.clamp(preset) == preset


def test_the_chords_notes_are_in_tune():
    assert pad.frequencies(Pad(key="A", octave="High", chord="Single note")) == [pytest.approx(440.0)]
    low, third, fifth = pad.frequencies(Pad(key="C", octave="Middle", chord="Major"))
    assert low == pytest.approx(130.81, abs=0.01)
    assert third / low == pytest.approx(2 ** (4 / 12)) and fifth / low == pytest.approx(2 ** (7 / 12))
    assert pad.frequencies(Pad(key="C", octave="Low"))[0] == pytest.approx(low / 2)


def test_a_cycle_holds_only_harmonics_below_16_khz_and_peaks_at_one():
    cycle = pad.table(TIMBRES["Warm pad"], 1000.0, 100)
    level = np.abs(np.fft.rfft(cycle))
    assert float(np.max(np.abs(cycle))) == pytest.approx(1.0)
    assert np.all(level[17:] < 1e-3 * level[1]) and level[16] > 1e-3 * level[1]
    hollow = np.abs(np.fft.rfft(pad.table(TIMBRES["Glass"], 440.0, 100)))
    assert hollow[2] < 1e-3 * hollow[1] and hollow[3] > 1e-2 * hollow[1]    # only the odd harmonics


def test_a_background_is_stereo_as_long_as_asked_and_as_loud_as_level():
    sound = pad.render(Pad(), 1.5)
    assert sound.shape == (int(1.5 * RATE), 2) and sound.dtype == np.float32
    assert float(np.max(np.abs(sound))) == pytest.approx(LEVEL, rel=1e-4)
    assert not np.allclose(sound[:, 0], sound[:, 1])        # spread left and right
    assert pad.render(Pad(), 0).shape == (0, 2)


def test_the_same_numbers_give_the_same_sound():
    assert np.array_equal(pad.render(Pad(), 1.0), pad.render(Pad(), 1.0))
    assert not np.array_equal(pad.render(Pad(), 1.0), pad.render(Pad(chord="Minor"), 1.0))


def test_the_note_that_sounds_is_the_key():
    hz, level = spectrum(pad.render(Pad(key="A", octave="Middle", chord="Single note", movement=0, space=0), 2.0))
    assert hz[int(np.argmax(level))] == pytest.approx(220.0, abs=2.0)


def test_tone_makes_it_brighter():
    dark = pad.render(Pad(tone=5, movement=0, space=0), 1.0)
    bright = pad.render(Pad(tone=95, movement=0, space=0), 1.0)
    assert brightness(bright) > 2 * brightness(dark)


def test_movement_makes_the_tone_drift_over_time():
    def drift(movement: int) -> float:
        """How far the share of the sound above 600 Hz goes up and down, second by second."""
        sound = pad.render(Pad(chord="Single note", movement=movement, space=0), 16.0).mean(axis=1)
        share = []
        for start in range(0, len(sound), RATE):
            level = np.abs(np.fft.rfft(sound[start:start + RATE] * np.hanning(RATE))) ** 2
            share.append(level[600:].sum() / level.sum())
        return max(share) / min(share)
    assert drift(100) > 2 * drift(0)


def test_space_lets_the_sound_ring_on():
    burst = np.zeros((RATE, 2), dtype=np.float32)
    burst[:480] = 0.5
    rng = np.random.default_rng(1)
    assert np.array_equal(pad.reverb(burst, 0.0, rng), burst)
    wet = pad.reverb(burst, 1.0, rng)
    assert float(np.abs(wet[RATE // 2:]).max()) > 0 and float(np.abs(burst[RATE // 2:]).max()) == 0


def test_convolving_in_blocks_is_convolving():
    rng = np.random.default_rng(2)
    sound, impulse = rng.standard_normal(5000).astype(np.float32), rng.standard_normal(300).astype(np.float32)
    assert np.allclose(pad.convolve(sound, impulse), np.convolve(sound, impulse)[:5000], atol=1e-3)


def test_values_of_another_version_become_valid():
    found = pad.from_values({"preset": "Gone", "key": "H", "octave": "Middle", "chord": "Minor", "tone": "999",
                             "movement": "x", "space": -4, "unknown": 1})
    assert found == Pad(chord="Minor", tone=100, movement=Pad().movement, space=0)
    assert pad.from_values(pad.to_values(PRESETS["Drone"])) == PRESETS["Drone"]
    as_text = {key: str(value) for key, value in pad.to_values(PRESETS["Glass"]).items()}
    assert pad.from_values(as_text) == PRESETS["Glass"]
