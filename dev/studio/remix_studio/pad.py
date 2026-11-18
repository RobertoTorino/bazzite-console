# SPDX-License-Identifier: GPL-3.0-or-later
"""The background: a sustained sound (a pad, a drone) made from a few numbers. Each note of the chord is a small
group of oscillators, a little out of tune with each other and spread left and right. An oscillator reads one cycle
of its waveform from a table built from harmonics (so nothing above the audible range is in it), once dark and once
bright; Movement fades slowly between the two and lets each oscillator swell and fade on its own. Space is a reverb,
the sound convolved with a burst of fading noise. The same numbers always give the same sound: what is played is what
is saved."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np

RATE = 48000                            # of the background and of the mix, stereo
TABLE = 2048                            # the samples of one cycle
KEYS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
OCTAVES = {"Low": 2, "Middle": 3, "High": 4}       # the octave of the chord's lowest note
CHORDS = {                              # semitones above the key
    "Single note": (0,),
    "Fifth": (0, 7),
    "Major": (0, 4, 7),
    "Minor": (0, 3, 7),
    "Open (sus2)": (0, 2, 7),
    "Major 7": (0, 4, 7, 11),
    "Minor 7": (0, 3, 7, 10),
}
SLIDERS = {                             # name: (label, what it does)
    "tone": ("Tone", "From dark and soft to bright"),
    "movement": ("Movement", "How much the sound drifts and swells over time"),
    "space": ("Space", "The reverb, from a dry sound to a large hall"),
}
REVERB_SECONDS = 3.0
LEVEL = 0.5                             # the loudest sample of a rendered background


@dataclass(frozen=True)
class Timbre:
    """What a preset's sound is made of."""

    rolloff: float                      # harmonic k is 1 / k ** rolloff loud
    odd_only: bool = False              # only the odd harmonics: hollow, like a clarinet
    formants: tuple[float, ...] = ()    # Hz around which the harmonics are louder: a sung vowel
    detune: float = 8.0                 # cents between the oscillators of a note
    voices: int = 3                     # oscillators per note
    sub: float = 0.0                    # an octave below the lowest note, this loud
    shimmer: float = 0.0                # an octave above each note, this loud


@dataclass(frozen=True)
class Pad:
    """A background as the window sets it; the sliders go from 0 to 100."""

    preset: str = "Warm pad"
    key: str = "C"
    octave: str = "Middle"
    chord: str = "Major"
    tone: int = 45
    movement: int = 40
    space: int = 50


TIMBRES = {
    "Warm pad": Timbre(rolloff=1.0),
    "Soft strings": Timbre(rolloff=1.0, detune=14.0, voices=4),
    "Drone": Timbre(rolloff=1.2, detune=5.0, sub=0.7),
    "Glass": Timbre(rolloff=1.6, odd_only=True, detune=4.0, shimmer=0.5),
    "Choir": Timbre(rolloff=1.0, formants=(650.0, 1100.0, 2650.0), detune=10.0, voices=4),
    "Dark": Timbre(rolloff=1.5, detune=9.0, sub=0.4),
}
PRESETS = {                             # the numbers a preset starts from
    "Warm pad": Pad(),
    "Soft strings": Pad("Soft strings", "D", "Middle", "Minor 7", 55, 35, 55),
    "Drone": Pad("Drone", "D", "Low", "Fifth", 35, 60, 60),
    "Glass": Pad("Glass", "A", "High", "Open (sus2)", 60, 50, 75),
    "Choir": Pad("Choir", "F", "Middle", "Major 7", 50, 45, 65),
    "Dark": Pad("Dark", "E", "Low", "Minor", 20, 55, 70),
}


def clamp(pad: Pad) -> Pad:
    """*pad* with every field a value the synth knows: what the settings hold may be of another version."""
    default = Pad()
    def slider(value: object, fallback: int) -> int:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return fallback
    return Pad(pad.preset if pad.preset in TIMBRES else default.preset,
               pad.key if pad.key in KEYS else default.key,
               pad.octave if pad.octave in OCTAVES else default.octave,
               pad.chord if pad.chord in CHORDS else default.chord,
               slider(pad.tone, default.tone), slider(pad.movement, default.movement),
               slider(pad.space, default.space))


def from_values(values: dict[str, object]) -> Pad:
    return clamp(replace(Pad(), **{name: value for name, value in values.items() if name in asdict(Pad())}))


def to_values(pad: Pad) -> dict[str, object]:
    return asdict(pad)


def frequencies(pad: Pad) -> list[float]:
    """The chord's notes in Hz, lowest first (A4 is 440 Hz)."""
    root = 12 * (OCTAVES[pad.octave] + 1) + KEYS.index(pad.key)     # its MIDI number
    return [440.0 * 2 ** ((root + step - 69) / 12) for step in CHORDS[pad.chord]]


def cutoff(tone: float) -> float:
    """The frequency above which the harmonics fade, from 250 Hz (tone 0) to 9 kHz (tone 100)."""
    return 250.0 * (9000.0 / 250.0) ** (max(0.0, min(100.0, tone)) / 100)


def table(timbre: Timbre, frequency: float, tone: float) -> np.ndarray:
    """One cycle of *timbre* at *frequency*: its harmonics up to 16 kHz, those above the tone's cutoff fading by
    12 dB an octave, with the loudest sample at 1."""
    count = max(1, min(TABLE // 2 - 1, int(16000 / frequency)))
    k = np.arange(1, count + 1)
    hz = k * frequency
    level = 1.0 / k ** timbre.rolloff
    if timbre.odd_only:
        level[1::2] = 0.0
    if timbre.formants:
        shape = sum(np.exp(-0.5 * ((hz - center) / (0.18 * center)) ** 2) for center in timbre.formants)
        level *= 0.15 + shape
    level = level / (1.0 + (hz / cutoff(tone)) ** 2)
    spectrum = np.zeros(TABLE // 2 + 1, dtype=complex)
    spectrum[1:count + 1] = -0.5j * level * TABLE       # each harmonic a sine
    cycle = np.fft.irfft(spectrum, TABLE)
    return (cycle / max(float(np.max(np.abs(cycle))), 1e-9)).astype(np.float32)


def _read(cycle: np.ndarray, phase: np.ndarray) -> np.ndarray:
    """*cycle* at each *phase* (in cycles), between its samples in a straight line."""
    position = (phase % 1.0) * TABLE
    index = position.astype(np.int64)
    part = (position - index).astype(np.float32)
    return cycle[index % TABLE] * (1 - part) + cycle[(index + 1) % TABLE] * part


def convolve(sound: np.ndarray, impulse: np.ndarray) -> np.ndarray:
    """*sound* convolved with *impulse*, as long as *sound*; in blocks, so a long sound takes no more memory."""
    size = 1 << int(np.ceil(np.log2(2 * len(impulse))))
    block = size - len(impulse) + 1
    shaped = np.fft.rfft(impulse, size)
    out = np.zeros(len(sound) + size, dtype=np.float32)
    for start in range(0, len(sound), block):
        out[start:start + size] += np.fft.irfft(np.fft.rfft(sound[start:start + block], size) * shaped, size)
    return out[:len(sound)]


def reverb(stereo: np.ndarray, amount: float, rng: np.random.Generator) -> np.ndarray:
    """*stereo* with its echo in a hall: each side convolved with its own burst of noise that fades over three
    seconds, mixed in by *amount* (0 to 1)."""
    if amount <= 0 or not len(stereo):
        return stereo
    length = int(REVERB_SECONDS * RATE)
    fade = np.exp(-6.9 * np.arange(length) / length)    # down 60 dB at its end
    out = np.empty_like(stereo)
    for side in range(2):
        noise = rng.standard_normal(length)
        noise = np.convolve(noise, np.ones(8) / 8, mode="same")     # the hall swallows the highest sounds
        impulse = (noise * fade).astype(np.float32)
        impulse /= np.sqrt(float(np.sum(impulse ** 2)))
        out[:, side] = (1 - 0.6 * amount) * stereo[:, side] + 0.9 * amount * convolve(stereo[:, side], impulse)
    return out


def render(pad: Pad, seconds: float) -> np.ndarray:
    """*pad* for *seconds*: float32 stereo at RATE, frames by 2, the loudest sample at LEVEL."""
    pad = clamp(pad)
    count = max(0, int(round(seconds * RATE)))
    out = np.zeros((count, 2), dtype=np.float32)
    if not count:
        return out
    timbre = TIMBRES[pad.preset]
    rng = np.random.default_rng(20261118)               # the same numbers, the same sound
    time = np.arange(count, dtype=np.float64) / RATE
    move = pad.movement / 100
    notes = [(hz, 1.0) for hz in frequencies(pad)]
    if timbre.sub:
        notes.append((notes[0][0] / 2, timbre.sub))
    if timbre.shimmer:
        notes += [(hz * 2, timbre.shimmer) for hz in frequencies(pad)]
    for hz, level in notes:
        dark = table(timbre, hz, pad.tone - 35 * move)
        bright = table(timbre, hz, pad.tone + 20 * move)
        for voice in range(timbre.voices):
            spread = (voice / (timbre.voices - 1) - 0.5) * 2 if timbre.voices > 1 else 0.0
            tuned = hz * 2 ** (spread * timbre.detune / 1200)
            phase = tuned * time + rng.random()
            # Each oscillator has its own slow swell and its own drift between the dark and the bright cycle
            swell = 1 - 0.5 * move * (0.5 + 0.5 * np.sin(2 * np.pi * (rng.uniform(0.05, 0.16) * time + rng.random())))
            drift = 0.5 + 0.5 * np.sin(2 * np.pi * (rng.uniform(0.03, 0.11) * time + rng.random()))
            sound = (_read(dark, phase) * (1 - drift) + _read(bright, phase) * drift) * swell * level
            side = 0.5 + 0.4 * spread                   # from left (0) to right (1)
            out[:, 0] += (sound * np.sqrt(1 - side)).astype(np.float32)
            out[:, 1] += (sound * np.sqrt(side)).astype(np.float32)
    out = reverb(out, pad.space / 100, rng)
    peak = float(np.max(np.abs(out)))
    return out * (LEVEL / peak) if peak > 0 else out


__all__ = ["CHORDS", "KEYS", "LEVEL", "OCTAVES", "PRESETS", "RATE", "SLIDERS", "TIMBRES", "Pad", "Timbre", "clamp",
           "convolve", "cutoff", "frequencies", "from_values", "render", "reverb", "table", "to_values"]
