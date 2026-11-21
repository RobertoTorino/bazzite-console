# SPDX-License-Identifier: GPL-3.0-or-later
"""The system part of the quickfixes: what runs as root. The app runs this file through pkexec with the system python3
in isolated mode (-I), one change per call, and it needs only the standard library:

    system.py mapcount on | off                 vm.max_map_count in /etc/sysctl.d (MAPCOUNT_CONF)
    system.py journal on | off                  the journal kept on the disk, in /var/log/journal
    system.py ethernet on | off                 the Wi-Fi off while a network cable is connected (ETHERNET_HOOK)
    system.py cmdline show [--file NAME]        prints /boot/efi/cmdline.txt (or NAME, one of CMDLINES), when your
                                                user may not read it
    system.py cmdline save --text FILE [--file NAME]   writes FILE's line to it, after a dated backup of it beside it

Each change touches only its own file and is undone by its "off"; a new command line keeps the old one as a backup.
The reading side is in the app (state.py): it needs no password."""

from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

SYSTEM_PYTHON = "/usr/bin/python3"
MAPCOUNT_CONF = "sysctl.d/90-ps5-quickfix-max-map-count.conf"      # in /etc
MAPCOUNT = 2147483642                                             # what SteamOS and Bazzite set
JOURNAL_DIR = "log/journal"                                       # in /var
JOURNAL_MARK = ".ps5-quickfix"                                     # in it: the quickfix made the folder
ETHERNET_HOOK = "NetworkManager/dispatcher.d/90-ps5-quickfix-ethernet-first"   # in /etc
ETHERNET_UNIT = "ps5-quickfix-ethernet-first"                       # .service and .timer, in /etc/systemd/system
ETHERNET_MARK = "lib/ps5-quickfix/wifi-off-by-ethernet-first"                 # in /var: the hook turned the Wi-Fi off
CMDLINE_DIR = "efi"                                               # in /boot: the PS5 loader's partition
CMDLINES = ("cmdline.txt", "cmdline.txt.m2", "cmdline.txt.usb")   # the line it starts Linux with; the fallback lines
CMDLINE = f"{CMDLINE_DIR}/{CMDLINES[0]}"


def command(args: list[str], own: Path = Path(__file__)) -> list[str]:
    """This file as root, through polkit's password dialog."""
    python = SYSTEM_PYTHON if Path(SYSTEM_PYTHON).is_file() else sys.executable
    return ["pkexec", python, "-I", str(own.resolve()), *args]


def answer(code: int, out: str) -> str:
    """What went wrong ("" when nothing did); pkexec exits with 126 or 127 when the password dialog is canceled."""
    if code == 0:
        return ""
    if code in (126, 127):
        return "Not authorized: the password dialog was canceled or refused."
    return out.strip() or f"It failed (exit code {code})."


def run(argv: list[str]) -> int:
    print("$ " + " ".join(argv), flush=True)
    try:
        return subprocess.run(argv, check=False).returncode
    except OSError as exc:
        print(f"{argv[0]}: {exc}")
        return 127


def write(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.chmod(tmp, mode)
    tmp.replace(path)
    print(f"Wrote {path}")


# ------------------------------------------------------------------------------------------------ the changes
def mapcount(etc: Path, on: bool) -> int:
    conf = etc / MAPCOUNT_CONF
    if on:
        write(conf, f"# Written by PS5 Quickfix (Game Memory Map): the memory areas a game may map.\n"
                    f"vm.max_map_count = {MAPCOUNT}\n")
        return run(["sysctl", "-w", f"vm.max_map_count={MAPCOUNT}"])
    conf.unlink(missing_ok=True)
    print(f"Removed {conf}")
    return run(["sysctl", "--system"])           # the value the other files set, else the kernel's own


def journal(var: Path, on: bool) -> int:
    folder = var / JOURNAL_DIR
    if on:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / JOURNAL_MARK).write_text("Made by PS5 Quickfix (Persistent Journal).\n", encoding="utf-8")
        code = run(["systemd-tmpfiles", "--create", "--prefix", str(folder)])
        return code or run(["journalctl", "--flush"])
    if not (folder / JOURNAL_MARK).is_file():
        print(f"{folder} was not made by PS5 Quickfix: it stays.")
        return 1
    run(["journalctl", "--relinquish-var"])
    shutil.rmtree(folder)
    print(f"Removed {folder}: the journal is kept in memory until the next boot again.")
    return 0


# ------------------------------------------------------------------------------------------------ Ethernet First
# NetworkManager runs the hook as root with the interface and the action; the timer's service runs it with "check".
ETHERNET_SCRIPT = f"""#!/bin/sh
# Written by PS5 Quickfix (Ethernet First): the Wi-Fi off while a network cable is connected, back on when the
# cable is gone. NetworkManager runs it on every up, down and connectivity change, {ETHERNET_UNIT}.timer once
# after boot. It turns the Wi-Fi back on only when it turned it off itself, so a Wi-Fi you turned off stays off.
case "$2" in up|down|connectivity-change|check) ;; *) exit 0 ;; esac
MARK=/var/{ETHERNET_MARK}
cable=no
for dev in $(nmcli -t -f DEVICE,TYPE,STATE device 2>/dev/null \\
        | awk -F: '$2 == "ethernet" && $3 == "connected" {{print $1}}'); do
    [ -e "/sys/class/net/$dev/device" ] && cable=yes      # a port of the board, not a bridge or a container's
done
if [ "$cable" = yes ]; then
    if [ "$(nmcli radio wifi 2>/dev/null)" = enabled ]; then
        mkdir -p "${{MARK%/*}}" && touch "$MARK"
        nmcli radio wifi off && logger -t ps5-quickfix "Ethernet First: a cable is connected, the Wi-Fi is off"
    fi
elif [ -e "$MARK" ]; then
    nmcli radio wifi on && rm -f "$MARK" && logger -t ps5-quickfix "Ethernet First: no cable, the Wi-Fi is on again"
fi
exit 0
"""

ETHERNET_SERVICE = f"""# Written by PS5 Quickfix (Ethernet First): checks the cable once after boot.
[Unit]
Description=PS5 Quickfix Ethernet First: the Wi-Fi off while a network cable is connected
After=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/etc/{ETHERNET_HOOK} - check
"""

# Late enough for the cable's DHCP; turns the Wi-Fi on again after a boot without the cable it was left off for.
ETHERNET_TIMER = """# Written by PS5 Quickfix (Ethernet First).
[Unit]
Description=PS5 Quickfix Ethernet First: check the cable after boot

[Timer]
OnBootSec=45s

[Install]
WantedBy=timers.target
"""


def ethernet(etc: Path, var: Path, on: bool) -> int:
    hook = etc / ETHERNET_HOOK
    units = etc / "systemd" / "system"
    if on:
        write(hook, ETHERNET_SCRIPT, 0o755)
        write(units / f"{ETHERNET_UNIT}.service", ETHERNET_SERVICE)
        write(units / f"{ETHERNET_UNIT}.timer", ETHERNET_TIMER)
        code = run(["systemctl", "daemon-reload"]) or run(["systemctl", "enable", f"{ETHERNET_UNIT}.timer"])
        return code or run([str(hook), "-", "check"])           # now, not only at the next change
    run(["systemctl", "disable", "--now", f"{ETHERNET_UNIT}.timer"])
    for path in (hook, units / f"{ETHERNET_UNIT}.service", units / f"{ETHERNET_UNIT}.timer"):
        path.unlink(missing_ok=True)
        print(f"Removed {path}")
    run(["systemctl", "daemon-reload"])
    mark = var / ETHERNET_MARK
    if not mark.is_file():
        return 0
    code = run(["nmcli", "radio", "wifi", "on"])        # the Wi-Fi this quickfix turned off
    if not code:
        mark.unlink()
        print("The Wi-Fi this quickfix turned off is on again.")
    return code


# ------------------------------------------------------------------------------------------- Boot Command Line
def cmdline_problem(text: str) -> str:
    """Why *text* cannot be the kernel command line ("" when it can): one line, with the root= of the system."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return "The command line is empty: it needs at least root=, the system Linux starts."
    if len(lines) != 1:
        return "cmdline.txt must be one line: the kernel arguments, separated by spaces."
    if not any(arg.startswith("root=") for arg in lines[0].split()):
        return "The line has no root=: Linux would not find its system and the board would not start it."
    return ""


def cmdline_show(boot: Path, name: str = CMDLINES[0]) -> int:
    path = boot / CMDLINE_DIR / name
    try:
        sys.stdout.write(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"{path} could not be read: {exc}")
        return 1
    return 0


def cmdline_save(boot: Path, source: Path, name: str = CMDLINES[0]) -> int:
    target = boot / CMDLINE_DIR / name
    text = source.read_text(encoding="utf-8")
    problem = cmdline_problem(text)
    if problem:
        print(problem)
        return 1
    if not target.parent.is_dir():
        print(f"{target.parent} is not there: is the loader's partition mounted?")
        return 1
    if target.is_file():
        backup = target.with_name(f"{target.name}.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}")
        shutil.copyfile(target, backup)
        print(f"Backup: {backup}")
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as out:      # no chmod: the loader's partition is FAT
        out.write(text.strip() + "\n")
        out.flush()
        os.fsync(out.fileno())
    tmp.replace(target)
    if name == CMDLINES[0]:
        print(f"Wrote {target}. Restart the board to start Linux with it: systemctl reboot.")
    else:
        print(f"Wrote {target}. The loader starts Linux with it once it is copied over {CMDLINES[0]}.")
    return 0


def main(argv: list[str] | None = None, etc: Path = Path("/etc"), var: Path = Path("/var"),
         boot: Path = Path("/boot")) -> int:
    parser = argparse.ArgumentParser(prog="system.py", description="PS5 Quickfix, the part that runs as root")
    parser.add_argument("change", choices=("mapcount", "journal", "ethernet", "cmdline"))
    parser.add_argument("state", choices=("on", "off", "show", "save"))
    parser.add_argument("--text", type=Path, help="cmdline save: the file with the new line")
    parser.add_argument("--file", choices=CMDLINES, default=CMDLINES[0], help="cmdline: which command line")
    args = parser.parse_args(argv)
    if (args.change == "cmdline") != (args.state in ("show", "save")) or (args.state == "save") != bool(args.text):
        parser.error(f"{args.change} does not take {args.state}" + (" without --text" if args.state == "save" else ""))
    if args.change == "cmdline":
        return cmdline_show(boot, args.file) if args.state == "show" else cmdline_save(boot, args.text, args.file)
    on = args.state == "on"
    if args.change == "mapcount":
        return mapcount(etc, on)
    if args.change == "ethernet":
        return ethernet(etc, var, on)
    return journal(var, on)


if __name__ == "__main__":
    sys.exit(main())
