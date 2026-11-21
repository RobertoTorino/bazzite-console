# SPDX-License-Identifier: GPL-3.0-or-later
"""The power button job on a fake board: which input devices it reads, how it tells sleep from soft mode, and what it
sends to the TV on a press, a wake and a failed sleep."""

from __future__ import annotations

from pathlib import Path

from cec_manager import button, cec
from cec_manager.runner import Result

# capabilities/key of the PS5's power button (KEY_POWER only) and of a keyboard without a power key.
POWER_KEY = "10000000000000 0"
NO_POWER_KEY = "1000000000007 ff9f207ac14057ff feaeffdfffefffff fffffffffffffffe"
ADAPTER = cec.Adapter("/dev/cec0", "ps5-cec", "ps5-cec", "1.0.0.0", ("4 (Playback Device 1)",))
UNCONFIGURED = cec.Adapter("/dev/cec0", "ps5-cec", "ps5-cec")


def put(root: Path, path: str, text: str) -> None:
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class Board:
    """systemctl and cec-ctl as the board answers them; suspend_ok=False is a sleep that fails."""

    def __init__(self, suspend_ok: bool = True):
        self.suspend_ok = suspend_ok
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> Result:
        self.calls.append(argv)
        if argv == button.SUSPEND:
            return Result(0, "") if self.suspend_ok else Result(1, "Call to Suspend failed: Access denied")
        return Result(0, "")

    def cec(self) -> list[str]:
        return [c[-1] if c[-1].startswith("--") else c[-2] for c in self.calls if c[0] == cec.CEC_CTL]


def test_the_power_key_in_a_capabilities_bitmap():
    assert button.has_power_key(POWER_KEY)
    assert not button.has_power_key(NO_POWER_KEY)
    assert not button.has_power_key("0") and not button.has_power_key("")


def test_power_buttons_are_the_devices_with_the_power_key(tmp_path):
    put(tmp_path, "sys/class/input/event0/device/capabilities/key", NO_POWER_KEY + "\n")
    put(tmp_path, "sys/class/input/event3/device/capabilities/key", POWER_KEY + "\n")
    assert button.power_buttons(tmp_path / "sys", tmp_path / "dev") == [tmp_path / "dev/input/event3"]


def test_sleep_needs_the_kernel_and_an_unmasked_suspend_target(tmp_path):
    sys_root = tmp_path / "sys"
    unmasked = lambda argv: Result(0, "static\n")                       # noqa: E731
    masked = lambda argv: Result(1, "masked\n")                         # noqa: E731
    assert not button.sleep_available(unmasked, sys_root)               # no /sys/power/state
    put(sys_root, "power/state", "disk\n")
    assert not button.sleep_available(unmasked, sys_root)
    put(sys_root, "power/state", "freeze\n")                            # the PS5 kernel: s2idle only
    assert button.sleep_available(unmasked, sys_root)
    assert not button.sleep_available(masked, sys_root)


def test_suspends_and_the_screen(tmp_path):
    sys_root = tmp_path / "sys"
    assert button.suspends(sys_root) == 0 and button.screen_on(sys_root) is None
    put(sys_root, "power/suspend_stats/success", "3\n")
    put(sys_root, "power/suspend_stats/fail", "1\n")
    assert button.suspends(sys_root) == 4
    put(sys_root, "class/drm/card0-DP-1/status", "connected\n")
    put(sys_root, "class/drm/card0-DP-1/dpms", "Off\n")
    assert button.screen_on(sys_root) is False


def test_a_press_sleeps_and_the_wake_turns_the_tv_on(tmp_path):
    sys_root, clock, board = tmp_path / "sys", Clock(), Board()
    put(sys_root, "power/suspend_stats/success", "0\n")
    press = button.PowerButton(board, lambda: ADAPTER, True, sys_root, clock)
    press.press()
    assert board.cec() == ["--standby"] and board.calls[-1] == button.SUSPEND
    press.press()                                                       # while it goes to sleep
    assert board.calls[-1] == button.SUSPEND and len(board.calls) == 2
    put(sys_root, "power/suspend_stats/success", "1\n")                 # the board is back
    press.tick()
    assert board.cec() == ["--standby", "--image-view-on", "--active-source"]
    assert "phys-addr=1.0.0.0" in board.calls[-1]
    clock.now += 2
    press.press()                                                       # the wake press, seen late
    assert board.calls[-1][0] == cec.CEC_CTL
    clock.now += button.IGNORE_AFTER_RESUME
    press.press()
    assert board.calls[-1] == button.SUSPEND


def test_a_failed_sleep_turns_the_tv_on_again(tmp_path):
    board = Board(suspend_ok=False)
    press = button.PowerButton(board, lambda: ADAPTER, True, tmp_path / "sys", Clock())
    press.press()
    assert board.cec() == ["--standby", "--image-view-on", "--active-source"] and not press.asleep_by_us


def test_without_cec_the_board_still_sleeps(tmp_path):
    board = Board()
    press = button.PowerButton(board, lambda: UNCONFIGURED, True, tmp_path / "sys", Clock())
    press.press()
    assert board.cec() == [] and board.calls[-1] == button.SUSPEND


def test_soft_mode_follows_the_screen(tmp_path):
    sys_root, clock, board = tmp_path / "sys", Clock(), Board()
    put(sys_root, "class/drm/card0-DP-1/status", "connected\n")
    put(sys_root, "class/drm/card0-DP-1/dpms", "Off\n")                 # an idle screen-off: left alone
    press = button.PowerButton(board, lambda: ADAPTER, False, sys_root, clock)
    press.tick()
    assert board.calls == []
    press.press()                                                       # the desktop turns the screen off
    press.tick()
    assert board.calls == []                                            # not before SETTLE
    clock.now += button.SETTLE
    press.tick()
    assert board.cec() == ["--standby"] and button.SUSPEND not in board.calls
    put(sys_root, "class/drm/card0-DP-1/dpms", "On\n")
    press.tick()
    assert board.cec() == ["--standby", "--image-view-on", "--active-source"]
