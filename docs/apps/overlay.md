<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![System Overlay](../assets/overlay/ps5-system-overlay.webp){ .app-logo }

# System Overlay

System Overlay is an optional app for PlayStation 5 hardware running Bazzite: a small window that stays on top of
your desktop and shows the PS5's live system values. It only reads sensors: nothing changes and it needs no root.

## What it shows

CPU load and clock, GPU load and clock, VRAM, RAM, the refresh rate, the fan's duty and mode, the CPU, SoC, GPU,
board and NVMe temperatures, the GPU's temperature limit, network and disk.

## Compatibility

The GPU's load, clock and temperature need a ps5-linux kernel with the GPU sensors (7.3.1 and later); on older
kernels those rows show "—". The PS5's fan reports no speed in RPM, so the overlay shows its duty (its share of full
speed) and whether the kernel's curve drives it (auto).

## Using it

Drag the window with the left mouse button. The right button opens a menu: the rows to show, the background, always
on top, and quit.

## Install and remove

The portal installs and removes the app. By hand, as your own user: `bash install.sh`, and
`bash install.sh --uninstall` to remove it.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/overlay/LICENSE).
