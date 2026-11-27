# SPDX-License-Identifier: GPL-3.0-or-later
"""bazzite_console_core from the checkout, as run.sh puts it on the path, the app's package, and a folder of recordings."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP.parents[1] / "core"))


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """The application with Nexus's theme, as create_app() sets it for this app."""
    from bazzite_console_core import widgets
    from bazzite_console_core.nexus import NEXUS
    from PyQt6.QtWidgets import QApplication
    widgets.set_theme(NEXUS)
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def settings_in_a_temp_folder(tmp_path):
    """The .ini settings in a temp folder: no test reads the user's own."""
    from PyQt6.QtCore import QSettings
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "config"))


@pytest.fixture(autouse=True)
def no_tooltip_left():
    """The rounded tooltip lets go of the app after each test (create_app() is not called here)."""
    yield
    from bazzite_console_core.widgets import RoundedToolTip
    RoundedToolTip.uninstall()


@pytest.fixture
def recordings(tmp_path):
    """A day of recordings: 00:40:00 to 00:52:59, a line per second; the GPU clock rises at 00:46, a restart at 00:50."""
    from nexus_flight_recorder.recorder import COLUMNS
    out = tmp_path / "log"
    out.mkdir()
    lines = [",".join(COLUMNS)]
    for minute in range(40, 53):
        for second in range(60):
            late = minute >= 46
            values = {"time": f"00:{minute:02d}:{second:02d}", "boot": "bbbbbbbb" if minute >= 50 else "aaaaaaaa",
                      "threads": "16", "load1": "1.0", "cpu_load": "100.0" if late else "5.0", "cpu_temp": "66.5",
                      "soc_temp": "60.0", "board_temp": "45.0", "gpu_load": "40.0",
                      "gpu_mhz": "1850" if late else "1000", "gpu_temp": "50.0", "gpu_limit": "90", "fan_duty": "40",
                      "ram_used": str(4096 << 20),
                      "vram_used": str(1024 << 20), "swap_used_kb": str(512 << 10), "mem_pressure": "0.50",
                      "busiest": "steam" if late else "code"}
            lines.append(",".join(values[c] for c in COLUMNS))
    (out / "2026-11-27.csv").write_text("\n".join(lines) + "\n")
    (out / "2026-11-26.csv").write_text(",".join(COLUMNS) + "\n")
    return out
