<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Deps

A window that lists the Python packages and external tools of the suite's apps installed on this machine, which apps
use them, what is missing or must be updated (with the known vulnerabilities from OSV.dev), Bazzite's update
state, and every update of the machine (Bazzite's image, Flatpaks, Homebrew, Rust, the development venv, Prime95's mprime); **Fix**
installs what is missing, outdated or newer, after it shows every command and asks. An hourly notification
says when something needs you. A development app: it runs from the checkout it lives in and has no releases of its own.
Start it from [Nexus Dashboard for PS5](../dash), or:

| | Linux |
|---|---|
| Open it | `dev/deps/run.sh` (`--fix` offers Fix at once, `--remind` is the hourly check) |
| Menu entry, Desktop icon and hourly reminder | `dev/deps/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

Nothing is copied: the entry starts the app of the checkout you installed it from. Its catalog of the suite is
`nexus_deps/catalogs/bazzite-console.toml`.

How to use it: [Deps in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#deps).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
