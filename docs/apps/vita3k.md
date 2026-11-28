<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 Vita3K Manager](../assets/vita3k/ps5-vita3k-manager.webp){ .app-logo }

# PS5 Vita3K Manager

Plays **PS Vita games** on the board with [Vita3K](https://vita3k.org), an open-source PS Vita emulator. The app
installs the Vita3K build pinned for this version of the app, installs the PS Vita's firmware and your games
through it, and adds the games to Steam, so they start from **Game Mode** like any other game.

Whether a game runs, and how well, is up to Vita3K. Its [compatibility list](https://vita3k.org/compatibility.html)
shows what others found. Vita3K compatibility and performance vary by title and are not guaranteed on PlayStation 5
hardware running Bazzite.

## What you need

- **Your games**, dumped from your own PS Vita: a `.vpk` or `.zip`, a `.pkg` with its zRIF license key, or a dumped
  game folder. The app never downloads games. Supply firmware and game files that you are entitled to use.
- **The PS Vita's firmware**, the PS Vita's system software. Vita3K needs it, and its font package, to start most
  games. The app cannot ship them; each is a file named `PSP2UPDAT.PUP`:
    - the firmware: download it [here](https://www.playstation.com/en-us/support/hardware/psvita/system-software/)
      (official page);
    - the font package: download it
      [here](http://dus01.psp2.update.playstation.net/update/psp2/image/2019_0924/sd_8b5f60b56c3da8365b973dba570c53a5/PSP2UPDAT.PUP?dest=us)
      (Sony's file);
    - optional, the preinstalled apps: download them
      [here](http://dus01.psp2.update.playstation.net/update/psp2/image/2022_0209/pre_efd1ef6c1cc2fe92e72e9e783e421237/PSP2UPDAT.PUP?dest=us)
      (Sony's file).

    Then put the files in `~/Games/Vita/Firmware`: the app gives them to Vita3K by itself (see **Firmware** below).
- **Steam**, started at least once, for Game Mode.
- About 86 MB for Vita3K itself. Its settings go in `~/.config/Vita3K`, the PS Vita's storage (firmware, installed
  games, saves) in `~/.local/share/Vita3K/Vita3K`.
- **fusermount** (FUSE), which Bazzite has. Vita3K comes as an AppImage, which mounts itself with it. Without it, it
  unpacks itself to a temporary folder on every start, which takes longer.

## Install

Install it from the [portal](../portal.md) (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/vita3k/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/vita3k/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/vita3k/install.sh --uninstall             # remove it; --purge removes its settings and log too
```

The launcher is `~/.local/bin/ps5-vita3k-manager`; the app runs on the suite's shared Python environment. Installing
needs no root: run it as your own user. Vita3K itself is not part of the install: the app downloads it when you
press **Install**.

Removing the app takes out the app and the Vita3K it installed; Vita3K's own folders (the firmware, your games, your
saves and settings) stay. The games in Steam then no longer start: take them out first by unticking them and
pressing **Update Steam**. With `--uninstall --purge` the app's settings, the covers found on SteamGridDB and the
log go too.

## Use it

The header has four pills: the **Vita3K version**, **Vita3K Install**, **Vita3K Uninstall** and **Refresh**, which reads everything again.

Beside the title is a row of states. Each shows its name and a dot. The dot is green when all is well,
and red when not. Hold the pointer over a state to read it in full.

- **Installed**: the app's own state, one of **Not installed**, **No firmware**, **No games** or **Ready**
- **Controller**: **Controller connected**, or **No controller** when none is, checked again every few seconds
- **Steam**: green while Steam runs and is signed in, red when it is not

A game started from Steam reads the controller that is connected when it starts, so switch yours on first. A game
in Steam starts only while Steam is signed in. So start Steam and sign in before you start a game.

Under the links to **Vita3K's release notes** and to this wiki, a second row of four pills follows, each with what it is for on top and what it does under it: **Games Install** and **Games Uninstall**, **Available in Steam** (how many of your games are in Steam) and **Play time**: the time spent in all your games together, as Vita3K counts it, with each game's time in the tooltip. Below the pills are two columns. The first says in three lines where each stands (**Vita3K:**, **Firmware:**, **Game folder:**), short, with more in their tooltips. The second shows the **Installed version:** of Vita3K. Then comes a row of six tabs: **Your games**, **Start game**, **Memory cards**, **Settings**, **View logs** and **Clear logs**. Start game and Clear logs are buttons.

- **Vita3K**: **Not installed.** or **Installed.**, with the button to use under it. The tooltip says which build is
  installed, or what Install takes, and when a newer build is out. **Install** asks first, then downloads Vita3K from
  GitHub (about 86 MB) and checks it against the checksum pinned in this version of the app before installing it; a
  file that differs is not installed. When another build is in use, the tooltip and the log say so, and **Install**
  puts the pinned one back in use. **Uninstall** takes it out again; Vita3K's own folders, with the firmware, your
  games, saves and settings, stay.
- **Firmware**: **Installed.** once Vita3K has the system software and the font package, **Partly installed.** with
  one of the two, **Not installed.** with neither. The tooltip names each part: the system software, the font package
  and the preinstalled apps (optional).
  The **i** beside them says where the files go and links to where each is downloaded. Put the `PSP2UPDAT.PUP`
  files you downloaded in `~/Games/Vita/Firmware` (each in a folder of its own there if you like, since Sony names
  all three the same): once Vita3K is installed, the app gives them to Vita3K by itself, the largest first, one
  after the other, when the window opens and on **Refresh**; the line under the tabs then says which part each was.
  A file is given once as it is, also one Vita3K could not use; a file you replace is given again. The files stay
  in the folder.
- **Game folder**: the app's own folder, `~/Games/Vita`, and a removable drive's `Games/Vita`; the **i** beside
  them says what goes there, and the tooltip how many games Vita3K has installed. **Games Install** installs one
  of yours, once Vita3K is installed; its window opens in that folder:
    - **From a file**: a `.vpk` or `.zip` is handed to Vita3K, which installs it and then starts it in its own
      window; a `.pkg` asks for the game's zRIF license key, and Vita3K installs it without a window.
    - **From a dumped folder**: Vita3K installs the folder's game and starts it in its own window.

    The list shows the game once it is installed.

Press Escape or the controller's B/back button to close the active window or dialog.

### Versions

The version box in the header is a pill. A click opens the list of the Vita3K builds installed, with a check mark at
the one in use; pick another to put it in use. The games in Steam start whichever build is in use, and every build
shares Vita3K's own folder (firmware, games, saves and settings). **Manage versions…** under the list opens the
version manager:

- **Installed**: every build in the app's folder, the one in use with a check mark and the one pinned in this version
  of the app marked **Tested**. **Use** puts the chosen build in use, **Delete** removes it (not the one in use), and
  **Add** (**Custom build**) takes an AppImage of your own, which is not checked.
- **Download**: **Refresh** asks GitHub which builds there are (the newest builds). **Download** fetches the chosen
  one, checks it against the SHA-256 GitHub publishes for it and puts it beside the others; **Use** then puts it in
  use.

Only the pinned build, marked **Tested**, was tried on the board. To go back to it, pick it in the version pill's list
or press **Vita3K Install**, which puts it back in use without a download when it is still there.

### Your games

The table lists every game Vita3K has installed: its title and ID (PCSB…, PCSE…) from the game's own files, its
version and its folder in Vita3K's storage (`ux0/app`).

**Games Uninstall**, the pill above, deletes the chosen game from the disk. A window first lists what would go, a row each with its
size: the game in Vita3K's storage, its update and extra content when they are there, and its Steam shortcut when
it is in Steam. Every row is ticked; untick what you want to keep, then **Delete marked**; **Cancel** deletes
nothing. The saves stay. Close Vita3K first: nothing is removed while it runs.

**Vita3K settings** opens Vita3K's own window, with its other settings, its controls and its game list. A game runs
from Steam: [**Start game**](#start-game) starts the chosen one there.

#### Game updates and extra content

Install an update or extra content (DLC) as a game: **Games Install** with its `.pkg` and zRIF key. Vita3K puts an
update in `ux0/patch` and extra content in `ux0/addcont`, and uses them when it starts the game. The table lists the
game once.

#### Steam

Tick the games you want in Steam and press **Update Steam**. The app adds them to Steam as non-Steam games, with
the game's own icon and LiveArea picture as their pictures and its icon (`icon0.png`) as the logo on the banner,
and takes out the games you unticked and games no longer installed. Steam keeps these files in memory, so it closes
for the change and starts again in the background. Vita3K has to be installed first: the games in Steam start it. The info symbol under the list
says in short what the boxes and **Start game** do; **Steam** in its text opens Steam's library.

In Steam each game's name starts with its system, for example **[PS Vita] Gravity Rush**, so it stands apart from the
same title on Steam or on another system in Steam's menus. Two games with the same title get their ID after the name.

The games are in the library under **Non-Steam**, on the desktop, in Big Picture Mode and in Game Mode alike. They
start the game alone in Vita3K, full screen, and Vita3K quits when the game ends. Steam's menu and **Exit game** work
as for any game.

Steam's overlay works over a game started from Steam, in Game Mode and on the desktop: press **Shift+Tab** or the
**PS button** for the game's page, its controller layout and its settings, without leaving the game.

A game started from Steam reads your controllers itself. [How it works](#how-it-works) explains both.

Change Steam from Desktop Mode: in Game Mode Steam is the session itself and cannot close for the change. **Update
Steam** is off there, and until Steam has been started once on the board.

##### Covers

A PS Vita game has no cover in the shape Steam's library uses, so the app draws one: the game's icon with its title on
a dark background. With a SteamGridDB API key, entered under **Steam artwork…**, **Update Steam** looks each game up
on SteamGridDB by its title and takes a cover from there instead; the background and the logo on the game's page
stay the game's own. The key is free with a SteamGridDB account, and it is one key for every app of the suite, kept
in `~/.config/bazzite-console/steamgriddb-key`. Leave the field empty to look nothing up: the covers already found
stay in use.

**Steam** in the info symbol's text under the table is a link: it opens Steam's library (Steam starts when it does
not run).

#### A game in Steam more than once

The app checks whether a game has more than one shortcut in Steam. When one has, the line under the tabs names
the game and says how often it is there, and the tooltip of its **In Steam** box says the same. **Update Steam** is
on for it: it leaves one shortcut of each game, with the latest play time, and takes the others out. Its question
says how many double shortcuts go.

#### Start game

The tab beside Your games, **Start game**, is a button. Choose a game in the table and click it: the game starts through Steam,
as its shortcut in Steam starts it. When Steam does not run, the app starts Steam first and waits until it is up,
which takes a while, and then starts the game. The line under the tabs says **Starting…** until Vita3K runs, and
says so when Steam did not start the game. While Vita3K runs already, no second game is started. The tab you were
on stays open. A
game that is not in Steam yet is not started: the line under the tabs says to tick it and press **Update Steam**
first.

#### Exit Vita3K

**Exit Vita3K** ends Vita3K at once, with everything it started. Use it when Vita3K is stuck, or when you can't
reach its own window. It is the first button under the table. It turns on only while Vita3K runs.

The app asks nothing first. A game that runs ends without saving, so save in the game before you click it. The line
under the tabs then says **Vita3K was ended.**

### Settings

The tab scrolls when it is higher than the window.

Vita3K's settings that matter for playing, each written into Vita3K's own settings file (`config.yml`) the moment
you change it. A game's own settings in Vita3K come before these; everything else is in Vita3K's own window
(**Vita3K settings**, under the games).

- **Picture**: the **Renderer** (Vulkan; OpenGL helps only a game that fails with Vulkan), the **Resolution** (a
  multiple of the PS Vita's 960 × 544: 2x fills a 1080p screen sharply; a higher one asks more of the GPU), the
  **Screen filter** (Bilinear smooth, Nearest sharp pixels, Bicubic sharper, FXAA smooths edges, FidelityFX Super
  Resolution with Vulkan only), **Anisotropic filtering**, **Fill the screen** (the picture stretched to the whole
  screen; off, the PS Vita's shape with borders) and **VSync**.
- **Speed**: **High accuracy** (draws more exactly, for a game that shows errors; slower), **Compile shaders in
  the background** (the game goes on while Vita3K compiles, with a stutter less), the **FPS hack** (may double a
  30 FPS game to 60, but makes some run twice as fast), the **Performance overlay** (the frames per second over the
  game) and the **Shader compilation message**.
- **Sound**: the **Volume**, the **Sound output** (SDL, Vita3K's own choice, or Cubeb when the sound crackles) and
  **NGS sound** (the PS Vita's sound engine; off, many games are silent, for one that hangs on it).
- **System**: the **Confirm button** (Cross as on a PS Vita sold outside Japan, Circle as in Japan) and the
  **Language** of the PS Vita, which a game with that language shows.

Each setting shows what Vita3K's settings file holds, or Vita3K's own default while the file does not name it; a
value set in Vita3K that the app does not offer is shown as it is. Nothing is written while Vita3K runs: Vita3K
writes its settings back when it closes, over any change.

### Memory cards

A PS Vita game keeps its save as a folder, not on a card file. This tab lists the saves on Vita3K's storage
(`ux0/user/00/savedata`, and every other user's): the game, its folder (named after the game's code), its size and
when it was last written.

- **Export…** writes the selected saves to one `.zip`, each as its folder, to keep or to share.
- **Import…** puts the saves from such a `.zip` in the first user's save folder. A save that is there already is
  replaced only after the app asks.
- **Delete…** deletes the selected saves after it asks. A deleted save is gone: export it first to keep a copy.

Nothing is imported or deleted while Vita3K runs: close it first. The encrypted saves of a real PS Vita are taken in
and written by Vita3K's own window (**Vita3K settings**), not here.

### View logs

Everything the app said and did, with the time: Vita3K installed or removed, what the app set up in Vita3K, the
firmware files given to Vita3K, the games installed or deleted, every change to Steam, and every error. The same
lines are in `~/.local/share/ps5-vita3k-manager/ps5-vita3k-manager.log`, which turns over at 1 MB (the three
older files are kept). **Clear logs**, the tab beside View logs, empties
the file and the View logs tab and removes the three older files. The log holds what the app did, with your home folder written as `~`, and not your
SteamGridDB key. `install.sh --uninstall` keeps it; `--purge` removes it.

Two buttons sit above the log. **PS5 Vita3K Manager** shows the app's own log. **Vita3K** shows what Vita3K
printed while the last games ran. The run wrapper writes it to `~/.local/share/ps5-vita3k-manager/emulator.log`. Each
game's part opens with a line that says how the wrapper started Vita3K. It ends with a line that gives Vita3K's exit
code. Every line shows your home folder as `~`. This file also turns over at 1 MB, and the app keeps
the three older files. With **Vita3K** chosen, **Clear logs** empties that log and removes its three older files.

## From a terminal

`ps5-vita3k-run` starts the installed Vita3K with the options you give it. The Steam shortcuts use it, so they keep
working when a newer version of the app brings a newer Vita3K.

```bash
ps5-vita3k-run --frontend sdl -r PCSB00245                   # a game alone, by its ID; Vita3K quits with it
ps5-vita3k-run --firmware "/path/to/PSP2UPDAT.PUP"           # install a part of the firmware
ps5-vita3k-run --pkg "/path/to/game.pkg" --zrif KO5i...      # install a game from its package and license
ps5-vita3k-run "/path/to/game.vpk"                           # install a game and start it
ps5-vita3k-run                                               # Vita3K's own window
```

The run wrapper stays while Vita3K runs. It passes a stop from Steam on to Vita3K, and ends with Vita3K's exit
code. What Vita3K prints goes to `~/.local/share/ps5-vita3k-manager/emulator.log`, not to the terminal. The
View logs tab shows it.

## New Vita3K builds

Vita3K has no stable releases: it publishes a new build for almost every change, numbered over its whole history
(4377). Each version of the app pins one build, the one **Install** puts in. When the window opens, the app asks
GitHub for Vita3K's newest build. When that one is newer, the Vita3K line's tooltip and the log say so, with a link to
what is new; the app does not install it by itself, but the [version manager](#versions) can. A newer Vita3K comes
with a newer version of the app, from the [portal](../portal.md): after updating the app, the tooltip and the log say
so, and **Install** brings it.

Vita3K's own window (**Vita3K settings**) would look for a newer build when it opens; the app turns that check off
in Vita3K's settings, with Vita3K's welcome window (see below). The AppImage Vita3K comes in can update itself, but
the app starts Vita3K with that turned off. Should Vita3K have been updated all the same, the Vita3K line's tooltip
says so, and **Install** puts the pinned build back.

## How it works

The Steam shortcuts start `ps5-vita3k-run`, which starts Vita3K with its plain game window: the game alone, and
Vita3K quits with it, so Steam sees the game end. Two things change when Steam is the one that starts it. Started
from outside Steam (**Vita3K settings**, or `ps5-vita3k-run` in a terminal), Vita3K runs as it is.

Once Vita3K is installed, each time the window opens and while Vita3K does not run, the app sets two lines of
Vita3K's settings (`config.yml` in its settings folder): its welcome window off, which would wait for a click
before a game, and its own update check off, which could replace the pinned build. Everything else in the file
stays as Vita3K wrote it, and what changed goes to the log.

The app goes online for three things: the download of Vita3K from GitHub when you press **Install**, the question
to GitHub for Vita3K's newest build when the window opens, and, only with a SteamGridDB key, the covers from
SteamGridDB on **Update Steam**. The firmware links open in your browser.
[Privacy](../privacy.md#what-goes-over-the-network) has the whole suite's list.

### Controllers

When Steam starts a game, it tells the game's controller library (SDL) to ignore the controllers Steam handles
itself, and gives the game Steam's virtual controller in their place (Steam Input). Vita3K then sees only that
virtual controller: it has no motion sensors or touchpad, and on the desktop it follows the layout Steam has active,
which may be Steam's desktop layout (mouse and keys).

So the run wrapper undoes it: while a real controller is connected, Vita3K reads that controller itself and leaves
Steam's virtual one (USB ID `28DE:11FF`) out. The PS button stays Steam's. Without a real controller, where the only
controls are Steam's virtual controller, the wrapper leaves Steam's choice as it is. The buttons are set in Vita3K's
own window (**Vita3K settings**, then **Controls**).

### Steam's overlay on the desktop

The KDE desktop of Bazzite is a Wayland session. Vita3K opens its windows through Wayland when it can, but Steam on
the desktop only sees windows that go through X11 (XWayland, the X11 server within the Wayland session). A game
window Steam cannot see has no overlay: **Shift+Tab** and the **PS button** do nothing.

So when Steam starts a game on the Wayland desktop, the run wrapper has Vita3K open its windows through XWayland
(`SDL_VIDEO_DRIVER=x11`, and `QT_QPA_PLATFORM=xcb` for its own window), and Steam's overlay works as in any other
game. Game Mode runs every game through X11 already.

## What goes where

| What | Where |
|---|---|
| The app | `~/.local/share/ps5-vita3k-manager/app` |
| Vita3K | `~/.local/share/ps5-vita3k-manager/emulator` |
| The firmware files you put there, and your games to install | `~/Games/Vita/Firmware` and `~/Games/Vita` (the app's own folder) |
| Vita3K's settings | `~/.config/Vita3K` (Vita3K's own folder) |
| The PS Vita's storage: firmware, installed games, saves | `~/.local/share/Vita3K/Vita3K` (Vita3K's own folder) |
| The app's settings | `~/.config/ps5-vita3k-manager` |
| The app's log | `~/.local/share/ps5-vita3k-manager/ps5-vita3k-manager.log` |
| What Vita3K printed while a game ran | `~/.local/share/ps5-vita3k-manager/emulator.log` |
| The Steam shortcuts | Steam's `shortcuts.vdf` and `grid` folder, per Steam user |
| The covers found on SteamGridDB | `~/.local/share/ps5-vita3k-manager/covers` |
| The SteamGridDB key, one for the suite | `~/.config/bazzite-console/steamgriddb-key` |
| Launchers | `~/.local/bin/ps5-vita3k-manager`, `~/.local/bin/ps5-vita3k-run` |

Vita3K can keep its storage elsewhere (its **Settings**, the storage folder); the app reads where it is.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/vita3k/LICENSE).
Vita3K is a separate program under its own license (GPL-2.0), downloaded from its own release.
