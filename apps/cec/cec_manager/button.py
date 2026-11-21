# SPDX-License-Identifier: GPL-3.0-or-later
"""The power button job of the watcher (--power-button): the board's power button puts the TV in standby and the board
to sleep, and the press that wakes the board turns the TV on and switches it to the board.

It reads the button from every input device that reports KEY_POWER (/dev/input/event*, so the user needs the input
group). Two modes, picked when the job starts:
 * sleep, when the kernel and systemd offer it (sleep_available): a press puts the TV in standby and runs
   `systemctl suspend`. The board's own standby look (light bar, boost, power profile) is the system unit that
   system.py installs, tied to sleep.target. A resume shows as a new count in /sys/power/suspend_stats: the PS5 has no
   RTC, so no clock tells the time asleep. Then the TV comes on and switches to the board. Presses within
   IGNORE_AFTER_RESUME seconds of a resume are ignored, so the wake press does not send the board back to sleep. A
   suspend that fails turns the TV on again.
 * soft, without sleep: the desktop turns the screen off on the press (the app sets that). When the screen is off
   SETTLE seconds after a press, the TV goes to standby; when the screen is on again, the TV comes on and switches to
   the board. An idle screen-off is left alone, so an idle board never turns the TV off while it shows another input.
It writes one line to the journal for each thing it does."""

from __future__ import annotations

import os
import select
import struct
import time
from pathlib import Path
from typing import Callable

from . import cec
from .runner import Result

EV_KEY, KEY_POWER = 1, 116
EVENT = struct.Struct("llHHi")                  # struct input_event on a 64-bit kernel
SETTLE = 1.5                                    # s after a press before soft mode reads the screen
IGNORE_AFTER_RESUME = 10.0                      # s: the wake press must not suspend again
SUSPEND = ["systemctl", "suspend"]

Runner = Callable[[list[str]], Result]


def has_power_key(capabilities: str) -> bool:
    """Whether an input device's capabilities/key bitmap (hex words of 64 bits, the highest first) has KEY_POWER."""
    words = capabilities.split()
    index, bit = divmod(KEY_POWER, 64)
    if index >= len(words):
        return False
    try:
        return bool(int(words[-1 - index], 16) >> bit & 1)
    except ValueError:
        return False


def power_buttons(sys_root: Path = Path("/sys"), dev_root: Path = Path("/dev")) -> list[Path]:
    """The input devices that report the power key."""
    found = []
    for caps in sorted((sys_root / "class" / "input").glob("event*/device/capabilities/key")):
        try:
            if has_power_key(caps.read_text()):
                found.append(dev_root / "input" / caps.parents[2].name)
        except OSError:
            pass
    return found


def suspends(sys_root: Path = Path("/sys")) -> int:
    """How many suspends ended since boot, failed ones too: the count moves when the board is back."""
    total = 0
    for name in ("success", "fail"):
        try:
            total += int((sys_root / "power" / "suspend_stats" / name).read_text().strip())
        except (OSError, ValueError):
            pass
    return total


def sleep_available(run: Runner, sys_root: Path = Path("/sys")) -> bool:
    """The kernel can suspend (freeze or mem in /sys/power/state) and systemd's suspend.target is not masked."""
    try:
        states = (sys_root / "power" / "state").read_text().split()
    except OSError:
        return False
    if not {"freeze", "mem"} & set(states):
        return False
    return run(["systemctl", "is-enabled", "suspend.target"]).out.strip() != "masked"


def screen_on(sys_root: Path = Path("/sys")) -> bool | None:
    """Whether the connected display's screen is on (DRM's dpms); None without a connected display."""
    for status in sorted((sys_root / "class" / "drm").glob("card*-*/status")):
        try:
            if status.read_text().strip() == "connected":
                return (status.parent / "dpms").read_text().strip() == "On"
        except OSError:
            continue
    return None


def log(text: str) -> None:
    print(text, flush=True)


class PowerButton:
    def __init__(self, run: Runner, adapter: Callable[[], cec.Adapter | None], sleep_mode: bool,
                 sys_root: Path = Path("/sys"), clock: Callable[[], float] = time.monotonic):
        self.run, self.adapter, self.sleep_mode = run, adapter, sleep_mode
        self.sys_root, self.clock = sys_root, clock
        self.count = suspends(sys_root)
        self.resumed_at: float | None = None
        self.asleep_by_us = False               # we started the suspend and wait for the board to come back
        self.check_at: float | None = None      # soft mode: when to read the screen after a press
        self.tv_off_by_us = False               # soft mode: we put the TV in standby

    def ready(self) -> cec.Adapter | None:
        adapter = self.adapter()
        if adapter is None or not adapter.configured:
            log("CEC is not configured (no physical address): turn the TV off and on once")
            return None
        return adapter

    def tv_off(self) -> bool:
        adapter = self.ready()
        if adapter is None:
            return False
        self.run([cec.CEC_CTL, *cec.standby(adapter.device)])
        return True

    def tv_on(self) -> None:
        adapter = self.ready()
        if adapter is None:
            return
        self.run([cec.CEC_CTL, *cec.image_view_on(adapter.device)])
        self.run([cec.CEC_CTL, *cec.active_source(adapter.device, adapter.physical_address)])
        log(f"the TV is on and shows the board ({adapter.physical_address})")

    def press(self) -> None:
        if not self.sleep_mode:
            self.check_at = self.clock() + SETTLE
            return
        if self.asleep_by_us:
            log("power button while going to sleep: ignored")
            return
        if self.resumed_at is not None and self.clock() - self.resumed_at < IGNORE_AFTER_RESUME:
            log("power button right after a wake: ignored")
            return
        off = self.tv_off()
        log(f"power button: the TV is {'in standby' if off else 'not reachable over CEC'}, the board goes to sleep")
        result = self.run(SUSPEND)
        if result.ok:
            self.asleep_by_us = True
            return
        log(f"the board did not go to sleep: {result.out.strip() or f'exit code {result.code}'}")
        if off:
            self.tv_on()

    def tick(self) -> None:
        """Once a second and after every press: a resume, and in soft mode the screen."""
        count = suspends(self.sys_root)
        if count > self.count:
            log("the board is awake")
            self.resumed_at = self.clock()
            if self.asleep_by_us:
                self.asleep_by_us = False
                self.tv_on()
        self.count = count
        if self.sleep_mode:
            return
        on = screen_on(self.sys_root)
        if self.check_at is not None and self.clock() >= self.check_at:
            self.check_at = None
            if on is False and not self.tv_off_by_us and self.tv_off():
                self.tv_off_by_us = True
                log("power button: the screen is off, the TV is in standby")
        if self.tv_off_by_us and on:
            self.tv_off_by_us = False
            self.tv_on()

    def loop(self, dev_root: Path = Path("/dev")) -> int:
        devices = power_buttons(self.sys_root, dev_root)
        fds = []
        for device in devices:
            try:
                fds.append(os.open(device, os.O_RDONLY | os.O_NONBLOCK))
            except OSError as exc:
                log(f"{device}: {exc.strerror} (the input group gives access)")
        if not fds:
            log("no power button this user may read: nothing to watch")
            return 1
        log(f"watching the power button ({len(fds)} device{'s' if len(fds) > 1 else ''}), "
            f"{'sleep' if self.sleep_mode else 'soft'} mode")
        while True:
            ready, _, _ = select.select(fds, [], [], 1.0)
            for fd in ready:
                data = os.read(fd, EVENT.size * 64)
                for start in range(0, len(data) - EVENT.size + 1, EVENT.size):
                    _, _, kind, code, value = EVENT.unpack_from(data, start)
                    if kind == EV_KEY and code == KEY_POWER and value == 1:
                        self.press()
            self.tick()
