# SPDX-License-Identifier: GPL-3.0-or-later
"""The system part of the power button job: what runs as root. The app runs this file through pkexec with the system
python3 in isolated mode (-I), and it needs only the standard library:

    system.py power-button on USER      the standby unit and its script, the login screen's button, USER in input
    system.py power-button off          removes the unit, its script and the login screen's setting

 * STANDBY_UNIT, in /etc/systemd/system, is tied to sleep.target: around every sleep it runs STANDBY_SCRIPT, which
   makes the light bar breathe orange, turns the CPU boost off and picks a power-saving tuned profile, and puts all
   three back at the wake. Nothing else runs as root while the board sleeps and wakes.
 * LOGIND_CONF makes logind ignore a short press, so a press at the login screen no longer powers the board off. In a
   desktop session the desktop has the button, and the app sets it to do nothing there.
 * The watcher reads the button from /dev/input, which the input group may read: USER joins it, from the next login.
Everything lives in /etc, so it works on a read-only /usr too. off leaves the input group as it is."""

from __future__ import annotations

import argparse
import grp
import os
import pwd
import subprocess
import sys
from pathlib import Path

SYSTEM_PYTHON = "/usr/bin/python3"
STANDBY_UNIT = "ps5-cec-manager-standby.service"                   # in /etc/systemd/system
STANDBY_SCRIPT = "ps5-cec-manager/standby"                          # in /etc
LOGIND_CONF = "systemd/logind.conf.d/90-ps5-cec-manager-power-key.conf"     # in /etc
INPUT_GROUP = "input"

SCRIPT = """#!/bin/sh
# Written by PS5 CEC Manager: the board's standby look while it sleeps. ps5-cec-manager-standby.service runs it
# around every sleep: "on" makes the light bar breathe orange, turns the CPU boost off and picks a power-saving tuned
# profile; "off" puts back what "on" found. Whatever the board lacks is left out.
STATE=/run/ps5-cec-manager-standby.state
LEDS=/sys/class/leds
BOOST=$(command -v ps5_control || echo /usr/local/sbin/ps5_control)
led() { [ -w "$LEDS/$1/brightness" ] && echo 1 > "$LEDS/$1/brightness"; }
case "$1" in
on)
    boost=$(systemctl is-active ps5boost.service 2>/dev/null)
    profile=$(tuned-adm active 2>/dev/null | sed -n 's/^Current active profile: //p')
    printf 'boost=%s\\nprofile=%s\\n' "$boost" "$profile" > "$STATE"
    led ps5:orange_breathe:indicator
    [ "$boost" = active ] && [ -x "$BOOST" ] && "$BOOST" --boost off
    if [ -n "$profile" ]; then
        for saving in powersave-bazzite powersave; do
            tuned-adm list 2>/dev/null | grep -q -- "- $saving\\b" && { tuned-adm profile "$saving"; break; }
        done
    fi
    ;;
off)
    [ -f "$STATE" ] || exit 0
    boost=$(sed -n 's/^boost=//p' "$STATE")
    profile=$(sed -n 's/^profile=//p' "$STATE")
    led ps5:white_dim:indicator
    [ -n "$profile" ] && tuned-adm profile "$profile"
    [ "$boost" = active ] && [ -x "$BOOST" ] && "$BOOST" --boost on
    rm -f "$STATE"
    ;;
esac
exit 0
"""

UNIT = f"""# Written by PS5 CEC Manager: the board's standby look while it sleeps.
[Unit]
Description=PS5 CEC Manager: the board's standby look while it sleeps
Before=sleep.target
StopWhenUnneeded=yes

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/etc/{STANDBY_SCRIPT} on
ExecStop=/etc/{STANDBY_SCRIPT} off

[Install]
WantedBy=sleep.target
"""

LOGIND = """# Written by PS5 CEC Manager: a short press of the power button does nothing in logind,
# so a press at the login screen no longer powers the board off. In a desktop session the desktop has the button.
[Login]
HandlePowerKey=ignore
"""


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


def in_group(user: str, group: str) -> bool:
    try:
        entry = grp.getgrnam(group)
        return user in entry.gr_mem or pwd.getpwnam(user).pw_gid == entry.gr_gid
    except KeyError:
        return False


def power_button(etc: Path, on: bool, user: str = "") -> int:
    units = etc / "systemd" / "system"
    if on:
        write(etc / STANDBY_SCRIPT, SCRIPT, 0o755)
        write(units / STANDBY_UNIT, UNIT)
        write(etc / LOGIND_CONF, LOGIND)
        code = run(["systemctl", "daemon-reload"]) or run(["systemctl", "enable", STANDBY_UNIT])
        if not code and not in_group(user, INPUT_GROUP):
            code = run(["usermod", "-aG", INPUT_GROUP, user])
            if not code:
                print(f"Added to the {INPUT_GROUP} group: it applies from the next login.")
        return code
    run(["systemctl", "disable", STANDBY_UNIT])
    for path in (units / STANDBY_UNIT, etc / STANDBY_SCRIPT, etc / LOGIND_CONF):
        path.unlink(missing_ok=True)
        print(f"Removed {path}")
    try:
        (etc / STANDBY_SCRIPT).parent.rmdir()
    except OSError:
        pass
    return run(["systemctl", "daemon-reload"])


def main(argv: list[str] | None = None, etc: Path = Path("/etc")) -> int:
    parser = argparse.ArgumentParser(prog="system.py", description="PS5 CEC Manager, the part that runs as root")
    parser.add_argument("change", choices=("power-button",))
    parser.add_argument("state", choices=("on", "off"))
    parser.add_argument("user", nargs="?", default="", help="on: the user whose watcher reads the button")
    args = parser.parse_args(argv)
    if args.state == "on":
        try:
            pwd.getpwnam(args.user)
        except KeyError:
            parser.error("on needs the name of an existing user")
    return power_button(etc, args.state == "on", args.user)


if __name__ == "__main__":
    sys.exit(main())
