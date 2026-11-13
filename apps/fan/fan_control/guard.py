# SPDX-License-Identifier: GPL-3.0-or-later
"""The thermal guard: a system service that watches the PS5's SoC, CPU and GPU temperatures, also while no app is
open, and acts at three limits on the hottest of them:
 * warn: a desktop notification (and a line in the journal);
 * cool: the fan to full speed (ps5_fan's full mode, pwm1_enable 0) and the CPU boost off (ps5_control --boost off);
 * shut down: when the temperature stays at or above the limit for hold_s seconds, a clean `systemctl poweroff`.
   The one place in the suite that powers the console off by itself: it protects the hardware.
Each limit re-arms REARM_C below the warning; the fan then goes back to the mode it was in (normally the kernel's
curve, auto). The boost stays off: turning it back on is the user's choice (`sudo systemctl restart ps5boost`, or a
reboot).

What the PS5 kernel already does on its own, so the guard adds to it rather than replaces it: ps5_fan runs the fan
on its curve (full duty at 87 °C SoC on our console) and forces it to maximum from 90 °C SoC (its emergency mode,
until 85 °C); ps5_gpufreq slows the GPU above temp_limit (85 °C). Neither warns, turns the boost off or shuts down.

This file runs as root and needs only the standard library. The app runs it through pkexec with the system python3
in isolated mode (-I) to install or remove the guard, and the installed copy runs as the service:
 * /etc/ps5-fan-control/guard.py is that copy, guard.json next to it holds the limits;
 * /etc/systemd/system/ps5-fan-control-guard.service starts it at boot and restarts it when it stops;
 * /run/ps5-fan-control/state.json is what the guard saw last and its recent events, for the app to show.

The window imports this file for reading the sensors, so the two read the same thing.

Ported from the BC250 Bazzite Suite's fan guard (BC-250 Fan Control 2.0.1)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

SYSTEM_PYTHON = "/usr/bin/python3"
FOLDER = "ps5-fan-control"                      # in /etc and /run
UNIT = "ps5-fan-control-guard.service"
MANUAL_URL = "https://robertotorino.github.io/nexus/bazzite-console-suite/apps/fan/"
APP_NAME = "Fan Control"
STEP_S = 2.0
REARM_C = 5
EVENTS = 30                                     # kept in the state file
STALE_S = 15                                    # a state file older than this: the guard is not running
VALID_C = (1.0, 150.0)                          # outside this a reading is a broken sensor, never a reason to act
FAN_DRIVER = "ps5_fan"
PWM_FULL, PWM_MANUAL, PWM_AUTO = 0, 1, 2        # ps5_fan's pwm1_enable
PWM_MAX = 255
PS5_CONTROL = "/usr/local/sbin/ps5_control"     # ps5-linux-tools: --boost on|off
CURVE_POINTS = 8

Runner = Callable[[list[str]], "Result"]


@dataclass(frozen=True)
class Result:
    code: int
    out: str

    @property
    def ok(self) -> bool:
        return self.code == 0


def run(argv: list[str]) -> Result:
    try:
        done = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Result(127, str(exc))
    return Result(done.returncode, done.stdout)


def log(text: str) -> None:
    print(text, flush=True)                     # the journal, through the service's stdout


# --- The limits ----------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Limits:
    warn_c: int = 85                            # where ps5_gpufreq starts to slow the GPU (temp_limit)
    cool_c: int = 88                            # past the curve's full duty (87), before the kernel's emergency (90)
    shutdown_c: int = 95
    hold_s: int = 10


def limits_problem(limits: Limits) -> str:
    if not 60 <= limits.warn_c < limits.cool_c < limits.shutdown_c <= 105:
        return "The limits must rise from the warning to the shutdown, between 60 and 105 °C."
    if not 3 <= limits.hold_s <= 60:
        return "The shutdown waits between 3 and 60 seconds."
    return ""


# --- The sensors ---------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Fan:
    pwm: int | None                             # 0-255, the duty the kernel set
    mode: int | None                            # pwm1_enable: 0 full, 1 manual, 2 the kernel's curve
    folder: str                                 # the hwmon folder
    curve: tuple[tuple[int, int], ...] = ()     # (°C, duty %) of the kernel's curve

    @property
    def duty(self) -> int | None:
        return None if self.pwm is None else round(100 * max(0, min(self.pwm, PWM_MAX)) / PWM_MAX)

    @property
    def mode_text(self) -> str:
        if self.mode == PWM_AUTO:
            return "the kernel's curve"
        if self.mode == PWM_MANUAL:
            return f"manual {self.duty} %"
        if self.mode == PWM_FULL:
            return "full speed"
        return "unknown mode"


@dataclass(frozen=True)
class Reading:
    soc_c: float | None = None                  # ps5_fan "MainSoC"
    cpu_c: float | None = None                  # k10temp "Tctl"
    gpu_c: float | None = None                  # amdgpu temp1 (kernel 7.3.1 on: ps5_sensors)
    board_c: float | None = None                # the warmest of ps5_fan's Local1..3
    fan: Fan | None = None

    @property
    def hottest(self) -> tuple[str, float] | None:
        found = [(name, c) for name, c in (("SoC", self.soc_c), ("CPU", self.cpu_c), ("GPU", self.gpu_c))
                 if c is not None]
        return max(found, key=lambda pair: pair[1]) if found else None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def read_int(path: Path) -> int | None:
    try:
        return int(read_text(path))
    except ValueError:
        return None


def celsius(path: Path) -> float | None:
    milli = read_int(path)
    if milli is None:
        return None
    value = milli / 1000
    return value if VALID_C[0] <= value <= VALID_C[1] else None


def labelled(folder: Path) -> dict[str, float]:
    """Label -> °C of the folder's temperatures that read and are valid."""
    found = {}
    for path in sorted(folder.glob("temp*_input")):
        value = celsius(path)
        if value is not None:
            found[read_text(path.with_name(path.name.replace("_input", "_label"))) or path.name[:-6]] = value
    return found


def read_fan(folder: Path) -> Fan:
    curve = []
    for point in range(1, CURVE_POINTS + 1):
        temp = read_int(folder / f"pwm1_auto_point{point}_temp")
        pwm = read_int(folder / f"pwm1_auto_point{point}_pwm")
        if temp is not None and pwm is not None:
            curve.append((round(temp / 1000), round(100 * pwm / PWM_MAX)))
    return Fan(pwm=read_int(folder / "pwm1"), mode=read_int(folder / "pwm1_enable"), folder=str(folder),
               curve=tuple(curve))


def read_sensors(sys_root: Path = Path("/sys")) -> Reading:
    """Looks the hwmon folders up by name every time: their numbers change between boots."""
    soc = cpu = gpu = board = None
    fan = None
    for folder in sorted((sys_root / "class/hwmon").glob("hwmon*")):
        name = read_text(folder / "name")
        if name == FAN_DRIVER and fan is None:
            temps = labelled(folder)
            soc = temps.get("MainSoC")
            local = [c for label, c in temps.items() if label.startswith("Local")]
            board = max(local) if local else None
            fan = read_fan(folder)
        elif name == "k10temp" and cpu is None:
            cpu = labelled(folder).get("Tctl", celsius(folder / "temp1_input"))
        elif name == "amdgpu" and gpu is None:
            gpu = celsius(folder / "temp1_input")
    return Reading(soc_c=soc, cpu_c=cpu, gpu_c=gpu, board_c=board, fan=fan)


# --- The files -----------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Paths:
    etc: Path = Path("/etc")
    run: Path = Path("/run")

    @property
    def folder(self) -> Path:
        return self.etc / FOLDER

    @property
    def script(self) -> Path:
        return self.folder / "guard.py"

    @property
    def config(self) -> Path:
        return self.folder / "guard.json"

    @property
    def unit(self) -> Path:
        return self.etc / "systemd/system" / UNIT

    @property
    def state(self) -> Path:
        return self.run / FOLDER / "state.json"


def paths_from_env() -> Paths:
    root = Path(os.environ.get("PS5_SYSTEM_ROOT", "/"))         # another root only for testing
    return Paths(root / "etc", root / "run")


def read_limits(paths: Paths) -> Limits | None:
    try:
        data = json.loads(paths.config.read_text(encoding="utf-8"))
        limits = Limits(**{k: int(data[k]) for k in asdict(Limits())})
    except (OSError, ValueError, TypeError, KeyError):
        return None
    return None if limits_problem(limits) else limits


def installed(paths: Paths) -> Limits | None:
    """The guard's limits when all of it is there, else None."""
    if not (paths.script.is_file() and paths.unit.is_file()):
        return None
    return read_limits(paths) or Limits()


def outdated(paths: Paths, own: Path = Path(__file__)) -> bool:
    """Whether the installed copy differs from this file: another version of the app installed it."""
    try:
        return paths.script.read_bytes() != own.read_bytes()
    except OSError:
        return True


def read_state(paths: Paths, now: float | None = None) -> dict | None:
    """What the running guard wrote last; None when it is missing or older than STALE_S."""
    try:
        data = json.loads(paths.state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or (now if now is not None else time.time()) - data.get("time", 0) > STALE_S:
        return None
    return data


def unit_text() -> str:
    return "\n".join([
        "[Unit]",
        f"Description={APP_NAME}: the PS5 thermal guard (warns, cools, shuts down at a critical temperature)",
        f"Documentation={MANUAL_URL}",
        "",
        "[Service]",
        "Type=simple",
        f"ExecStart={SYSTEM_PYTHON} -I {Paths().script} run",
        "Restart=always",
        "RestartSec=5",
        f"RuntimeDirectory={FOLDER}",
        "RuntimeDirectoryMode=0755",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ])


def write(path: Path, data: bytes) -> None:
    """Root-owned, readable by everyone, written whole."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.new")
    temp.write_bytes(data)
    temp.chmod(0o644)
    temp.replace(path)


def relabel(run: Runner, *paths: Path) -> None:
    """The SELinux labels of the files (Fedora, Bazzite)."""
    if shutil.which("restorecon"):
        run(["restorecon", "-R", *map(str, paths)])


# --- What the app asks for, as root --------------------------------------------------------------------------------

def install(paths: Paths, limits: Limits, run: Runner = run, own: Path = Path(__file__)) -> None:
    problem = limits_problem(limits)
    if problem:
        raise ValueError(problem)
    write(paths.script, own.read_bytes())
    write(paths.config, (json.dumps(asdict(limits), indent=2) + "\n").encode())
    write(paths.unit, unit_text().encode())
    relabel(run, paths.folder, paths.unit)
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", UNIT])
    result = run(["systemctl", "restart", UNIT])                # new limits and a new copy take effect now
    if not result.ok:
        raise ValueError(f"The guard is installed but did not start: {result.out.strip()}")


def uninstall(paths: Paths, run: Runner = run) -> None:
    run(["systemctl", "disable", "--now", UNIT])                # the guard puts the fan back as it stops
    for path in (paths.unit, paths.config, paths.script):
        path.unlink(missing_ok=True)
    try:
        paths.folder.rmdir()
    except OSError:
        pass
    run(["systemctl", "daemon-reload"])


# --- Asked for by the app ------------------------------------------------------------------------------------------

def command(args: list[str], own: Path = Path(__file__)) -> list[str]:
    """This file as root, through polkit's password dialog."""
    python = SYSTEM_PYTHON if Path(SYSTEM_PYTHON).is_file() else sys.executable
    return ["pkexec", python, "-I", str(own.resolve()), *args]


def answer(code: int, out: str) -> str:
    """What went wrong ("" when nothing did): main() prints one JSON line; pkexec exits with 126 or 127 when the
    password dialog is canceled."""
    if code in (126, 127):
        return "Not authorized: the password dialog was canceled or refused."
    for line in reversed(out.strip().splitlines()):
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if isinstance(data, dict):
            return "" if data.get("ok") else str(data.get("error") or "It failed without saying why.")
    return f"The helper stopped with exit code {code} without an answer:\n{out.strip()}"


# --- The service ---------------------------------------------------------------------------------------------------

def notify_desktop(run: Runner, title: str, body: str, run_root: Path = Path("/run")) -> None:
    """A notification in every desktop session: as each user, on that user's session bus."""
    import pwd                                  # Linux only
    for bus in sorted((run_root / "user").glob("*/bus")):
        try:
            uid = int(bus.parent.name)
            user = pwd.getpwuid(uid).pw_name
        except (ValueError, KeyError):
            continue
        if uid < 1000:
            continue
        run(["runuser", "-u", user, "--", "env", f"DBUS_SESSION_BUS_ADDRESS=unix:path={bus}", "notify-send",
             "--urgency=critical", f"--app-name={APP_NAME}", "--icon=dialog-warning", title, body])


@dataclass
class Guard:
    limits: Limits
    paths: Paths = field(default_factory=Paths)
    sys_root: Path = Path("/sys")
    run: Runner = run
    notify: Callable[[str, str], None] | None = None
    clock: Callable[[], float] = time.monotonic
    wall: Callable[[], float] = time.time
    ps5_control: str = PS5_CONTROL

    def __post_init__(self) -> None:
        if self.notify is None:
            self.notify = lambda title, body: notify_desktop(self.run, title, body, self.paths.run)
        self.warned = False
        self.cooling = False
        self.hot_since: float | None = None
        self.powering_off = False
        self.saved: tuple[str, int | None, int | None] | None = None   # folder, mode, pwm before the cooling
        self.events: deque[dict] = deque(maxlen=EVENTS)
        self.no_sensor = False

    def event(self, text: str, kind: str = "info", alert: bool = False) -> None:
        log(text)
        self.events.append({"time": self.wall(), "kind": kind, "text": text})
        if alert:
            self.notify(APP_NAME, text)

    def step(self) -> Reading:
        reading = read_sensors(self.sys_root)
        hottest = reading.hottest
        if hottest is None:
            if not self.no_sensor:
                self.no_sensor = True
                self.event("No SoC, CPU or GPU temperature can be read; the guard waits for one and does nothing "
                           "until then.", "warn")
        else:
            self.no_sensor = False
            self.check_limits(*hottest)
        self.write_state(reading)
        return reading

    def check_limits(self, name: str, celsius: float) -> None:
        lim, now = self.limits, self.clock()
        rearm = lim.warn_c - REARM_C
        if celsius >= lim.warn_c and not self.warned:
            self.warned = True
            self.event(f"The {name} is at {celsius:.0f} °C (warning at {lim.warn_c} °C).", "warn", alert=True)
        elif self.warned and celsius < rearm:
            self.warned = False
            self.event(f"The {name} is back at {celsius:.0f} °C.")
        if celsius >= lim.cool_c and not self.cooling:
            self.cooling = True
            done = " and ".join(d for d in (self.fan_full(), self.boost_off()) if d) or "nothing to do"
            self.event(f"The {name} is at {celsius:.0f} °C (cooling at {lim.cool_c} °C): {done}.", "bad",
                       alert=True)
        elif self.cooling and celsius < rearm:
            self.cooling = False
            self.restore_fan()
            self.event(f"The {name} is back at {celsius:.0f} °C: the fan is back as it was. The CPU boost stays off "
                       "until you turn it on (sudo systemctl restart ps5boost) or reboot.")
        if celsius >= lim.shutdown_c:
            if self.hot_since is None:
                self.hot_since = now
                self.event(f"The {name} is at {celsius:.0f} °C (shutdown at {lim.shutdown_c} °C): the PS5 shuts "
                           f"down in {lim.hold_s} s unless it cools.", "bad", alert=True)
            elif now - self.hot_since >= lim.hold_s and not self.powering_off:
                self.powering_off = True
                self.event(f"The {name} stayed at or above {lim.shutdown_c} °C for {lim.hold_s} s "
                           f"({celsius:.0f} °C now): shutting down to protect the PS5.", "bad", alert=True)
                self.run(["systemctl", "poweroff"])
        elif self.hot_since is not None:
            self.hot_since = None
            self.event(f"The {name} is below {lim.shutdown_c} °C again ({celsius:.0f} °C): no shutdown.")

    def fan_full(self) -> str:
        """ps5_fan's full mode; the old mode (and a manual duty) is kept to put back."""
        fan = read_sensors(self.sys_root).fan
        if fan is None:
            return ""
        if self.saved is None:
            self.saved = (fan.folder, fan.mode, fan.pwm)
        try:
            (Path(fan.folder) / "pwm1_enable").write_text(str(PWM_FULL))
        except OSError as exc:
            log(f"pwm1_enable: {exc}")
            return ""
        return "the fan to full speed"

    def restore_fan(self) -> None:
        if self.saved is None:
            return
        folder, mode, pwm = self.saved
        try:
            if mode is not None:
                (Path(folder) / "pwm1_enable").write_text(str(mode))
            if mode == PWM_MANUAL and pwm is not None:          # the driver takes a duty only in manual mode
                (Path(folder) / "pwm1").write_text(str(pwm))
        except OSError as exc:
            log(f"fan: {exc}")
        self.saved = None

    def boost_off(self) -> str:
        if not Path(self.ps5_control).is_file():
            return ""
        result = self.run([self.ps5_control, "--boost", "off"])
        return "the CPU boost off" if result.ok else ""

    def level(self) -> str:
        if self.hot_since is not None:
            return "shutdown"
        if self.cooling:
            return "cooling"
        if self.warned:
            return "warn"
        return "ok"

    def write_state(self, reading: Reading) -> None:
        data = {"time": self.wall(), "level": self.level(), "limits": asdict(self.limits),
                "soc_c": reading.soc_c, "cpu_c": reading.cpu_c, "gpu_c": reading.gpu_c, "board_c": reading.board_c,
                "fan": asdict(reading.fan) if reading.fan else None, "events": list(self.events)}
        try:
            write(self.paths.state, (json.dumps(data) + "\n").encode())
        except OSError as exc:
            log(f"{self.paths.state}: {exc}")

    def stop(self) -> None:
        """When the service stops: the fan back as it was."""
        if self.saved is not None:
            self.restore_fan()
            log("Stopped: the fan is back as it was.")

    def loop(self, sleep: Callable[[float], None] = time.sleep) -> int:
        def stop(_signum, _frame):
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, stop)
        lim = self.limits
        self.event(f"Guard on: warning at {lim.warn_c} °C, cooling at {lim.cool_c} °C, shutdown at "
                   f"{lim.shutdown_c} °C held for {lim.hold_s} s.")
        try:
            while True:
                self.step()
                sleep(STEP_S)
        finally:
            self.stop()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="guard.py", description=__doc__.split("\n\n")[0])
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("run", help="watch the temperatures (the service)")
    add = actions.add_parser("install", help="install or update the guard and (re)start it")
    defaults = Limits()
    add.add_argument("--warn", type=int, default=defaults.warn_c, help="°C")
    add.add_argument("--cool", type=int, default=defaults.cool_c, help="°C")
    add.add_argument("--shutdown", type=int, default=defaults.shutdown_c, help="°C")
    add.add_argument("--hold", type=int, default=defaults.hold_s, help="seconds")
    actions.add_parser("uninstall", help="stop and remove the guard")
    args = parser.parse_args(argv)
    paths = paths_from_env()

    if args.action == "run":
        limits = read_limits(paths)
        if limits is None:
            limits = Limits()
            log(f"{paths.config} is missing or broken; the guard uses its defaults")
        return Guard(limits, paths).loop()
    try:
        if args.action == "install":
            install(paths, Limits(args.warn, args.cool, args.shutdown, args.hold))
        else:
            uninstall(paths)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
