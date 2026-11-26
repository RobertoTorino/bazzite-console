# SPDX-License-Identifier: GPL-3.0-or-later
"""The run wrapper (ps5-vita3k-run) with a fake Vita3K that prints its arguments and environment: the AppImage's
self-updater turned off; Steam's list of controllers to ignore replaced while a real controller is there, left alone
otherwise; a game Steam starts on a Wayland desktop opened through XWayland, so Steam's overlay works over it;
unpacking when there is no fusermount."""

from __future__ import annotations

import os
import re
import signal as signal_module
import subprocess
import sys
import time

import pytest

from vita3k_manager import ROOT

WRAPPER = ROOT / "ps5-vita3k-run"

# /proc/bus/input/devices with Steam running (the shadPS4 Manager's, from the owner's board): a DualShock 4 on USB,
# its motion sensors and touchpad, and Steam's virtual controller.
DS4_AND_STEAM = """\
I: Bus=0003 Vendor=054c Product=09cc Version=8111
N: Name="Sony Interactive Entertainment Wireless Controller"
H: Handlers=event3 js0

I: Bus=0003 Vendor=054c Product=09cc Version=8111
N: Name="Sony Interactive Entertainment Wireless Controller Motion Sensors"
H: Handlers=event4

I: Bus=0003 Vendor=054c Product=09cc Version=8111
N: Name="Sony Interactive Entertainment Wireless Controller Touchpad"
H: Handlers=mouse0 event5

I: Bus=0003 Vendor=28de Product=11ff Version=0001
N: Name="Microsoft X-Box 360 pad 0"
H: Handlers=event14 js1
"""
STEAM_ONLY = DS4_AND_STEAM.split("\n\n")[-1]
STEAM_LIST = "0x054C/0x09CC"
GAME = ("--frontend", "sdl", "-r", "PCSB00245")
UNSET = {"ignore": "unset", "except": "unset", "sdl": "unset", "qpa": "unset", "extract": "unset", "updates": "1"}

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="a bash script for Linux")


def _printed(log: Path) -> dict[str, str]:
    """What the fake emulator printed, from the app's emulator log, where the wrapper writes it (owner, 26-11-2026):
    its own started and ended lines left out. The log is removed, so the next start has its own."""
    lines = [line for line in log.read_text().splitlines() if not re.match(r"\d\d-\d\d-\d{4} ", line)]
    log.unlink()
    return dict(line.split("=", 1) for line in lines)


@pytest.fixture
def run(tmp_path):
    vita3k = tmp_path / "data" / "ps5-vita3k-manager" / "emulator" / "current" / "vita3k.AppImage"
    vita3k.parent.mkdir(parents=True)
    vita3k.write_text('#!/bin/sh\necho "args=$*"\necho "ignore=${SDL_GAMECONTROLLER_IGNORE_DEVICES-unset}"\n'
                      'echo "except=${SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT-unset}"\n'
                      'echo "sdl=${SDL_VIDEO_DRIVER-unset}"\necho "qpa=${QT_QPA_PLATFORM-unset}"\n'
                      'echo "extract=${APPIMAGE_EXTRACT_AND_RUN-unset}"\n'
                      'echo "updates=${DISABLE_AUTO_UPDATES-unset}"\n')
    vita3k.chmod(0o755)
    devices = tmp_path / "devices"
    fusermount = tmp_path / "bin"
    fusermount.mkdir()
    (fusermount / "fusermount3").write_text("#!/bin/sh\n")
    (fusermount / "fusermount3").chmod(0o755)

    def go(inputs: str, *args: str, path: str | None = None, **env: str) -> dict[str, str]:
        devices.write_text(inputs)
        environ = {k: v for k, v in os.environ.items()
                   if not k.startswith(("SDL_", "QT_", "APPIMAGE", "DISABLE_")) and
                   k not in ("SteamGameId", "WAYLAND_DISPLAY", "DISPLAY")}
        # Only the tools the wrapper needs, and the fake fusermount3 unless *path* says otherwise.
        tools = tmp_path / "tools"
        if not tools.exists():
            tools.mkdir()
            for name in ("awk", "sed", "dirname"):
                found = subprocess.run(["bash", "-c", f"command -v {name}"], capture_output=True, text=True)
                if found.stdout.strip():
                    (tools / name).symlink_to(found.stdout.strip())
        environ.update(XDG_DATA_HOME=str(tmp_path / "data"), PS5_INPUT_DEVICES=str(devices),
                       PATH=path if path is not None else f"{fusermount}:{tools}", **env)
        done = subprocess.run(["/bin/bash", str(WRAPPER), *args], capture_output=True, text=True, env=environ,
                              check=True)
        return _printed(tmp_path / "data" / "ps5-vita3k-manager" / "emulator.log")
    return go


def test_started_by_steam_with_a_real_controller(run):
    out = run(DS4_AND_STEAM, *GAME, SDL_GAMECONTROLLER_IGNORE_DEVICES=STEAM_LIST,
              SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT="0x28DE/0x1205")
    assert out == {**UNSET, "args": " ".join(GAME), "ignore": "0x28DE/0x11FF"}


def test_started_by_steam_with_only_steams_controller(run):
    out = run(STEAM_ONLY, *GAME, SDL_GAMECONTROLLER_IGNORE_DEVICES=STEAM_LIST)
    assert out["ignore"] == STEAM_LIST                                  # Steam's choice stands


def test_started_outside_steam(run):
    assert run(DS4_AND_STEAM) == {**UNSET, "args": ""}                  # the self-updater is off all the same


def test_started_by_steam_on_a_wayland_desktop(run):
    desktop = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}
    out = run(DS4_AND_STEAM, *GAME, SteamGameId="3710761059", **desktop)
    assert (out["sdl"], out["qpa"]) == ("x11", "xcb")
    out = run(DS4_AND_STEAM, *GAME, **desktop)                                              # Play, outside Steam
    assert (out["sdl"], out["qpa"]) == ("unset", "unset")
    out = run(DS4_AND_STEAM, *GAME, SteamGameId="1", DISPLAY=":0")                          # X11 only
    assert (out["sdl"], out["qpa"]) == ("unset", "unset")
    out = run(DS4_AND_STEAM, *GAME, SteamGameId="1", SDL_VIDEO_DRIVER="wayland", QT_QPA_PLATFORM="wayland",
              **desktop)
    assert (out["sdl"], out["qpa"]) == ("wayland", "wayland")                               # a choice of the user's


def test_without_fusermount_it_unpacks_itself(run, tmp_path):
    run(DS4_AND_STEAM)                                                  # makes the tools folder
    assert run(DS4_AND_STEAM, path=str(tmp_path / "tools"))["extract"] == "1"


def test_help_and_not_installed(tmp_path):
    env = {**os.environ, "XDG_DATA_HOME": str(tmp_path)}
    done = subprocess.run(["/bin/bash", str(WRAPPER), *GAME], capture_output=True, text=True, env=env)
    assert done.returncode == 1 and "Vita3K is not installed" in done.stderr
    shown = subprocess.run(["/bin/bash", str(WRAPPER), "--help"], capture_output=True, text=True, env=env, check=True)
    assert shown.stdout.startswith("Starts the Vita3K") and "--zrif KEY" in shown.stdout
    assert "set -euo" not in shown.stdout


def _emulator(tmp_path: Path, script: str) -> tuple[Path, dict[str, str]]:
    """A fake Vita3K that runs *script*, and the wrapper's environment for it: the home folder in tmp_path."""
    appimage = tmp_path / "data" / "ps5-vita3k-manager" / "emulator" / "current" / "vita3k.AppImage"
    appimage.parent.mkdir(parents=True, exist_ok=True)
    appimage.write_text("#!/bin/bash\n" + script)
    appimage.chmod(0o755)
    environ = {k: v for k, v in os.environ.items() if not k.startswith(("SDL_", "QT_")) and k != "SteamGameId"}
    environ.update(XDG_DATA_HOME=str(tmp_path / "data"), HOME=str(tmp_path / "home"),
                   PS5_INPUT_DEVICES=str(tmp_path / "none"))
    return tmp_path / "data" / "ps5-vita3k-manager" / "emulator.log", environ


def test_what_the_emulator_prints_goes_to_its_log(tmp_path):
    """Its output and errors in the app's emulator log (owner, 26-11-2026: the View logs tab shows it), between a
    started and an ended line in the app's form, with the home folder written as ~; a last line without a newline
    is ended before the wrapper's own. The wrapper ends with the emulator's exit code."""
    home = str(tmp_path / "home")
    log, environ = _emulator(tmp_path, f'echo "out {home}/x"\necho "error at {home}" >&2\n'
                                       f'echo "not {home}2"\nprintf "last"\nexit 3\n')
    (tmp_path / "home").mkdir()
    (tmp_path / "home" / "game").write_text("")
    done = subprocess.run(["/bin/bash", str(WRAPPER), f"{home}/game"], capture_output=True, text=True, env=environ)
    assert done.returncode == 3 and done.stdout == ""
    lines = log.read_text().splitlines()
    assert all(re.fullmatch(r"\d\d-\d\d-\d{4} \d\d:\d\d:\d\d", line[:19]) for line in (lines[0], lines[-1]))
    assert [lines[0][20:], *lines[1:-1], lines[-1][20:]] == [
        "INFO Vita3K started: ~/game", "out ~/x", "error at ~", f"not {home}2", "last",
        "INFO Vita3K ended (exit code 3)."]


def test_a_stop_is_passed_on(tmp_path):
    """Steam's stop (SIGTERM) and Ctrl+C in a terminal (SIGINT, passed on as SIGTERM) reach the emulator, which
    saves and ends as on any close; the wrapper waits for it and ends with its exit code."""
    for signal in (signal_module.SIGTERM, signal_module.SIGINT):
        log, environ = _emulator(tmp_path, 'trap "echo stopped; exit 5" TERM\necho ready\n'
                                           'while :; do sleep 0.05; done\n')
        log.unlink(missing_ok=True)
        wrapper = subprocess.Popen(["/bin/bash", str(WRAPPER)], env=environ, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 10
        while not (log.exists() and "ready" in log.read_text()) and time.monotonic() < deadline:
            time.sleep(0.05)
        wrapper.send_signal(signal)
        assert wrapper.wait(timeout=10) == 5
        assert log.read_text().splitlines()[-2:][0] == "stopped"
        assert log.read_text().endswith("INFO Vita3K ended (exit code 5).\n")


def test_the_log_turns_over_at_1_mb(tmp_path):
    """As the app's own log: at 1 MB the file becomes emulator.log.1 when a game starts, three older ones kept."""
    log, environ = _emulator(tmp_path, "echo new\n")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("x" * 1_000_000)
    for number in (1, 2, 3):
        log.with_name(f"emulator.log.{number}").write_text(f"old {number}")
    subprocess.run(["/bin/bash", str(WRAPPER)], env=environ, capture_output=True, check=True)
    assert log.with_name("emulator.log.1").stat().st_size == 1_000_000
    assert [log.with_name(f"emulator.log.{n}").read_text() for n in (2, 3)] == ["old 1", "old 2"]
    assert "new" in log.read_text() and len(log.read_text()) < 1000
