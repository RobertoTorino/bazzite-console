# SPDX-License-Identifier: GPL-3.0-or-later
"""Sound files in and out. A voice file of any rate and any number of channels becomes float32 stereo at the mix's
rate; the mix is written as Ogg Vorbis, MP3, FLAC or WAV, 16-bit where the format has a width. Both go through
libsndfile (the soundfile package)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .pad import RATE

FORMATS = {".ogg": ("OGG", "VORBIS"), ".mp3": ("MP3", "MPEG_LAYER_III"), ".flac": ("FLAC", "PCM_16"),
           ".wav": ("WAV", "PCM_16")}
OPEN_FILTER = "Sound files (*.wav *.ogg *.oga *.flac *.mp3 *.aiff *.aif);;All files (*)"
TAPS = 16                               # the samples around each new one that resample() weighs


class AudioError(Exception):
    """A sound file that cannot be read or written; the message is for the status line."""


def resample(sound: np.ndarray, rate: int, wanted: int = RATE) -> np.ndarray:
    """*sound* (frames by channels) from *rate* to *wanted*: each new sample is a weighted sum of the TAPS around
    its place (a windowed sinc), which keeps what both rates can hold and drops the rest."""
    if rate == wanted or not len(sound):
        return sound.astype(np.float32, copy=False)
    count = int(round(len(sound) * wanted / rate))
    scale = min(1.0, wanted / rate)                     # going down: also drop what the new rate cannot hold
    half = int(np.ceil(TAPS / 2 / scale))
    offsets = np.arange(-half + 1, half + 1)
    out = np.empty((count, sound.shape[1]), dtype=np.float32)
    padded = np.concatenate([np.zeros((half, sound.shape[1]), np.float32), sound.astype(np.float32, copy=False),
                             np.zeros((half + 1, sound.shape[1]), np.float32)])
    for start in range(0, count, 65536):                # in blocks: a long file takes no more memory
        place = np.arange(start, min(start + 65536, count)) * (rate / wanted)
        whole = np.floor(place).astype(np.int64)
        distance = (place - whole)[:, None] - offsets[None, :]
        weight = np.sinc(distance * scale) * scale * (0.5 + 0.5 * np.cos(np.pi * np.clip(distance / half, -1, 1)))
        index = whole[:, None] + offsets[None, :] + half
        out[start:start + len(place)] = np.einsum("nt,ntc->nc", weight.astype(np.float32), padded[index])
    return out


def stereo(sound: np.ndarray) -> np.ndarray:
    """*sound* (frames by channels) as two channels: one channel on both sides, more than two as their first two."""
    if sound.shape[1] == 1:
        return np.repeat(sound, 2, axis=1)
    return sound[:, :2]


def load(path: Path) -> np.ndarray:
    """The sound file *path* as float32 stereo at RATE."""
    import soundfile
    try:
        sound, rate = soundfile.read(str(path), dtype="float32", always_2d=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise AudioError(f"{path.name} is not a sound file this app can read.") from error
    if not len(sound):
        raise AudioError(f"{path.name} has no sound in it.")
    return np.ascontiguousarray(stereo(resample(sound, int(rate))))


def save(path: Path, sound: np.ndarray, rate: int = RATE) -> None:
    """Write *sound* (float32, frames by channels) to *path* in the format of its suffix. It goes to a .part file a
    second at a time (libsndfile's Ogg writer crashes on minutes handed over in one piece), kept only when complete."""
    import soundfile
    suffix = path.suffix.lower()
    if suffix not in FORMATS:
        raise AudioError(f"Unknown format {path.suffix}. Use {', '.join(FORMATS)}.")
    kind, subtype = FORMATS[suffix]
    part = path.with_name(path.name + ".part")
    try:
        with soundfile.SoundFile(str(part), "w", samplerate=rate, channels=sound.shape[1], format=kind,
                                 subtype=subtype) as file:
            for start in range(0, len(sound), rate):
                file.write(sound[start:start + rate])
        part.replace(path)
    except (OSError, RuntimeError, ValueError) as error:
        part.unlink(missing_ok=True)
        raise AudioError(f"{path.name} could not be written: {error}") from error


def pcm(sound: np.ndarray) -> bytes:
    """*sound* as 16-bit samples for the audio output."""
    return (np.clip(sound, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def peaks(sound: np.ndarray, columns: int) -> list[tuple[float, float]]:
    """The lowest and the highest sample of *sound* (both sides together) in each of *columns* equal parts: what a
    drawing of it needs."""
    if columns < 1 or not len(sound):
        return []
    mono = sound.mean(axis=1) if sound.ndim == 2 else sound
    edges = np.linspace(0, len(mono), columns + 1).astype(np.int64)
    starts = np.minimum(edges[:-1], len(mono) - 1)
    low = np.minimum.reduceat(mono, starts)
    high = np.maximum.reduceat(mono, starts)
    return list(zip(low.tolist(), high.tolist()))


__all__ = ["AudioError", "FORMATS", "OPEN_FILTER", "TAPS", "load", "pcm", "peaks", "resample", "save", "stereo"]
