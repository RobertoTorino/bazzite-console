<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Xenia Manager](../assets/xenia/ps5-xenia-manager.webp){ .app-logo }

# Xenia Manager

Plays **XBOX 360 games** on the board with [Xenia](https://xenia.jp), an XBOX 360 emulator, in its
[Xenia Canary](https://github.com/xenia-canary/xenia-canary) builds. The app installs the build pinned for this
version of the app, finds your games and adds them to Steam, so they start from **Game Mode** like any other game.

Xenia is an experimental emulator, and its Linux build more so: not every game starts, and a game that runs on
Windows may not run here. Whether a game runs, and how well, is up to Xenia. Its
[compatibility list](https://github.com/xenia-canary/game-compatibility/issues) says what is known. Compatibility
and performance vary by title and are not guaranteed on PlayStation 5 hardware running Bazzite.

## What you need

- **Your games**, from your own discs and console: disc images (`.iso`), discs unpacked to a folder with a
  `default.xex`, Xenia's `.zar` archives, and Games on Demand and Arcade packages as the console keeps them. The app
  never downloads games. Use game files that you are entitled to use.
- **Steam**, started at least once, for Game Mode.
- **fusermount** (FUSE), which Bazzite has. Xenia comes as an AppImage, which mounts itself with it. Without it, it
  unpacks itself to a temporary folder on every start, which takes longer.
- About 18 MB for Xenia itself. Its settings, saves and installed content go in `~/.local/share/Xenia`.
- No BIOS or firmware: Xenia does not need the console's.

## Install

Install it from the [portal](../portal.md) (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/xenia/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/xenia/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/xenia/install.sh --uninstall             # remove it; --purge removes its settings and log too
```

The launcher is `~/.local/bin/ps5-xenia-manager`; the app runs on the suite's shared Python environment. Installing
needs no root: run it as your own user. Xenia itself is not part of the install: the app downloads it when you press
**Install**.

Removing the app takes out the app and the Xenia it installed; Xenia's own folder (your settings, saves and
installed content) and your games stay. The games in Steam then no longer start: take them out first by unticking
them and pressing **Update Steam**. With `--uninstall --purge` the app's settings, the pictures found on SteamGridDB
and the log go too.

## Use it

The header has four pills: the **Xenia version**, **Xenia Install**, **Xenia Uninstall** and **Refresh**, which reads everything again. Beside the title, next to the app's state, stands the controller's:
**Controller connected**, or **No controller** when none is, looked at again every few seconds. A game started
from Steam reads the controller that is connected when it starts, so switch yours on first. Beside the title stands the app's state: **Not installed**, **No games** or
**Ready**. Under the links to **Xenia's release notes** and to this wiki, a second row of two pills follows, each with what it is for on top and what it does under it: **Games Uninstall** and **Available in Steam** (how many of your games are in Steam). Below the pills are two columns. The first says in two lines where each stands (**Xenia:**, **Game folder:**), short, with more in their tooltips. The second shows the **Installed version:** of Xenia. Then comes a row of six tabs: **Your games**, **Start game**, **Memory cards**, **Settings**, **View logs** and **Clear logs**. Start game and Clear logs are buttons.

- **Xenia**: **Not installed.** or **Installed.**, with the button to use under it. The tooltip says which build
  is installed, or what Install takes, and when a newer build is out. **Install** asks first, then downloads Xenia
  from GitHub (about 18 MB) and checks it against the checksum pinned in this version of the app before installing
  it; a file that differs is not installed. When another build is in use, the tooltip and the log say so, and
  **Install** puts the pinned one back in use. **Uninstall** takes it out again; Xenia's own folder, with its settings,
  saves and installed content, stays.
- **Game folder**: where the app looks for games, `~/Games/XBOX360` and a removable drive's `Games/XBOX360` (see
  [Where your games go](#where-your-games-go)); nothing is chosen or browsed to. The **i** beside them says what
  goes there. A game may sit up to six folders deep.

Press Escape or the controller's B/back button to close the active window or dialog.

### Versions

The version box in the header is a pill. A click opens the list of the Xenia builds installed, with a check mark at
the one in use; pick another to put it in use. The games in Steam start whichever build is in use, and every build
shares Xenia's own folder (settings, saves and installed content). **Manage versions…** under the list opens the
version manager:

- **Installed**: every build in the app's folder, the one in use with a check mark and the one pinned in this version
  of the app marked **Tested**. **Use** puts the chosen build in use, **Delete** removes it (not the one in use), and
  **Add** (**Custom build**) takes an AppImage of your own, which is not checked.
- **Download**: **Refresh** asks GitHub which builds there are (the newest Canary builds). **Download** fetches the
  chosen one, checks it against the SHA-256 GitHub publishes for it and puts it beside the others; **Use** then puts
  it in use.

Only the pinned build, marked **Tested**, was tried on the board. To go back to it, pick it in the version pill's list
or press **Xenia Install**, which puts it back in use without a download when it is still there.

### Where your games go

The app has a folder of its own, which it makes when it opens; you never choose or browse to a folder:
`~/Games/XBOX360`. Put your games there, or in folders in it, and they show in the table. On a USB drive or an SD
card, make a folder `Games/XBOX360` on it, and the app looks there too while the drive is mounted (under
`/run/media` or `/media`, as Bazzite mounts it).

### Your games

The table lists every game found, with its kind (ISO, XEX, ZAR, Games on Demand or Arcade) and its file:

- A **disc image** is a game when it is an XBOX 360 disc (the app looks for the disc's mark where Xenia looks for
  it), listed under its file's name.
- An **unpacked disc** is its `default.xex`, listed under its folder's name; the other `.xex` files in that folder
  are its parts. Any other `.xex` is listed under its own name.
- A **.zar** archive is listed under its file's name; the app does not look into it.
- A **Games on Demand** or **Arcade** package is listed under the name in its header. Keep it in the folders the
  console made (`<title ID>/00007000/` or `<title ID>/000D0000/`). Saves, downloadable content and title updates are
  not games and are left out.

The **Title ID** column shows the game's ID (4D5307E6), from the `.xex` or the package, where the app can read it.

**Games Uninstall**, the pill above, deletes the chosen game from the disk. A window first lists what would go, a row each with its
size: the game's file or folder; for a Games on Demand or Arcade title in the console's layout a row per part of its
title ID folder (the game, its title updates, its add-ons), so the add-ons can stay; and its Steam shortcut when it
is in Steam. Every row is ticked; untick what you want to keep, then **Delete marked**; **Cancel** deletes nothing.
Xenia's content folder, with the saves, stays. A game the app will not delete (one at the top of a drive, or in a
folder that holds another game) is said so under the tabs: delete it by hand.

**Xenia settings** opens Xenia's own window, with its other settings, profiles and installed content. A game runs
from Steam: [**Start game**](#start-game) starts the chosen one there.

#### Steam

Tick the games you want in Steam and press **Update Steam**. The app adds them to Steam as non-Steam games and
takes out the games you unticked and games it no longer finds. Steam keeps these files in memory, so it closes for
the change and starts again in the background. The pictures on the tiles are drawn from the app's icon, with the
game's title, and the icon is the logo on the banner. Xenia has to be installed first: the games in Steam start it. The info symbol under the list
says in short what the boxes and **Start game** do; **Steam** in its text opens Steam's library.

In Steam each game's name starts with its system, for example **[X360] Halo 3**, so it stands apart from the same
title on Steam or on another system in Steam's menus.

The games are in the library under **Non-Steam**, on the desktop, in Big Picture Mode and in Game Mode alike. They
start the game alone in Xenia, full screen. Steam's overlay works over a game started from Steam, in Game Mode and
on the desktop: press **Shift+Tab** or the **Steam button** for the game's page, its controller layout and its
settings, without leaving the game.

Change Steam from Desktop Mode: in Game Mode Steam is the session itself and cannot close for the change. **Update
Steam** is off there, and until Steam has been started once on the board.

##### Covers

With a SteamGridDB API key, the app takes all four pictures from SteamGridDB instead of drawing them: the cover, the
wide picture, the banner and the logo. Press **Steam artwork…** to enter the key; **Update Steam** then looks each
game up on SteamGridDB by its title. A picture SteamGridDB does not have stays drawn. The key is free with a
SteamGridDB account, and it is one key for every app of the suite, kept in
`~/.config/bazzite-console/steamgriddb-key`. Leave the field empty to look nothing up: the pictures already found
stay in use.

**Steam** in the line under the table is a link: it opens Steam's library (Steam starts when it does not run).

#### A game in Steam more than once

The app checks whether a game has more than one shortcut in Steam. When one has, the line under the tabs names
the game and says how often it is there, and the tooltip of its **In Steam** box says the same. **Update Steam** is
on for it: it leaves one shortcut of each game, with the latest play time, and takes the others out. Its question
says how many double shortcuts go.

#### Start game

The tab beside Your games, **Start game**, is a button. Choose a game in the table and click it: the game starts through Steam,
as its shortcut in Steam starts it. When Steam does not run, the app starts Steam first and waits until it is up,
which takes a while, and then starts the game. The line under the tabs says **Starting…** until Xenia runs, and
says so when Steam did not start the game. While Xenia runs already, no second game is started. The tab you were
on stays open. A
game that is not in Steam yet is not started: the line under the tabs says to tick it and press **Update Steam**
first.

### Settings

The tab scrolls when it is higher than the window.

Xenia's settings that matter for playing, each written into Xenia's own settings file (`xenia-canary.config.toml`
in its folder) the moment you change it; Xenia reads it when it starts. A game's own settings file in Xenia comes
before these; everything else is in Xenia's own window (**Xenia settings**, under the games).

- **Picture**: **Graphics** (Vulkan, the Linux build's; Automatic picks it), the **Resolution scale** (a multiple
  of the game's own picture, mostly 1280 × 720; a higher one asks much more of the GPU, and breaks some games),
  **Anti-aliasing** (FXAA smooths jagged edges after the game has drawn), **Scaling and sharpening** (Bilinear,
  Contrast Adaptive Sharpening or FidelityFX Super Resolution), **Keep the picture's shape** (bars where the
  screen's shape differs; off, the picture is stretched) and **VSync**.
- **Speed**: the **Frame limit** (As the game is 60 with VSync on) and **Readback resolve** (for a game that shows
  wrong or missing effects: Fast reads them a frame late, Full exactly and slowly).
- **Sound**: the **Sound output** (SDL, the Linux build's; Automatic picks it) and **Mute**.
- **Console**: the **Arcade license** (for an XBOX Live Arcade game: Full version unlocks the whole game where its
  package has the trial alone licensed; All licenses also its other content), **Achievement messages** and **Guide
  button to the game** (the controller's guide button reaches the game; off, Steam keeps it).

Each setting shows what Xenia's settings file holds, or Xenia's own default while there is no file or line; a value
set in Xenia that the app does not offer is shown as it is. Nothing is written while Xenia runs.

### Memory cards

An XBOX 360 game keeps each saved game as a folder, not on a card file. This tab lists the saved games in Xenia's
content folder (`~/.local/share/Xenia/content/<profile>/<game's code>/00000001`, for every profile): the game, the
save's name, its folder, its size and when it was last written.

- **Export…** writes the selected saved games to one `.zip`, each under its game's code, with what Xenia notes of
  it beside it, to keep or to share.
- **Import…** puts the saved games from such a `.zip` under the first profile. Xenia needs a profile for that: start
  it once with **Xenia settings** and make one. A saved game that is there already is replaced only after the app
  asks.
- **Delete…** deletes the selected saved games after it asks. A deleted one is gone: export it first to keep a copy.

Nothing is imported or deleted while Xenia runs: close it first.

### View logs

Everything the app said and did, with the time: Xenia installed or removed, games deleted, every change to Steam,
and every error. The same lines are in `~/.local/share/ps5-xenia-manager/ps5-xenia-manager.log`, which turns
over at 1 MB (the three older files are kept). **Clear logs**, the tab beside View logs, empties
the file and the View logs tab and removes the three older files. The log holds what the app did, with your home folder written as
`~`, and not your SteamGridDB key. `install.sh --uninstall` keeps it; `--purge` removes it.

## From a terminal

`ps5-xenia-run` starts the installed Xenia with the options you give it. The Steam shortcuts use it, so they keep
working when a newer version of the app brings a newer Xenia. Xenia's options take the form `--name=value`.

```bash
ps5-xenia-run --fullscreen=true "/path/to/game.iso"   # a game full screen (Steam)
ps5-xenia-run "/path/to/game.iso"                     # a game in a window
ps5-xenia-run                                         # Xenia's own window
```

## New Xenia builds

Xenia has no stable releases: Xenia Canary publishes a build for almost every change, named after the change
(`54386cb`). Each version of the app pins one build, the one **Install** puts in. When the window opens, the app asks
GitHub for the newest build; when one was published after the app's, the Xenia line's tooltip and the log say so, with
a link to what changed. The app does not install it by itself, but the [version manager](#versions) can. A newer build
comes with a newer version of the app, from the [portal](../portal.md): after updating the app, the tooltip and the
log say so, and **Install** brings it.

## How it works

The Steam shortcuts start `ps5-xenia-run`, which starts Xenia. Started from outside Steam (**Xenia settings**,
or `ps5-xenia-run` in a terminal), Xenia runs as it is.

The app goes online for three things: the download of Xenia from GitHub when you press **Install**, the question to
GitHub for the newest build when the window opens, and, only with a SteamGridDB key, the pictures from SteamGridDB
on **Update Steam**. [Privacy](../privacy.md#what-goes-over-the-network) has the whole suite's list.

### Controllers

When Steam starts a game, it tells the game's controller library (SDL) to ignore the controllers Steam handles
itself, and gives the game Steam's virtual controller in their place (Steam Input). Xenia then sees only that
virtual controller, and on the desktop it follows the layout Steam has active, which may be Steam's desktop layout
(mouse and keys).

So the run wrapper undoes it: while a real controller is connected, Xenia reads that controller itself and leaves
Steam's virtual one (USB ID `28DE:11FF`) out. Without a real controller, where the only controls are Steam's
virtual controller, the wrapper leaves Steam's choice as it is.

### A game renamed, moved or gone

A game renamed or moved after it was put in Steam keeps its mark: the app knows each game in Steam by its code (or,
without one, its file's size), so on **Refresh** it finds the game again under its new name, ticked, and says so
under the tabs; **Update Steam** then takes the old shortcut out and puts the game in under its new name. A
shortcut to a game that is no longer there (deleted, or on a drive that is not in) does not start Xenia: a
window says which file is missing and what to do, and closes by itself, so Steam sees the game end.

### Steam's overlay on the desktop

Xenia's window goes through X11 (XWayland on the KDE desktop of Bazzite) by itself, so Steam's overlay sees it on
the desktop too, and the run wrapper has nothing to change for it.

## What goes where

| What | Where |
|---|---|
| The app | `~/.local/share/ps5-xenia-manager/app` |
| Xenia | `~/.local/share/ps5-xenia-manager/emulator` |
| Xenia's settings, saves and installed content | `~/.local/share/Xenia` (Xenia's own folder) |
| Your games | `~/Games/XBOX360` (the app's own folder), and `Games/XBOX360` on a removable drive |
| The app's settings | `~/.config/ps5-xenia-manager` |
| The app's log | `~/.local/share/ps5-xenia-manager/ps5-xenia-manager.log` |
| The Steam shortcuts | Steam's `shortcuts.vdf` and `grid` folder, per Steam user |
| The pictures found on SteamGridDB | `~/.local/share/ps5-xenia-manager/covers` |
| The SteamGridDB key, one for the suite | `~/.config/bazzite-console/steamgriddb-key` |
| Launchers | `~/.local/bin/ps5-xenia-manager`, `~/.local/bin/ps5-xenia-run` |

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/xenia/LICENSE).
Xenia (BSD-3-Clause) is a separate program under its own license, downloaded from its own
releases.
