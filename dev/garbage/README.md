<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Garbage Remover

A window that shows the garbage on this machine and deletes what you check. It lists crash dumps, Steam's crash
reports, the Trash and caches that fill up, each with its size and the command that empties it. An hourly
notification says when there is 1 GB or more. A development app: it runs from the checkout it lives in and has no
releases of its own. Start it from [Nexus Dashboard](../dash), or:

| | Linux |
|---|---|
| Open it | `dev/garbage/run.sh`, or `dev/garbage/run.sh --remind` for the hourly check |
| Menu entry, Desktop icon and hourly reminder | `dev/garbage/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

How to use it: [Garbage Remover in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#garbage-remover).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
