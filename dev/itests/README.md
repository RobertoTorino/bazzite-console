<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Installer Tests

A window that runs this suite's installer tests one at a time, with live output and each test's result. Start it
from [the developer dashboard](../dash), or:

| | Linux | Windows (Git Bash) |
|---|---|---|
| Open it | `dev/itests/run.sh` | `dev/itests/run.sh` (PowerShell: `dev\itests\run.ps1`) |
| Menu entry and Desktop icon | `dev/itests/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) | |

Nothing is copied: the entry starts the app of the checkout you installed it from.

Documentation: [Bazzite Console](https://robertotorino.github.io/nexus-console/).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
