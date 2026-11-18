# SPDX-License-Identifier: GPL-3.0-or-later
"""The mix: the background from its first to its last second, fading in and out, and the voice over it after the
lead-in. Without a voice the background alone lasts the length set. A mix louder than the file can hold is turned
down as a whole, never clipped."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np

from . import pad as synth
from .pad import RATE, Pad

RANGES = {                              # name: (least, most, label, unit, what it does)
    "voice_volume": (0, 150, "Voice volume", "%", "How loud the voice is in the mix"),
    "background_volume": (0, 150, "Background volume", "%", "How loud the background is in the mix"),
    "lead": (0, 30, "Lead-in", "s", "The background alone before the voice starts"),
    "tail": (0, 30, "Tail", "s", "The background alone after the voice ends"),
    "fade": (0, 15, "Fade", "s", "The background's fade in at the start and fade out at the end"),
    "length": (5, 600, "Length", "s", "How long the mix lasts"),
}
CEILING = 0.98                          # the loudest sample a mix may have


@dataclass(frozen=True)
class Mix:
    voice_volume: int = 100
    background_volume: int = 40
    lead: int = 3
    tail: int = 4
    fade: int = 3
    length: int = 30


@dataclass(frozen=True)
class Result:
    sound: np.ndarray                   # float32 stereo at RATE
    turned_down: float                  # dB the whole mix was turned down to fit, 0.0 when it fitted

    @property
    def seconds(self) -> float:
        return len(self.sound) / RATE


def clamp(mix: Mix) -> Mix:
    values = {}
    for name, (least, most, *_rest) in RANGES.items():
        try:
            values[name] = max(least, min(most, int(getattr(mix, name))))
        except (TypeError, ValueError):
            values[name] = getattr(Mix(), name)
    return Mix(**values)


def from_values(values: dict[str, object]) -> Mix:
    return clamp(replace(Mix(), **{name: value for name, value in values.items() if name in RANGES}))


def to_values(mix: Mix) -> dict[str, object]:
    return asdict(mix)


def seconds(mix: Mix, voice: np.ndarray | None) -> float:
    """How long the mix lasts."""
    if voice is None:
        return float(mix.length)
    return mix.lead + len(voice) / RATE + mix.tail


def fades(count: int, fade: float) -> np.ndarray:
    """The background's volume over *count* samples: up over *fade* seconds, down over the last ones; half the
    sound each at most."""
    curve = np.ones(count, dtype=np.float32)
    ramp = min(int(fade * RATE), count // 2)
    if ramp > 0:
        rise = np.sin(0.5 * np.pi * np.arange(ramp, dtype=np.float32) / ramp) ** 2
        curve[:ramp] = rise
        curve[count - ramp:] = rise[::-1]
    return curve


def render(pad: Pad, mix: Mix, voice: np.ndarray | None = None) -> Result:
    """The mix of *voice* (float32 stereo at RATE, or None) over the background *pad*."""
    mix = clamp(mix)
    background = synth.render(pad, seconds(mix, voice))
    sound = background * (fades(len(background), mix.fade)[:, None] * (mix.background_volume / 100))
    if voice is not None:
        start = mix.lead * RATE
        sound[start:start + len(voice)] += voice[:len(sound) - start] * (mix.voice_volume / 100)
    peak = float(np.max(np.abs(sound))) if len(sound) else 0.0
    turned_down = 0.0
    if peak > CEILING:
        sound *= CEILING / peak
        turned_down = float(20 * np.log10(peak / CEILING))
    return Result(sound.astype(np.float32, copy=False), turned_down)


__all__ = ["CEILING", "RANGES", "Mix", "Result", "clamp", "fades", "from_values", "render", "seconds", "to_values"]
