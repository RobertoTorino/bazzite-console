<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Marketing for PS5

Nexus Marketing for PS5 writes an article that presents the portal and every app in it. The article is a web page
to share. It takes the apps from the portal's `apps.toml` and the words from `nexus_marketing/copy.md`, so it keeps
up with the suite. It shows stills of the portal and links to the latest release, the wiki, the Portal Tour and
GitHub. Nexus Marketing is a development app. It runs from the checkout it lives in and has no releases of its own. Start it from
[Nexus Dashboard for PS5](../dash), or with these commands:

| | Linux |
|---|---|
| Open it | `dev/marketing/run.sh` |
| Menu entry and Desktop icon | `dev/marketing/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

The installer copies nothing. The entry starts the app of the checkout you installed it from.

How to use it: [Marketing in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#marketing).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
