# SPDX-License-Identifier: GPL-3.0-or-later
"""guard.py on a fake PS5: the sensors, the limits, the three actions and their re-arming, the fan mode put back,
the files it installs and its answers to the app."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import CURVE, FAN, fan, set_temps, write

from fan_control import guard


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Recorder:
    def __init__(self, answers: dict[str, guard.Result] | None = None):
        self.calls: list[list[str]] = []
        self.answers = answers or {}

    def __call__(self, argv: list[str]) -> guard.Result:
        self.calls.append(argv)
        for key, result in self.answers.items():
            if key in argv:
                return result
        return guard.Result(0, "")


@pytest.fixture
def control(tmp_path) -> str:
    """A stand-in for /usr/local/sbin/ps5_control: the guard only checks that it exists and runs it."""
    path = tmp_path / "ps5_control"
    path.write_text("#!/bin/sh\n")
    return str(path)


@pytest.fixture
def setup(sys_root, paths, control):
    clock, run, alerts = Clock(), Recorder(), []
    g = guard.Guard(guard.Limits(), paths, sys_root, run, lambda title, body: alerts.append(body), clock, clock,
                    control)
    return g, clock, run, alerts


BOOST_OFF_SUFFIX = ["--boost", "off"]


# --- sensors -------------------------------------------------------------------------------------------------------

def test_reads_the_ps5(sys_root):
    r = guard.read_sensors(sys_root)
    assert (r.soc_c, r.cpu_c, r.gpu_c, r.board_c) == (55.656, 55.75, None, 45.25)
    assert r.hottest == ("CPU", 55.75)
    assert (r.fan.pwm, r.fan.duty, r.fan.mode, r.fan.mode_text) == (55, 22, 2, "the kernel's curve")
    assert r.fan.curve == tuple((c, round(100 * p / 255)) for c, p in CURVE)
    assert r.fan.curve[-1] == (87, 100)


def test_gpu_on_kernel_731(sys_root):
    set_temps(sys_root, gpu=70)
    r = guard.read_sensors(sys_root)
    assert r.gpu_c == 70.0 and r.hottest == ("GPU", 70.0)


def test_hwmon_numbers_do_not_matter(sys_root):
    hw = sys_root / "class/hwmon"
    (hw / "hwmon0").rename(hw / "hwmon7")
    assert guard.read_sensors(sys_root).soc_c == 55.656


def test_a_broken_reading_is_no_temperature(sys_root):
    set_temps(sys_root, soc=0, cpu=200)
    assert guard.read_sensors(sys_root).hottest is None


def test_no_fan_driver(sys_root):
    write(sys_root / FAN / "name", "something")
    r = guard.read_sensors(sys_root)
    assert r.fan is None and r.soc_c is None and r.hottest == ("CPU", 55.75)


@pytest.mark.parametrize("mode, pwm, text", [(0, 255, "full speed"), (1, 90, "manual 35 %"), (5, 1, "unknown mode")])
def test_mode_text(mode, pwm, text):
    assert guard.Fan(pwm, mode, "/x").mode_text == text


# --- limits --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("limits, ok", [
    (guard.Limits(), True),
    (guard.Limits(80, 88, 93, 10), True),
    (guard.Limits(90, 85, 95, 10), False),            # not rising
    (guard.Limits(85, 90, 90, 10), False),
    (guard.Limits(55, 90, 95, 10), False),            # below 60
    (guard.Limits(85, 90, 110, 10), False),           # above 105
    (guard.Limits(85, 90, 95, 1), False),             # hold too short
])
def test_limits_problem(limits, ok):
    assert (guard.limits_problem(limits) == "") is ok


def test_defaults_follow_the_kernel():
    assert guard.Limits() == guard.Limits(85, 88, 95, 10)


# --- the guard -----------------------------------------------------------------------------------------------------

def test_cool_ps5_does_nothing(setup, sys_root):
    g, _clock, run, alerts = setup
    g.step()
    assert alerts == [] and run.calls == [] and g.level() == "ok"
    assert fan(sys_root, "pwm1_enable") == "2"


def test_warns_once_and_rearms_5_below(setup, sys_root):
    g, _clock, run, alerts = setup
    set_temps(sys_root, soc=86)
    g.step()
    g.step()
    assert len(alerts) == 1 and "SoC is at 86 °C" in alerts[0] and g.level() == "warn"
    set_temps(sys_root, soc=81)
    g.step()
    assert g.level() == "warn"                         # 81 is not below 80
    set_temps(sys_root, soc=79)
    g.step()
    assert g.level() == "ok"
    set_temps(sys_root, soc=85)
    g.step()
    assert len(alerts) == 2
    assert run.calls == []


def test_cooling_turns_the_fan_full_and_the_boost_off_then_puts_the_fan_back(setup, sys_root, control):
    g, _clock, run, alerts = setup
    set_temps(sys_root, soc=89)
    g.step()
    assert g.level() == "cooling"
    assert fan(sys_root, "pwm1_enable") == "0"         # ps5_fan's full mode
    assert run.calls == [[control, *BOOST_OFF_SUFFIX]]
    assert "the fan to full speed and the CPU boost off" in alerts[-1]
    set_temps(sys_root, soc=85)
    g.step()
    assert g.level() == "cooling"                      # stays until below the warning's re-arm
    set_temps(sys_root, soc=79)
    g.step()
    assert g.level() == "ok"
    assert fan(sys_root, "pwm1_enable") == "2"         # the kernel's curve again
    assert run.calls == [[control, *BOOST_OFF_SUFFIX]]  # the boost is not turned back on
    assert "boost stays off" in g.events[-1]["text"]


def test_without_ps5_control_only_the_fan(sys_root, paths, tmp_path):
    run, alerts = Recorder(), []
    g = guard.Guard(guard.Limits(), paths, sys_root, run, lambda _t, b: alerts.append(b), Clock(), Clock(),
                    str(tmp_path / "missing"))
    set_temps(sys_root, soc=90)
    g.step()
    assert run.calls == [] and alerts[-1].endswith("the fan to full speed.")


def test_a_manual_duty_is_put_back(setup, sys_root):
    g, _clock, _run, _alerts = setup
    write(sys_root / FAN / "pwm1_enable", "1")
    write(sys_root / FAN / "pwm1", "150")
    set_temps(sys_root, soc=95)
    g.step()
    assert fan(sys_root, "pwm1_enable") == "0"
    g.stop()                                           # the service stops while it cools
    assert (fan(sys_root, "pwm1_enable"), fan(sys_root, "pwm1")) == ("1", "150")


def test_shutdown_after_the_hold(setup, sys_root):
    g, clock, run, alerts = setup
    set_temps(sys_root, soc=96)
    g.step()
    assert g.level() == "shutdown" and "shuts down in 10 s" in alerts[-1]
    clock.now += 9
    g.step()
    assert ["systemctl", "poweroff"] not in run.calls
    clock.now += 1
    g.step()
    g.step()
    assert run.calls.count(["systemctl", "poweroff"]) == 1
    assert "shutting down to protect the PS5" in alerts[-1]


def test_no_shutdown_when_it_cools_in_time(setup, sys_root):
    g, clock, run, _alerts = setup
    set_temps(sys_root, soc=96)
    g.step()
    clock.now += 5
    set_temps(sys_root, soc=93)
    g.step()
    clock.now += 20
    set_temps(sys_root, soc=96)
    g.step()                                           # the hold starts again
    assert ["systemctl", "poweroff"] not in run.calls
    assert "no shutdown" in g.events[-2]["text"]


def test_a_broken_sensor_never_shuts_down(setup, sys_root):
    g, clock, run, _alerts = setup
    set_temps(sys_root, soc=0, cpu=0)
    for _ in range(3):
        g.step()
        clock.now += 30
    assert ["systemctl", "poweroff"] not in run.calls
    assert sum("No SoC, CPU or GPU temperature" in e["text"] for e in g.events) == 1


def test_one_sensor_is_enough(setup, sys_root):
    g, _clock, _run, alerts = setup
    write(sys_root / FAN / "temp1_input", "garbage")
    set_temps(sys_root, cpu=87)
    g.step()
    assert "CPU is at 87 °C" in alerts[-1]


def test_state_file(setup, sys_root, paths):
    g, clock, _run, _alerts = setup
    set_temps(sys_root, soc=86)
    g.step()
    state = guard.read_state(paths, clock.now)
    assert state["level"] == "warn" and state["soc_c"] == 86.0
    assert state["fan"]["mode"] == 2 and state["limits"]["shutdown_c"] == 95
    assert guard.read_state(paths, clock.now + guard.STALE_S + 1) is None


def test_desktop_notification_per_user(tmp_path, monkeypatch):
    import pwd
    run = Recorder()
    for uid in ("1000", "0", "42"):
        write(tmp_path / "user" / uid / "bus", "")
    monkeypatch.setattr(pwd, "getpwuid", lambda uid: type("P", (), {"pw_name": f"user{uid}"})())
    guard.notify_desktop(run, "Title", "Body", tmp_path)
    assert len(run.calls) == 1
    call = run.calls[0]
    assert call[:4] == ["runuser", "-u", "user1000", "--"]
    assert f"DBUS_SESSION_BUS_ADDRESS=unix:path={tmp_path}/user/1000/bus" in call
    assert call[-2:] == ["Title", "Body"]


# --- install, uninstall, answers -----------------------------------------------------------------------------------

def test_install_and_uninstall(paths):
    run = Recorder()
    guard.install(paths, guard.Limits(80, 88, 93, 15), run)
    assert paths.script.read_bytes() == Path(guard.__file__).read_bytes()
    assert json.loads(paths.config.read_text()) == {"warn_c": 80, "cool_c": 88, "shutdown_c": 93, "hold_s": 15}
    unit = paths.unit.read_text()
    assert "ExecStart=/usr/bin/python3 -I /etc/ps5-fan-control/guard.py run" in unit
    assert "Restart=always" in unit and "WantedBy=multi-user.target" in unit
    assert ["systemctl", "enable", guard.UNIT] in run.calls and ["systemctl", "restart", guard.UNIT] in run.calls
    assert guard.installed(paths) == guard.Limits(80, 88, 93, 15)
    assert not guard.outdated(paths)
    guard.uninstall(paths, run)
    assert ["systemctl", "disable", "--now", guard.UNIT] in run.calls
    assert not paths.unit.exists() and not paths.folder.exists()
    assert guard.installed(paths) is None


def test_install_refuses_bad_limits(paths):
    with pytest.raises(ValueError):
        guard.install(paths, guard.Limits(95, 90, 85, 10), Recorder())
    assert not paths.script.exists()


def test_install_says_when_the_service_does_not_start(paths):
    with pytest.raises(ValueError, match="did not start"):
        guard.install(paths, guard.Limits(), Recorder({"restart": guard.Result(1, "failed\n")}))


def test_broken_config_means_defaults(paths):
    guard.install(paths, guard.Limits(80, 88, 93, 15), Recorder())
    paths.config.write_text("{broken")
    assert guard.read_limits(paths) is None
    assert guard.installed(paths) == guard.Limits()


def test_outdated(paths, tmp_path):
    guard.install(paths, guard.Limits(), Recorder())
    other = tmp_path / "other.py"
    other.write_text("# another version\n")
    assert guard.outdated(paths, other)


def test_main_install_prints_an_answer(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PS5_SYSTEM_ROOT", str(tmp_path))
    monkeypatch.setattr(guard, "run", Recorder())
    monkeypatch.setattr(guard.install, "__defaults__", (guard.run, Path(guard.__file__)))
    assert guard.main(["install", "--warn", "80", "--cool", "85", "--shutdown", "90", "--hold", "5"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True}
    assert guard.installed(guard.paths_from_env()) == guard.Limits(80, 85, 90, 5)
    assert guard.main(["install", "--warn", "99"]) == 1
    assert "rise" in json.loads(capsys.readouterr().out)["error"]


def test_command_and_answer():
    cmd = guard.command(["uninstall"])
    assert cmd[0] == "pkexec" and cmd[2] == "-I" and cmd[3].endswith("guard.py") and cmd[-1] == "uninstall"
    assert guard.answer(0, '{"ok": true}\n') == ""
    assert guard.answer(1, 'noise\n{"ok": false, "error": "nope"}\n') == "nope"
    assert "canceled" in guard.answer(126, "")
    assert "without an answer" in guard.answer(1, "Traceback")
