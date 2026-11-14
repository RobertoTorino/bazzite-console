<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Release Tool

The release front end for Bazzite Console: it plans app and portal releases, updates versions and CHANGELOG entries,
pins app checksums, and runs the suite's board checks. It only edits this checkout. Review its generated commands
before choosing to commit, tag, or push.

Publishing is manual: after the release commit is pushed, `tools/tag-release.sh ps5-<app>-v<x.y.z>` builds the
release asset and publishes it with `gh`. The script does not commit or push source.
`tools/installer-tests/release.sh local` tests a local portal build in an isolated temporary home.
`tools/check-release.sh release ps5-portal-v<x.y.z>` verifies and installs a published portal release on the board
(its draft while it is not published). On a machine without the suite, the test removes what it installed when the
portal closes; a machine that had the suite keeps it. `tools/check-release.sh status` says what is installed and
whether a test put it there, `tools/check-release.sh remove` removes the suite: the **Remove suite** button.

Publishing Remote Play also builds its native decoder wheel. That path needs `maturin` and a C toolchain; FFmpeg is
built into the user cache when it is not already available.

## Start it

From this suite's root, with its development venv:

| | |
|---|---|
| Open it | `dev/nrt/run.sh` |
| The overview in the terminal | `dev/nrt/run.sh --list` |
| Menu entry and Desktop icon | `dev/nrt/install.sh` |

The installer takes `--no-desktop-shortcut`, `--uninstall` and `--uninstall --purge` (the settings too). Nothing is
copied: the entry starts the app of the checkout you installed it from.

Releases: [GitHub Releases](https://github.com/RobertoTorino/bazzite-console/releases).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
