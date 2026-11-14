<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Fan Control](../assets/fan/ps5-fan-control.webp){ .app-logo }

# Fan Control

!!! warning "Changes the board"
    The thermal guard is a root system service, ps5-fan-control-guard.service with its files in /etc/ps5-fan-control, that reads the temperatures every two seconds. At the cool limit it sets the fan to full speed in sysfs (ps5_fan's full mode) and turns the CPU boost off (ps5_control --boost off); at the shutdown limit, held for the set number of seconds, it powers the PS5 off cleanly with systemctl poweroff. The service stays enabled across reboots and power offs. The fan setting is written in memory only, and the guard puts the saved mode back when it re-arms or stops. Nothing is written to the firmware or the kernel's arguments. Turn off disables the service and removes its files; the fan is back on its previous mode, and the boost, once the guard turned it off, stays off until you turn it on again or reboot.

Fan Control shows the temperatures and the fan of a **PlayStation 5** running **Bazzite**. It can also turn on a
**thermal guard**, a background service that protects the console from overheating. The guard keeps watching when
no app is open. When the console gets too hot it warns you. If it gets hotter still, it runs the fan at full speed
and turns the CPU boost off. As a last resort it shuts the console down cleanly.

Nothing changes until you turn the guard on.

## Compatibility

The app reads the sensors of the ps5-linux kernel: the SoC temperature, three mainboard temperatures and the fan
from `ps5_fan`, the CPU from `k10temp` (Tctl), and the GPU from `amdgpu`. The GPU's temperature needs a ps5-linux kernel with the
GPU sensors (7.3.1 and later); on older kernels the guard watches the SoC and the CPU.

The PS5 kernel already protects the console on its own: it slows the GPU from 85 °C, runs the fan at full duty from
87 °C and forces it to maximum from 90 °C. The guard adds what the kernel does not do: a warning on the desktop, the
CPU boost off, and a clean shutdown.

## Using it

The top row has four boxes: the **SoC** temperature, the **CPU (Tctl)** temperature, the **Fan** with its duty and
mode, and the state of the **Thermal guard**. A temperature box turns orange at the warning limit and red at the
cooling limit. The status next to the title says the same as the guard's box: **Guard off**, **Guard on**, **Hot**,
**Cooling**, **Shutting down** or **Guard not running**.

Under **Thermal guard** you set the limits and turn the guard on or off.

- **Warn at, cool at, shut down at:** the guard's three temperature limits, in °C. They must rise from the warning
  to the shutdown, between 60 and 105 °C.
- **after:** how many seconds the temperature must stay at the shutdown limit before the guard shuts the console
  down, from 3 to 60.
- **Turn on…:** turns the guard on with these limits. The app asks you to confirm, then asks for your password
  (pkexec), because the guard is a system service. The guard starts at once, and again every time the console
  starts.
- **Apply…:** takes the place of Turn on… while the guard is on. It gives the guard the limits you changed. After
  an update of the app it also replaces the guard with the new version's; the app says when that is needed.
- **Turn off…:** stops the guard and removes it, after your password. The fan goes back to how it was.
- **Defaults:** puts 85, 88 and 95 °C and 10 seconds back in the fields.

**Fan** shows the fan's duty and what sets it (the kernel's curve, a manual value or full speed), the **Board**
temperature (the warmest of the three mainboard sensors), the GPU's temperature where the kernel reports it, and
the kernel's fan curve: the duty per SoC temperature. **What the guard did** lists the guard's recent warnings and actions,
newest first.

The window reads the sensors itself, every two seconds, so it shows them also while the guard is off.

## The thermal guard

Every two seconds the guard reads the SoC, the CPU and the GPU temperature and takes the hottest of them. It acts
at three limits:

| Limit | Default | What the guard does |
|---|---|---|
| Warning | 85 °C | It sends a desktop notification and writes a line in the journal. |
| Cooling | 88 °C | It runs the fan at full speed (`ps5_fan`'s full mode) and turns the CPU boost off (`ps5_control --boost off`). |
| Shutdown | 95 °C, held for 10 s | It shuts the console down cleanly (`systemctl poweroff`), to protect it. |

- **When the console has cooled down.** At 5 °C below the warning limit the guard puts the fan back to how it was:
  the kernel's curve, or the manual value it had. With the defaults that is at 80 °C. From then on the guard can
  warn again.
  **The CPU boost stays off.** Turn it on again with `sudo systemctl restart ps5boost`, or restart the console.
- **The shutdown waits.** The guard shuts the console down only when the temperature stays at the shutdown limit
  for the whole time you set. If the temperature drops below the limit before that, the countdown stops. The guard
  tells you when a countdown starts.
- **A broken sensor never shuts the console down.** The guard ignores a reading below 1 °C or above 150 °C. If it
  can read none of the three temperatures, it says so and does nothing.
- **When the guard stops,** because you turned it off or uninstalled the app, it puts the fan back to how it was.
- **When the guard is installed but does not run,** the app shows **Guard not running** and points to its log.

Sony publishes no thermal limits for the PS5. The defaults follow the kernel's: the warning is where the kernel
starts to slow the GPU, and the cooling limit lies past the fan curve's full duty and before the kernel forces the
fan to maximum.

## The fan

The kernel's `ps5_fan` driver drives the PS5's fan, by default on a curve that follows the SoC temperature. The fan
reports no speed in RPM. What the app shows is its **duty**: the share of full speed the kernel asks for.

When the app finds no fan, the driver is not loaded: the ps5-linux kernel has it.
[Bazzite Test](bazzite.md) shows the kernel and the sensors.

## Files

- `/etc/ps5-fan-control/guard.py` and `guard.json`: the guard and its limits, while it is on.
- `/etc/systemd/system/ps5-fan-control-guard.service`: the service that starts the guard when the console starts.
- `/run/ps5-fan-control/state.json`: what the guard last read and recently did. The app shows it.
- `~/.config/ps5-fan-control/ps5-fan-control.ini`: the size and position of the window.

To read the guard's log, run `journalctl -u ps5-fan-control-guard`.

## Install and remove

The portal installs and removes the app; it is on the **Sustainable** tab. By hand, from a clone or a release
folder, as your own user:

```bash
./install.sh                         # app menu entry and Desktop icon
./install.sh --no-desktop-shortcut   # app menu entry only
./install.sh --uninstall             # remove the app and the thermal guard; keeps its settings
./install.sh --uninstall --purge     # also remove its settings
```

It installs:

- the app in `~/.local/share/ps5-fan-control/app`;
- PyQt6 in the suite's shared venv `~/.local/share/bazzite-console-suite/venv`;
- the launcher `~/.local/bin/ps5-fan-control`, an app menu entry and a Desktop icon.

Turning the guard on and off needs `pkexec` and the system `python3`. Bazzite has both. Uninstalling the app also
stops and removes the guard, which needs `sudo`.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/fan/LICENSE).
