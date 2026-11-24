<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Sound Lab

A window that makes and tries short sound effects for the suite's windows, such as the tick a menu makes when the
controller moves the focus: a preset and a waveform to start from, a slider for each number of the sound, the
sound drawn beside them and played at every change, a row of buttons to try it while moving between them, and
Save as WAV for the portal's sounds folder. A development app: it runs from the checkout it lives in and has no releases of
its own. Start it from [Nexus Dashboard for PS5](../dash), or:

| | Linux |
|---|---|
| Open it | `dev/sounds/run.sh` |
| Menu entry and Desktop icon | `dev/sounds/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

Nothing is copied: the entry starts the app of the checkout you installed it from.

How to use it: [Sound Lab in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#sound-lab).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
