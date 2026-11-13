<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Bazzite Console Developer Dashboard

One place for Bazzite Console development workflows: release planning, dependency checks, installer tests, OBS demo
recording, sound design, and the suite's video-tour tools. The dashboard and its tools run from this checkout.

## Start it

From the repository's root, with the checkout's venv for the system (see the root CLAUDE.md):

| | Linux | Windows (PowerShell) |
|---|---|---|
| Open it | `dev/dash/run.sh` | `dev\dash\run.ps1` |
| Menu entry and Desktop icon | `dev/dash/install.sh` | `powershell -ExecutionPolicy Bypass -File dev\dash\install.ps1` |

Both installers take `--no-desktop-shortcut`, `--uninstall` and `--uninstall --purge` (the settings too). Nothing is
copied: the entry starts the app of the checkout you installed it from.

Documentation: [Bazzite Console](https://robertotorino.github.io/nexus-console/).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
