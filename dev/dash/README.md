<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Dashboard for PS5

One door to the tools for working on the suite. Its tiles start the development apps of the checkout, each in a window
of its own ([Nexus Release Tool](../nrt), [Nexus Installer Tests](../itests), [Nexus Marketing for PS5](../marketing),
[Nexus Demo Recorder](../demo),
[Nexus Sound Lab](../sounds), [Nexus Deps](../deps), [Nexus TTS](../text), [Nexus Remix Studio](../studio)), and
open the suite's tools: the portal's and the apps' video tours, and the category icons. A development app: it runs from the checkout it lives in and has no releases of its own.

## Start it

From the repository's root, with the checkout's venv ([Set up and test](https://robertotorino.github.io/bazzite-console/development/#set-up-and-test)):

| | Linux |
|---|---|
| Open it | `dev/dash/run.sh` |
| Menu entry and Desktop icon | `dev/dash/install.sh` |

The installer takes `--no-desktop-shortcut`, `--uninstall` and `--uninstall --purge` (the settings too). Nothing is
copied: the entry starts the app of the checkout you installed it from.

How to use it: [Dashboard in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
