# SPDX-License-Identifier: GPL-3.0-or-later
"""The run wrapper (ps5-kytyps5-run) with a fake KytyPS5-Native that prints its arguments and SDL's controller lists: Steam's
list of controllers to ignore replaced while a real controller is there, left alone otherwise; a game Steam starts on
a Wayland desktop opened through XWayland, so Steam's overlay works over it."""

from __future__ import annotations

import os
import re
import signal as signal_module
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

WRAPPER = Path(__file__).resolve().parents[1] / "ps5-kytyps5-run"

# /proc/bus/input/devices on a board with Steam running (PS5 shadPS4 Manager's fixture): a DualShock 4 on USB, its motion
# sensors and touchpad, and Steam's virtual controller.
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
# Game folders that are there (the wrapper refuses one that is not), with a space in a path.
_GAMES = Path(tempfile.mkdtemp(prefix="ps5-wrapper-")) / "games"
for _name in ("a b", "x", "a b/PPSA11624", "PPSA00001", "PPSA00002"):
    (_GAMES / _name).mkdir(parents=True, exist_ok=True)
STEAM_LIST = "0x054C/0x09CC"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="a bash script for Linux")


def _printed(log: Path) -> dict[str, str]:
    """What the fake emulator printed (its key=value lines), from the app's emulator log, where the wrapper writes
    it with the time and a level: the wrapper's own lines left out. The log is removed, so the next start has its
    own."""
    found = [re.fullmatch(r"\d\d-\d\d-\d{4} \d\d:\d\d:\d\d INFO (args|ignore|except|video)=(.*)", line)
             for line in log.read_text().splitlines()]
    log.unlink()
    return {match[1]: match[2] for match in found if match}


@pytest.fixture
def run(tmp_path):
    shad = tmp_path / "data" / "ps5-kytyps5" / "emulator" / "current" / "kyty_emulator"
    shad.parent.mkdir(parents=True)
    shad.write_text('#!/bin/sh\necho "args=$*"\necho "ignore=${SDL_GAMECONTROLLER_IGNORE_DEVICES-unset}"\n'
                    'echo "except=${SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT-unset}"\n'
                    'echo "video=${SDL_VIDEO_DRIVER-unset}"\n')
    shad.chmod(0o755)
    devices = tmp_path / "devices"

    def go(inputs: str, *args: str, **env: str) -> dict[str, str]:
        devices.write_text(inputs)
        environ = {k: v for k, v in os.environ.items()
                   if not k.startswith("SDL_") and k not in ("SteamGameId", "WAYLAND_DISPLAY", "DISPLAY")}
        environ.update(XDG_DATA_HOME=str(tmp_path / "data"), PS5_INPUT_DEVICES=str(devices), GAMELOG_WAIT="0",
                       **env)
        done = subprocess.run(["/bin/bash", str(WRAPPER), *args], capture_output=True, text=True, env=environ,
                              check=True)
        return _printed(tmp_path / "data" / "ps5-kytyps5" / "emulator.log")
    return go


def test_started_by_steam_with_a_real_controller(run):
    out = run(DS4_AND_STEAM, "--fullscreen", "--game", f"{_GAMES}/a b", SDL_GAMECONTROLLER_IGNORE_DEVICES=STEAM_LIST,
              SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT="0x28DE/0x1205")
    assert out == {"args": f"--fullscreen --game {_GAMES}/a b", "ignore": "0x28DE/0x11FF", "except": "unset",
                   "video": "unset"}


def test_started_by_steam_with_only_steams_controller(run):
    out = run(STEAM_ONLY, "--game", f"{_GAMES}/x", SDL_GAMECONTROLLER_IGNORE_DEVICES=STEAM_LIST)
    assert out["ignore"] == STEAM_LIST                                  # Steam's choice stands


def test_started_outside_steam(run):
    out = run(DS4_AND_STEAM, "--game", f"{_GAMES}/x")
    assert out == {"args": f"--game {_GAMES}/x", "ignore": "unset", "except": "unset",  # SDL leaves Steam's controller out itself
                   "video": "unset"}


def test_started_by_steam_on_a_wayland_desktop(run):
    desktop = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}
    assert run(DS4_AND_STEAM, "--game", f"{_GAMES}/x", SteamGameId="3710761059", **desktop)["video"] == "x11"
    assert run(DS4_AND_STEAM, "--game", f"{_GAMES}/x", **desktop)["video"] == "unset"                     # Play, outside Steam
    assert run(DS4_AND_STEAM, "--game", f"{_GAMES}/x", SteamGameId="1", DISPLAY=":0")["video"] == "unset"  # X11 only
    assert run(DS4_AND_STEAM, "--game", f"{_GAMES}/x", SteamGameId="1", SDL_VIDEO_DRIVER="wayland",
               **desktop)["video"] == "wayland"                                             # a choice of the user's


def test_the_game_started_goes_to_the_apps_log(run, tmp_path):
    """One line in the app's log file, in its form, with the game's folder name (not its path) and from where; a
    start without a game says nothing. Only the tools the
    wrapper needs on the PATH, so no real desktop notification is sent."""
    import re
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("awk", "dirname", "grep", "mkdir", "readlink", "stat"):
        found = subprocess.run(["bash", "-c", f"command -v {name}"], capture_output=True, text=True)
        if found.stdout.strip():
            (tools / name).symlink_to(found.stdout.strip())
    path = str(tools)
    log = tmp_path / "data" / "ps5-kytyps5" / "ps5-kytyps5.log"
    run(DS4_AND_STEAM, "--help-me", PATH=path)
    assert not log.exists()
    run(DS4_AND_STEAM, "--fullscreen", "--game", f"{_GAMES}/a b/PPSA11624", SteamGameId="3710761059", PATH=path)
    run(DS4_AND_STEAM, "--game", f"{_GAMES}/PPSA00001/", PATH=path)
    run(STEAM_ONLY, "--game", f"{_GAMES}/PPSA00002", SteamGameId="3710761059", PATH=path)   # no real controller
    lines = log.read_text().splitlines()
    assert [line[20:] for line in lines] == ["INFO Started PPSA11624 from Steam, with a controller.",
                                             "INFO Started PPSA00001 from a terminal, with a controller.",
                                             "INFO Started PPSA00002 from Steam, without a controller."]
    assert all(re.fullmatch(r"\d\d-\d\d-\d{4} \d\d:\d\d:\d\d", line[:19]) for line in lines)
    assert "/games/" not in log.read_text()


def test_a_game_that_is_gone_is_not_started(tmp_path):
    """A shortcut to a game renamed, moved or deleted: the emulator is not started, the wrapper
    says so and ends with 1, so Steam sees the game end; without the app's Python, the words go to stderr alone."""
    emulator = tmp_path / "data" / "ps5-kytyps5" / "emulator" / "current" / "kyty_emulator"
    emulator.parent.mkdir(parents=True)
    emulator.write_text('#!/bin/sh\necho started\n')
    emulator.chmod(0o755)
    gone = tmp_path / "Games" / "gone"
    done = subprocess.run(["/bin/bash", str(WRAPPER), "--fullscreen", "--game", str(gone)], capture_output=True, text=True,
                          env={**os.environ, "XDG_DATA_HOME": str(tmp_path / "data"), "HOME": str(tmp_path),
                               "PS5_INPUT_DEVICES": str(tmp_path / "none")})
    assert done.returncode == 1 and "started" not in done.stdout
    assert "This game is no longer there" in done.stderr and str(gone) in done.stderr


def _emulator(tmp_path: Path, script: str) -> tuple[Path, dict[str, str]]:
    """A fake KytyPS5-Native that runs *script*, and the wrapper's environment for it: the home folder in tmp_path."""
    emulator = tmp_path / "data" / "ps5-kytyps5" / "emulator" / "current" / "kyty_emulator"
    emulator.parent.mkdir(parents=True, exist_ok=True)
    emulator.write_text("#!/bin/bash\n" + script)
    emulator.chmod(0o755)
    environ = {k: v for k, v in os.environ.items() if not k.startswith(("SDL_", "QT_")) and k != "SteamGameId"}
    environ.update(XDG_DATA_HOME=str(tmp_path / "data"), HOME=str(tmp_path / "home"),
                   PS5_INPUT_DEVICES=str(tmp_path / "none"), GAMELOG_WAIT="0")
    return tmp_path / "data" / "ps5-kytyps5" / "emulator.log", environ


def test_what_the_emulator_prints_goes_to_its_log(tmp_path):
    """Its output and errors in the app's emulator log (the View logs tab shows it), between a
    started and an ended line, every line in the app's form (the time and a level), with the home folder written
    as ~; a last line without a newline is ended before the wrapper's own. An exit code that is not 0 is a
    WARNING. The wrapper ends with the emulator's exit code."""
    home = str(tmp_path / "home")
    log, environ = _emulator(tmp_path, f'echo "out {home}/x"\necho "error at {home}" >&2\n'
                                       f'echo "not {home}2"\nprintf "last"\nexit 3\n')
    (tmp_path / "home").mkdir()
    (tmp_path / "home" / "game").write_text("")
    done = subprocess.run(["/bin/bash", str(WRAPPER), f"{home}/game"], capture_output=True, text=True, env=environ)
    assert done.returncode == 3 and done.stdout == ""
    lines = log.read_text().splitlines()
    assert all(re.match(r"\d\d-\d\d-\d{4} \d\d:\d\d:\d\d (INFO|WARNING|ERROR) ", line) for line in lines)
    lines = [line[20:] for line in lines]
    assert lines[0] == "INFO KytyPS5-Native started: ~/game"
    printed = ["INFO out ~/x", "ERROR error at ~", f"INFO not {home}2", "INFO last"]
    assert [line for line in lines if line in printed] == printed
    ended = next(i for i, line in enumerate(lines) if "KytyPS5-Native ended" in line)
    assert re.fullmatch(r"WARNING KytyPS5-Native ended \(exit code 3\) after \d+ s\.", lines[ended])
    assert lines.index("INFO last") < ended


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
        assert any(line.endswith(" INFO stopped") for line in log.read_text().splitlines())
        assert re.search(r"WARNING KytyPS5-Native ended \(exit code 5\) after \d+ s\.\n", log.read_text())


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
    assert " INFO new\n" in log.read_text() and len(log.read_text()) < 10_000     # a new file


def test_it_starts_from_the_emulators_own_data_folder(tmp_path):
    """KytyPS5-Native keeps its saves in the folder it is started from: its own data folder, never the build's."""
    log, environ = _emulator(tmp_path, 'echo "from=$(pwd)"\n')
    subprocess.run(["/bin/bash", str(WRAPPER)], env=environ, capture_output=True, check=True)
    assert f" INFO from={tmp_path / 'data' / 'KytyPS5-Native' / 'data'}\n" in log.read_text()


def test_the_launcher_and_no_emulator(tmp_path):
    """--launcher starts KytyPS5-Native's own window with the rest of the arguments; without an installed emulator
    the wrapper says so and ends with 1."""
    done = subprocess.run(["/bin/bash", str(WRAPPER), "--game", "x"], capture_output=True, text=True,
                          env={**os.environ, "XDG_DATA_HOME": str(tmp_path / "data")})
    assert done.returncode == 1 and "KytyPS5-Native is not installed" in done.stderr
    _log, environ = _emulator(tmp_path, "echo emulator\n")
    launcher = tmp_path / "data" / "ps5-kytyps5" / "emulator" / "current" / "kyty_launcher"
    launcher.write_text('#!/bin/sh\necho "launcher=$*"\n')
    launcher.chmod(0o755)
    _log.unlink(missing_ok=True)
    done = subprocess.run(["/bin/bash", str(WRAPPER), "--launcher", "a"], capture_output=True, text=True, env=environ)
    assert done.returncode == 0 and done.stdout == ""                 # in the emulator log, as a game's
    assert " INFO launcher=a\n" in _log.read_text()
    assert "INFO KytyPS5-Native started: --launcher a" in _log.read_text()


def _tools(tmp_path: Path, journal: str, xrandr: str = "", helper: str = "not-found\ninactive") -> dict[str, str]:
    """Stand-ins for the programs the wrapper asks (journalctl prints *journal* for a range and one line for -n 1,
    xrandr prints *xrandr*, systemctl prints *helper*), a display, a meminfo and a home: the wrapper's environment."""
    tools = tmp_path / "tools"
    tools.mkdir(exist_ok=True)
    (tmp_path / "journal").write_text(journal)
    scripts = {"journalctl": f'case "$*" in *-n\\ 1*) [ -s {tmp_path}/journal ] && echo boot ;; '
                             f'*) cat {tmp_path}/journal ;; esac\n',
               "xrandr": f"cat <<'END'\n{xrandr}END\n",
               "systemctl": f"printf '%s\\n' '{helper.splitlines()[0]}' '{helper.splitlines()[1]}'\n",
               "pgrep": "exit 1\n"}
    for name, body in scripts.items():
        (tools / name).write_text("#!/bin/bash\n" + body)
        (tools / name).chmod(0o755)
    connector = tmp_path / "sys" / "class" / "drm" / "card1-DP-1"
    connector.mkdir(parents=True, exist_ok=True)
    (connector / "status").write_text("connected\n")
    (connector / "modes").write_text("3840x2160\n1920x1080\n")
    (connector / "edid").write_bytes(EDID)
    unused = tmp_path / "sys" / "class" / "drm" / "card1-DP-2"
    unused.mkdir(exist_ok=True)
    (unused / "status").write_text("disconnected\n")
    dmi = tmp_path / "sys" / "class" / "dmi" / "id"
    dmi.mkdir(parents=True, exist_ok=True)
    for name, value in {"board_vendor": "ASRock", "board_name": "AMD BC-250", "bios_version": "P5.00",
                        "bios_date": "05/03/2022", "board_serial": "SERIAL-NOT-READ"}.items():
        (dmi / name).write_text(value + "\n")
    (tmp_path / "cpuinfo").write_text("processor\t: 0\nmodel name\t: AMD BC-250\n\nprocessor\t: 1\n"
                                      "model name\t: AMD BC-250\n")
    (tmp_path / "meminfo").write_text("MemTotal:       15556608 kB\nMemFree:  1 kB\nMemAvailable:   11586560 kB\n"
                                      "SwapTotal:       7778300 kB\nSwapFree:        6666240 kB\n")
    return {"PATH": f"{tools}:{os.environ['PATH']}", "GAMELOG_SYS": str(tmp_path / "sys"),
            "GAMELOG_MEMINFO": str(tmp_path / "meminfo"), "GAMELOG_CPUINFO": str(tmp_path / "cpuinfo"), "DISPLAY": ":0", "XDG_SESSION_TYPE": "wayland",
            "XDG_CURRENT_DESKTOP": "KDE", "GAMELOG_HOSTNAME": "board-a"}


def _edid(name: str, serial: str) -> bytes:
    """A 128-byte EDID: maker XMD (0x61A4, the board's TV), a display name descriptor and a serial number one."""
    edid = bytearray(128)
    edid[0:8] = bytes([0, 255, 255, 255, 255, 255, 255, 0])
    edid[8:10] = bytes([0x61, 0xA4])
    for at, tag, text in ((54, 0xFF, serial), (72, 0xFC, name)):
        edid[at + 3] = tag
        edid[at + 5:at + 18] = (text + "\n").encode().ljust(13, b" ")[:13]
    return bytes(edid)


EDID = _edid("Mi TV", "SECRET123")
XRANDR = """Screen 0: minimum 16 x 16, current 1920 x 1080, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 1880mm x 1050mm
   1920x1080    119.93*+
DP-2 disconnected (normal left inverted right x axis y axis)
"""
OOM = ("2026-11-28T14:51:59+01:00 bc250-1 kernel: Out of memory: Killed process 749990 (steamwebhelper) "
       "total-vm:49619248kB\n2026-11-28T14:51:59+01:00 bc250-1 steam[1]: something else\n")


def _ours(log: Path) -> list[str]:
    """Every line in the emulator log (the wrapper's and what the emulator printed), without its time."""
    return [line[20:] for line in log.read_text().splitlines() if re.match(r"\d\d-\d\d-\d{4} \d\d:\d\d:\d\d ", line)]


def test_the_log_says_what_a_game_ran_with_and_how_it_ended(tmp_path):
    """Before the game: the build, the board, the processor, the game, each controller, the session, each connected
    display with its name and preferred mode, the desktop's mode, the size the game gets, the memory left and the GPU
    helper. After it: the exit code with its signal (a crash is an ERROR), the time it ran, the memory left and the
    system log's out-of-memory kills, without the host name. No serial number is read."""
    log, environ = _emulator(tmp_path, "echo playing\nexit 141\n")
    current = tmp_path / "data" / "ps5-kytyps5" / "emulator" / "current"
    build = current.with_name("2026-11-27-8278d03")
    current.rename(build)
    current.symlink_to(build.name)
    (tmp_path / "home").mkdir()
    (tmp_path / "home" / "game").mkdir()
    environ.update(_tools(tmp_path, OOM, XRANDR))
    (tmp_path / "none").write_text(DS4_AND_STEAM)
    done = subprocess.run(["/bin/bash", str(WRAPPER), "--fullscreen", "--game", str(tmp_path / "home" / "game")],
                          capture_output=True, text=True, env=environ)
    assert done.returncode == 141
    lines = _ours(log)
    assert lines[0] == "INFO KytyPS5-Native started: --fullscreen --game ~/game"
    assert lines[1] == "INFO Build: 2026-11-27-8278d03."
    assert lines[2] == "INFO Board: board-a, ASRock AMD BC-250, BIOS P5.00 of 05/03/2022."
    assert re.fullmatch(r"INFO Processor: AMD BC-250, \d+ threads, kernel .+\.", lines[3])
    assert lines[4:13] == [
        "INFO Game: game, from ~/game.",                                    # no param.json: the folder's name
        "INFO Controller: Sony Interactive Entertainment Wireless Controller (054c:09cc).",
        "INFO Controller: Microsoft X-Box 360 pad 0 (28de:11ff), Steam's virtual controller.",
        "INFO Session: wayland, desktop KDE, SDL video driver not set.",
        "INFO Display card1-DP-1: Mi TV (XMD), preferred mode 3840x2160.",
        "INFO Desktop mode: DP-1 1920x1080 at 119.93 Hz.",
        "INFO Game size: not given, so KytyPS5-Native's own default applies.",
        "INFO GPU helper kyty-lodhw: not installed.",
        "INFO Memory at the start: 11315 MiB of 15192 MiB available, swap 6510 MiB of 7595 MiB free."]
    assert lines[13] == "INFO playing"
    assert re.fullmatch(r"ERROR KytyPS5-Native ended \(exit code 141, SIGPIPE\) after \d+ s\.", lines[14])
    assert lines[15:] == [
        "INFO Memory at the end: 11315 MiB of 15192 MiB available, swap 6510 MiB of 7595 MiB free.",
        "WARNING System log: 2026-11-28T14:51:59+01:00 kernel: Out of memory: Killed process 749990 (steamwebhelper) "
        "total-vm:49619248kB"]
    assert "bc250-1" not in log.read_text()
    assert "SECRET123" not in log.read_text() and "SERIAL-NOT-READ" not in log.read_text()
    assert not log.with_name("emulator.running").exists()


def test_the_size_given_and_a_quiet_system_log(tmp_path):
    """--screen-width and --screen-height are logged as the game's size; an active GPU helper and a system log
    without events say so; a log that cannot be read says that."""
    log, environ = _emulator(tmp_path, "exit 0\n")
    (tmp_path / "game").mkdir()
    environ.update(_tools(tmp_path, "2026-11-28T14:51:59+01:00 host steam[1]: fine\n", helper="loaded\nactive"))
    subprocess.run(["/bin/bash", str(WRAPPER), "--screen-width", "1920", "--screen-height", "1080", "--game",
                    str(tmp_path / "game")], capture_output=True, env=environ, check=True)
    lines = _ours(log)
    assert "INFO Game size: 1920x1080, from --screen-width and --screen-height." in lines
    assert "INFO GPU helper kyty-lodhw: active." in lines
    assert lines[-1] == "INFO System log: no out-of-memory kill, GPU reset, GPU fault or core dump."
    log.unlink()
    (tmp_path / "journal").write_text("")                                       # not readable for this user
    subprocess.run(["/bin/bash", str(WRAPPER), "--game", str(tmp_path / "game")], capture_output=True, env=environ,
                   check=True)
    assert _ours(log)[-1] == "INFO System log: not read, so out-of-memory kills and GPU resets are not known."


def test_a_start_ended_from_outside_is_reported_at_the_next(tmp_path):
    """A start without an end (the wrapper was killed with the game): the next start says so first, with what the
    system log has from then on."""
    log, environ = _emulator(tmp_path, "exit 0\n")
    (tmp_path / "game").mkdir()
    environ.update(_tools(tmp_path, OOM))
    log.parent.mkdir(parents=True, exist_ok=True)
    log.with_name("emulator.running").write_text("1764337860\n")
    subprocess.run(["/bin/bash", str(WRAPPER), "--game", str(tmp_path / "game")], capture_output=True, env=environ,
                   check=True)
    lines = _ours(log)
    assert re.fullmatch(r"WARNING The start at \d\d-\d\d-\d{4} \d\d:\d\d:\d\d has no end line: it was ended from "
                        r"outside\.", lines[0])
    assert lines[1].startswith("WARNING System log: 2026-11-28T14:51:59+01:00 kernel: Out of memory: Killed process")
    assert lines[2].startswith("INFO KytyPS5-Native started: --game ")


def test_the_launcher_logs_the_size_kytys_own_window_sets(tmp_path):
    """KytyPS5-Native's own window starts games with the size in its Kyty.ini: the log says which."""
    log, environ = _emulator(tmp_path, "exit 0\n")
    launcher = log.parent / "emulator" / "current" / "kyty_launcher"
    launcher.write_text("#!/bin/sh\necho window\n")
    launcher.chmod(0o755)
    environ.update(_tools(tmp_path, ""), XDG_CONFIG_HOME=str(tmp_path / "config"))
    (tmp_path / "config" / "Kyty").mkdir(parents=True)
    (tmp_path / "config" / "Kyty" / "Kyty.ini").write_text(
        "[GlobalConfiguration]\nfullscreen_enabled=false\nscreen_resolution=1280x720\n")
    subprocess.run(["/bin/bash", str(WRAPPER), "--launcher"], capture_output=True, env=environ, check=True)
    assert ("INFO Game size: set in KytyPS5-Native's own window, screen_resolution=1280x720, "
            "fullscreen_enabled=false.") in _ours(log)
    assert " INFO window\n" in log.read_text()


def test_the_game_is_named_as_the_app_names_it(tmp_path):
    """With the app installed (its package and core beside it, the suite's Python), the game's title, title ID and
    version come from its param.json; no controller is a WARNING; a display without an EDID says so."""
    log, environ = _emulator(tmp_path, "exit 0\n")
    data = tmp_path / "data"
    app = data / "ps5-kytyps5" / "app"
    app.mkdir(parents=True)
    (app / "kytyps5_manager").symlink_to(Path(__file__).resolve().parents[1] / "kytyps5_manager")
    (app / "bazzite_console_core").symlink_to(Path(__file__).resolve().parents[3] / "core" / "bazzite_console_core")
    python = data / "bazzite-console-suite" / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    game = tmp_path / "Games" / "PPSA21567"
    (game / "sce_sys").mkdir(parents=True)
    (game / "sce_sys" / "param.json").write_text(
        '{"titleId": "PPSA21567", "contentVersion": "01.019.000", "localizedParameters": '
        '{"defaultLanguage": "en-US", "en-US": {"titleName": "ASTRO BOT"}}}')
    environ.update(_tools(tmp_path, ""))
    (tmp_path / "sys" / "class" / "drm" / "card1-DP-1" / "edid").write_bytes(b"")
    subprocess.run(["/bin/bash", str(WRAPPER), "--fullscreen", "--game", str(game)], capture_output=True, env=environ,
                   check=True)
    lines = _ours(log)
    assert f"INFO Game: ASTRO BOT (PPSA21567) version 01.019.000, from {game}." in lines
    assert "WARNING Controller: none connected." in lines
    assert "INFO Display card1-DP-1: no EDID, preferred mode 3840x2160." in lines


def test_a_crash_is_an_error_and_a_stop_is_not(tmp_path):
    """The end line's level: a signal other than a stop (here SIGSEGV) is an ERROR, Steam's stop (SIGTERM) INFO."""
    for script, level in (("kill -SEGV $$\n", "ERROR"), ("kill -TERM $$\n", "INFO")):
        log, environ = _emulator(tmp_path, script)
        log.unlink(missing_ok=True)
        environ.update(_tools(tmp_path, ""))
        subprocess.run(["/bin/bash", str(WRAPPER)], capture_output=True, env=environ)
        ended = [line for line in _ours(log) if "KytyPS5-Native ended" in line]
        assert ended and ended[0].startswith(f"{level} KytyPS5-Native ended (exit code ")
