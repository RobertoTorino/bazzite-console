# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures: an offscreen QApplication, settings in a temp folder, and a fake /sys of a PS5 (CFI-1000A) as it
reported on 11-11-2026: ps5_fan with MainSoC 55.6 °C, Local1..3, the fan at duty 55 of 255 on the kernel's curve
(pwm1_enable 2) and its 8 curve points; k10temp Tctl 55.8 °C; nvme. The amdgpu hwmon (kernel 7.3.1's ps5_sensors)
is left out: kernel 7.2.3 has none."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CORE = Path(__file__).resolve().parents[3] / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))           # bazzite_console_core from the checkout, as the installer bundles it
APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def settings_dir(tmp_path, monkeypatch):
    """The app keeps an .ini (AppInfo.settings_ini), so this also keeps the tests out of the Windows registry."""
    from PyQt6.QtCore import QSettings
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return tmp_path / "settings"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")


FAN = "class/hwmon/hwmon0"
CURVE = ((50, 26), (60, 77), (65, 102), (70, 128), (75, 166), (80, 204), (85, 242), (87, 255))


def set_temps(sys_root: Path, soc: float | None = None, cpu: float | None = None, gpu: float | None = None) -> None:
    if soc is not None:
        write(sys_root / FAN / "temp1_input", str(int(soc * 1000)))
    if cpu is not None:
        write(sys_root / "class/hwmon/hwmon2/temp1_input", str(int(cpu * 1000)))
    if gpu is not None:
        write(sys_root / "class/hwmon/hwmon3/name", "amdgpu")
        write(sys_root / "class/hwmon/hwmon3/temp1_input", str(int(gpu * 1000)))


def fan(sys_root: Path, name: str) -> str:
    return (sys_root / FAN / name).read_text().strip()


@pytest.fixture
def sys_root(tmp_path) -> Path:
    root = tmp_path / "sys"
    hw = root / "class/hwmon"
    write(hw / "hwmon0/name", "ps5_fan")
    for n, (label, milli) in enumerate((("MainSoC", 55656), ("Local1", 45250), ("Local2", 21027),
                                        ("Local3", 41750)), start=1):
        write(hw / f"hwmon0/temp{n}_label", label)
        write(hw / f"hwmon0/temp{n}_input", str(milli))
    write(hw / "hwmon0/pwm1", "55")
    write(hw / "hwmon0/pwm1_enable", "2")
    for n, (celsius, pwm) in enumerate(CURVE, start=1):
        write(hw / f"hwmon0/pwm1_auto_point{n}_temp", str(celsius * 1000))
        write(hw / f"hwmon0/pwm1_auto_point{n}_pwm", str(pwm))
    write(hw / "hwmon1/name", "nvme")
    write(hw / "hwmon1/temp1_label", "Composite")
    write(hw / "hwmon1/temp1_input", "36850")
    write(hw / "hwmon2/name", "k10temp")
    write(hw / "hwmon2/temp1_label", "Tctl")
    write(hw / "hwmon2/temp1_input", "55750")
    return root


@pytest.fixture
def paths(tmp_path):
    from fan_control import guard
    return guard.Paths(tmp_path / "etc", tmp_path / "run")
