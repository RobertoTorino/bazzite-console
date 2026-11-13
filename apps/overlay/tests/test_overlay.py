# SPDX-License-Identifier: GPL-3.0-or-later
"""The overlay window on a fake PS5: the rows, the formatting, temperature colors and the menu settings."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from bazzite_console_core.sensors import Fan, Reading, Sensors
from bazzite_console_core.theme import ORANGE, RED
from system_overlay import overlay
from conftest import Clock, proc_stat, write


def make(root) -> overlay.OverlayWindow:
    return overlay.OverlayWindow(Sensors(root, clock=Clock()))


def test_format_reading():
    rows = overlay.format_reading(Reading(
        cpu_load=12.4, cpu_mhz=3486, cpu_temp=72.1, soc_temp=81.0, board_temp=45.2, gpu_load=45.5, gpu_mhz=2000,
        gpu_temp=91.0, gpu_limit=85, vram=(300_000_000, 536_870_912), ram=(6_500_000_000, 16_200_000_000),
        nvme_temp=40.0, net=(2_100_000.0, 80_000.0), disk=(150_000_000.0, 0.0), fan=Fan(22, "auto")), 60.0)
    assert rows == {
        "cpu": ("12 % · 3486 MHz", ""),
        "gpu": ("46 % · 2000 MHz", ""),
        "vram": ("0.3 / 0.5 GB", ""),
        "ram": ("6.5 / 16.2 GB", ""),
        "refresh": ("60 Hz", ""),
        "fan": ("22 % · auto", ""),
        "cpu_temp": ("72 °C", ""),
        "soc_temp": ("81 °C", ORANGE),
        "gpu_temp": ("91 °C", RED),
        "gpu_limit": ("85 °C", ""),
        "board_temp": ("45 °C", ""),
        "nvme_temp": ("40 °C", ""),
        "net": ("↓ 2.1 MB/s · ↑ 80.0 KB/s", ""),
        "disk": ("R 150.0 MB/s · W 0 B/s", ""),
    }
    assert [key for key, _ in overlay.ROWS] == list(rows)          # every row has a value, in order


def test_format_missing_values():
    rows = overlay.format_reading(Reading(cpu_mhz=2800), None)
    assert rows["cpu"] == ("2800 MHz", "")
    assert all(text == overlay.DASH for key, (text, _) in rows.items() if key != "cpu")


def test_warm_is_orange():
    assert overlay._temp(80.0) == ("80 °C", ORANGE)
    assert overlay._temp(79.4)[1] == ""


def test_window_shows_the_ps5(qapp, ps5):
    w = make(ps5)
    texts = {k: label.text() for k, label in w.values.items()}
    assert texts["gpu"] == "46 % · 2000 MHz" and texts["fan"] == "22 % · auto"
    assert texts["gpu_limit"] == "85 °C" and texts["vram"] == "0.3 / 0.5 GB"
    assert texts["cpu_temp"] == "56 °C" and texts["soc_temp"] == "56 °C" and texts["board_temp"] == "45 °C"
    assert texts["cpu"] == "3486 MHz" and texts["net"] == overlay.DASH      # these need a second reading
    write(ps5 / "proc/stat", proc_stat(1000 + 50, 9000 + 150))
    w.refresh()
    assert w.values["cpu"].text() == "25 % · 3486 MHz"
    assert "no RPM" in w.values["fan"].toolTip()
    w.close()


def test_kernel_without_gpu_sensors(qapp, ps5_old):
    w = make(ps5_old)
    assert w.values["gpu"].text() == overlay.DASH and w.values["gpu_temp"].text() == overlay.DASH
    assert "7.3.1" in w.values["gpu"].toolTip()
    w.close()


def test_window_flags(qapp, ps5):
    w = make(ps5)
    flags = w.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint and flags & Qt.WindowType.WindowStaysOnTopHint
    assert w.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    w.set_on_top(False)
    assert not w.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    w.close()


def test_rows_can_be_hidden(qapp, ps5):
    w = make(ps5)
    w.show()
    height = w.height()
    rows = next(a.menu() for a in w.build_menu().actions() if a.text() == "Rows")
    next(a for a in rows.actions() if a.text() == "Disk").toggle()
    assert w.values["disk"].isHidden() and w.captions["disk"].isHidden()
    assert w.height() < height                                     # the window shrinks with it
    w.close()
    again = make(ps5)
    assert again.hidden_rows() == {"disk"} and again.values["disk"].isHidden()
    again.set_row_visible("disk", True)
    assert again.hidden_rows() == set()
    again.close()


def test_the_last_row_stays(qapp, ps5):
    w = make(ps5)
    for key, _ in overlay.ROWS:
        w.set_row_visible(key, False)
    assert len(w.hidden_rows()) == len(overlay.ROWS) - 1
    w.close()


def test_menu_choices_are_remembered(qapp, ps5):
    w = make(ps5)
    menu = w.build_menu()
    background = next(a.menu() for a in menu.actions() if a.text() == "Background")
    next(a for a in background.actions() if a.text() == "Very see-through").trigger()
    next(a for a in menu.actions() if a.text() == "Always on top").toggle()
    w.close()
    again = make(ps5)
    assert again.settings.get("background") == 35 and again.settings.get("on_top") is False
    assert not again.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    again.close()


def test_position_is_remembered(qapp, ps5):
    w = make(ps5)
    w.move(123, 45)
    w.close()
    again = make(ps5)
    assert (again.x(), again.y()) == (123, 45)
    again.close()
