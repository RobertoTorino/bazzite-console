# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures: an offscreen QApplication, bazzite_console_core from the checkout, settings and XDG folders in a temp
folder, PS5 game folders made here (eboot.bin and sce_sys/param.json with the fields a game has) and a /sys tree
with the figures the board check reads."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CORE = Path(__file__).resolve().parents[3] / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))           # bazzite_console_core from the checkout, as the installer bundles it


def make_game(folder: Path, title: str | None = None, title_id: str = "PPSA00001", version: str = "01.000.000",
              pictures: bool = False) -> Path:
    """A game folder with eboot.bin and, unless *title* is None, sce_sys/param.json. Returns eboot.bin."""
    (folder / "sce_sys").mkdir(parents=True)
    eboot = folder / "eboot.bin"
    eboot.write_bytes(b"\x7fELF")
    if title is not None:
        (folder / "sce_sys" / "param.json").write_text(json.dumps({
            "titleId": title_id, "contentVersion": version,
            "localizedParameters": {"defaultLanguage": "en-US", "en-US": {"titleName": title},
                                    "ja-JP": {"titleName": title + " (ja)"}}}))
    if pictures:
        from PyQt6.QtGui import QColor, QImage
        for name, size, colour in (("icon0.png", (512, 512), "#ff0000"), ("pic1.png", (1920, 1080), "#00ff00")):
            image = QImage(*size, QImage.Format.Format_ARGB32)
            image.fill(QColor(colour))
            image.save(str(folder / "sce_sys" / name))
    return eboot


def make_sys(root: Path, vram_mib: int | None = 512, gtt_mib: int = 14336, driver: str = "amdgpu",
             options: dict[str, int] | None = None, card: str = "card1") -> Path:
    """A /sys with one GPU: its memory figures, the driver it runs and the amdgpu options. *vram_mib* None: a card
    without the figures."""
    device = root / "class" / "drm" / card / "device"
    device.mkdir(parents=True)
    drivers = root / "bus" / "pci" / "drivers" / driver
    drivers.mkdir(parents=True, exist_ok=True)
    (device / "driver").symlink_to(drivers)
    if vram_mib is not None:
        (device / "mem_info_vram_total").write_text(f"{vram_mib << 20}\n")
        (device / "mem_info_gtt_total").write_text(f"{gtt_mib << 20}\n")
    params = root / "module" / "amdgpu" / "parameters"
    params.mkdir(parents=True, exist_ok=True)
    for name, value in ({"sched_policy": 2, "vm_update_mode": 0, "cwsr_enable": 0} if options is None
                        else options).items():
        (params / name).write_text(f"{value}\n")
    return root


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
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    return tmp_path / "settings"
