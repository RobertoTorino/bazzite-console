<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![System Overlay](../assets/overlay/ps5-system-overlay.webp){ .app-logo }

# System Overlay

A small window that stays on top of your desktop and shows the live system values of a **PlayStation 5** running
**Bazzite**. It only reads sensors: nothing on the console changes and it needs no root.

| Row | What it shows | Source |
|---|---|---|
| CPU | load over the last second and the average core clock | `/proc/stat`, cpufreq or `/proc/cpuinfo` |
| GPU | load and clock | `amdgpu` (`gpu_busy_percent`, its clock sensor) |
| VRAM | used / total of the GPU's share of the memory | `amdgpu` |
| RAM | used / total | `/proc/meminfo` |
| Refresh | the refresh rate of the screen the window is on | Qt |
| Fan | the fan's duty (its share of full speed) and its mode: auto, manual or full speed | `ps5_fan` |
| CPU temp | Tctl | `k10temp` |
| SoC temp | the main SoC sensor | `ps5_fan` ("MainSoC") |
| GPU temp | the GPU's own sensor | `amdgpu` |
| GPU limit | the temperature above which the kernel's GPU governor slows the GPU down | `ps5_gpufreq` (`temp_limit`) |
| Board temp | the warmest of the three board sensors | `ps5_fan` ("Local") |
| NVMe temp | the SSD | `nvme` |
| Network | download and upload, all interfaces except loopback | `/proc/net/dev` |
| Disk | read and write, all disks | `/proc/diskstats` |

A row shows "—" when the console's kernel does not offer its value. Temperatures turn orange from 80 °C and red
from 90 °C. The values update every second.

## Compatibility

The GPU's load, clock and temperature need a ps5-linux kernel with the GPU sensors (7.3.1 and later); on older
kernels those rows show "—", and hovering the GPU row says why. The PS5's fan reports no speed in RPM, so the
overlay shows its duty (its share of full speed) and whether the kernel's curve drives it (auto).

## Using it

- **Move it:** drag it with the left mouse button. It opens where you left it.
- **Options:** right-click it.
    - **Rows:** tick the rows you want to see; the window resizes to fit. At least one row stays.
    - **Background:** Solid, Light see-through, See-through or Very see-through. The text stays fully visible.
    - **Always on top:** on by default.
    - **Quit.**

The window is frameless and see-through, with rounded corners and a thin border in the suite's accent color.
Starting it a second time brings the running window to the front.

### Where it shows

On top of the desktop and of windowed or borderless games. A game in exclusive fullscreen can still cover it.

On Wayland a window cannot keep itself on top or choose where it opens, so the overlay runs through XWayland.
`ps5-system-overlay --native-wayland` runs it as a Wayland window instead: sharper on a scaled screen, but KDE
decides whether it stays on top (a KWin window rule can keep it there).

## Install and remove

The portal installs and removes the app; it is on the **Sustainable** tab. By hand, from a clone or a release
folder, as your own user:

```bash
./install.sh                         # app menu entry and Desktop icon
./install.sh --no-desktop-shortcut   # app menu entry only
./install.sh --uninstall             # remove the app; keeps its settings
./install.sh --uninstall --purge     # also remove its settings
```

It installs:

- the app in `~/.local/share/ps5-system-overlay/app`;
- PyQt6 in the suite's shared venv `~/.local/share/bazzite-console-suite/venv`;
- the launcher `~/.local/bin/ps5-system-overlay`, an app menu entry and a Desktop icon.

Settings are kept in `~/.config/ps5-system-overlay/ps5-system-overlay.ini`.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/overlay/LICENSE).
