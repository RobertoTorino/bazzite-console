<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 Quickfix](../assets/quickfix/ps5-quickfix.webp){ .app-logo }

# PS5 Quickfix

Small windows for one job each, which come with the suite: the portal installs them with itself, with Board Test,
and keeps them. In the portal's **Utilities** tab each quickfix is a tile of its own; the app's menu entry,
**PS5 Quickfix**, lists them all in one window.

Every quickfix's window has the suite's header: the quickfix's name with the version, its state, and **Refresh**. The
small round **i** beside the state says what the quickfix contains and does. The quickfixes that change the board say so
on their tile; the portal asks before it opens one. Each of those asks for your password (pkexec) for every change,
turns on only what is off, and turns off only what it turned on itself.

| Quickfix | What it does | Changes the board |
|--------|--------------|-------------------|
| [Quickfix](#quickfix) | The optional tools Board Test's tests use: which are there, and their installer. | No |
| [MangoHud Config](#mangohud-config) | Open or create MangoHud's config, edit and save it; turn on the FPS log Board Test reads. | No |
| [Game Memory Map](#game-memory-map) | Raise vm.max_map_count, the number of memory areas a game may map. | Yes |
| [Persistent Journal](#persistent-journal) | Keep the system journal on the disk, so the logs of a boot that crashed can be read after it. | Yes |
| [Boot Command Line](#boot-command-line) | Edit cmdline.txt, the kernel command line the PS5 loader starts Linux with. | Yes |

## Quickfix

Board Test runs without extra tools: a test whose tool is missing says so. **Quickfix** lists the tools the tests
use when they are there, with a dot for each one that is found and the tests that use it, and the **Tools found**
box counts them. It looks where the tests look: on `PATH`, in `~/.local/bin` and in Homebrew.

Each group's heading is a pill: a click on it (**Install**) runs Board Test's own installer for that group in a
terminal, `/opt/ps5-board-test/development/tools/install-requirements.sh` with the group's option; it reads
**Installed** and is off when everything in the group is there. **Install all** installs every group but
the development extras (`--all`), and **Refresh** beside it reads the tools again. The groups and their tools are
listed in [PS5 Board Test](board.md#requirements). The RPM packages are installed with `dnf` on a flattened image
(one that does not boot from ostree, such as a PS5 image) and are there at once. On an Atomic image they are
layered with `rpm-ostree` and are active after a reboot (`systemctl reboot`); until then the tools of that group
still show as missing. The tooltip of a group's pill says which one this console uses.

A tool you put in `~/.local/bin` yourself counts when the file has the tool's own name and may be run. Ookla's
download is a `.tgz` archive: unpack `speedtest` from it and make it executable, then press **Refresh**:

```bash
cd ~/.local/bin && tar -xzf ookla-speedtest-*.tgz speedtest && chmod +x speedtest
```

## MangoHud Config

Opens MangoHud's own settings file, `~/.config/MangoHud/MangoHud.conf`, in an editor; a file that is not there yet
is made by **Save**. **Revert** reads the file again. The boxes show whether the file is there, whether MangoHud's
log is on, and how many log files there are.

Board Test shows a game's FPS from MangoHud's log, which MangoHud writes while the game runs. **FPS log** sets the
three lines it needs:

```ini
output_folder=/home/<you>/mangohud-logs
autostart_log=1
log_interval=500
```

A line that sets one of them already is changed where it is; the others are added at the end. **Save** writes the
file and makes the log folder. MangoHud must be active for the game, for example with the Steam launch option
`mangohud %command%`. A log file is written per game session: **Delete old logs** removes the ones older than 30
days, and **Log folder** opens the folder. Without the log, Board Test still shows the game's name and its CPU and
GPU share.

## Game Memory Map

!!! warning "Changes the board"
    Turn on writes vm.max_map_count = 2147483642 to /etc/sysctl.d/90-ps5-quickfix-max-map-count.conf and sets it now: the
    number of memory areas one program may map. The file stays across reboots and power offs. Nothing is written to the
    console's firmware or the kernel's arguments. Turn off removes the file and reads the system's settings again, so
    the value the other settings files give, else the kernel's own, is back.

`vm.max_map_count` is the number of memory areas one program may map. Some games, and Proton, need far more than
the kernel's default and crash without them; SteamOS and Bazzite set 2147483642. The boxes show the value now and
what set it: the quickfix, or the system (another file in `/etc/sysctl.d` or the image's own). **Turn on** is offered
only when the value is lower. Board Test's test 37 reports it.

## Persistent Journal

!!! warning "Changes the board"
    Turn on makes the folder /var/log/journal, with systemd-tmpfiles, and moves the journal there: journald then keeps
    the system's logs on the disk, within its own size limits, instead of in memory only. The folder stays across
    reboots and power offs. Nothing is written to the console's firmware. Turn off works only on a folder this quickfix
    made: it moves the journal back to memory and removes the folder, with the logs in it.

Without `/var/log/journal`, journald keeps the system journal in memory only, and the logs of a boot that crashed or
froze are gone after it: Board Test's test 34 cannot read the previous boot's logs. The boxes show where the journal
is kept and who made the folder. **Turn on** is offered only when the folder is not there; **Turn off** asks first,
as it removes the logs of every earlier boot.

## Boot Command Line

!!! warning "Changes the board"
    Save changes writes the edited line to /boot/efi/cmdline.txt, the kernel command line the PS5 loader starts Linux
    with, or to the fallback line it opened beside it (cmdline.txt.m2 or cmdline.txt.usb), after it asks and after your
    password, and keeps the file it replaces as a dated backup beside it (for example cmdline.txt.bak-YYYYMMDD-HHMMSS).
    A change to cmdline.txt changes the boot settings of PS5 Linux from the next boot: a wrong argument can keep Linux
    from starting. The file stays across reboots and power offs. A line without root=, or of more than one line, is not
    saved. Nothing is written to the console's firmware. To undo it, edit the line back, or copy a backup over the file.

The PS5 loader starts Linux from the FAT partition of a USB drive or SSD, mounted at `/boot/efi`, with the kernel
command line in `cmdline.txt`: one line of kernel arguments. [PS5 Linux boot partition](../boot-partition.md)
describes the partition, its files and every argument of the PS5 Linux command lines. Board Test's test 54 checks the
file, and its hints say which arguments to add there.

The table shows the line one argument per row, in its order, with what each argument does; an argument the quickfix
does not know says so. A double click edits a row. **Add** puts a known argument (or an empty row for your own) under
the selected row; **Remove**, **Up** and **Down** work on the selected row; the line below the table is what **Save
changes** writes. **All settings** lists every argument the PS5 Linux command lines use, with its values; the info
symbol beside it links the [PS5 Linux boot partition](../boot-partition.md) chapter. The boxes show whether the file
is there, how many arguments the line has, and how many backups the quickfix kept.

The list beside the boxes opens the fallback lines when they are on the partition: `cmdline.txt.m2` and
`cmdline.txt.usb`, the lines you copy over `cmdline.txt` to start the system on the M.2 SSD or the USB drive. Save
or Revert your edits before you open another file.

**Save changes** asks first, with the warning that it changes the boot settings of PS5 Linux: **Yes** saves, **No**
drops your edits, **Cancel** goes back to editing. A line without `root=` is not saved. **Revert** reads the file
again. When your user may not read the file, the File box says **Locked**, and **Read** shows it after your password.
A change to `cmdline.txt` applies from the next boot: restart the console with `systemctl reboot`.

`mitigations=off` turns off the kernel's guards against the CPU's speculative execution flaws (Spectre, Meltdown and
the like), which cost speed in games; the ps5-linux command line often sets it already. Without them a program could,
in principle, read the memory of other programs: keep them on where the console runs code you do not trust.
`amd_iommu=off` keeps the kernel from using the IOMMU. By default leave the IOMMU off. If it is on and you experience
an unstable system, turn it off again.

To undo a change, edit the line back, or copy a backup over the file (`cmdline.txt.bak-YYYYMMDD-HHMMSS`, beside
it). A console that no longer starts Linux after a change needs the file fixed on another computer: the partition is
FAT, so any computer can open the USB drive.

## Install

The portal installs the quickfixes with itself, and its uninstall removes them; the portal lists no Uninstall for them.
From a checkout of the repository:

```bash
apps/quickfix/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/quickfix/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/quickfix/install.sh --uninstall             # remove it; --purge removes its settings too
```

The launcher is `~/.local/bin/ps5-quickfix`: without an argument it opens the list, with a quickfix's key the quickfix's
own window (`ps5-quickfix tools`, `mangohud`, `mapcount`, `journal`, `cmdline`). The app runs on the
suite's shared Python environment.

## Files

- `~/.config/MangoHud/MangoHud.conf` and `~/mangohud-logs/`: MangoHud's own settings file and its log folder.
- `/etc/sysctl.d/90-ps5-quickfix-max-map-count.conf` and `/var/log/journal/.ps5-quickfix`: what Game Memory Map and
  Persistent Journal turned on, while it is on.
- `/boot/efi/cmdline.txt`, the fallback lines `cmdline.txt.m2` and `cmdline.txt.usb`, and their `.bak-*` backups: the
  kernel command lines Boot Command Line saved, and the files it replaced.

Uninstalling the app leaves all of them as they are: turn a quickfix off first to undo it.

## License

GPL-3.0-or-later.
