<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 KytyPS5 Manager](../assets/kytyps5/ps5-kytyps5.webp){ .app-logo }

# PS5 KytyPS5 Manager

PS5 KytyPS5 Manager plays **PS5 games** on the board with
[KytyPS5-Native](https://github.com/superkeka/KytyPS5-Native), an open-source PS5 emulator. The app does these
things for you:

- It installs the KytyPS5-Native release it was tried with.
- It checks whether the board has the memory settings the emulator asks for.
- It finds the games in your game folders.
- It adds them to Steam.

A game then starts from Steam like any other. KytyPS5-Native decides whether a game runs, and how well.

KytyPS5-Native is written for the AMD BC-250. Its README says it "will likely run on a PS5 under Linux too".

The app changes nothing on the board by itself. It only reads the memory settings. The emulator's GPU helper is an
option that you install yourself, see [The GPU helper](#the-gpu-helper).

## What you need

- **Your games**, from your own PS5. Each game sits in a folder of its own, with its `eboot.bin` and its `sce_sys`
  folder. The app never downloads games.
- **Steam**, started at least once.
- About 110 MB for KytyPS5-Native itself. The download is about 41 MB.
- **The memory settings the emulator asks for**, see [Board settings](#board-settings).

## Using it

The header has four pills:

- **KytyPS5 version**, the date of the installed release
- **KytyPS5 Install**
- **KytyPS5 Uninstall**
- **Refresh**, which reads everything again

Beside the title is a row of states. Each shows its name and a dot. The dot is green when all is well, and red when
not. Hold the pointer over a state to read it in full.

- **Installed**: the app's own state, such as **Not installed** or **Check the board**
- **Controller**: **Controller connected**, or **No controller** when none is, checked again every few seconds
- **Steam**: green while Steam runs and is signed in, red when it is not

When the window opens without a controller, a desktop notification says so too. It asks you to switch the
controller on or press its PS button.

A game started from Steam reads the controller that is connected when it starts. So switch yours on before you
start a game, or press its PS button to wake it. A game in Steam starts only while Steam is signed in.

Under the header are links to **KytyPS5-Native's release notes** and to this wiki. Below them is a second row of
four pills:

- **Games Uninstall**
- **Available in Steam**, how many of your games are in Steam
- **Board settings**, **Ok** or how many settings differ
- **GPU helper**, **Install** or **Uninstall**

Under the pills, four lines give the state of KytyPS5-Native, the board, the game folders and the GPU helper. The
installed version is beside them.

### Install KytyPS5-Native

Click **KytyPS5 Install**. The app asks first, then downloads the release from GitHub. It checks the file against
the SHA-256 this version of the app was tried with. A file that differs is not installed.

**KytyPS5 Uninstall** removes the installed emulator. Your saves, the emulator's settings and your games stay. The
GPU helper also stays, so uninstall it first with its own pill.

### Board settings

KytyPS5-Native's README asks three things of an AMD BC-250:

| Setting | What it asks |
|---|---|
| VRAM split | 512 MB, for big games |
| GTT limit | 14 GiB (`ttm.pages_limit=3670016`) |
| GPU driver options | `sched_policy=2 vm_update_mode=0 cwsr_enable=0` |

The app reads what the board has and shows **Ok** in green, or **Not as KytyPS5-Native asks** in red. Click the info
symbol beside it for each figure next to what is asked. The app sets none of them.

This suite has no app that sets the VRAM split or the GTT limit. The GPU driver options are kernel arguments on
Bazzite. Set them in a terminal, then restart:

```bash
rpm-ostree kargs --append-if-missing=amdgpu.sched_policy=2 --append-if-missing=amdgpu.vm_update_mode=0 --append-if-missing=amdgpu.cwsr_enable=0
```

These three options change the GPU driver for every program, not only for the emulator. Remove them the same way,
with `--delete-if-present=` in place of `--append-if-missing=`.

### Where your games go

Put your games in `~/Games/PS5`, each in a folder of its own. The app makes that folder when it opens. A USB drive
or an SD card with a `Games/PS5` folder is checked too. The app looks up to five folders deep.

### Your games

The **Your games** tab lists every game found, with its title, ID, version and folder. The title, ID and version
come from the game's own `sce_sys/param.json`. A game without that file is listed under its folder's name.

**Games Uninstall** deletes the chosen game from the disk. A window first lists what would go, with its size. You
choose what to keep. Nothing is deleted before you confirm, and your saves stay.

#### Steam

Check the box before a game and click **Update Steam**. The app adds the game to Steam as a non-Steam game, named
**[PS5]** and its title. Uncheck a game and click **Update Steam** to take it out again. Steam closes for the change
and starts again.

The shortcut starts the game full screen. It gets the game's own pictures as its artwork in Steam.

**Steam artwork…** takes a SteamGridDB API key, one for the whole suite. With a key, **Update Steam** gives each
game its cover from SteamGridDB.

#### Start game

Choose a game under **Your games** and click the **Start game** tab. The game starts through Steam, as its shortcut
there does. The game must be in Steam first.

#### Quit a game

**Exit KytyPS5** ends the emulator at once, with no question. A game that is running ends without saving.

### KytyPS5 settings

**KytyPS5 settings** opens KytyPS5-Native's own window. Set there what the app does not set. That is the
controller, the screen and a game's own settings.

### The GPU helper

The GPU helper is a part of KytyPS5-Native named `kyty-lodhw`. It runs as a system service, from every start of the
board. For a game, it writes PS5 values to the GPU's registers and puts the old ones back afterward. The emulator
runs without it.

The helper is an option. Click **GPU helper Install** to install it. The app asks first and then asks for your
password. It runs the emulator's own `install-helper.sh`. Click **GPU helper Uninstall** to stop and remove the
service again.

Installing the helper changes how the board runs. To check that it is gone, run `systemctl status kyty-lodhw`.

### View logs

The **View logs** tab shows what the app said and did, newest last. A box above it switches to what KytyPS5-Native
printed while a game ran. **Clear logs** empties the log that is shown.

Every line of the emulator log starts with its time and a level: INFO, WARNING or ERROR. A line KytyPS5-Native
prints is an ERROR when it starts with error or tells of a crash. It is a WARNING when it starts with warning or
tells of something that failed.

The emulator log also has lines of its own around each game. Before the game starts it gives:

- the KytyPS5-Native build
- the board by its name, with its BIOS
- the processor, its threads and the kernel
- the game, with its title ID and version
- each controller, or a warning that none is connected
- the session, such as Wayland on KDE
- each connected display with its name and preferred mode
- the desktop's mode, such as 1920x1080 at 120 Hz
- the size the game gets
- the memory and swap left
- whether the GPU helper runs

KytyPS5-Native's own window sets the game's size in its settings. The log then gives `screen_resolution` and
`fullscreen_enabled` from its `Kyty.ini`.

After the game it gives:

- the exit code and the signal that ended it, such as SIGPIPE, as an error for a crash
- how long the game ran
- the memory and swap left
- the system log's out-of-memory kills, GPU hangs, resets and faults, and core dumps while the game ran

A game can be killed together with the wrapper that logs it. The next start then says so first, with what the system
log has from that start on.

## New KytyPS5-Native releases

Each version of the app was tried with one KytyPS5-Native release, the one **Install** puts in. When the window
opens, the app asks GitHub for the newest release. When that one is newer, the KytyPS5-Native line's tooltip and the
log say so, with a link. The app does not install it. A newer release comes with a newer version of the app, from
the [portal](../portal.md).

## How it works

The Steam shortcuts start `ps5-kytyps5-run`, which starts KytyPS5-Native:

```bash
ps5-kytyps5-run --fullscreen --game /path/to/game   # a game, full screen (the Steam shortcuts)
ps5-kytyps5-run --game /path/to/game                # a game, in a window
ps5-kytyps5-run --launcher                          # KytyPS5-Native's own window
```

KytyPS5-Native keeps its saves in the folder it is started from. The run wrapper always starts it from
`~/.local/share/KytyPS5-Native/data`. So your saves never sit in the emulator's own folder, and **Uninstall** never
takes them.

### Controllers

When Steam starts a game, it tells the game's controller library (SDL) to ignore the controllers Steam handles
itself. It gives the game Steam's virtual controller in their place. While a real controller is connected, the run
wrapper undoes that. KytyPS5-Native then reads the real controller and leaves Steam's virtual one (USB ID
`28DE:11FF`) out. Without a real controller, the wrapper leaves Steam's choice as it is.

### A game that is gone

A game may be no longer there, because it was deleted or is on a drive that is not in. Its shortcut then does not
start KytyPS5-Native. A window says which game is missing and what to do.

### Steam's overlay on the desktop

When Steam starts a game on the Wayland desktop, the run wrapper has the emulator open its window through XWayland
(`SDL_VIDEO_DRIVER=x11`). Steam on the desktop only sees windows that go through X11.

## What goes where

| What | Where |
|---|---|
| The app | `~/.local/share/ps5-kytyps5/app` |
| KytyPS5-Native | `~/.local/share/ps5-kytyps5/emulator` |
| Your games | `~/Games/PS5`, and `Games/PS5` on a removable drive |
| KytyPS5-Native's saves | `~/.local/share/KytyPS5-Native/data`, the emulator's own folder |
| KytyPS5-Native's settings | `~/.config/Kyty`, the emulator's own folder |
| The app's log | `~/.local/share/ps5-kytyps5/ps5-kytyps5.log` |
| What KytyPS5-Native printed while a game ran | `~/.local/share/ps5-kytyps5/emulator.log` |
| The app's settings | `~/.config/ps5-kytyps5` |
| The Steam shortcuts | Steam's `shortcuts.vdf` and `grid` folder, per Steam user |
| The covers found on SteamGridDB | `~/.local/share/ps5-kytyps5/covers` |
| Launchers | `~/.local/bin/ps5-kytyps5`, `~/.local/bin/ps5-kytyps5-run` |
| The GPU helper, when you installed it | `/etc/systemd/system/kyty-lodhw.service` and the `kyty-lodhw` program |

## Install and remove

Install the app from the [portal](../portal.md), where it is under Gaming. Removing it takes out the app and the
KytyPS5-Native it installed. The emulator's own folders, with your saves, stay, and so do your games. The games in
Steam then no longer start. So take them out first. Uncheck them and press **Update Steam**.

Removing the app does not remove the GPU helper. Uninstall the helper in the app first.

```bash
./install.sh                         # install or update
./install.sh --no-desktop-shortcut   # app menu entry only, no icon on the Desktop
./install.sh --uninstall             # remove the app and the KytyPS5-Native it installed; keeps its settings and log
./install.sh --uninstall --purge     # also remove its settings, covers and log
```

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/kytyps5/LICENSE).
KytyPS5-Native is a separate program under its own license (GPL-2.0-only), downloaded from its own release.
