# SPDX-License-Identifier: GPL-3.0-or-later
"""The window on folders made in a temp folder, built as shadPS4 Manager's: the states before and after installing,
the board check, the games in the table, installing through the worker, Steam's shortcuts changed with a fake "close
Steam", the GPU helper as an option, Start game, Games Uninstall, the controller and Steam states and the log."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

from conftest import make_game, make_sys
from test_emulator import RELEASE, archive

from bazzite_console_core import steam
from bazzite_console_core.theme import GREEN, RED
from bazzite_console_core.updates import ReleaseInfo
from bazzite_console_core.widgets import Pill
from kytyps5_manager import APP_ID, INFO, LOGO_PATH, ROOT, __version__, emulator, shortcuts, style
from kytyps5_manager.main_window import HEIGHT, WIDTH, MainWindow


@pytest.fixture
def folders(tmp_path):
    games = tmp_path / "Games" / "PS5"                                         # the app's own folder
    make_game(games / "one", "One", "PPSA00001")
    make_game(games / "two", "Two", "PPSA00002")
    (tmp_path / "Steam" / "userdata" / "1000" / "config").mkdir(parents=True)
    run = tmp_path / "bin" / "ps5-kytyps5-run"
    run.parent.mkdir()
    run.write_text("#!/bin/sh\n")
    log = tmp_path / "data" / APP_ID / f"{APP_ID}.log"
    log.parent.mkdir(parents=True)
    return {"home": tmp_path / "emulator", "steam_dir": tmp_path / "Steam", "run": run, "log_path": log,
            "user_home": tmp_path, "drives": lambda: [], "sys_root": make_sys(tmp_path / "sys"),
            "helper_unit": tmp_path / "etc" / "kyty-lodhw.service"}


def _install(home: Path) -> None:
    (home / emulator.VERSION).mkdir(parents=True)
    (home / emulator.VERSION / emulator.MEMBER).write_text("")
    (home / emulator.VERSION / emulator.HELPER_INSTALL).write_text("")
    (home / "current").symlink_to(emulator.VERSION)


def _wait(window, qapp) -> None:
    deadline = time.monotonic() + 10
    while window.worker.running and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()


def _window(folders, **kwargs) -> MainWindow:
    closed = kwargs.pop("closed", [])
    kwargs.setdefault("newer_release", lambda: None)                         # never GitHub in a test
    kwargs.setdefault("kyty_running", lambda: False)
    kwargs.setdefault("devices", folders["home"].parent / "no-devices")       # no controller, no file
    kwargs.setdefault("open_url", lambda url: True)
    kwargs.setdefault("helper_run", lambda script, remove: (_ for _ in ()).throw(AssertionError("root asked")))
    kwargs.setdefault("covers_key", folders["home"].parent / "no-key")
    kwargs.setdefault("covers_home", folders["home"].parent / "covers")
    # Start game: Steam takes the address at once and the game runs (never the real Steam in a test)
    kwargs.setdefault("steam_play", lambda url, open_url, started: steam.play(
        url, open_url, lambda: True, ready=lambda: True, sleep=lambda seconds: None))
    return MainWindow(**folders, steam_closed=lambda change: (closed.append(1), change())[0] and False,
                      steam_running=lambda: False, **kwargs)


def _yes(monkeypatch, asked: list | None = None) -> None:
    def question(parent, title, text, *args, **kwargs):
        if asked is not None:
            asked.append(text)
        return QMessageBox.StandardButton.Yes
    monkeypatch.setattr(QMessageBox, "question", question)


def test_version_is_the_single_source():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == __version__ == INFO.version


def test_icons_are_beside_the_package():
    assert LOGO_PATH.is_file() and LOGO_PATH.name == f"{APP_ID}.webp"
    assert (ROOT / "images" / f"{APP_ID}-128.png").is_file()


def test_before_installing(qapp, folders):
    window = _window(folders)
    assert window.pill.text() == "Not installed"
    assert window.emulator_state.text() == "Not installed. Install it with the Install button."
    assert emulator.VERSION in window.emulator_state.toolTip() and "checks it" in window.emulator_state.toolTip()
    assert window.emulator_box.value.text() == "—" and window.version_state.text() == "—"
    assert window.install_pill.isEnabled() and not window.remove_pill.isEnabled()
    assert not window.kyty_button.isEnabled() and not window.helper_pill.isEnabled()
    assert not window.exit_button.isEnabled() and not window.steam_button.isEnabled()
    assert [window.table.item(row, 1).text() for row in range(window.table.rowCount())] == ["One", "Two"]
    assert [window.table.item(0, column).text() for column in range(2, 5)] == ["PPSA00001", "01.000.000", "one"]
    assert window.folders_state.text().endswith("Games/PS5</b>")
    window.close()


def test_installed_with_games(qapp, folders):
    _install(folders["home"])
    window = _window(folders)
    assert window.pill.text() == "Ready"
    assert window.emulator_state.text() == "Installed. Uninstall with the Uninstall button."
    assert window.emulator_box.value.text() == emulator.VERSION[:10]
    assert window.version_state.text() == emulator.VERSION
    assert not window.install_pill.isEnabled() and window.remove_pill.isEnabled()      # installed: not again
    assert window.kyty_button.isEnabled() and window.helper_pill.isEnabled()
    assert window.steam_box.value.text() == "0"
    window.close()


def test_the_board_is_read_and_never_set(qapp, folders, tmp_path):
    _install(folders["home"])
    window = _window(folders)
    assert window.board_state.text() == f"<b style='color:{GREEN};'>Ok</b>" and window.board_box.value.text() == "Ok"
    text = window.board_info.text_
    assert "VRAM split: 512 MB, asked 512 MB (ok)" in text and "GTT limit: 14336 MiB, asked 14336 MiB (ok)" in text
    assert "sched_policy=2 vm_update_mode=0 cwsr_enable=0, asked sched_policy=2" in text
    assert "The app only reads them" in text and "for the AMD BC-250" in text and "apps/kytyps5/" in text
    window.close()
    stock = {**folders, "sys_root": make_sys(tmp_path / "stock", vram_mib=6144, gtt_mib=11776,
                                             options={"sched_policy": 0, "vm_update_mode": 3, "cwsr_enable": 1})}
    window = _window(stock)
    assert window.board_state.text() == f"<b style='color:{RED};'>Not as KytyPS5-Native asks</b>"
    assert window.board_box.value.text() == "3 to set" and window.pill.text() == "Check the board"
    assert "VRAM split: 6144 MB, asked 512 MB (to set)" in window.board_info.text_
    assert "sched_policy=0 vm_update_mode=3 cwsr_enable=1" in window.board_info.text_
    window.close()
    none = {**folders, "sys_root": tmp_path / "no-sys"}
    window = _window(none)
    assert window.board_state.text() == "Not read" and window.board_box.value.text() == "—"
    window.close()


def test_install_runs_off_the_window_and_uninstall_asks(qapp, folders, monkeypatch):
    payload = archive(RELEASE)
    monkeypatch.setattr(emulator, "SHA256", hashlib.sha256(payload).hexdigest())
    asked: list[str] = []
    _yes(monkeypatch, asked)
    window = _window(folders, fetch=lambda url, dest, progress=None: dest.write_bytes(payload))
    window.on_install()
    assert asked[0].startswith(f"Download KytyPS5-Native {emulator.VERSION} from GitHub (about 41 MB)?")
    assert not window.install_pill.isEnabled() and not window.refresh_pill.isEnabled()        # busy
    _wait(window, qapp)
    assert window.running.text() == f"KytyPS5-Native {emulator.VERSION} is installed."
    assert window.version == emulator.VERSION and window.pill.text() == "Ready" and window.refresh_pill.isEnabled()
    window.on_remove()
    assert asked[-1].startswith("Remove the installed KytyPS5-Native?") and "saves and settings, stay" in asked[-1]
    assert window.version == "" and window.running.text() == "KytyPS5-Native was removed."
    window.close()


def test_a_failed_install_is_said(qapp, folders, monkeypatch):
    _yes(monkeypatch)
    window = _window(folders, fetch=lambda url, dest, progress=None: dest.write_bytes(b"other"))
    window.on_install()
    _wait(window, qapp)
    assert window.running.text().startswith("KytyPS5-Native was not installed:") and window.version == ""
    assert "c62828" in window.running.styleSheet()
    window.close()


def test_steam_added_and_taken_out(qapp, folders, monkeypatch):
    _install(folders["home"])
    _yes(monkeypatch)
    closed = []
    window = _window(folders, closed=closed)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    assert window.steam_button.isEnabled()
    add, remove = window.steam_plan()
    assert [g.title for g in add] == ["One"] and remove == []
    window.on_update_steam()
    _wait(window, qapp)
    assert closed == [1] and window.running.text().startswith("1 game(s) in Steam")
    assert list(shortcuts.in_steam(folders["steam_dir"]).values()) == ["[PS5] One"]
    item = next(i for i in steam.shortcuts(folders["steam_dir"]) if shortcuts.ours(i))
    assert steam.field(item, "LaunchOptions") == f'--fullscreen --game "{folders["user_home"] / "Games/PS5/one"}"'
    assert window.steam_box.value.text() == "1" and window.table.item(0, 0).toolTip() == "In Steam"
    assert not window.steam_button.isEnabled()                              # nothing to change now
    window.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    window.on_update_steam()
    _wait(window, qapp)
    assert shortcuts.in_steam(folders["steam_dir"]) == {} and "1 taken out" in window.running.text()
    window.close()


def test_update_steam_needs_the_emulator_and_the_wrapper(qapp, folders, monkeypatch):
    _yes(monkeypatch)
    window = _window(folders)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    assert window.running.text() == "Install KytyPS5-Native first: the games in Steam start it."
    folders["run"].unlink()
    window.on_update_steam()
    assert "which is not there" in window.running.text() and "through the portal" in window.running.text()
    window.close()


def test_the_gpu_helper_is_an_option(qapp, folders, monkeypatch):
    """Owner, 27-11-2026: the app changes nothing on the board by itself. The pill asks first, says what the helper
    does and that a password is asked, and runs the emulator's own script as root only after a yes."""
    _install(folders["home"])
    asked: list[str] = []
    answers = [QMessageBox.StandardButton.No]
    monkeypatch.setattr(QMessageBox, "question",
                        lambda parent, title, text, *a, **k: (asked.append(text), answers[-1])[1])
    calls: list[tuple[Path, bool]] = []

    def run(script: Path, remove: bool) -> tuple[int, str]:
        calls.append((script, remove))
        if remove:
            folders["helper_unit"].unlink()
        else:
            folders["helper_unit"].parent.mkdir(exist_ok=True)
            folders["helper_unit"].write_text("[Unit]\n")
        return 0, ""
    window = _window(folders, helper_run=run)
    assert window.helper_state.text() == "Not installed. The emulator runs without it."
    assert window.helper_pill.caption.text() == "Install"
    window.on_helper()
    assert calls == [] and asked[0].startswith("Install the GPU helper?")              # No: nothing ran
    assert asked[0].rstrip().endswith("You are asked for your password.")
    answers.append(QMessageBox.StandardButton.Yes)
    window.on_helper()
    _wait(window, qapp)
    assert calls == [(folders["home"] / "current" / "install-helper.sh", False)]
    assert window.running.text() == "The GPU helper is installed and runs."
    assert window.helper_state.text() == "Installed" and window.helper_pill.caption.text() == "Uninstall"
    window.on_helper()
    _wait(window, qapp)
    assert asked[-1].startswith("Uninstall the GPU helper?") and calls[-1][1] is True
    assert window.running.text() == "The GPU helper was uninstalled."
    window.helper_run = lambda script, remove: (126, "")
    window.on_helper()
    _wait(window, qapp)
    assert window.running.text() == "The GPU helper was not changed: no password was given."
    window.helper_run = lambda script, remove: (1, "systemctl failed")
    window.on_helper()
    _wait(window, qapp)
    assert window.running.text() == "The GPU helper was not changed: systemctl failed"
    window.close()


def test_the_helper_script_runs_through_polkit_with_the_users_group(monkeypatch, tmp_path):
    import os
    import subprocess
    from kytyps5_manager import main_window
    seen = []

    def fake(command, **kwargs):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, "out", "err")
    monkeypatch.setattr(subprocess, "run", fake)
    assert main_window.run_helper(tmp_path / "install-helper.sh", True) == (0, "outerr")
    assert seen == [["pkexec", "/usr/bin/env", f"SUDO_GID={os.getgid()}", "/bin/sh",
                     str(tmp_path / "install-helper.sh"), "--remove"]]


def test_start_game_starts_the_chosen_game_through_steam(qapp, folders, monkeypatch):
    _install(folders["home"])
    _yes(monkeypatch)
    opened: list[str] = []
    window = _window(folders, open_url=lambda url: (opened.append(url), True)[1])
    window.on_start_game()
    assert window.running.text().startswith("Choose a game under Your games first")
    window.table.selectRow(0)
    window.on_start_game()
    assert window.running.text() == "One is not in Steam yet: check it and press Update Steam first."
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    _wait(window, qapp)
    window.table.selectRow(0)
    window.on_start_game()
    _wait(window, qapp)
    number = steam.shortcut_number(folders["steam_dir"], shortcuts.for_game(window.games[0]))
    assert opened == [steam.play_url(number)] and window.running.text() == "One runs, started through Steam."
    window.kyty_running = lambda: True
    window.on_start_game()
    assert window.running.text() == "KytyPS5-Native is running. Close it first, then start the game."
    window.close()


def test_games_uninstall_asks_what_to_keep(qapp, folders, monkeypatch, tmp_path):
    from bazzite_console_core.keep_dialog import KeepDialog
    window = _window(folders)
    assert not window.remove_game_pill.isEnabled()                            # nothing chosen yet
    window.table.selectRow(0)
    assert window.chosen().title == "One" and window.remove_game_pill.isEnabled()
    target = tmp_path / "Games" / "PS5" / "one"
    seen = []
    monkeypatch.setattr(KeepDialog, "exec", lambda self: (seen.append(self.items), QDialog.DialogCode.Rejected)[1])
    window.on_remove_game()
    assert [item.label for item in seen[0]] == ["one (the game's folder)"] and target.exists()
    assert window.running.text() == "Nothing was deleted."
    monkeypatch.setattr(KeepDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.on_remove_game()
    _wait(window, qapp)
    assert not target.exists() and window.running.text() == "One: deleted one (the game's folder)."
    assert [window.table.item(r, 1).text() for r in range(window.table.rowCount())] == ["Two"]
    window.close()


def test_exit_kytyps5_is_on_while_it_runs_and_ends_it_at_once(qapp, folders):
    runs = [True]
    ended: list[int] = []

    def end() -> list[int]:
        ended.append(1)
        runs[0] = False
        return [10]
    window = _window(folders, kyty_running=lambda: runs[0], kyty_end=end)
    assert window.exit_button.text() == "Exit KytyPS5" and window.exit_button.isEnabled()
    window.exit_button.click()
    assert ended == [1] and window.running.text() == "KytyPS5-Native was ended."
    assert not window.exit_button.isEnabled()
    window.kyty_end = lambda: []
    window.on_exit_kyty()
    assert window.running.text() == "KytyPS5-Native was not running."
    window.close()


def test_nothing_of_the_emulator_is_changed_while_it_runs(qapp, folders, monkeypatch):
    _install(folders["home"])
    _yes(monkeypatch)
    window = _window(folders, kyty_running=lambda: True)
    window.on_remove()
    assert window.version == emulator.VERSION and "Close it first" in window.running.text()
    window.on_helper()
    assert window.running.text() == "KytyPS5-Native is running. Close it first, then change the GPU helper."
    window.table.selectRow(0)
    window.on_remove_game()
    assert window.running.text() == "KytyPS5-Native is running. Close it first, then remove the game."
    window.close()


def test_kytyps5s_own_window_opens_through_the_wrapper(qapp, folders):
    _install(folders["home"])
    window = _window(folders)
    assert window.kyty_command("--launcher") == [str(folders["run"]), "--launcher"]
    folders["run"].unlink()
    assert window.kyty_command("--launcher") == [str(ROOT / "ps5-kytyps5-run"), "--launcher"]
    window.close()


def test_the_controller_and_steam_states(qapp, folders, tmp_path, monkeypatch):
    devices = tmp_path / "devices"
    devices.write_text('I: Bus=0003 Vendor=054c Product=0ce6 Version=8111\nN: Name="DualSense"\n'
                       "H: Handlers=event3 js0\n")
    monkeypatch.setattr(steam, "signed_in", lambda folder: False)
    window = _window(folders, devices=devices)
    assert window.controller.text() == "Controller connected" and "DualSense" in window.controller.toolTip()
    assert window.steam_state.text() == "Steam not signed in"
    devices.write_text("")
    monkeypatch.setattr(steam, "signed_in", lambda folder: True)
    window.show_controller()
    window.show_steam()
    assert window.controller.text() == "No controller" and window.steam_state.text() == "Steam signed in"
    window.close()


def test_a_newer_release_is_mentioned_in_the_tip_and_the_log(qapp, folders):
    newer = ReleaseInfo(version="x", tag="KytyPS5-Native-2099-01-01-abcdef0", published="2099-01-01",
                        url="https://example.invalid/r")
    window = _window(folders, newer_release=lambda: newer)
    deadline = time.monotonic() + 10
    while window.newer is None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert "KytyPS5-Native-2099-01-01-abcdef0 is out (2099-01-01)" in window.emulator_state.toolTip()
    assert "is out (2099-01-01)" in window.log_page.output.toPlainText()
    assert window.emulator_state.text() == "Not installed. Install it with the Install button."    # the state stays
    window.close()


def test_the_log_tab_and_clear_logs(qapp, folders):
    window = _window(folders)
    window.say("Something happened.")
    assert "INFO Something happened." in window.log_page.output.toPlainText()
    window.say("Something failed.", ok=False)
    assert "ERROR Something failed." in window.log_page.output.toPlainText()
    window.on_clear_logs()
    assert window.log_page.output.toPlainText() == "" and window.running.text() == "The log was cleared."
    window.close()


def test_the_layout_follows_shadps4_managers(qapp, folders):
    """The icon and the title, four pills in the header, four in the row under it, the state lines, the tabs."""
    window = _window(folders)
    window.show()
    assert (window.width(), window.height()) == (WIDTH, HEIGHT) and window.minimumWidth() == WIDTH
    assert [(p.value.text(), p.caption.text()) for p in window.header_pills] == [
        ("—", "KytyPS5 version"), ("KytyPS5", "Install"), ("KytyPS5", "Uninstall"), ("Refresh", "Click to refresh")]
    assert [(p.value.text(), p.caption.text()) for p in window.second_row] == [
        ("Games", "Uninstall"), ("0", "Available in Steam"), ("Ok", "Board settings"), ("GPU helper", "Install")]
    assert all(isinstance(p, Pill) for p in (window.install_pill, window.remove_pill, window.refresh_pill,
                                             window.remove_game_pill, window.helper_pill))    # actions are pills
    assert [window.tabs.tabText(n) for n in range(window.tabs.count())] == ["Your games", "Start game", "View logs",
                                                                           "Clear logs"]
    assert style.BLUE in window.styleSheet()
    window.close()
