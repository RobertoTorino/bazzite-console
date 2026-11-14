<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# System Overlay

A small window that stays on top of your desktop and shows the **PlayStation 5**'s live system values on **Bazzite**:
CPU load and clock, GPU load and clock, VRAM, RAM, refresh rate, the fan's duty and mode, the CPU, SoC, GPU, mainboard
and NVMe temperatures, the GPU's temperature limit, network and disk. It only reads sensors: nothing changes and it
needs no root.

The GPU's load, clock and temperature need a ps5-linux kernel with the GPU sensors (7.3.1 and later); on older
kernels those rows show "—". The PS5's fan reports no speed in RPM, so the overlay shows its duty (share of full
speed) and whether the kernel's curve drives it (auto).

Drag it with the left mouse button; the right button opens a menu: rows, background, always on top, quit.

Install: `bash install.sh` (as your own user). Remove: `bash install.sh --uninstall`.
