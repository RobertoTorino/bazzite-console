<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Text Check for PS5

Nexus Text Check for PS5 shows what the suite's text check finds. It runs `tools/text_check.py` on the whole suite
or on a file or folder you choose. It lists the files worst first, with their problems per check. Select a file to
see each problem with its line and a suggestion. Nexus Text Check is a development app. It runs from the checkout it
lives in and has no releases of its own. Start it from [Nexus Dashboard for PS5](../dash), or with these commands:

| | Linux |
|---|---|
| Open it | `dev/textcheck/run.sh` |
| Menu entry and Desktop icon | `dev/textcheck/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

The installer copies nothing. The entry starts the app of the checkout you installed it from.

How to use it: [Text Check in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#text-check).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
