<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-8b4fd8)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# PCSX2 Manager

PCSX2 Manager installs and configures [PCSX2](https://pcsx2.net) on **Bazzite** running on PlayStation 5 hardware.
It manages PS2 BIOS files, game folders, Steam entries, emulator settings, per-game display options, and memory
cards. Game compatibility and performance vary by title and are not guaranteed on this hardware.

How to install and use it: [PCSX2 Manager in the manual](https://robertotorino.github.io/bazzite-console/apps/pcsx2/).

Select a game in **Your games** and use **Start game** to launch its existing Steam shortcut. Press Escape or the controller’s B/back button to close the active window or dialog.

## Disclaimer

Bazzite Console is an independent community project, not affiliated with or endorsed by AMD, ASRock, the Bazzite /
Universal Blue project, Sony, Microsoft, Valve, or the makers of the emulators and the other programs the apps work
with. Bazzite is developed by the Universal Blue project. PlayStation, PS4, PS5, PS3, PS2, PSP, PS
Vita, PSN, DualSense and Remote Play are Sony's; XBOX, XBOX 360, XBOX Cloud Gaming, Game Pass and Windows are
Microsoft's; Steam, Steam Deck and Big Picture are Valve's; the names of the emulators (shadPS4, RPCS3, PPSSPP, PCSX2,
Vita3K, Xenia) and the names of HelixSR and DirectMesh belong to their owners. The project uses them only to say what
its apps work with.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE). PCSX2 is a separate program (GPL-3.0), downloaded from its own release.
The memory card code in `pcsx2_manager/mymc` is from [mymc++](https://github.com/Adubbz/mymcplusplus)
(GPL-3.0-or-later) by Adubbz, based on mymc+ by Florian Märkl and mymc by Ross Ridge.
