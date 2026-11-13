<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-8b4fd8)
[![CI](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/nexus-console/actions/workflows/ci.yml)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue)](LICENSE)

# Remote Play

Remote Play is a Linux Remote Play client for PlayStation 5 hardware running **Bazzite**. It finds PS4 and PS5
consoles on your network, can wake them from rest mode, registers the client, and starts a session and stream.
Console, firmware, and network compatibility vary.

How to install and use it: [Remote Play in the manual](https://robertotorino.github.io/nexus-console/apps/remoteplay/).

Escape closes the main window when it is not otherwise handled; dialogs keep their normal Escape behavior. In a
stream, Escape only leaves full screen and never ends the session. Controller buttons remain available to the game.

## Disclaimer

Bazzite Console is an independent community project, not affiliated with or endorsed by AMD, ASRock, the Bazzite /
Universal Blue project, Sony, Microsoft, Valve, or the makers of the emulators and the other programs the apps work
with. Bazzite is developed by the Universal Blue project. PlayStation, PS4, PS5, PS3, PS2, PSP, PS
Vita, PSN, DualSense and Remote Play are Sony's; XBOX, XBOX 360, XBOX Cloud Gaming, Game Pass and Windows are
Microsoft's; Steam, Steam Deck and Big Picture are Valve's; the names of the emulators (shadPS4, RPCS3, PPSSPP, PCSX2,
Vita3K, Xenia) and the names of HelixSR and DirectMesh belong to their owners. The project uses them only to say what
its apps work with.

## License

AGPL-3.0, see [LICENSE](LICENSE). The protocol code is ported from [chiaki-ng](https://github.com/streetpea/chiaki-ng)
(AGPL-3.0-only with an OpenSSL exception); those files keep that license. They are the files marked
`SPDX-License-Identifier: AGPL-3.0-only`, modified from chiaki-ng's code (ported to Python and Rust, from
12-10-2026 on); the code and tests call chiaki-ng "the reference". The app's own files are AGPL-3.0-or-later. The native core links [FFmpeg](https://ffmpeg.org), LGPL-2.1-or-later (see
[native/ffmpeg/COPYING.LGPLv2.1](native/ffmpeg/COPYING.LGPLv2.1)), built from its own sources by
`native/ffmpeg/build.sh`.
