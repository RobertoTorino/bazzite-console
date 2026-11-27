<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Flight Recorder

Nexus Flight Recorder writes down what the board does, one line per second, so the minutes before a fault are there
afterwards. A system service does the recording. The window starts and stops it, and shows the minutes around a time
you type. Each line holds:

- the load and the temperatures of the CPU, the SoC, the board and the GPU
- the GPU clock and the fan
- the memory, the swap and the memory pressure
- the name of the busiest program

Nexus Flight Recorder is a development app. It runs from the checkout it lives in and has no releases of its own.
Start it from [Nexus Dashboard for PS5](../dash), or with these commands:

| | Linux |
|---|---|
| Open it | `dev/flight/run.sh` |
| Menu entry and Desktop icon | `dev/flight/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

How to use it: [Flight Recorder in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#flight-recorder).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
