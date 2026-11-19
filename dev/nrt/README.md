<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Release Tool

The suite's release front end: it writes the versions, CHANGELOG entries, pins and portal bump of a release, and
runs the board checks of a portal release. It commits, pushes, tags and starts the release workflow only when you
press its buttons. It edits the checkout it lives in, so it is not part of a portal's releases and has none of its
own.

## Start it

From the repository's root, with the checkout's venv ([Set up and test](https://robertotorino.github.io/bazzite-console/development/#set-up-and-test)):

| | Command |
|---|---|
| Open it | `tools/nrt.sh` |
| The overview in the terminal | `tools/nrt.sh --list` |
| Menu entry and Desktop icon | `dev/nrt/install.sh` |

The installer takes `--no-desktop-shortcut`, `--uninstall` and `--uninstall --purge` (the settings too). Nothing is
copied: the entry starts the app of the checkout you installed it from. The window's header names the checkout's
last commit and its time: the tool is never released and has no version.

How to use it: [Releases in the wiki](https://robertotorino.github.io/bazzite-console/development/releases/).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
