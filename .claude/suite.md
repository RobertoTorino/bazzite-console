<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# This suite (Bazzite Console Suite)

What only this suite has. The rules every suite shares are in [CLAUDE.md](../CLAUDE.md), which reads this file.

## What it is

- **Name:** the **Bazzite Console Suite**: control your PlayStation 5 running Bazzite.
- **Repository:** `github.com/RobertoTorino/bazzite-console`, branch `main`.
- **Wiki:** robertotorino.github.io/bazzite-console/
- **System:** `bazzite` (`SYSTEM`). **Tags:** `ps5-<app>-v<x.y.z>` and `ps5-portal-v<x.y.z>` (`TAG_PREFIX`).
- **Twin:** the BC250 Bazzite Suite (`github.com/RobertoTorino/bc250-bazzite`), for the AMD BC-250 board, checked
  out beside this one.
- **Design:** the Bazzite design, purple, for the wiki and the shared Bazzite app theme. The portal, the wiki and
  the category icons use artwork made for this suite.

## Names

- **Portal package:** `bazzite_console_portal`. **Core package:** `core/bazzite_console_core/`.
- **On the board:** the program in `~/.local/share/bazzite-console-suite/` (`portal`, `state`), the settings in
  `~/.config/bazzite-console/`.
- **Nexus Deps' catalog:** `dev/deps/nexus_deps/catalogs/bazzite-console.toml`.
- **A new app's name** starts with "PS5".
- **Board Test:** its Python package is `board_test`; its app folder and manifest key are `board`.

## The apps

**Board Test** (`apps/board/`) is the first tile, always installed and the only required app.

`apps/<name>/`: board, overlay, fan, compute, cores, upscaler, rpcs3, remoteplay, clb, shadps4, datstation, ppsspp, pcsx2, vita3k,
xenia, sftp, webcam, controller, ssd, cec, bluetooth, quickfix, password.

**Licenses:** remoteplay is AGPL-3.0, its protocol code from chiaki-ng. The rest is GPL-3.0-or-later.

**Apps that change the board:** Fan Controller's thermal guard, Webcam's camera rule, the SSH server of SFTP
Tools, and the CU and core unlocks of CU Tools and CPU Tools. In `portal/apps.toml`: fan, webcam, sftp, compute,
cores. CU Tools and CPU Tools came from the twin as they are there (owner, 20-11-2026): their scripts still hold the
twin's hardware until the owner adapts them on the PS5.

The portal and its apps are for PlayStation 5 hardware running Bazzite. They read system and device information.

## Rules for this suite alone

- **The twin is not named in this repository** (owner, 15-11-2026): no bc250, bc-250, BC250 or BC-250 anywhere
  (code, comments, tests, the wiki, READMEs, CHANGELOGs), in any case. Write "its twin" where a CHANGELOG entry
  needs it. Three exceptions, which stay: this file, `CROSS-REFERENCE.md` (the table for porting apps) and the
  stream chapter's line "Test results are from a BC250 board." (`docs/development/remoteplay-stream.md`).
- **"Board", never "console"** (owner, 19-11-2026: "board everywhere"): the PS5 that runs Bazzite and the suite is
  **the board** in every text: code, comments, tests, the wiki, READMEs and the apps' windows, as in "changes the
  board" (owner, 18-11-2026). "Console" stays only where it means something else: a PS5 or other console the text
  is about as a product or as another machine ("I just bought a new PS5 console", Remote Play's and XBOX Remote
  Play's consoles, the emulated systems, PlayStation history), the kernel's `console=` and `/dev/console`, and the
  names Bazzite Console Suite, `bazzite-console`, `bazzite_console` and Console Link. DatStation's texts are left
  as they are. CHANGELOG entries are history and keep their words.
