<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 Bluetooth](../assets/bluetooth/ps5-bluetooth.webp){ .app-logo }

# PS5 Bluetooth

Use the board with a Bluetooth keyboard, mouse and controllers only, with no USB ones needed, also on a new board
and after a fresh install. After every boot the app's service looks for the devices you listed and pairs the ones in
pairing mode, on the login screen, before anyone logs in.

## Using it

1. **Add…** the devices to pair. Pick one Bluetooth knows (paired before, or found with **Search nearby** while it
   is in pairing mode), or type its name exactly as the device gives it.
2. Switch on **Pair the listed devices after every boot**. It installs a small system service and asks for your
   password.
3. From then on, after a boot, put the keyboard and the mouse in pairing mode: hold the connect button until the
   light blinks fast. They connect within a few seconds, on the login screen.

The list shows each device with what Bluetooth knows of it: connected, paired, known, or not seen yet. **Remove**
takes a name off the list; the device itself stays paired. Once the service is installed, a changed list waits for
**Save**, which asks for your password once.

The header shows whether Bluetooth is on, whether the service pairs after boot, the controller batteries and what
Plasma does with Bluetooth at login. The small round **i** beside the state says the same in short.

## Pair after boot

For 5 minutes after every boot, the service searches for the listed devices and stops as soon as every one is
connected:

- A listed device in pairing mode is trusted, paired and connected.
- A listed device that was paired before reconnects. One that refuses its old pairing twice (it was paired with
  another computer, or reset) is removed and paired again.
- Devices with other names are never paired. Every DualSense calls itself the same, so any DualSense nearby in pairing
  mode is paired while none is connected; once one is, another is left alone.

**Search now** searches again without a reboot, for another 5 minutes: put the device in pairing mode first. It asks
for your password. **The search after this boot** at the bottom shows what the search did, with the time of each
line.

A name can be copied by someone nearby with deliberate effort. The search is limited to the listed names and to the
first minutes after a boot.

## Controller batteries

A DualSense or DualSense Edge reports its battery through its own driver, not through Bluetooth, so the Bluetooth
icon shows no battery for it, as it does for a keyboard or a mouse. **Show controller batteries in the Bluetooth
icon** installs a second small service that hands each controller's battery to Bluetooth every 30 seconds. It uses
Bazzite's own D-Bus and GLib for Python (`python3-dbus`, `python3-gobject`).

## Bluetooth at login

Plasma switches Bluetooth on or off when you log in. By default it restores the state it saved when the last session
ended. A reboot from a terminal, or one that an update starts, stops Bluetooth before the desktop session ends, so
Plasma saves it as off. The keyboard and the mouse then work on the login screen and stop as soon as the desktop
appears, with nothing to say why.

**Switch Bluetooth on at every login** sets Plasma's own setting (System Settings, Bluetooth, **When logging in**:
Enable Bluetooth), so Bluetooth is on at every login whatever was saved. It is your own setting and asks for no
password. Switched off, Plasma restores the saved state again. On another desktop than Plasma it does not apply.

## A USB 3 device beside the receiver

A device in a USB 3 port (USB 3.0 to 3.2: a drive, a hub, a camera, a Wi-Fi stick) can heavily interfere with a
Bluetooth receiver in a USB port beside it: USB 3 gives off noise in the same 2.4 GHz band that Bluetooth uses.
Devices then pair late or not at all, lose their connection, or a mouse or controller lags. A USB extension cable
helps: put the receiver (or the USB 3 device) on it and keep the two as far apart as you can.

## Install

Install it from the portal (the **Utilities** tab), or from a checkout of the repository:

```bash
apps/bluetooth/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/bluetooth/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/bluetooth/install.sh --uninstall             # remove it; --purge removes its settings too
```

The launcher is `~/.local/bin/ps5-bluetooth`; the app runs on the suite's shared Python environment.
You need a keyboard and a mouse once, to install the app and list the devices.

## Files

- `~/.config/ps5-bluetooth/ps5-bluetooth.ini`: the list, while the service is not installed.
- `/etc/ps5-bluetooth/` (`boot.py`, `boot.json`), `/etc/systemd/system/ps5-bluetooth.service`
  and `/etc/systemd/system/ps5-bluetooth-battery.service`: the search after boot and the controller
  batteries, only while one of them is on. The names and the two choices are in `boot.json`. Uninstalling removes
  them; it asks for the sudo password then. What the search did: `journalctl -b -u ps5-bluetooth`.
- `~/.config/bluedevilglobalrc`, `launchState` under `[General]`: Plasma's Bluetooth at login. Uninstalling leaves it
  as it is: it is Plasma's own setting.

## License

GPL-3.0-or-later.
