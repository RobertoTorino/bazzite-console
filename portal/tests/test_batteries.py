# SPDX-License-Identifier: GPL-3.0-or-later
"""The devices' batteries in the header (owner, 22-11-2026): read from UPower, one upright battery each left of ☰."""

from __future__ import annotations

import pytest

from bazzite_console_portal import batteries
from bazzite_console_portal.batteries import Device

PATH = "/org/freedesktop/UPower/devices/"
# As UPower answers on the owner's machine (22-11-2026), with a controller, the board's supply and line power added
DEVICES = {
    PATH + "mouse_dev_1": {"Type": 5, "Model": "Satechi M1 Mouse", "PowerSupply": False, "IsPresent": True,
                           "Percentage": 52.0, "State": 0},
    PATH + "keyboard_dev_2": {"Type": 6, "Model": "Slim X1 Keyboard", "PowerSupply": False, "IsPresent": True,
                              "Percentage": 100.0, "State": 0},
    PATH + "battery_ps_controller_battery_3": {"Type": 12, "Model": "DualSense Wireless Controller",
                                               "PowerSupply": False, "IsPresent": True, "Percentage": 15.0,
                                               "State": 1},
    PATH + "battery_BAT0": {"Type": 2, "Model": "", "PowerSupply": True, "IsPresent": True, "Percentage": 80.0,
                            "State": 2},
    PATH + "line_power_AC": {"Type": 1, "PowerSupply": True, "IsPresent": True, "Percentage": 0.0, "State": 0},
}


def fake_upower(devices: dict[str, dict]):
    calls = []

    def call(path, interface, method, arguments):
        calls.append((path, method))
        if method == "EnumerateDevices":
            return [list(devices)]
        if method == "GetAll" and arguments == [batteries.DEVICE]:
            return [devices[path]]
        return []
    return call, calls


def test_read_gives_each_device_with_a_battery_and_leaves_out_the_supply_and_line_power():
    call, _calls = fake_upower(DEVICES)
    assert batteries.read(call) == [Device("Mouse", "Satechi M1 Mouse", 52, False),
                                    Device("Keyboard", "Slim X1 Keyboard", 100, False),
                                    Device("Controller", "DualSense Wireless Controller", 15, True)]


def test_read_without_upower_gives_nothing():
    assert batteries.read(lambda *_args: []) == []


@pytest.mark.parametrize("properties, expected", [
    ({"Type": 17, "Model": "Headset", "Percentage": 70.4, "State": 2}, Device("Headset", "Headset", 70, False)),
    ({"Type": 99, "Model": "", "Percentage": 101, "State": 1}, Device("Device", "", 100, True)),
    ({"Type": 5, "Model": "Gone", "IsPresent": False, "Percentage": 40}, None),
    ({"Type": 5, "Model": "No level"}, None),
])
def test_device_reads_the_kind_from_upowers_type(properties, expected):
    assert batteries.device(properties) == expected


def test_tooltip_names_the_kind_the_model_and_the_level():
    assert Device("Controller", "DualSense", 15, True).tooltip() == "Controller: DualSense, 15 %, charging"
    assert Device("Mouse", "", 52, False).tooltip() == "Mouse, 52 %"


def test_the_header_shows_a_battery_per_device_left_of_the_settings_symbol(qapp, home, settings_dir, tmp_path,
                                                                           monkeypatch):
    from test_bigpicture import make_window

    call, _calls = fake_upower(DEVICES)
    monkeypatch.setattr(batteries, "dbus_call", call)
    window, _pad = make_window(tmp_path)
    marks = window.big.batteries
    assert [mark.toolTip() for mark in marks] == ["Mouse: Satechi M1 Mouse, 52 %",
                                                  "Keyboard: Slim X1 Keyboard, 100 %",
                                                  "Controller: DualSense Wireless Controller, 15 %, charging"]
    upper = window.big.upper
    assert upper.indexOf(window.big.battery_row) < upper.indexOf(window.settings_button)
    assert all(mark.focusPolicy().name == "NoFocus" for mark in marks)
    window.big.set_scale(0.5)
    assert marks[0].width() == round(58 * 0.5)
    monkeypatch.setattr(batteries, "dbus_call", lambda *_args: [])
    window.show_batteries()
    assert window.big.batteries == []
    window.close()
