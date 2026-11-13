<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Fan Control](../assets/fan/ps5-fan-control.webp){ .app-logo }

# Fan Control

!!! warning "Changes the board"
    The thermal guard is a root system service, ps5-fan-control-guard.service with its files in /etc/ps5-fan-control, that reads the temperatures every two seconds. At the cool limit it sets the fan to full speed in sysfs (ps5_fan's full mode) and turns the CPU boost off (ps5_control --boost off); at the shutdown limit, held for the set number of seconds, it powers the PS5 off cleanly with systemctl poweroff. The service stays enabled across reboots and power offs. The fan setting is written in memory only, and the guard puts the saved mode back when it re-arms or stops. Nothing is written to the firmware or the kernel's arguments. Turn off disables the service and removes its files; the fan is back on its previous mode, and the boost, once the guard turned it off, stays off until you turn it on again or reboot.

Fan Control is an optional app for PlayStation 5 hardware running Bazzite. It shows the PS5's temperatures and its
fan, and runs a thermal guard: a system service that watches the SoC, the CPU and the GPU, also when no app is open.

## Compatibility

The GPU's temperature needs a ps5-linux kernel with the GPU sensors (7.3.1 and later); on older kernels the guard
watches the SoC and the CPU.

The PS5 kernel already protects the console on its own: it slows the GPU from 85 °C, runs the fan at full duty from
87 °C and forces it to maximum from 90 °C. The guard adds what the kernel does not do: a warning on the desktop, the
CPU boost off, and a clean shutdown.

## Using it

The window shows the temperatures and the fan. Turn the guard on to have it watch the temperatures in the
background. When they rise it warns on the desktop, turns the fan to full speed and the CPU boost off, and at a
critical temperature it shuts the console down cleanly.

Turning the guard on or off asks for your password (pkexec), because the guard is a system service. The box at the
top of this page says what the guard changes and how turning it off undoes it.

## Install and remove

The portal installs and removes the app. By hand, as your own user: `bash install.sh`, and
`bash install.sh --uninstall` to remove it, which also removes the guard.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/fan/LICENSE).
