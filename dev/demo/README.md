<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Demo Recorder

Records a Bazzite Console portal installation with OBS: a portal release extracted in Downloads, or this checkout,
installed in a terminal while OBS records the screen, then the portal opened and an optional app installed and shown.
Start it from [the developer dashboard](../dash), or:

| | Linux | Windows |
|---|---|---|
| Open it | `dev/demo/run.sh` | `dev\demo\run.ps1` (PowerShell), or `dev/demo/run.sh` (Git Bash) |
| Menu entry and Desktop icon | `dev/demo/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) | |

Nothing is copied: the entry starts the app of the checkout you installed it from.

Documentation: [Bazzite Console](https://robertotorino.github.io/nexus-console/).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
