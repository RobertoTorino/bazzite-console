# SPDX-License-Identifier: GPL-3.0-or-later
"""Reads the PlayStation 5's live values from /proc and /sys, without root. Every reader returns None when its
source is missing, so an app shows "—" instead of failing on a kernel that lacks it.

On the PS5 (ps5-linux kernel): the CPU temperature from k10temp (Tctl); the SoC and three board temperatures, the
fan's duty and its mode from ps5_fan (the fan reports no speed in RPM); the GPU governor's temperature limit from
ps5_gpufreq; VRAM from amdgpu. amdgpu runs without its SMU on the PS5, so the GPU's load, clock and temperature
exist only on kernels with the ps5_sensors export (ps5-linux-patches #78, kernel 7.3.1 on): an "amdgpu" hwmon with
temp1/freq1 and the device's gpu_busy_percent. Older kernels: those are None."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

SECTOR = 512                    # /proc/diskstats counts 512-byte sectors, whatever the disk's own sector size
_NOT_A_DISK = ("loop", "ram", "zram", "dm-", "md", "sr", "fd")
PWM_MAX = 255
FAN_MODES = {0: "full speed", 1: "manual", 2: "auto"}     # hwmon pwm1_enable


@dataclass(frozen=True)
class Fan:
    duty: int                   # percent of full speed (pwm1 of 255)
    mode: str                   # "auto" (the kernel's curve), "manual", "full speed", or "" when unknown


@dataclass(frozen=True)
class Reading:
    cpu_load: float | None = None           # percent, over the time since the previous reading
    cpu_mhz: int | None = None              # average of the cores' current clocks
    cpu_temp: float | None = None           # °C, k10temp Tctl
    soc_temp: float | None = None           # °C, ps5_fan MainSoC
    board_temp: float | None = None         # °C, the warmest of ps5_fan's Local1..3
    gpu_load: float | None = None           # percent (ps5_sensors, 7.3.1 on)
    gpu_mhz: int | None = None              # (ps5_sensors)
    gpu_temp: float | None = None           # °C (ps5_sensors)
    gpu_limit: int | None = None            # °C, ps5_gpufreq's temp_limit: the governor slows the GPU above it
    vram: tuple[int, int] | None = None     # used, total bytes
    ram: tuple[int, int] | None = None      # used, total bytes
    nvme_temp: float | None = None
    net: tuple[float, float] | None = None  # download, upload bytes/s since the previous reading
    disk: tuple[float, float] | None = None     # read, write bytes/s since the previous reading
    fan: Fan | None = None


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except (OSError, ValueError):
        return None


def _read_int(path: Path) -> int | None:
    text = _read(path)
    try:
        return int(text) if text is not None else None
    except ValueError:
        return None


class _Rate:
    """Bytes per second of growing counters, between two readings."""

    def __init__(self, clock: Callable[[], float]):
        self._clock = clock
        self._last: tuple[float, tuple[int, ...]] | None = None

    def __call__(self, counters: tuple[int, ...] | None) -> tuple[float, ...] | None:
        if counters is None:
            return None
        now = self._clock()
        previous, self._last = self._last, (now, counters)
        if previous is None or now <= previous[0] or any(c < p for c, p in zip(counters, previous[1])):
            return None
        return tuple((c - p) / (now - previous[0]) for c, p in zip(counters, previous[1]))


class Sensors:
    def __init__(self, root: Path | str = "/", clock: Callable[[], float] = time.monotonic):
        self.root = Path(root)
        self._last_cpu: tuple[int, int] | None = None      # (busy, total) jiffies of the previous reading
        self._clock = clock
        self._net_rates: dict[str | None, _Rate] = {}       # per interface; None: all of them
        self._disk_rate = _Rate(clock)
        self.interface: str | None = None       # the network interface read() measures; None: all but loopback

    # ------------------------------------------------------------------ hwmon
    def _hwmons(self) -> list[Path]:
        return sorted((self.root / "sys/class/hwmon").glob("hwmon*"))

    def _hwmon(self, name: str) -> Path | None:
        return next((folder for folder in self._hwmons() if _read(folder / "name") == name), None)

    def _temp(self, name: str, number: int = 1) -> float | None:
        folder = self._hwmon(name)
        value = _read_int(folder / f"temp{number}_input") if folder else None
        return value / 1000 if value is not None else None

    def _labelled_temps(self, name: str) -> dict[str, float]:
        """Label -> °C of every temperature of the hwmon *name* that reads."""
        folder = self._hwmon(name)
        found = {}
        for input_file in sorted(folder.glob("temp[0-9]*_input")) if folder else []:
            value = _read_int(input_file)
            if value is not None:
                label = _read(folder / input_file.name.replace("_input", "_label")) or input_file.name[:-6]
                found[label] = value / 1000
        return found

    def _gpu_device(self) -> Path | None:
        """The GPU's PCI device folder: through amdgpu's hwmon (7.3.1 on), else the first DRM card's device."""
        folder = self._hwmon("amdgpu")
        if folder is not None and (folder / "device").exists():
            return folder / "device"
        return next((c / "device" for c in sorted((self.root / "sys/class/drm").glob("card[0-9]"))
                     if (c / "device").exists()), None)

    # -------------------------------------------------------------------- CPU
    def cpu_load(self) -> float | None:
        """Busy share of all cores since the previous call; None on the first call."""
        line = (_read(self.root / "proc/stat") or "").splitlines()[:1]
        if not line or not line[0].startswith("cpu "):
            return None
        try:
            values = [int(v) for v in line[0].split()[1:]]
        except ValueError:
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)       # idle + iowait
        total = sum(values[:8])                                          # without guest, already in user/nice
        busy = total - idle
        previous, self._last_cpu = self._last_cpu, (busy, total)
        if previous is None or total <= previous[1]:
            return None
        return max(0.0, min(100.0, 100 * (busy - previous[0]) / (total - previous[1])))

    def cpu_mhz(self) -> int | None:
        khz = [_read_int(p) for p in (self.root / "sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_cur_freq")]
        khz = [k for k in khz if k]
        if khz:
            return round(sum(khz) / len(khz) / 1000)
        # The PS5 has no cpufreq driver; /proc/cpuinfo still has each core's clock ("cpu MHz : 3490.888").
        mhz = []
        for line in (_read(self.root / "proc/cpuinfo") or "").splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "cpu MHz":
                try:
                    mhz.append(float(value))
                except ValueError:
                    pass
        return round(sum(mhz) / len(mhz)) if mhz else None

    def cpu_temp(self) -> float | None:
        return self._temp("k10temp")

    # -------------------------------------------------------------- SoC, board
    def soc_temp(self) -> float | None:
        temps = self._labelled_temps("ps5_fan")
        return temps.get("MainSoC")

    def board_temp(self) -> float | None:
        temps = [v for k, v in self._labelled_temps("ps5_fan").items() if k.startswith("Local")]
        return max(temps) if temps else None

    # -------------------------------------------------------------------- GPU
    def gpu_load(self) -> float | None:
        device = self._gpu_device()
        value = _read_int(device / "gpu_busy_percent") if device else None
        return float(value) if value is not None and 0 <= value <= 100 else None

    def gpu_mhz(self) -> int | None:
        folder = self._hwmon("amdgpu")
        hz = _read_int(folder / "freq1_input") if folder else None
        return round(hz / 1_000_000) if hz else None

    def gpu_temp(self) -> float | None:
        return self._temp("amdgpu")

    def gpu_limit(self) -> int | None:
        return _read_int(self.root / "sys/module/ps5_gpufreq/parameters/temp_limit")

    # ----------------------------------------------------------------- memory
    def vram(self) -> tuple[int, int] | None:
        device = self._gpu_device()
        if device is None:
            return None
        used, total = _read_int(device / "mem_info_vram_used"), _read_int(device / "mem_info_vram_total")
        return (used, total) if used is not None and total else None

    def ram(self) -> tuple[int, int] | None:
        info = {}
        for line in (_read(self.root / "proc/meminfo") or "").splitlines():
            key, _, rest = line.partition(":")
            if rest.strip().endswith("kB"):
                try:
                    info[key] = int(rest.split()[0]) * 1024
                except ValueError:
                    pass
        total, available = info.get("MemTotal"), info.get("MemAvailable")
        return (total - available, total) if total and available is not None else None

    def nvme_temp(self) -> float | None:
        return self._temp("nvme")

    # --------------------------------------------------------------- activity
    def _net_lines(self) -> list[tuple[str, list[str]]]:
        found = []
        for line in (_read(self.root / "proc/net/dev") or "").splitlines()[2:]:
            name, _, rest = line.partition(":")
            if name.strip() and name.strip() != "lo" and len(rest.split()) >= 9:
                found.append((name.strip(), rest.split()))
        return found

    def interfaces(self) -> list[str]:
        """The network interfaces, without loopback, in the kernel's order."""
        return [name for name, _ in self._net_lines()]

    def _net_counters(self, interface: str | None = None) -> tuple[int, int] | None:
        rx = tx = 0
        lines = [(n, f) for n, f in self._net_lines() if interface is None or n == interface]
        if not lines:
            return None
        for _, fields in lines:
            try:
                rx, tx = rx + int(fields[0]), tx + int(fields[8])
            except ValueError:
                return None
        return rx, tx

    def net(self, interface: str | None = None) -> tuple[float, float] | None:
        """Download and upload of *interface*, or of all but loopback; each interface has its own previous reading."""
        rate = self._net_rates.setdefault(interface, _Rate(self._clock))
        return rate(self._net_counters(interface))

    def _disk_counters(self) -> tuple[int, int] | None:
        disks = {p.name for p in (self.root / "sys/block").glob("*") if not p.name.startswith(_NOT_A_DISK)}
        lines = (_read(self.root / "proc/diskstats") or "").splitlines()
        if not lines or not disks:
            return None
        read = written = 0
        for line in lines:
            fields = line.split()
            if len(fields) >= 10 and fields[2] in disks:          # whole disks only, not their partitions
                try:
                    read, written = read + int(fields[5]) * SECTOR, written + int(fields[9]) * SECTOR
                except ValueError:
                    return None
        return read, written

    def disk(self) -> tuple[float, float] | None:
        return self._disk_rate(self._disk_counters())

    # -------------------------------------------------------------------- fan
    def fan(self) -> Fan | None:
        folder = self._hwmon("ps5_fan")
        pwm = _read_int(folder / "pwm1") if folder else None
        if pwm is None:
            return None
        mode = FAN_MODES.get(_read_int(folder / "pwm1_enable"), "")
        return Fan(duty=round(100 * max(0, min(pwm, PWM_MAX)) / PWM_MAX), mode=mode)

    def read(self) -> Reading:
        return Reading(cpu_load=self.cpu_load(), cpu_mhz=self.cpu_mhz(), cpu_temp=self.cpu_temp(),
                       soc_temp=self.soc_temp(), board_temp=self.board_temp(), gpu_load=self.gpu_load(),
                       gpu_mhz=self.gpu_mhz(), gpu_temp=self.gpu_temp(), gpu_limit=self.gpu_limit(), vram=self.vram(),
                       ram=self.ram(), nvme_temp=self.nvme_temp(), net=self.net(self.interface), disk=self.disk(),
                       fan=self.fan())
