#!/usr/bin/python3 -I
# SPDX-License-Identifier: GPL-3.0-or-later
"""The recorder itself, as the system service runs it: one line per second with the sensors, the memory and the load,
one file per day in /var/log/nexus-flight-recorder, the newest 7 kept. A line reaches the disk within 2 seconds, so a
freeze keeps the last moments. Standard library only; sensors.py beside the installed copy is a copy of core's
(helper.py puts both under /usr/local/lib/nexus-flight-recorder)."""

from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path

OUT = Path("/var/log/nexus-flight-recorder")
KEEP_DAYS = 7
SYNC_S = 2
COLUMNS = ("time", "boot", "threads", "load1", "cpu_load", "cpu_temp", "soc_temp", "board_temp", "gpu_load",
           "gpu_mhz", "gpu_temp", "gpu_limit", "fan_duty", "ram_used", "vram_used", "swap_used_kb", "mem_pressure",
           "busiest")


def read(path: Path | str) -> str:
    try:
        return Path(path).read_text()
    except OSError:
        return ""


def swap_used_kb(proc: Path = Path("/proc")) -> int | None:
    info = dict(line.split(":", 1) for line in read(proc / "meminfo").splitlines() if ":" in line)
    try:
        return int(info["SwapTotal"].split()[0]) - int(info["SwapFree"].split()[0])
    except (KeyError, ValueError, IndexError):
        return None


def pressure(proc: Path = Path("/proc")) -> str:
    """The memory pressure of the last 10 seconds, as the kernel prints it ("some avg10=")."""
    for part in read(proc / "pressure/memory").split():
        if part.startswith("avg10="):
            return part[6:]
    return ""


class Busiest:
    """The program that used the most CPU time since the last look: its name only, never its arguments."""

    def __init__(self, proc: Path = Path("/proc")):
        self.proc = proc
        self.last: dict[str, int] = {}

    def __call__(self) -> str:
        now, best, name = {}, 0, ""
        try:
            entries = [e.name for e in os.scandir(self.proc) if e.name.isdigit()]
        except OSError:
            entries = []
        for pid in entries:
            stat = read(self.proc / pid / "stat")
            try:
                comm = stat[stat.index("(") + 1:stat.rindex(")")]
                fields = stat[stat.rindex(")") + 2:].split()
                ticks = int(fields[11]) + int(fields[12])
            except (ValueError, IndexError):
                continue
            now[pid] = ticks
            used = ticks - self.last.get(pid, ticks)
            if used > best:
                best, name = used, comm
        self.last = now
        return name.replace(",", " ")


def cell(value: object) -> str:
    if value is None:
        return ""
    return f"{value:.1f}" if isinstance(value, float) else str(value)


def row(reading, now: datetime.datetime, boot: str, busiest: str, proc: Path = Path("/proc")) -> list[str]:
    """One line of the file from a sensors Reading."""
    load = read(proc / "loadavg").split()
    fan = reading.fan
    values = [now.strftime("%H:%M:%S"), boot, os.cpu_count(), load[0] if load else None, reading.cpu_load,
              reading.cpu_temp, reading.soc_temp, reading.board_temp, reading.gpu_load, reading.gpu_mhz,
              reading.gpu_temp, reading.gpu_limit, fan and fan.duty,
              reading.ram and reading.ram[0], reading.vram and reading.vram[0], swap_used_kb(proc), pressure(proc),
              busiest]
    return [cell(v) for v in values]


def open_day(out: Path, day: str, keep: int = KEEP_DAYS):
    """Today's file, opened for appending with its heading when new; the files older than *keep* days go."""
    out.mkdir(mode=0o755, parents=True, exist_ok=True)
    path = out / f"{day}.csv"
    new = not path.exists()
    handle = open(path, "a")
    if new:
        handle.write(",".join(COLUMNS) + "\n")
    for old in sorted(out.glob("*.csv"))[:-keep]:
        old.unlink()
    return handle


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sensors import Sensors                 # the copy beside the installed recorder

    sensors, busiest = Sensors(), Busiest()
    boot = read("/proc/sys/kernel/random/boot_id").strip()[:8]
    day, handle, synced = "", None, 0.0
    while True:
        now = datetime.datetime.now()
        if now.strftime("%Y-%m-%d") != day:
            day = now.strftime("%Y-%m-%d")
            if handle:
                handle.close()
            handle = open_day(OUT, day)
        handle.write(",".join(row(sensors.read(), now, boot, busiest())) + "\n")
        handle.flush()
        if time.monotonic() - synced >= SYNC_S:
            os.fsync(handle.fileno())
            synced = time.monotonic()
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
