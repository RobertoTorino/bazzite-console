<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PPSSPP Manager](../assets/ppsspp/ps5-ppsspp-manager.webp){ .app-logo }

# PPSSPP Manager

Plays **PSP games** on the console with [PPSSPP](https://www.ppsspp.org), an open-source PSP emulator. The app
installs the PPSSPP release pinned for this version of the app, finds your games and adds them to Steam, so they
start from **Game Mode** like any other game. It also sets PPSSPP's common picture, sound, controller and display
settings, and can rename ISO and CSO files after their game metadata.

Whether a game runs, and how well, is up to PPSSPP. Its [compatibility list](https://report.ppsspp.org) shows what
others found. PSP game compatibility and performance vary by title and are not guaranteed on PlayStation 5 hardware
running Bazzite.

## What you need

- **Your games**, dumped from your own discs: ISO, CSO or CHD images, or (for homebrew and games bought digitally)
  a folder with an `EBOOT.PBP`. The app never downloads games. Use game files you are entitled to use.
- **Steam**, started at least once, for Game Mode.
- About 50 MB for PPSSPP itself. Its saves, settings and memory stick games go in `~/.config/ppsspp`, the PSP's
  memory stick.
- **fusermount** (FUSE), which Bazzite has. PPSSPP comes as an AppImage, which mounts itself with it. Without it,
  it unpacks itself to a temporary folder on every start, which takes longer.

No firmware is needed: PPSSPP plays the PSP's system software itself.

## Install

Install it from the [portal](../portal.md) (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/ppsspp/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/ppsspp/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/ppsspp/install.sh --uninstall             # remove it; --purge removes its settings and log too
```

The launcher is `~/.local/bin/ps5-ppsspp-manager`; the app runs on the suite's shared Python environment. Installing
needs no root: run it as your own user. PPSSPP itself is not part of the install: the app downloads it when you
press **Install**.

Removing the app takes out the app and the PPSSPP it installed; PPSSPP's own folder (your saves, settings and memory
stick games) and your games stay. The games in Steam then no longer start: take them out first by unticking them and
pressing **Update Steam**. With `--uninstall --purge` the app's settings, the covers found on SteamGridDB and the
log go too.

## Use it

The header shows the **PPSSPP version**, **Your games** (the games found) and those **Available in Steam**.
**Refresh** reads everything again. Beside the title stands the app's state: **Not installed**, **No games** or
**Ready**. Under the introduction, which links to **PPSSPP's release notes** and to this wiki, a row of three pills
does the setting up, each with what it is for on top and what it does under it: **PPSSPP Install**, **PPSSPP
Uninstall** and **Games Rename**. Two lines below the pills say where each stands, and then come three tabs: **Your
games**, **Settings** and **Log**, and **Start game**, a tab that is a button.

- **PPSSPP**: **Not installed.** or **Installed.**, with the button to use under it. The tooltip says which
  release is installed, or what Install takes, and when a newer PPSSPP is out. **Install** asks first, then
  downloads PPSSPP from its GitHub release (about 48 MB) and checks it against the checksum pinned in this version
  of the app before installing it; a file that differs is not installed. When another release is installed, the
  tooltip and the log say so, and **Install** puts the pinned one in. **Uninstall** takes it out again; PPSSPP's
  own folder, with your saves, settings and memory stick games, stays.
- **Game folder**: where the app looks for games, `~/Games/PSP` and a removable drive's `Games/PSP` (see [Where
  your games go](#where-your-games-go)); nothing is chosen or browsed to. The **i** beside them says what goes
  there, and the tooltip how many games are on PPSSPP's memory stick. A game may sit up to five folders deep.
- **Games Rename** renames the ISO and CSO images after their `PARAM.SFO`: see [Renaming the
  files](#renaming-the-files).

Press Escape or the controller's B/back button to close the active window or dialog.

### Where your games go

The app has a folder of its own, which it makes when it opens; you never choose or browse to a folder:
`~/Games/PSP`. Put your disc images and your `EBOOT.PBP` folders there, or in folders in it, and they show in the
table. On a USB drive or an SD card, make a folder `Games/PSP` on it, and the app looks there too while the drive is
mounted (under `/run/media` or `/media`, as Bazzite mounts it).

### Your games

The table lists every game found: its title and ID (ULUS…, UCES…) from the `PARAM.SFO` inside the image, its kind
and its file. It has two kinds of games:

- **Disc images** in the game folders: ISO and CSO are read for their title, ID and pictures. A **CHD** is listed
  under its file name: the app does not look into that archive format, so Steam gets no pictures from it, but
  PPSSPP plays it the same. An image without a PSP game in it, such as a UMD video, is not listed.
- **Memory stick games**: folders with an `EBOOT.PBP`, in the game folders and on PPSSPP's own memory stick
  (`~/.config/ppsspp/PSP/GAME`), where PPSSPP keeps homebrew and installed games. A game's update there (its
  `PARAM.SFO` says category PG) is not a game to start: PPSSPP lays it over the disc game by itself.

**Remove game…** deletes the chosen game from the disk. A window first lists what would go, a row each with its
size: the disc image, or a memory stick game's own folder, and its Steam shortcut when it is in Steam. Every row is
ticked; untick what you want to keep, then **Delete marked**; **Cancel** deletes nothing. The saves on the memory
stick stay. A game the app will not delete (one at the top of a drive, or in a folder that holds another game) is
said so under the tabs: delete it by hand. Close PPSSPP first: nothing is removed while it runs.

**PPSSPP settings** opens PPSSPP's own window, with its other settings, its controller settings and its game list.
A game runs from Steam: [**Start game**](#start-game) starts the chosen one there.

#### Steam

Tick the games you want in Steam and press **Update Steam**. The app adds them to Steam as non-Steam games, with
the game's own icon and background (from inside the image) as their pictures and its icon (`ICON0.PNG`) as the
logo on the banner, and takes out the games you unticked and games it no longer finds. Steam keeps these files in
memory, so it closes for the change and starts again in the background. PPSSPP has to be installed first: the games
in Steam start it.

In Steam each game's name starts with its system, for example **[PSP] Lumines**, so it stands apart from the same
title on Steam or on another system in Steam's menus. Two games with the same title get their ID after the name.

The games are in the library under **Non-Steam**, on the desktop, in Big Picture Mode and in Game Mode alike. They
start the game full screen in PPSSPP, with an **Exit** entry in PPSSPP's pause menu. Steam's menu and **Exit game**
work as for any game.

Steam's overlay works over a game started from Steam, in Game Mode and on the desktop: press **Shift+Tab** or the
**PS button** for the game's page, its controller layout and its settings, without leaving the game.

A game started from Steam reads your controllers itself. [How it works](#how-it-works) explains both.

Change Steam from Desktop Mode: in Game Mode Steam is the session itself and cannot close for the change. **Update
Steam** is off there, and until Steam has been started once on the console.

##### Covers

A PSP game has no cover in the shape Steam's library uses, so the app draws one: the game's icon with its title on a
dark background. With a SteamGridDB API key, entered under **Steam artwork…**, **Update Steam** looks each game up
on SteamGridDB by its title and takes a cover from there instead; the background and the logo on the game's page
stay the game's own. The key is free with a SteamGridDB account, and it is one key for every app of the suite, kept
in `~/.config/bazzite-console/steamgriddb-key`. Leave the field empty to look nothing up: the covers already found
stay in use.

**Steam** in the line under the table is a link: it opens Steam's library (Steam starts when it does not run).

#### Start game

The last tab, **Start game**, is a button. Choose a game in the table and click it: the game starts through Steam,
as its shortcut in Steam starts it, and Steam starts first when it does not run. The tab you were on stays open. A
game that is not in Steam yet is not started: the line under the tabs says to tick it and press **Update Steam**
first.

### Settings

PPSSPP's settings that matter for playing, each written into PPSSPP's own settings file the moment you change
it. Everything else is in PPSSPP's own window (**PPSSPP settings**, under the games).

- **Picture**: the **Renderer** (Vulkan, PPSSPP's own choice, or OpenGL when a game shows faults), the **Internal
  resolution** (Automatic follows the screen; 3x fills a 1080p screen sharply, 6x a 4K one; a higher one asks more
  of the GPU), **Stretch to the screen**, **Integer scaling**, **Texture filtering** (Nearest keeps pixel art
  sharp), **Anisotropic filtering** and **VSync**.
- **Game**: **Frame skipping** (frames left out to keep a slow game at full speed) and **Cheats** (the cheats in
  PPSSPP's cheats folder).
- **Sound**: the **Volume**.
- **Controller**: the **Stick dead zone** (how far a stick moves before the game sees it, for a stick that drifts)
  and the **Stick sensitivity** (how far the PSP's stick goes for the stick's travel: PPSSPP's 1.10 reaches the
  edge a little sooner).
- **On screen**: **Show FPS** and **Show speed**, in a corner of the picture.

Each setting shows what PPSSPP's settings file holds, or PPSSPP's own default while the file does not name it; a
value set in PPSSPP that the app does not offer is shown as it is. Nothing is written while PPSSPP runs: PPSSPP
writes its settings back when it closes, over any change.

### Log

Everything the app said and did, with the time: PPSSPP installed or removed, what the app set up in PPSSPP, files
renamed, games deleted, every change to Steam, and every error. The same lines are in
`~/.local/share/ps5-ppsspp-manager/ps5-ppsspp-manager.log`, which turns over at 1 MB (the three older files are
kept). The log holds what the app did, with your home folder written as `~`, and not your SteamGridDB key.
`install.sh --uninstall` keeps it; `--purge` removes it.

## Renaming the files

A dumped disc often gets a meaningless file name. **Games Rename** opens the **Rename files** window with the ISO
and CSO images the app found and the name each would get from its own `PARAM.SFO`: pick one of eight naming
templates under **Naming**, and press **Rename all**. The window shows the selected game's pictures (a click cycles
ICON0, PIC0 and PIC1), and for a title in another language you can type a **translation**, used as the title in
that file's new name (**Translate** opens the title in Google Translate, in your browser). A name another file
already has is never taken over; characters that are illegal in file names are removed. The app remembers the
template you chose.

| Naming | Example |
|---|---|
| ID - Title | `ULJM05437 - Ever17.iso` |
| ID Title | `ULJM05437 Ever17.iso` |
| ID - Title - Version | `ULJM05437 - Ever17 - v1.01.iso` |
| Title - ID | `Ever17 - ULJM05437.iso` |
| Title Id | `Ever17 ULJM05437.iso` |
| Title only | `Ever17.iso` |
| Title [ID] | `Ever17 [ULJM05437].iso` |
| Title [ID] [Version] | `Ever17 [ULJM05437] [v1.01].iso` |

A memory stick game is never renamed (its file must stay `EBOOT.PBP`), and a CHD is not read; with no ISO or CSO
image found, **Games Rename** is off. A renamed game that is in Steam needs **Update Steam** afterwards: its
shortcut names the file.

## From a terminal

`ps5-ppsspp-run` starts the installed PPSSPP with the options you give it. The Steam shortcuts use it, so
they keep working when a newer version of the app brings a newer PPSSPP.

```bash
ps5-ppsspp-run --fullscreen --pause-menu-exit "/path/to/game.iso"   # a game full screen (Steam)
ps5-ppsspp-run "/path/to/game.iso"                                  # a game, as PPSSPP is set up
ps5-ppsspp-run                                                      # PPSSPP's own window
```

## New PPSSPP releases

Each version of the app installs one PPSSPP release, the one pinned in it. When the window opens, the app asks
GitHub for PPSSPP's newest release. When that one is newer, the PPSSPP line's tooltip and the log say so, with a
link to what is new; the app does not install it. A newer PPSSPP comes with a newer version of the app, from the
[portal](../portal.md): after updating the app, the tooltip and the log say so, and **Install** brings it.
PPSSPP's own notice of a new release is turned off by the app (see below); on Linux PPSSPP does not update itself.

## How it works

The Steam shortcuts start `ps5-ppsspp-run`, which starts PPSSPP. Two things change when Steam is the one that
starts it. Started from outside Steam (**PPSSPP settings**, or `ps5-ppsspp-run` in a terminal), PPSSPP runs as
it is.

Once PPSSPP is installed, each time the window opens and while PPSSPP does not run, the app turns off PPSSPP's
notice of a newer release in its settings (`PSP/SYSTEM/ppsspp.ini` on its memory stick): a newer PPSSPP comes with
the app. Everything else in the file stays as PPSSPP wrote it, and what changed goes to the log.

The app goes online for three things: the download of PPSSPP from GitHub when you press **Install**, the question
to GitHub for PPSSPP's newest release when the window opens, and, only with a SteamGridDB key, the covers from
SteamGridDB on **Update Steam**. [Privacy](../privacy.md#what-goes-over-the-network) has the whole suite's list.

### Controllers

When Steam starts a game, it tells the game's controller library (SDL) to ignore the controllers Steam handles
itself, and gives the game Steam's virtual controller in their place (Steam Input). PPSSPP then sees only that
virtual controller, and on the desktop it follows the layout Steam has active, which may be Steam's desktop layout
(mouse and keys).

So the run wrapper undoes it: while a real controller is connected, PPSSPP reads that controller itself and leaves
Steam's virtual one (USB ID `28DE:11FF`) out. The PS button stays Steam's. Without a real controller, where the
only controls are Steam's virtual controller, the wrapper leaves Steam's choice as it is. Controls are mapped in
PPSSPP's own window (**PPSSPP settings**, then **Settings > Controls**).

### A game renamed, moved or gone

A game renamed or moved after it was put in Steam keeps its mark: the app knows each game in Steam by its code (or,
without one, its file's size), so on **Refresh** it finds the game again under its new name, ticked, and says so
under the tabs; **Update Steam** then takes the old shortcut out and puts the game in under its new name. A
shortcut to a game that is no longer there (deleted, or on a drive that is not in) does not start PPSSPP: a
window says which file is missing and what to do, and closes by itself, so Steam sees the game end.

### Steam's overlay on the desktop

The KDE desktop of Bazzite is a Wayland session. PPSSPP (an SDL program) may open its window through Wayland, but
Steam on the desktop only sees windows that go through X11 (XWayland, the X11 server within the Wayland session).
A game window Steam cannot see has no overlay: **Shift+Tab** and the **PS button** do nothing.

So when Steam starts a game on the Wayland desktop, the run wrapper has PPSSPP open its window through XWayland
(`SDL_VIDEODRIVER=x11`), and Steam's overlay works as in any other game. Game Mode runs every game through X11
already.

## What goes where

| What | Where |
|---|---|
| The app | `~/.local/share/ps5-ppsspp-manager/app` |
| PPSSPP | `~/.local/share/ps5-ppsspp-manager/emulator` |
| PPSSPP's saves, settings, memory stick games | `~/.config/ppsspp` (the PSP's memory stick) |
| Your games | `~/Games/PSP` (the app's own folder), and `Games/PSP` on a removable drive |
| The app's settings | `~/.config/ps5-ppsspp-manager` |
| The app's log | `~/.local/share/ps5-ppsspp-manager/ps5-ppsspp-manager.log` |
| The Steam shortcuts | Steam's `shortcuts.vdf` and `grid` folder, per Steam user |
| The covers found on SteamGridDB | `~/.local/share/ps5-ppsspp-manager/covers` |
| The SteamGridDB key, one for the suite | `~/.config/bazzite-console/steamgriddb-key` |
| Launchers | `~/.local/bin/ps5-ppsspp-manager`, `~/.local/bin/ps5-ppsspp-run` |

PPSSPP can keep its memory stick elsewhere (its `--root` option and settings); the app reads the standard place.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/ppsspp/LICENSE).
PPSSPP is a separate program under its own license (GPL-2.0-or-later), downloaded from its own
release.
