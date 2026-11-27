# SPDX-License-Identifier: GPL-3.0-or-later
"""Reads the recordings: the days there are, the lines around a time, and each value's lowest and highest in them.
The files are the recorder's (recorder.py): one per day, a line per second."""

from __future__ import annotations

import csv
import datetime
import re
from dataclasses import dataclass
from pathlib import Path

from .recorder import OUT

MINUTES = 5                                     # before and after the time
# column, what the window calls it, unit, digits
VALUES = (("cpu_load", "CPU load", "%", 0), ("cpu_temp", "CPU temperature", "°C", 1),
          ("soc_temp", "SoC temperature", "°C", 1), ("board_temp", "Board temperature", "°C", 1),
          ("gpu_load", "GPU load", "%", 0), ("gpu_mhz", "GPU clock", "MHz", 0),
          ("gpu_temp", "GPU temperature", "°C", 0), ("gpu_limit", "GPU temperature limit", "°C", 0),
          ("fan_duty", "Fan", "%", 0), ("ram_used", "Memory in use", "MiB", 0),
          ("swap_used_kb", "Swap in use", "MiB", 0), ("mem_pressure", "Memory pressure", "", 2),
          ("threads", "Threads online", "", 0))
TO_MIB = {"ram_used": 1 << 20, "swap_used_kb": 1 << 10}
TIME = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")


@dataclass
class Stat:
    name: str
    unit: str
    digits: int
    last: float | None = None
    low: float | None = None
    high: float | None = None

    def text(self, value: float | None) -> str:
        if value is None:
            return ""
        return f"{value:.{self.digits}f} {self.unit}".strip()


@dataclass
class Window:
    day: str                                    # YYYY-MM-DD
    start: str                                  # HH:MM:SS of the first line in it, "" when none
    end: str
    lines: int
    stats: list[Stat]
    busiest: list[tuple[str, int]]              # program, seconds it was the busiest, most first
    boots: int                                  # how many boots the lines belong to


def days(out: Path = OUT) -> list[str]:
    """The days with a recording, newest first."""
    return sorted((p.stem for p in out.glob("*.csv") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)), reverse=True)


def parse_time(text: str) -> tuple[int, int] | None:
    """"00:46" or "0.46" as (hour, minute); None for anything else."""
    match = TIME.match(text.strip())
    return (int(match.group(1)), int(match.group(2))) if match else None


def rows(day: str, out: Path = OUT) -> list[dict[str, str]]:
    try:
        with open(out / f"{day}.csv", newline="") as handle:
            return [r for r in csv.DictReader(handle) if r.get("time")]
    except OSError:
        return []


def around(day: str, at: tuple[int, int] | None, out: Path = OUT, minutes: int = MINUTES) -> Window:
    """The lines from *minutes* before to *minutes* after *at*; without a time, the last 2 x *minutes* of the day."""
    found = rows(day, out)
    if at is None:
        found = found[-2 * minutes * 60:]
    else:
        middle = datetime.timedelta(hours=at[0], minutes=at[1])
        low, high = middle - datetime.timedelta(minutes=minutes), middle + datetime.timedelta(minutes=minutes)

        def seconds(text: str) -> datetime.timedelta:
            h, m, s = (int(x) for x in text.split(":"))
            return datetime.timedelta(hours=h, minutes=m, seconds=s)
        kept = []
        for r in found:
            try:
                if low <= seconds(r["time"]) <= high:
                    kept.append(r)
            except ValueError:
                continue
        found = kept
    stats = []
    for column, name, unit, digits in VALUES:
        numbers = []
        for r in found:
            try:
                numbers.append(float(r[column]) / TO_MIB.get(column, 1))
            except (KeyError, ValueError, TypeError):
                continue
        stats.append(Stat(name, unit, digits, *((numbers[-1], min(numbers), max(numbers)) if numbers else ())))
    busy: dict[str, int] = {}
    for r in found:
        if r.get("busiest"):
            busy[r["busiest"]] = busy.get(r["busiest"], 0) + 1
    return Window(day, found[0]["time"] if found else "", found[-1]["time"] if found else "", len(found), stats,
                  sorted(busy.items(), key=lambda item: -item[1]), len({r.get("boot", "") for r in found}))


def size_text(size: int) -> str:
    return f"{size / (1 << 20):.1f} MB" if size >= 1 << 20 else f"{max(size, 0) // 1024} KB"
