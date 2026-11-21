# SPDX-License-Identifier: GPL-3.0-or-later
"""system.py, the part that runs as root, on a folder of its own: each change writes only its own file (and, for a
new cmdline.txt, a backup of the old one beside it), and its off undoes it."""

from __future__ import annotations

import pytest

from quickfix import system

@pytest.fixture
def ran(monkeypatch):
    calls = []
    monkeypatch.setattr(system, "run", lambda argv: calls.append(argv) or 0)
    return calls


def test_mapcount_on_and_off(tmp_path, ran):
    system.main(["mapcount", "on"], etc=tmp_path)
    conf = tmp_path / system.MAPCOUNT_CONF
    assert f"vm.max_map_count = {system.MAPCOUNT}" in conf.read_text()
    system.main(["mapcount", "off"], etc=tmp_path)
    assert not conf.exists()
    assert ran == [["sysctl", "-w", f"vm.max_map_count={system.MAPCOUNT}"], ["sysctl", "--system"]]


def test_journal_on_and_off_only_its_own(tmp_path, ran):
    folder = tmp_path / system.JOURNAL_DIR
    assert system.main(["journal", "on"], var=tmp_path) == 0
    assert (folder / system.JOURNAL_MARK).is_file()
    assert ran == [["systemd-tmpfiles", "--create", "--prefix", str(folder)], ["journalctl", "--flush"]]
    assert system.main(["journal", "off"], var=tmp_path) == 0 and not folder.exists()
    folder.mkdir(parents=True)                                  # the system's own folder
    assert system.main(["journal", "off"], var=tmp_path) == 1 and folder.is_dir()


def test_ethernet_on_and_off(tmp_path, ran):
    etc, var = tmp_path / "etc", tmp_path / "var"
    hook, units = etc / system.ETHERNET_HOOK, etc / "systemd" / "system"
    timer = f"{system.ETHERNET_UNIT}.timer"
    assert system.main(["ethernet", "on"], etc=etc, var=var) == 0
    assert hook.stat().st_mode & 0o777 == 0o755 and "nmcli radio wifi off" in hook.read_text()
    assert f"ExecStart=/etc/{system.ETHERNET_HOOK} - check" in (units / f"{system.ETHERNET_UNIT}.service").read_text()
    assert "OnBootSec=45s" in (units / timer).read_text()
    assert ran == [["systemctl", "daemon-reload"], ["systemctl", "enable", timer], [str(hook), "-", "check"]]
    ran.clear()
    mark = var / system.ETHERNET_MARK                           # the hook keeps the Wi-Fi off for the cable
    mark.parent.mkdir(parents=True)
    mark.touch()
    assert system.main(["ethernet", "off"], etc=etc, var=var) == 0
    assert not hook.exists() and not list(units.iterdir()) and not mark.exists()
    assert ran == [["systemctl", "disable", "--now", timer], ["systemctl", "daemon-reload"],
                   ["nmcli", "radio", "wifi", "on"]]


def test_ethernet_off_leaves_a_wifi_it_did_not_turn_off(tmp_path, ran):
    assert system.main(["ethernet", "off"], etc=tmp_path / "etc", var=tmp_path / "var") == 0
    assert ["nmcli", "radio", "wifi", "on"] not in ran


def test_the_command_and_its_answer(tmp_path):
    argv = system.command(["mapcount", "on"], own=tmp_path / "system.py")
    assert argv[0] == "pkexec" and argv[2] == "-I" and argv[-3:] == [str(tmp_path / "system.py"), "mapcount", "on"]
    assert system.answer(0, "anything") == ""
    assert "canceled" in system.answer(126, "") and "canceled" in system.answer(127, "")
    assert system.answer(1, "it broke\n") == "it broke"


LINE = "root=UUID=1234 rw quiet mitigations=off ttm.pages_limit=3014656\n"


def test_cmdline_save_keeps_a_backup(tmp_path, capsys):
    boot = tmp_path / "boot"
    target = boot / system.CMDLINE
    target.parent.mkdir(parents=True)
    target.write_text(LINE)
    source = tmp_path / "new.txt"
    source.write_text("  root=UUID=1234 rw quiet amd_iommu=off  \n\n")
    assert system.main(["cmdline", "save", "--text", str(source)], boot=boot) == 0
    assert target.read_text() == "root=UUID=1234 rw quiet amd_iommu=off\n"
    backups = list(target.parent.glob("cmdline.txt.bak-*"))
    assert len(backups) == 1 and backups[0].read_text() == LINE
    assert "systemctl reboot" in capsys.readouterr().out
    assert system.main(["cmdline", "show"], boot=boot) == 0 and capsys.readouterr().out == target.read_text()


@pytest.mark.parametrize("text, message", [
    ("rw quiet\n", "no root="),
    ("root=UUID=1 rw\nquiet\n", "one line"),
    ("\n", "empty"),
])
def test_cmdline_refuses_a_line_that_would_not_boot(tmp_path, capsys, text, message):
    boot = tmp_path / "boot"
    (boot / "efi").mkdir(parents=True)
    (boot / system.CMDLINE).write_text(LINE)
    source = tmp_path / "new.txt"
    source.write_text(text)
    assert system.main(["cmdline", "save", "--text", str(source)], boot=boot) == 1
    assert message in capsys.readouterr().out and (boot / system.CMDLINE).read_text() == LINE
    assert not list((boot / "efi").glob("*.bak-*"))


def test_cmdline_saves_a_fallback_line(tmp_path, capsys):
    boot = tmp_path / "boot"
    usb = boot / "efi" / "cmdline.txt.usb"
    usb.parent.mkdir(parents=True)
    usb.write_text(LINE)
    (boot / system.CMDLINE).write_text("root=LABEL=bazzite rw\n")
    source = tmp_path / "new.txt"
    source.write_text("root=UUID=1234 rw rootwait\n")
    assert system.main(["cmdline", "save", "--text", str(source), "--file", "cmdline.txt.usb"], boot=boot) == 0
    assert usb.read_text() == "root=UUID=1234 rw rootwait\n" and "copied over cmdline.txt" in capsys.readouterr().out
    assert (boot / system.CMDLINE).read_text() == "root=LABEL=bazzite rw\n"
    assert [p.name[:len("cmdline.txt.usb.bak-")] for p in usb.parent.glob("*.bak-*")] == ["cmdline.txt.usb.bak-"]
    assert system.main(["cmdline", "show", "--file", "cmdline.txt.usb"], boot=boot) == 0
    assert capsys.readouterr().out == usb.read_text()
    with pytest.raises(SystemExit):                     # only the loader's command lines
        system.main(["cmdline", "show", "--file", "../../etc/shadow"], boot=boot)


def test_cmdline_without_the_loaders_partition(tmp_path, capsys):
    source = tmp_path / "new.txt"
    source.write_text(LINE)
    assert system.main(["cmdline", "save", "--text", str(source)], boot=tmp_path / "boot") == 1
    assert "mounted" in capsys.readouterr().out
    assert system.main(["cmdline", "show"], boot=tmp_path / "boot") == 1


@pytest.mark.parametrize("argv", [["cmdline", "on"], ["mapcount", "show"], ["ethernet", "show"], ["cmdline", "save"]])
def test_the_changes_take_only_their_own_states(argv):
    with pytest.raises(SystemExit):
        system.main(argv)
