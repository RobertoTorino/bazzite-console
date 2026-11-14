<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Webcam](../assets/webcam/ps5-webcam.webp){ .app-logo }

# Webcam

!!! warning "Changes the board"
    Allow access installs a system-wide udev rule for supported camera identifiers. A per-user service loads camera firmware when the camera connects. The udev rule is removed when the app is uninstalled.

Makes a supported Sony USB camera a webcam on **Bazzite**: the **PS5 HD Camera (CFI-ZEY1)**, and the PS4 Camera
(CUH-ZEY1 or CUH-ZEY2) on Sony's PlayStation Camera Adapter (CFI-ZAA1). The app loads the camera's firmware and
shows its picture, with picture settings, screenshots and recordings. After that, OBS, a browser, Discord or any
other app can use the camera like any USB camera.

It has not been validated on PS5 hardware. Recognition of these camera identifiers does not
establish that every PS5 Bazzite system, USB port or adapter is compatible.

## How the camera works

The camera has no memory of its own. When it is plugged in, it is only a boot loader, an OmniVision OV580 that
waits for its firmware:

```bash
lsusb | grep 05a9           # ... ID 05a9:0580 OmniVision Technologies, Inc. USB Boot
```

The host sends the firmware each time the camera is plugged in, and this app does that. Then the camera leaves the
bus and comes back within a few seconds as a USB video camera:

```bash
lsusb | grep 05a9           # ... ID 05a9:058c OmniVision Technologies, Inc. USB Camera-OV580
```

From there on Linux's own `uvcvideo` driver drives it, so it needs **no kernel driver**. It shows up as
`/dev/video<n>`.

The camera needs a **USB 3 port** (5 Gbit/s, usually blue). The boot loader also starts on a USB 2 port, but the
video does not fit through it. The header's **USB** box shows the port's speed and flags a port that is too slow.

## The window

The header shows four boxes: **Camera** (the model and its USB port), **USB** (the port's speed), **Firmware**
(the firmware file the app has) and **Video** (the camera's video node, once it is ready). Beside them, the
**Load firmware** pill sends the firmware now. The state beside the title says where the camera is:

| State | What it means |
|---|---|
| **No camera** | No supported camera is found. If it is connected, unplug it and reconnect it. |
| **No access** | The camera waits for its firmware, and your user may not send it yet: see [Access to the camera](#access-to-the-camera). |
| **Needs its firmware** | The app has no firmware file for this camera: see [The firmware](#the-firmware). |
| **Waiting for its firmware** | Everything is there; **Load firmware** sends it now. |
| **Loading the firmware** | The firmware was sent; the camera comes back as a camera in a few seconds. |
| **Firmware not loaded** | Sending it failed; the window says why. |
| **Starting**, **Ready** | The camera is back; when it is ready, other apps can use it while the preview is off. |

## USB bandwidth

The firmware asks for the largest video stream USB 3 has, reserved whatever mode is used. A USB controller that
cannot give that sends no picture. **USB bandwidth** in the Firmware box chooses what the camera asks for:

| Setting | What it asks for |
|---|---|
| **Reduced** (the default) | two thirds of it, for USB controllers that cannot handle the full bandwidth; some modes or rates may not fit |
| **Full** | the firmware as it is: every mode at every rate, if the USB controller allows it |

The app changes only the copy of the firmware it sends (2 bytes of the camera's USB description), not the file.
A change takes effect the next time the firmware is sent: unplug the camera and plug it in again.

## Access to the camera

The boot loader belongs to root. The first time, the window shows **Access to the camera**: **Allow access…** asks
for your password in the system's password dialog and adds a system-wide udev rule that gives the logged-in user
the boot loader, for its USB ID only. The same rule starts the load service when the camera is plugged in (see
[Loading by itself](#loading-by-itself)). It takes effect at once; there is no need to unplug the camera or log
out. The app and its firmware loader run as your user, never as root.

The rule is `/etc/udev/rules.d/70-ps5-webcam.rules`:

```
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="05a9", ATTR{idProduct}=="0580", TAG+="uaccess", TAG+="systemd", ENV{SYSTEMD_USER_WANTS}+="ps5-webcam-load.service"
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="05a9", ATTR{idProduct}=="058c|058a", TEST=="power/control", ATTR{power/control}="on"
```

The second line keeps a camera with its firmware out of USB autosuspend while it is plugged in. When the app finds
a rule from an earlier version, it offers **Allow access…** again to update it. `install.sh --uninstall` removes
the rule again (with sudo).

## The firmware

The firmware is Sony's, so the suite does not include it. The **Firmware** box offers two ways to get it:

- **Download…** gets the firmware of the camera that is plugged in, from a project that publishes it, after
  asking. The app downloads one fixed version of each file from GitHub (`raw.githubusercontent.com`) and checks
  its size and SHA-256, so it uses the file it expects or nothing:

    | Camera | Firmware | From |
    |---|---|---|
    | PS5 HD Camera | 21.01-03.20.00.04 (67 KB) | [prosperodev/hdcamera](https://github.com/prosperodev/hdcamera) |
    | PS4 Camera | from PS4 system software 1.50 to 3.15 (65 KB) | [psxdev/luke_firmwares](https://github.com/psxdev/luke_firmwares) |

- **Use a file…** takes a firmware file you have.

The app checks the SHA-256 of the file it has and names the files it knows. A known file turns the header's
**Firmware** box green, with the version, and the line under the file's name says "SHA-256 checked: it is the known
file", with the hash; a file of your own turns the box orange. The SHA-1 is the hash the projects that publish the
files quote.

| Firmware | SHA-256 | SHA-1 |
|---|---|---|
| PS5 HD Camera 21.01-03.20.00.04: the download | `10af1aee76fe0057a88db7ebf5f3ebf32430633effb93722be4cd0a9ed4fce54` | `0fa4da31a12b662a9a80abc8b84932770df8f7e1` |
| The same with the Discord and gamma fix | `42ce5f7033a1115988cada3ebb8e0a143e8b241661f203a12275354dd2ba0bf6` | `a5d8aadab91d78e33f4c038798c047066e6713d7` |
| PS4 Camera, from PS4 system software 1.00 to 1.05 | `8262c2a785128a04273bbcf360e29e30c10c9f3b1c3e2571a5eea5b929f41e16` | `7390be76a163c2d4a68d939577d46d7c20165881` |
| PS4 Camera, from PS4 system software 1.50 to 3.15: the download | `d550c4abc416385810ca181867f4dd650198e1214d371ba058005a10f420fd9b` | `fe86162309518a0ffe267075a2fcf728c5856b3e` |
| PS4 Camera, from PS4 system software 3.50 to 5.05 | `a6f99b283b707ece098602aea823415e614db3d64b21a22c53d45476e5405b24` | `c556911796202deef1cbb051390b5c3a2e6c0a7a` |
| PS4 Camera, from PS4 system software 6.00 to 7.02 | `09513d1068b9b5e23b09e03bca5640ed4d01830b034b9802395006b14a927b01` | `8b8a6621d358f6782c2e3b31aac2cdfb25102c00` |

Any other file of a sensible size is your choice, and the app says it is not a file it knows. It refuses a file it
knows to be the other camera's firmware. The files are kept in `~/.local/share/ps5-webcam/firmware/`:
`cfi-zey1.bin` for the PS5 HD Camera, `ps4-camera.bin` for the PS4 Camera.

## Loading by itself

With **Load it by itself when the camera is plugged in** on (the default), you do not need to open the app again
once the camera has its firmware file and access. The installer adds a service for your user,
`~/.config/systemd/user/ps5-webcam-load.service`. It sends the firmware:

- when the camera is plugged in, started by the udev rule;
- at login, for a camera that was plugged in before.

It runs as your user, not as root. To see what it did:

```bash
journalctl --user -u ps5-webcam-load.service
```

With the option off, the service does nothing and the **Load firmware** pill in the window's header sends the
firmware. While the window is open it also sends the firmware itself, once per plug-in, when the service could not
(for example because the firmware file or the access came later).

Without the window, the same is a terminal command:

```bash
ps5-webcam --load      # sends the firmware to every camera that waits for it
```

When no camera is found although one is connected, unplug it and plug it in again: it starts as a boot loader, and
the load service sends the firmware as usual.

## The picture

Once the camera is ready, the header shows its video node and the **Picture** box offers every mode the camera
reports, each frame size at each of its rates. The camera has two image sensors, and its modes are of two kinds:

| Kind | For example |
|---|---|
| One camera | 1920 × 1080, 1280 × 800 |
| Both cameras, side by side in one frame | 3840 × 1080, 2560 × 800 |

The list shows what your camera reports, the one-camera modes first, the largest at the top. Not every mode gives a
picture. A mode may need more USB bandwidth than the system gives, and then its frames arrive damaged; in some
modes a camera sends nothing at all. After a few seconds the window says which, and stops the preview: choose a
slower rate or a smaller mode.

**Start preview** shows the picture. For a side-by-side mode, **Show** picks the whole frame or either half. Each
half is the lens on that side as you face the camera. **Save picture…** saves what the preview shows, at the
camera's own size, as a PNG, where you choose. The preview shows up to 30 frames a second; other apps get every
frame the camera sends.

While the preview runs, the app holds the camera, and other apps cannot use it. **Stop preview** (or closing the
window) gives it back.

### Full screen

**Full screen** shows the picture over the whole screen, and starts the preview when it was not running. The row
at the bottom holds its buttons, and the line above it shows the mode, the zoom and, while it records, the
recording's time:

| Button | What it does |
|---|---|
| **Screenshot** (S) | Saves what the screen shows as a PNG in your **Pictures** folder |
| **Record**, **Stop** (R) | Starts a recording of what the screen shows, and stops it; it goes to your **Videos** folder |
| **Gray**, **Color** (G) | Black and white, or color again; the app remembers it |
| **Zoom −**, **Zoom +** (−, +, or the mouse wheel) | Zooms out or in: 1x, 1.5x, 2x, 3x and 4x |
| the arrow keys, or a drag with the mouse | Move the zoomed picture |
| **Mode −**, **Mode +** (PageUp, PageDown) | The mode before or the next one; the picture starts again in it |
| **Close** (Esc) | Back to the window; a recording stops and is kept |

Screenshots and recordings show what you see: zoomed in and black and white too. Each goes in a **Webcam** folder,
named with the date and the time (`Webcam 2026-11-01 21-04-09.png`); the line above the buttons says where the
file was saved. A recording is an MP4 with at most 30 frames a second, written with the video encoder Qt brings.
The mode does not change while it records: stop it first. If the camera stops sending, choose another mode with
**Mode −** or **Mode +**. Closing the app while it records stops the recording and writes its file first.

## Picture settings

Beside the preview, **Picture settings** shows the camera's own settings, as it reports them, such as brightness,
contrast, gain, white balance and exposure. A setting the camera does not let be changed now is grayed, for
example one that an automatic setting decides. **Defaults** puts every setting back.

The app sets the camera's exposure to automatic unless you choose otherwise; **Defaults** keeps that too.

The camera forgets its settings when it is unplugged. The app keeps the ones you changed and sets them again each
time the camera is ready, so other apps get the same picture.

## Using it in other apps

Any app that uses a webcam finds the camera as a USB video device (the PS5 HD Camera as **USB Camera-OV580**). In
OBS, add a **Video Capture Device (V4L2)** source and choose that device. A one-camera mode such as 1920 × 1080
gives an ordinary webcam picture. Many apps pick the camera's first mode by themselves; choose the resolution in
the app if it offers one.

## PS4 Camera

The PS4 Camera (CUH-ZEY1 or CUH-ZEY2) on Sony's PlayStation Camera Adapter (CFI-ZAA1) starts as the same boot
loader. The app knows it by the adapter between them and shows **PS4 Camera**; the adapter does not say which of the
two models it is. It has its own firmware, which **Download…** gets for it, and the same USB bandwidth setting
applies. Once loaded, it is USB ID `05a9:058a`. A PS4 Camera on another adapter, without Sony's, looks like a PS5
HD Camera to the app and is not supported.

## Install

Install it from the [portal](../portal.md), on its **Utilities** tab, or run the installer from a repository
checkout, as your own user:

```bash
apps/webcam/install.sh                         # app menu entry and Desktop icon
apps/webcam/install.sh --no-desktop-shortcut   # app menu entry only
apps/webcam/install.sh --uninstall             # remove the app, its udev rule and its load service; keeps its settings and firmware
apps/webcam/install.sh --uninstall --purge     # also remove its settings and firmware
```

Installing needs no root and changes no system permissions; only **Allow access…** in the app does.
It installs:

- the app in `~/.local/share/ps5-webcam/app`;
- PyQt6 in the suite's shared environment `~/.local/share/bazzite-console-suite/venv`;
- the launcher `~/.local/bin/ps5-webcam`, an app menu entry and a Desktop icon;
- the load service `~/.config/systemd/user/ps5-webcam-load.service`, enabled for your login.

Settings are kept in `~/.config/ps5-webcam/ps5-webcam.ini`.

## Credits

The upload protocol was found by the PS4EYECam driver (Antonio Jose Ramos Marquez) and is used by
[PS Move API](https://github.com/thp/psmoveapi), whose camera firmware loader this app follows. The PS5 HD Camera's
firmware file and the camera's USB description come from
[prosperodev/hdcamera](https://github.com/prosperodev/hdcamera); the PS4 Camera's firmware is published by
[psxdev/luke_firmwares](https://github.com/psxdev/luke_firmwares).

## Firmware and license

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/webcam/LICENSE).
The camera's firmware belongs to Sony and is not part of the app.
