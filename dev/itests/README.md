<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Installer Tests

A window that runs the suite's installer tests, `tools/installer-tests/*.sh`, one at a time, with their live
output and each one's result. A development app: it runs from the checkout it lives in and has no releases of its own. Start it
from [Nexus Dashboard](../dash), or:

| | Linux |
|---|---|
| Open it | `dev/itests/run.sh` |
| Menu entry and Desktop icon | `dev/itests/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

Nothing is copied: the entry starts the app of the checkout you installed it from.

How to use it: [Installer tests in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#installer-tests).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
