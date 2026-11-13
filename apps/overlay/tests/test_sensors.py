# SPDX-License-Identifier: GPL-3.0-or-later
"""bazzite_console_core.sensors against a fake PS5 /proc and /sys: each value, the values measured over two
readings, a kernel without the GPU sensors, and missing sources."""

from __future__ import annotations

import shutil

from bazzite_console_core.sensors import Fan, Sensors
from conftest import Clock, diskstats, net_dev, proc_stat, write


def test_values_from_a_ps5(ps5):
    s = Sensors(ps5, clock=Clock())
    assert s.cpu_mhz() == 3486                                    # /proc/cpuinfo: no cpufreq driver
    assert s.cpu_temp() == 55.75
    assert s.soc_temp() == 55.656
    assert s.board_temp() == 45.25                                # the warmest of Local1..3
    assert s.gpu_load() == 46.0
    assert s.gpu_mhz() == 2000
    assert s.gpu_temp() == 61.0
    assert s.gpu_limit() == 85
    assert s.vram() == (309_907_456, 536_870_912)
    assert s.ram() == ((15800512 - 9405112) * 1024, 15800512 * 1024)
    assert s.nvme_temp() == 36.85
    assert s.fan() == Fan(duty=22, mode="auto")                   # 55 of 255


def test_kernel_without_gpu_sensors(ps5_old):
    s = Sensors(ps5_old, clock=Clock())
    assert s.gpu_load() is None and s.gpu_mhz() is None and s.gpu_temp() is None
    assert s.vram() == (309_907_456, 536_870_912)                 # from the DRM card instead of amdgpu's hwmon


def test_cpufreq_wins_when_present(ps5):
    write(ps5 / "sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "3200000")
    assert Sensors(ps5).cpu_mhz() == 3200


def test_fan_modes(ps5):
    write(ps5 / "sys/class/hwmon/hwmon0/pwm1_enable", "1")
    write(ps5 / "sys/class/hwmon/hwmon0/pwm1", "255")
    assert Sensors(ps5).fan() == Fan(duty=100, mode="manual")
    write(ps5 / "sys/class/hwmon/hwmon0/pwm1_enable", "7")
    assert Sensors(ps5).fan().mode == ""


def test_cpu_load_over_two_readings(ps5):
    s = Sensors(ps5)
    assert s.cpu_load() is None                                   # nothing to compare with yet
    write(ps5 / "proc/stat", proc_stat(1000 + 300, 9000 + 100))   # 300 busy of 400 jiffies
    assert s.cpu_load() == 75.0


def test_rates_over_two_readings(ps5):
    clock = Clock()
    s = Sensors(ps5, clock=clock)
    assert s.net() is None and s.disk() is None
    clock.now += 2
    write(ps5 / "proc/net/dev", net_dev(1_000_000 + 4_000_000, 50_000 + 1000))
    write(ps5 / "proc/diskstats", diskstats(2000 + 4000, 100))
    assert s.net() == (2_000_000.0, 500.0)
    assert s.disk() == (4000 * 512 / 2, 0.0)
    assert s.interfaces() == ["enp64s0f2"]


def test_nothing_there(tmp_path):
    reading = Sensors(tmp_path).read()
    assert all(value is None for value in reading.__dict__.values())


def test_without_ps5_fan(ps5):
    shutil.rmtree(ps5 / "sys/class/hwmon/hwmon0")
    s = Sensors(ps5)
    assert s.fan() is None and s.soc_temp() is None and s.board_temp() is None
