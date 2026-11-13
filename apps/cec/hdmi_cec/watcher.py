# SPDX-License-Identifier: GPL-3.0-or-later
"""The background part of the app: python -m hdmi_cec.watcher [--pause-media], started by the user service
ps5-hdmi-cec-watch.service with the desktop session.

Every POLL_S seconds it asks the TV for its power status (Give Device Power Status: a question, it wakes nothing).
 * --pause-media: when the TV goes to standby, it pauses the media players that play (media.py), and continues
   them when the TV is on again.
One missed answer is not "off": only SILENT_POLLS of them in a row are (the TV unplugged), so a glitch on the bus
pauses nothing. It writes one line to the journal for each thing it does. (The BC250 suite's --restart-picture, a
DP-to-HDMI converter workaround, is left out: the PS5 has its own HDMI port.)"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from bazzite_console_core.platform import config_home

from . import bazzite, cec, media
from .runner import Result

POLL_S = 5
SILENT_POLLS = 3                        # this many unanswered questions in a row: the TV counts as off


def run(argv: list[str]) -> Result:
    try:
        done = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Result(127, str(exc))
    return Result(done.returncode, done.stdout)


def log(text: str) -> None:
    print(text, flush=True)


class Watcher:
    def __init__(self, run: Callable[[list[str]], Result] = run, sleep: Callable[[float], None] = time.sleep,
                 pause_media: bool = False, config_dir: Path | None = None):
        self.run, self.sleep = run, sleep
        self.config_dir = config_dir or config_home()
        self.pause = pause_media
        self.adapter: cec.Adapter | None = None
        self.last: str | None = None            # "on" or "off" at the last look; None before the first answer
        self.silent = 0                         # unanswered questions in a row
        self.paused: list[str] = []             # the players paused while the TV is off

    def find_adapter(self, dev_root: Path = Path("/dev")) -> cec.Adapter | None:
        found = []
        for device in cec.devices(dev_root):
            result = self.run([cec.CEC_CTL, *cec.info(device)])
            if result.ok:
                found.append(cec.parse_info(device, result.out))
        adapter = cec.pick(found)
        if adapter is None:
            return None
        name = bazzite.read_fragment(self.config_dir).get("osd_name") or cec.OSD_NAME
        cecd = self.run(["systemctl", "--user", "is-active", bazzite.CECD_UNIT]).ok    # it names the adapter itself
        if not adapter.configured or (cec.needs_name(adapter, name) and not cecd):   # as the app does
            configured = self.run([cec.CEC_CTL, *cec.configure(adapter.device, name)])
            adapter = cec.parse_info(adapter.device, configured.out) if "Driver Info" in configured.out else adapter
        return adapter

    def tv_power(self) -> str:
        return cec.power_status(self.run([cec.CEC_CTL, *cec.give_power_status(self.adapter.device)]).out)

    def change(self, power: str) -> str:
        """ "came on", "went off" or "" for the TV's power now: "on", "standby" or a transition, "" for no answer."""
        if power:
            self.silent = 0
            now = "on" if power == "on" else "off"
        else:
            self.silent += 1
            if self.silent < SILENT_POLLS:
                return ""
            now = "off"
        before, self.last = self.last, now
        if before is None or before == now:
            return ""
        return "came on" if now == "on" else "went off"

    def step(self) -> None:
        change = self.change(self.tv_power())
        if change == "went off" and self.pause:
            self.paused = media.pause_all(self.run)
            log(f"the TV is off; paused {', '.join(self.paused) or 'nothing (nothing played)'}")
        elif change == "came on":
            if self.pause and self.paused:
                media.resume(self.run, self.paused)
                log(f"the TV is on again; continued {', '.join(self.paused)}")
                self.paused = []

    def loop(self) -> int:
        self.adapter = self.find_adapter()
        if self.adapter is None:
            log("no CEC adapter (/dev/cec*); nothing to watch")
            return 1
        jobs = ["pause media"] if self.pause else []
        log(f"watching the TV on {self.adapter.device} ({self.adapter.name}): {' and '.join(jobs) or 'nothing to do'}")
        while True:
            self.step()
            self.sleep(POLL_S)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="hdmi_cec.watcher")
    parser.add_argument("--pause-media", action="store_true", help="pause media players while the TV is off")
    args = parser.parse_args(argv)
    return Watcher(pause_media=args.pause_media).loop()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
