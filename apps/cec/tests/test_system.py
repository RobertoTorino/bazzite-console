# SPDX-License-Identifier: GPL-3.0-or-later
"""system.py, the power button's part that runs as root, on a folder of its own: on writes the standby unit, its
script and the login screen's setting, and adds the user to the input group; off removes the three."""

from __future__ import annotations

import pytest

from cec_manager import system


@pytest.fixture
def ran(monkeypatch):
    calls = []
    monkeypatch.setattr(system, "run", lambda argv: calls.append(argv) or 0)
    return calls


def test_on_and_off(tmp_path, ran, monkeypatch):
    monkeypatch.setattr(system, "in_group", lambda user, group: False)
    monkeypatch.setattr(system.pwd, "getpwnam", lambda user: None)
    assert system.main(["power-button", "on", "player"], etc=tmp_path) == 0
    script, unit = tmp_path / system.STANDBY_SCRIPT, tmp_path / "systemd/system" / system.STANDBY_UNIT
    assert script.stat().st_mode & 0o777 == 0o755 and "orange_breathe" in script.read_text()
    assert f"ExecStart=/etc/{system.STANDBY_SCRIPT} on" in unit.read_text()
    assert "WantedBy=sleep.target" in unit.read_text()
    assert "HandlePowerKey=ignore" in (tmp_path / system.LOGIND_CONF).read_text()
    assert ran == [["systemctl", "daemon-reload"], ["systemctl", "enable", system.STANDBY_UNIT],
                   ["usermod", "-aG", "input", "player"]]
    ran.clear()
    assert system.main(["power-button", "off"], etc=tmp_path) == 0
    assert not script.exists() and not script.parent.exists() and not unit.exists()
    assert not (tmp_path / system.LOGIND_CONF).exists()
    assert ran == [["systemctl", "disable", system.STANDBY_UNIT], ["systemctl", "daemon-reload"]]


def test_a_user_in_the_input_group_stays_as_it_is(tmp_path, ran, monkeypatch):
    monkeypatch.setattr(system, "in_group", lambda user, group: True)
    monkeypatch.setattr(system.pwd, "getpwnam", lambda user: None)
    assert system.main(["power-button", "on", "player"], etc=tmp_path) == 0
    assert not any(argv[0] == "usermod" for argv in ran)


def test_on_needs_an_existing_user(tmp_path, ran):
    with pytest.raises(SystemExit):
        system.main(["power-button", "on", "no-such-user-here"], etc=tmp_path)
    with pytest.raises(SystemExit):
        system.main(["power-button", "on"], etc=tmp_path)
    assert ran == []


def test_the_command_and_its_answer():
    argv = system.command(["power-button", "off"])
    assert argv[0] == "pkexec" and argv[2] == "-I" and argv[-2:] == ["power-button", "off"]
    assert system.answer(126, "") and system.answer(0, "anything") == ""
