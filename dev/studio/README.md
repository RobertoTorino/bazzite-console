<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus Remix Studio

A window that mixes a voice with a synthesized background and saves the result as a sound file. The voice is a sound
file, or a text spoken by [Nexus TTS](../text). The background is a sustained sound, a pad or a drone, made in
the app from a preset, a chord and three sliders. The mix sets how loud each track is and how the background leads
in, trails and fades.

A development app: it runs from the checkout it lives in and has no releases of its own. Start it from
[Nexus Dashboard](../dash), or:

| | Linux |
|---|---|
| Open it | `dev/studio/run.sh` |
| Menu entry and Desktop icon | `dev/studio/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

Nothing is copied: the entry starts the app of the checkout you installed it from.

How to use it: [Remix Studio in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#remix-studio).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
