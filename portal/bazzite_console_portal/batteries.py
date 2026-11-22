# SPDX-License-Identifier: GPL-3.0-or-later
"""The batteries of the devices connected to the board (owner, 22-11-2026): a controller, a mouse, a keyboard, a
headset. The header shows one upright battery for each, left of ☰, with its level under it and a bolt while it
charges; nothing when no device with a battery is connected.

Read from UPower on the system bus (QtDBus: no process started), which knows the kernel's batteries (a controller's)
and BlueZ's (a Bluetooth mouse's, keyboard's or headset's). The board's own power supply and line power are left
out. What kind of device it is comes from UPower's Type, its name from Model. A device's object path holds its
address, so it is never shown or logged."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

SERVICE = "org.freedesktop.UPower"
PATH = "/org/freedesktop/UPower"
DEVICE = "org.freedesktop.UPower.Device"
PROPERTIES = "org.freedesktop.DBus.Properties"
BATTERY_MS = 5000               # the batteries are read again this often
LOW = 20                        # % and lower: the level shows red
LINE_POWER = 1                  # UPower's Type of a power line, never a device's battery
CHARGING = 1                    # UPower's State while a battery charges
# UPower's Type to the word the tooltip starts with; another type is a "Device"
KINDS = {2: "Battery", 5: "Mouse", 6: "Keyboard", 8: "Phone", 9: "Media player", 10: "Tablet", 12: "Controller",
         13: "Pen", 14: "Touchpad", 17: "Headset", 18: "Speakers", 19: "Headphones", 21: "Audio device",
         22: "Remote control", 26: "Wearable", 27: "Toy"}

Call = Callable[[str, str, str, list], list]        # (object path, interface, method, arguments) -> the reply


@dataclass(frozen=True)
class Device:
    kind: str
    model: str
    percent: int
    charging: bool

    def tooltip(self) -> str:
        """As "Controller: DualSense Wireless Controller, 82 %", with ", charging" while it charges."""
        name = f"{self.kind}: {self.model}" if self.model else self.kind
        return f"{name}, {self.percent} %" + (", charging" if self.charging else "")


def device(properties: dict) -> Device | None:
    """A device with a battery from UPower's properties of it; None for the board's own supply, line power, a
    device not there, or one without a level."""
    if properties.get("PowerSupply") or properties.get("Type") == LINE_POWER:
        return None
    if not properties.get("IsPresent", True):
        return None
    try:
        percent = round(float(properties["Percentage"]))
    except (KeyError, TypeError, ValueError):
        return None
    kind = KINDS.get(int(properties.get("Type", 0) or 0), "Device")
    return Device(kind, str(properties.get("Model", "")).strip(), max(0, min(100, percent)),
                  properties.get("State") == CHARGING)


def dbus_call(path: str, interface: str, method: str, arguments: list) -> list:
    """One call to UPower on the system bus; [] when it does not answer (no UPower, no system bus)."""
    from PyQt6.QtDBus import QDBusConnection, QDBusMessage
    bus = QDBusConnection.systemBus()
    if not bus.isConnected():
        return []
    message = QDBusMessage.createMethodCall(SERVICE, path, interface, method)
    message.setArguments(arguments)
    reply = bus.call(message)
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        return []
    return reply.arguments()


def read(call: Call | None = None) -> list[Device]:
    """The connected devices with a battery, in UPower's order."""
    call = call or dbus_call
    reply = call(PATH, SERVICE, "EnumerateDevices", [])
    found = []
    for path in (reply[0] if reply else []):
        answer = call(str(path.path() if hasattr(path, "path") else path), PROPERTIES, "GetAll", [DEVICE])
        if answer and isinstance(answer[0], dict) and (one := device(answer[0])) is not None:
            found.append(one)
    return found
