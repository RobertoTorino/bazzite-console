<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![RPCS3 Manager](../assets/rpcs3/ps5-rpcs3-manager.webp){ .app-logo }

# RPCS3 Manager

Plays **PS3 games** on the console with [RPCS3](https://rpcs3.net), an open-source PS3 emulator. The app installs
the RPCS3 build pinned for this version of the app, takes the PS3's firmware, finds your games and adds them to
Steam, so a game starts straight away, on the desktop, from Steam's **Big Picture Mode** or in Game Mode. A game
runs from Steam: [**Start game**](#start-game) starts the chosen one there. The app sets RPCS3 up for that: its
welcome dialog and its own update check off, player 1 on your controller, each game's screen. RPCS3 installs the
firmware and the packages itself, without opening its window; its own window opens only for
[RPCS3's settings](#rpcs3s-settings). Use firmware and game files that you are entitled to use.

Whether a game runs, and how well, is up to RPCS3. Its [compatibility list](https://rpcs3.net/compatibility) shows
what others found. Game compatibility and performance vary by title and are not guaranteed on PlayStation 5
hardware running Bazzite.

## Install

Install it from the [portal](../portal.md) (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/rpcs3/install.sh                         # the app, its launchers, a menu entry and a Desktop icon
apps/rpcs3/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/rpcs3/install.sh --uninstall             # remove the app and its RPCS3; keeps its settings and log
apps/rpcs3/install.sh --uninstall --purge     # also remove its settings, covers and log
```

The launcher is `~/.local/bin/ps5-rpcs3-manager`; the app runs on the suite's shared Python environment.

Removing the app takes out the app and the RPCS3 it installed; RPCS3's own folder (the firmware, your saves) and
your games stay. The games in Steam then no longer start: take them out first by unticking them and pressing
**Update Steam**.

## What you need

- **Your games**, from your own discs or installed from your own packages. The app never downloads games.
- **The PS3's firmware** (`PS3UPDAT.PUP`), the PS3's system software. RPCS3 needs it to start any game.
  The app cannot ship it: download the firmware from
  [PlayStation's firmware page](https://www.playstation.com/en-us/support/hardware/ps3/system-software/), then
  put it in `~/Games/PS3/Firmware`: the app gives it to RPCS3.
- **Steam**, started at least once: a game is started from Steam.
- About 80 MB for RPCS3 itself. Its firmware, saves, settings and installed games go in `~/.config/rpcs3`, its
  shader cache in `~/.cache/rpcs3`.
- **fusermount** (FUSE), which Bazzite has. RPCS3 comes as an AppImage, which mounts itself with it. Without it, it
  unpacks itself to a temporary folder on every start, which takes longer.

## Use it

The header shows the **RPCS3 version**, **Your games** (the games found), those **Available in Steam** and the
**Play time**: the time spent in all your games together, as RPCS3 counts it, with each game's time in the
tooltip. **Refresh** reads everything again. Beside the title, next to the app's state, stands the controller's:
**Controller connected**, or **No controller** when none is, looked at again every few seconds. A game started
from Steam reads the controller that is connected when it starts, so switch yours on, or press its PS button to
wake it, before starting a game. When Steam starts a game without one, the app also says so in a desktop
notification. Under
the introduction, which links to **RPCS3's release notes** and to this wiki, a row of three pills does the setting
up, each with what it is for on top and what it does under it: **RPCS3 Install**, **RPCS3 Uninstall** and **Games
Install**. Your disc games and the firmware go into the app's own folder (see [Where your games
go](#where-your-games-go)); nothing is chosen or browsed to for them. Four lines below the pills say where each
stands, short, with more in their tooltips, and then come three tabs: **Your games**, **Settings** and **Log**, and
**Start game**, a tab that is a button.

- **RPCS3**: **Not installed.** or **Installed.**, with the button to use under it; the version box in the header
  shows the version installed. The tooltip says which build is installed, or what Install takes, and when a newer
  RPCS3 is out. When another build than the one pinned for this version of the app is installed, or RPCS3 updated
  itself in its own window, the tooltip says so, and **Install** puts the pinned build back. Another build and a
  newer RPCS3 also go to the log, once. **Install** downloads RPCS3 from GitHub (about 80 MB): the pinned build,
  checked against its checksum before it is installed. **Uninstall** takes it out again; RPCS3's own folder, with
  the firmware, your saves, settings and installed games, stays.
- **Firmware**: *No firmware detected*, or *Firmware 4.93 is installed.* with the version RPCS3 has (the folder's
  path is in the tooltip; the **i** beside it says where the firmware comes from). Put the `PS3UPDAT.PUP` you
  downloaded in `~/Games/PS3/Firmware`: once RPCS3 is installed, the app gives it to RPCS3 by itself, when the
  window opens and on **Refresh**, and RPCS3 installs it without opening its window. The line under the tabs says
  when it is done, and the Firmware line shows the new version. A file whose version RPCS3 has already is left
  alone, and so is a file RPCS3 refused, until it changes. An older firmware than the one installed is not given
  to RPCS3. The file stays in the folder.
- **Disc games**: where the app looks for disc games, `~/Games/PS3` and a removable drive's `Games/PS3` (the count
  is in the tooltip; the **i** beside it says what goes there), each game in a folder of its own. Games in
  subfolders are found too, up to five folders deep.
- **PKG games**: RPCS3's games folder, `dev_hdd0/game/` within RPCS3's own folder, while a game is installed in
  it, or **—** while none is (the whole path and the count are in the tooltip). **Install** asks for the folder
  with your `.pkg` files and has RPCS3 install them without opening its window: the `.rap` (or `.edat`) license of
  a PSN game that is beside them first, copied into RPCS3's own folder, then each package, a game's update last
  (an update needs its game installed first). RPCS3 is started once per file, and a large package takes minutes;
  the line under the tabs says what came, and the line and the table follow. The files in the folder itself are
  taken, not those in its subfolders. A game's update is a package too: RPCS3 uses it when it starts the game,
  and the table lists the game once.

Press Escape or the controller's B/back button to close the active window or dialog.

### Where your games go

The app has folders of its own, which it makes when it opens; you never choose or browse to a folder for them:

- `~/Games/PS3`: put your disc games there, each in a folder of its own, and they show on **Your games**. On a
  USB drive or an SD card, make a folder `Games/PS3` on it, and the app looks there too while the drive is
  mounted (under `/run/media` or `/media`, as Bazzite mounts it).
- `~/Games/PS3/Firmware`: put `PS3UPDAT.PUP` there, and the app gives it to RPCS3.

Packages (`.pkg`, with their `.rap` or `.edat` licenses) are installed from a folder you choose with **Games
Install**; its window opens in `~/Games/PS3`.

### Your games

The table lists every game found: its title and **Id** (BLUS…, NPUB…) from the game's own files, its version and
its **Folder** (the folder's name; the path is in the tooltip), and its **Screen setting**. It has three kinds of
games:

- **Disc games** in the game folders, each in a folder of its own, as copied from the disc: `PS3_DISC.SFB` and the
  `PS3_GAME` folder. RPCS3 does not start a disc game without its `PS3_DISC.SFB`; the table shows its folder in red.
- **Disc games RPCS3 knows**: those it started before, wherever they are.
- **Installed games**: games installed from a package, in RPCS3's `dev_hdd0/game`.

```
~/Games/PS3/
└── Demon's Souls/
    ├── PS3_DISC.SFB
    └── PS3_GAME/          PARAM.SFO, ICON0.PNG, USRDIR/EBOOT.BIN, ...
```

**Remove game…** deletes the chosen game from the disk. A window first lists what would go, a row each with its
size: a disc game's folder and its update in RPCS3's games folder, or a package game's folder there, and its Steam
shortcut when it is in Steam. Every row is ticked; untick what you want to keep, then **Delete marked**; **Cancel**
deletes nothing. The saves and the licenses stay. A game the app will not delete (one at the top of a drive, or in a
folder that holds another game) is said so under the tabs: delete it by hand.

#### Screen setting

How the game fills the screen, chosen per game and kept in the game's own settings in RPCS3 (the file RPCS3's own
window writes for a game's custom configuration; the app changes its two lines and leaves the rest):

- **16:9**: the PS3's picture for a wide screen, as RPCS3 draws it by default.
- **4:3**: the picture for a 4:3 screen, with borders on a wide one; for a game made for it.
- **Fill screen**: the picture stretched to fill the window, whatever its shape.

The choice is written the moment you change it, while RPCS3 does not run (RPCS3 writes its own settings when it
closes, over any change made meanwhile). A game is started full screen from Steam; `ps5-rpcs3-run` without
`--fullscreen` starts it in a window (see [From a terminal](#from-a-terminal)).

#### Steam

Tick the games you want in Steam and press **Update Steam**. The app adds them to Steam as non-Steam games, with
the game's own icon and background as their pictures and its icon (`ICON0.PNG`) as the logo on the banner, and
takes out the games you unticked and games it no longer finds. Steam keeps these files in memory, so it closes for
the change and starts again in the background.

In Steam each game's name starts with its system, for example **[PS3] Lumines**, so it stands apart from the same
title on Steam or on another system in Steam's menus. A game whose name in Steam differs from its title in the app
is renamed the next time you press **Update Steam**, which is on for it until then. Steam sees the renamed game as
a new one: its play time stays, but a controller layout or collection you set for it in Steam has to be set again.

The games are in the library under **Non-Steam**, on the desktop, in Big Picture Mode and in Game Mode alike. They
start the game alone in RPCS3, full screen. Steam's menu and **Exit game** work as for any game; on the controller,
**Share + Options** together open RPCS3's own menu with **Exit Game** (see [Controllers](#controllers)).

Steam's overlay works over a game started from Steam, in Big Picture Mode and on the desktop: press **Shift+Tab**
or the **PS button** for the game's page, its controller layout and its settings, without leaving the game. In
Big Picture Mode the PS button opens Steam's menu over the game; pressed again there, it opens the power menu,
with **Exit game** and the way out of Big Picture Mode.

A game started from Steam reads your controllers itself. [How it works](#how-it-works) explains both.

Change Steam from Desktop Mode: in Game Mode Steam is the session itself and cannot close for the change.

##### Covers

A PS3 game has no cover in the shape Steam's library uses, so the app draws one: the game's icon with its title on
a dark background. **Steam artwork…** takes a SteamGridDB API key, one for the whole suite. With it, **Update
Steam** takes a cover from SteamGridDB for each game instead; the wide picture, the banner and the logo stay the
game's own.

**Steam** in the line under the table is a link: it opens Steam's library (Steam starts when it does not run).

#### Start game

The last tab, **Start game**, is a button. Choose a game in the table and click it: the game starts through Steam,
as its shortcut in Steam starts it, and Steam starts first when it does not run. The tab you were on stays open. A
game that is not in Steam yet is not started: the line under the tabs says to tick it and press **Update Steam**
first.

### Settings

RPCS3's settings that matter for playing, each written into RPCS3's own settings file (`config.yml`) the moment
you change it, while RPCS3 does not run; RPCS3 reads them when a game starts, and a game's own settings in RPCS3
(the Screen setting, or settings made for the game in RPCS3's window) come before them. The tooltips say what
each does.

- **Picture**: the renderer (Vulkan; OpenGL is slower and helps only when Vulkan fails), the resolution scale in
  percent of the PS3's 1280 × 720 (150 % fills a 1080p screen, 300 % a 4K one; a higher one asks more of the GPU
  and breaks some games), anisotropic filtering, anti-aliasing, VSync, the frame limit, output scaling (bilinear,
  nearest or AMD's FidelityFX Super Resolution) and **Fill the screen**, the stretch for every game without a
  Screen setting of its own.
- **Emulation**: the PPU and SPU decoders (the recompilers are the fast ones, the interpreters exact and slow).
- **Sound**: the sound output library, the volume (up to 200 %) and buffering. Beside the volume stands **Bazzite's
  volume for RPCS3**, which is not RPCS3's: Bazzite's sound settings remember a volume and a mute per application,
  also once it is closed, so a game plays without a sound while RPCS3 is muted there. The app says so, in red, when
  RPCS3 is muted or turned down to nothing. **Unmute** beside it turns a muted RPCS3 on again, and Bazzite keeps it
  on from then on; a volume turned down is changed in the sound applet (the speaker in the panel, under
  Applications) while a game plays.
- **Messages in a game**: the trophy message and the shader compilation message.

A value RPCS3 knows and the app does not is shown as it is. Everything else RPCS3 can set stays in RPCS3's own
window (**RPCS3 settings**).

#### RPCS3's settings

**RPCS3 settings** opens RPCS3's own window for what the app does not set: its other settings, its controllers
beyond player 1 and 2 (**Pads**) and its online service (RPCN). What the app sets by itself, before RPCS3's
window first opens: RPCS3's welcome dialog off (it would wait for a tick in "I have read the Quickstart guide"
first), RPCS3's question before a game's window closes off ("Exit Game?": a game closed from Steam would stop at
it), RPCS3's own update check off (see [New RPCS3 builds](#new-rpcs3-builds)), RPCS3's dark style when the
suite's theme is dark (the welcome dialog would have offered it) and player 1 on your controller (see
[Controllers](#controllers)). What the app set up goes to the log.

When RPCS3's Settings open with a `config.yml` another build of RPCS3 wrote, RPCS3 asks **Remove obsolete
settings?**: the two builds know different settings. That happens after RPCS3 updated itself in its own window;
with its update check off it does not. Answer **Yes** to let RPCS3 tidy its file for the build that runs; the app's
settings are not in it.

### Log

Everything the app said and did, with the time: RPCS3 installed or removed, what the app set up in RPCS3, the
firmware, the packages (what RPCS3's own log, `~/.cache/rpcs3/RPCS3.log`, says each package came to) and the
folders chosen, every change to Steam, and every error. Each game started from Steam is logged by its folder's name
when it starts, with whether a controller was connected. The same lines are in
`~/.local/share/ps5-rpcs3-manager/ps5-rpcs3-manager.log`, which turns over at 1 MB (the three older files are
kept). The log holds what the app did, not your SteamGridDB key or anything personal. `install.sh --uninstall`
keeps it; `--purge` removes it.

## From a terminal

`ps5-rpcs3-run` starts the installed RPCS3 with the options you give it. The Steam shortcuts use it, so they
keep working when a newer version of the app brings a newer RPCS3.

```bash
ps5-rpcs3-run --no-gui --fullscreen "/path/to/PS3_GAME/USRDIR/EBOOT.BIN"   # a game alone, full screen
ps5-rpcs3-run --no-gui "/path/to/PS3_GAME/USRDIR/EBOOT.BIN"                # a game alone, in a window
ps5-rpcs3-run --installfw "/path/to/PS3UPDAT.PUP"                          # install the firmware
ps5-rpcs3-run --headless --installfw "/path/to/PS3UPDAT.PUP"               # the same, without RPCS3's window
ps5-rpcs3-run --installpkg "/path/to/folder"                               # the .pkg (and .rap) files in a folder
ps5-rpcs3-run --headless --installpkg "/path/to/file.pkg"                  # the same, without RPCS3's window
ps5-rpcs3-run                                                              # RPCS3's own window
```

## New RPCS3 builds

RPCS3 has no stable releases: it publishes a new build for almost every change, and now and then marks one with a
version number (0.0.43). Each version of the app installs one build, the one pinned for it. When the window opens,
the app asks GitHub for RPCS3's newest version number. When that one is newer, the RPCS3 line's tooltip and the log
say so, with a link to what is new; the app does not install it. A newer RPCS3 comes with a newer version of the
app, from the [portal](../portal.md): after updating the app, the RPCS3 line's tooltip says so, and **Install**
brings it.

RPCS3's own window looks for a newer build when it opens and offers to update itself; the app turns that check
off, so the build stays the pinned one (RPCS3's **Help** menu can still update it by hand). If you update it there,
the RPCS3 line's tooltip says that RPCS3 updated itself, and **Install** puts the pinned build back; RPCS3's
Settings then ask once to remove the settings the other build left (see [RPCS3's settings](#rpcs3s-settings)). A
game started from Steam never asks.

## How it works

The Steam shortcuts start `ps5-rpcs3-run`, which starts RPCS3. Two things change because Steam is the one that
starts it.

### Controllers

When Steam starts a game, it tells the game's controller library (SDL) to ignore the controllers Steam handles
itself, and gives the game Steam's virtual controller in their place (Steam Input). With RPCS3's SDL controller
setting, RPCS3 then sees only that virtual controller: it has no motion sensors, and on the desktop it follows the
layout Steam has active, which may be Steam's desktop layout (mouse and keys).

So the run wrapper undoes it: while a real controller is connected, RPCS3 reads that controller itself and leaves
Steam's virtual one (USB ID `28DE:11FF`) out. The PS button stays Steam's. Without a real controller, the wrapper
leaves Steam's choice as it is.

RPCS3 only reads a controller that its pad settings name; until they name one, it plays with the keyboard. So the
app writes them: player 1 on the controller connected (a second one is player 2), through RPCS3's SDL controller
setting with RPCS3's own button layout for it, so Cross is the bottom face button and **Share + Options**
together (or the Guide button) open RPCS3's own menu in the game, with **Exit Game** in it: RPCS3 has no button
chord that quits a game outright, that menu is its way out on the controller, beside Steam's. RPCS3 knows a
controller by the name SDL gives it, which is not the kernel's: the app asks SDL (Bazzite's SDL3 library, the same
RPCS3 uses) for the names whenever the controllers connected change, and the log says which player went on which
name. Once you save RPCS3's own **Pads** settings in its window, that file is RPCS3's and the app leaves it alone.
On a system without SDL3 the app writes the kernel's name, which RPCS3 may not match; the log says so.

### A game renamed, moved or gone

A game renamed or moved after it was put in Steam keeps its mark: the app knows each game in Steam by its code (or,
without one, its file's size), so on **Refresh** it finds the game again under its new name, ticked, and says so
under the tabs; **Update Steam** then takes the old shortcut out and puts the game in under its new name. A
shortcut to a game that is no longer there (deleted, or on a drive that is not in) does not start RPCS3: a
window says which file is missing and what to do, and closes by itself, so Steam sees the game end.

### Steam's overlay on the desktop

The KDE desktop of Bazzite is a Wayland session. RPCS3 opens its windows through Wayland when it can, but Steam on
the desktop only sees windows that go through X11 (XWayland, the X11 server within the Wayland session). A game
window Steam cannot see has no overlay: **Shift+Tab** and the **PS button** do nothing.

So when Steam starts a game on the Wayland desktop, the run wrapper has RPCS3 open its windows through XWayland
(`QT_QPA_PLATFORM=xcb`), and Steam's overlay works as in any other game. Game Mode runs every game through X11
already.

## What goes where

| What | Where |
|---|---|
| The app | `~/.local/share/ps5-rpcs3-manager/app` |
| RPCS3 | `~/.local/share/ps5-rpcs3-manager/emulator` |
| RPCS3's firmware, saves, settings, installed games | `~/.config/rpcs3` (RPCS3's own folder) |
| RPCS3's play time per game | `~/.config/rpcs3/GuiConfigs/persistent_settings.dat`, RPCS3's own |
| RPCS3's settings (the Settings tab) | `~/.config/rpcs3/config.yml`, RPCS3's own |
| RPCS3's GUI settings (the welcome dialog, the exit question, the update check, the style) | `~/.config/rpcs3/GuiConfigs/CurrentSettings.ini`, RPCS3's own |
| Player 1 and 2 on your controllers | `~/.config/rpcs3/input_configs/global/Default.yml`, RPCS3's own |
| Each game's screen setting | `~/.config/rpcs3/custom_configs/config_<Id>.yml`, RPCS3's own |
| RPCS3's shader cache and its own log (`RPCS3.log`, read for what an install did) | `~/.cache/rpcs3` |
| The volume Bazzite remembers for RPCS3 (read only) | `~/.local/state/wireplumber/stream-properties`, WirePlumber's |
| Your disc games and the firmware file | `~/Games/PS3` and `~/Games/PS3/Firmware` (the app's own folder), and `Games/PS3` on a removable drive |
| The app's settings | `~/.config/ps5-rpcs3-manager` |
| The app's log | `~/.local/share/ps5-rpcs3-manager/ps5-rpcs3-manager.log` |
| The Steam shortcuts | Steam's `shortcuts.vdf` and `grid` folder, per Steam user |
| The covers found on SteamGridDB | `~/.local/share/ps5-rpcs3-manager/covers` |
| Launchers | `~/.local/bin/ps5-rpcs3-manager`, `~/.local/bin/ps5-rpcs3-run` |

RPCS3 can keep its drives elsewhere (its **Configuration > Virtual File System**); the app reads where they are.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/rpcs3/LICENSE).
RPCS3 is a separate program under its own license (GPL-2.0), downloaded from its own release.
