<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<span class="page-icon">:material-view-grid-outline:</span>

# Apps

**Closing an app.** In every app's window **Escape** closes the window, as its close button does, and so does **B** on a
controller (Circle on a PlayStation controller): first an open menu, then a question or a dialog, then the window
itself. Where Escape already has a meaning in an app (back to the tiles in PS5 DatStation), that comes first. An app
that is busy asks before it closes, as always. The controller's B needs the app to have the focus, and is left out where
the controller belongs to something else: in the two Remote Play apps (a stream's window keeps all its keys too, Escape
among them), in PS5 Controller and in PS5 System Overlay. A controller Steam Input owns sends what its desktop layout
says, by default Escape for B.

**Sustainable**: system and device information, and what keeps the board cool.

| App | What it does |
|---|---|
| ![](../assets/apps/board.webp){ .app-icon } [PS5 Board Test](board.md) | Read-only system details for PlayStation 5 hardware running Bazzite. |
| ![](../assets/apps/fan.webp){ .app-icon } [PS5 Fan Controller](fan.md) | The PS5's temperatures and fan, and a thermal guard that warns, cools and shuts down cleanly at a critical temperature. |
| ![](../assets/apps/compute.webp){ .app-icon } [PS5 CU Tools](compute.md) | Tell bad CUs apart from an unstable CU unlock, and apply a tested unlock. |
| ![](../assets/apps/cores.webp){ .app-icon } [PS5 CPU Tools](cores.md) | Tell bad CPU cores apart from an unstable core unlock, before you persist the 8C/16T unlock. |
| ![](../assets/apps/overlay.webp){ .app-icon } [PS5 System Overlay](overlay.md) | A small always-on-top window with the PS5's live CPU, GPU, memory, fan and temperature values. |

**Graphics**: Graphics features and tools for games.

| App | What it does |
|---|---|
| ![](../assets/apps/upscaler.webp){ .app-icon } [PS5 Upscaler Manager](upscaler.md) | Deploy HelixSR (FSR 3.1 drop-in upscaler with DLSS-style networks) into games. |

**Gaming**: Emulators and console tools for games.

| App | What it does |
|---|---|
| ![](../assets/apps/datstation.webp){ .app-icon } [PS5 DatStation](datstation.md) | Play a PlayStation quiz and explore console history, system versions, region codes, manuals, and news. |
| ![](../assets/apps/pcsx2.webp){ .app-icon } [PCSX2 Manager](pcsx2.md) | Install PCSX2 for PS2 games, manage BIOS and game libraries, and add games to Game Mode. |
| ![](../assets/apps/ppsspp.webp){ .app-icon } [PPSSPP Manager](ppsspp.md) | Install PPSSPP for PSP games, manage game libraries, and add games to Game Mode. |
| ![](../assets/apps/remoteplay.webp){ .app-icon } [Remote Play](remoteplay.md) | Find, wake, and register PS4 and PS5 consoles on the network, and stream Remote Play. |
| ![](../assets/apps/rpcs3.webp){ .app-icon } [RPCS3 Manager](rpcs3.md) | Install RPCS3 for PS3 games, manage game libraries, and add games to Game Mode. |
| ![](../assets/apps/shadps4.webp){ .app-icon } [shadPS4 Manager](shadps4.md) | Install shadPS4 for PS4 games, manage game libraries, and add games to Game Mode. |
| ![](../assets/apps/vita3k.webp){ .app-icon } [Vita3K Manager](vita3k.md) | Install Vita3K for PS Vita games and add installed titles to Game Mode. |
| ![](../assets/apps/clb.webp){ .app-icon } [XBOX Remote Play](clb.md) | Stream XBOX consoles or XBOX Cloud Gaming after signing in with a Microsoft account. |
| ![](../assets/apps/xenia.webp){ .app-icon } [Xenia Manager](xenia.md) | Install Xenia Canary for XBOX 360 games and add games to Game Mode. |

**Utilities**: Tools for files, peripherals, and storage.

| App | What it does |
|---|---|
| ![](../assets/apps/bluetooth.webp){ .app-icon } [PS5 Bluetooth](bluetooth.md) | Pair your Bluetooth keyboard, mouse and controllers at boot, with no USB keyboard or mouse needed. |
| ![](../assets/apps/controller.webp){ .app-icon } [PS5 Controller](controller.md) | Manage DualSense and DualSense Edge controllers. |
| ![](../assets/apps/cec.webp){ .app-icon } [PS5 CEC Manager](cec.md) | Turn the TV on and off with the PS5, switch its input and use its remote, over HDMI-CEC. |
| ![](../assets/apps/sftp.webp){ .app-icon } [PS5 SFTP Tools](sftp.md) | Transfer files over SFTP and manage SSH servers on Bazzite hosts. |
| ![](../assets/apps/ssd.webp){ .app-icon } [PS5 SSD Check](ssd.md) | Inspect storage health and drive information when supported. |
| ![](../assets/apps/webcam.webp){ .app-icon } [PS5 Webcam](webcam.md) | Use a compatible PlayStation camera as a webcam. |
| ![](../assets/apps/quickfix.webp){ .app-icon } [PS5 Quickfix](quickfix.md) | Small quickfixes for one job each: Board Test's optional tools, MangoHud's config, the memory map, the journal and the boot command line. Always installed. |
| ![](../assets/apps/password.webp){ .app-icon } [PS5 Password Generator](password.md) | Makes a random password of 8 or 15 characters with a capital letter, a small letter, a number and a special character, and keeps it nowhere. |

The tools for working on the suite run from a checkout of the repository. They are not in the portal.
[Nexus Dashboard](../development/dashboard.md) opens them all.

- Nexus Release Tool
- Nexus Installer Tests
- Nexus Demo Recorder
- Nexus Sound Lab
- Nexus TTS
- Nexus Remix Studio
- The video tours and the icons

Apps that change the board must explain their changes and ask before applying them.
