# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures: an offscreen QApplication, settings in a temp folder, and a fake PS5 /proc and /sys tree (as read
on a real CFI-1000A on 11-11-2026: ps5_fan, k10temp, nvme, ps5_gpufreq, no cpufreq driver); `ps5` adds the GPU
sensors of kernel 7.3.1 (amdgpu ps5_sensors), `ps5_old` is the 7.2.3 kernel without them."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CORE = Path(__file__).resolve().parents[3] / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))           # bazzite_console_core from the checkout, as the installer bundles it


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def settings_dir(tmp_path):
    """The app keeps an .ini (AppInfo.settings_ini), so this also keeps the tests out of the Windows registry."""
    from PyQt6.QtCore import QSettings
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    return tmp_path / "settings"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")


def proc_stat(busy: int, idle: int) -> str:
    """A /proc/stat whose first line has *busy* jiffies of user time and *idle* of idle time."""
    return f"cpu  {busy} 0 0 {idle} 0 0 0 0 0 0\ncpu0 {busy} 0 0 {idle} 0 0 0 0 0 0"


def net_dev(rx: int, tx: int) -> str:
    """/proc/net/dev with lo (not counted) and the PS5's ethernet port with *rx*/*tx* bytes."""
    return ("Inter-|   Receive  |  Transmit\n face |bytes packets ...\n"
            f"    lo: 999999 1 0 0 0 0 0 0 999999 1 0 0 0 0 0 0\n"
            f"enp64s0f2: {rx} 10 0 0 0 0 0 0 {tx} 5 0 0 0 0 0 0")


def diskstats(read_sectors: int, written_sectors: int) -> str:
    """/proc/diskstats: the nvme disk gets the sectors; its partition, zram and loop must not be counted."""
    return (f" 259 0 nvme0n1 1 0 {read_sectors} 0 1 0 {written_sectors} 0 0 0 0\n"
            f" 259 1 nvme0n1p1 1 0 {read_sectors} 0 1 0 {written_sectors} 0 0 0 0\n"
            "   8 0 sda 1 0 0 0 0 0 0 0 0 0 0\n"
            " 252 0 zram0 1 0 777 0 1 0 777 0 0 0 0\n"
            "   7 0 loop0 1 0 555 0 0 0 0 0 0 0 0")


def _ps5(root: Path, gpu_sensors: bool) -> Path:
    write(root / "proc/stat", proc_stat(1000, 9000))
    write(root / "proc/cpuinfo", "processor\t: 0\ncpu MHz\t\t: 3490.888\n\nprocessor\t: 1\ncpu MHz\t\t: 3481.619")
    (root / "sys/devices/system/cpu/cpu0").mkdir(parents=True)          # no cpufreq on the PS5
    hwmon = root / "sys/class/hwmon"
    write(hwmon / "hwmon0/name", "ps5_fan")
    for n, (label, milli) in enumerate((("MainSoC", 55656), ("Local1", 45250), ("Local2", 21027),
                                        ("Local3", 41750)), start=1):
        write(hwmon / f"hwmon0/temp{n}_label", label)
        write(hwmon / f"hwmon0/temp{n}_input", str(milli))
    write(hwmon / "hwmon0/pwm1", "55")
    write(hwmon / "hwmon0/pwm1_enable", "2")
    write(hwmon / "hwmon1/name", "nvme")
    write(hwmon / "hwmon1/temp1_input", "36850")
    write(hwmon / "hwmon2/name", "k10temp")
    write(hwmon / "hwmon2/temp1_input", "55750")
    gpu = root / "sys/class/drm/card0/device"
    write(gpu / "mem_info_vram_used", str(309_907_456))
    write(gpu / "mem_info_vram_total", str(536_870_912))
    if gpu_sensors:                                         # amdgpu ps5_sensors (7.3.1 on)
        write(hwmon / "hwmon3/name", "amdgpu")
        write(hwmon / "hwmon3/temp1_input", "61000")
        write(hwmon / "hwmon3/freq1_input", "2000000000")
        (hwmon / "hwmon3/device").symlink_to(gpu)
        write(gpu / "gpu_busy_percent", "46")
    write(root / "sys/module/ps5_gpufreq/parameters/temp_limit", "85")
    write(root / "proc/meminfo", "MemTotal:       15800512 kB\nMemFree:          100000 kB\n"
                                 "MemAvailable:    9405112 kB\nSwapTotal:       7812092 kB")
    write(root / "proc/net/dev", net_dev(1_000_000, 50_000))
    for disk in ("nvme0n1", "sda", "zram0", "loop0"):
        (root / "sys/block" / disk).mkdir(parents=True)
    write(root / "proc/diskstats", diskstats(2000, 100))
    return root


@pytest.fixture
def ps5(tmp_path) -> Path:
    return _ps5(tmp_path / "root", gpu_sensors=True)


@pytest.fixture
def ps5_old(tmp_path) -> Path:
    return _ps5(tmp_path / "root-723", gpu_sensors=False)


class Clock:
    """A clock the test moves by hand."""

    def __init__(self):
        self.now = 100.0

    def __call__(self) -> float:
        return self.now
