<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# The owner's decisions on the text

These hold for every rewrite of the text, on top of [writing.md](writing.md). They were made on 16-11-2026, unless
a line says otherwise.

## Windows

- **The emulator managers** (PCSX2, RPCS3, shadPS4, PPSSPP, Vita3K, Xenia) show no introduction under their pills.
  Only the links stay: the emulator's release notes and the wiki. No info symbol beside them. The wiki chapter says
  what the app does.
- **A dialog** may open with its question. The exception is the question before closing while a job runs. It keeps
  the old order: "A download ... is still running. Close anyway?"
- **Nexus Release Tool's confirmations** end with "Go ahead?".
- **The portal's question before an app that changes the board** keeps "Read the app's manual first and know how to
  undo the change." and "Read their manuals first."
- **RPCS3's message after an install** keeps joining its parts with "; ".
- **Sound Lab's checkbox** is **Keep the audio link awake**. Its tooltip says that it plays a silent loop while the
  window is open.
- **The Upscaler Manager's Help page** is short: what the app does, a link to its chapter in the wiki, and where its
  files are. What only the Help page said goes into the chapter first.
- **A long explanation** goes behind core's `InfoButton`, with a link to the wiki (CLAUDE.md, owner 01-11-2026).

## Words

- An app that changes the board says **board**, never console.
- **No version or build numbers** in new text, except where the text is about that version.
- A label in the wiki is written as the window shows it, for example **Install all apps** with a lowercase "all".

## The wiki and the READMEs

- **An app's README** has a short introduction, then "How to install and use it: [<app name> in the
  wiki](https://robertotorino.github.io/bazzite-console/apps/<key>/).", then its License section. Badges, install
  blocks and license notices stay.
- **The Development index** keeps "`launch_in_terminal()` takes an exit file the caller can watch." and "board-test's
  manual tooltips" as they are.
- **DESIGN.md** describes active red `#8b0000` as a toggle button while its state is on.
- **A fact that was wrong** is corrected and named in the CHANGELOG entry. Nothing else about what an app does
  changes in a rewrite.
