# SPDX-License-Identifier: GPL-3.0-or-later
"""The window on folders made in a temp folder: the states before and after installing, the games in the table, the
game folders, the plan for Steam, installing through the worker, Steam's shortcuts changed with a fake "close
Steam", the Settings and Log tabs, and the blue look of PS5 RPCS3 Manager's design."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMessageBox

from conftest import make_disc, make_memstick, make_pbp

from bazzite_console_core import processes, steam
from ppsspp_manager import LOGO_PATH, emulator, shortcuts, style
from ppsspp_manager.games import Game, memstick_game
from ppsspp_manager.main_window import MainWindow


@pytest.fixture
def folders(tmp_path):
    memstick = make_memstick(tmp_path / "ppsspp")
    make_pbp(memstick_game(memstick) / "HOMEBREW", "Two")
    make_disc(tmp_path / "Games" / "PSP" / "one.iso", "One", "ULUS00001")       # the app's own folder
    config = tmp_path / "Steam" / "userdata" / "1000" / "config"
    config.mkdir(parents=True)
    run = tmp_path / "bin" / "ps5-ppsspp-run"
    run.parent.mkdir()
    run.write_text("#!/bin/sh\n")
    log = tmp_path / "data" / "ps5-ppsspp-manager" / "ps5-ppsspp-manager.log"
    log.parent.mkdir(parents=True)
    return {"home": tmp_path / "emulator", "memstick": memstick, "steam_dir": tmp_path / "Steam", "run": run,
            "log_path": log, "user_home": tmp_path, "drives": lambda: []}


def _install(home: Path) -> None:
    (home / emulator.VERSION).mkdir(parents=True)
    (home / emulator.VERSION / emulator.MEMBER).write_text("")
    (home / "current").symlink_to(emulator.VERSION)


def _wait(window, qapp) -> None:
    deadline = time.monotonic() + 10
    while window.worker.running and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()


def _window(folders, **kwargs) -> MainWindow:
    closed = kwargs.pop("closed", [])
    kwargs.setdefault("devices", folders["user_home"] / "no-devices")         # no controller, no file
    kwargs.setdefault("newer_release", lambda: None)                         # never GitHub in a test
    kwargs.setdefault("ppsspp_running", lambda: False)
    # Start game: Steam takes the address at once and the game runs (never the real Steam in a test)
    kwargs.setdefault("steam_play", lambda url, open_url, started: steam.play(
        url, open_url, lambda: True, ready=lambda: True, sleep=lambda seconds: None))
    return MainWindow(**folders, steam_closed=lambda change: (closed.append(1), change())[0] and False,
                      steam_running=lambda: False, **kwargs)


def test_ppsspp_is_set_up_once_installed(qapp, folders):
    """Once PPSSPP is installed, and while it does not run, the app turns its notice of a newer release off in
    ppsspp.ini (owner, 03-11-2026); the Log tab says so once, and nothing is written while PPSSPP runs."""
    ini = folders["memstick"] / "PSP" / "SYSTEM" / "ppsspp.ini"
    window = _window(folders)
    assert ini.read_text() == "[General]\n"                                           # not installed: left alone
    window.close()
    _install(folders["home"])
    running = [True]
    window = _window(folders, ppsspp_running=lambda: running[0])
    assert ini.read_text() == "[General]\n"                                           # PPSSPP runs: left alone
    running[0] = False
    window.refresh()
    assert ini.read_text() == "[General]\nCheckForNewVersion = False\n"
    assert window.output.toPlainText().splitlines()[-1].endswith(" INFO PPSSPP set up: its notice of a newer release off.")
    lines = len(window.output.toPlainText().splitlines())
    window.refresh()
    assert len(window.output.toPlainText().splitlines()) == lines                      # said once
    window.close()


def test_no_user_name_on_the_screen(qapp, folders, tmp_path, monkeypatch):
    """The user's folders show as ~ (owner, 03-11-2026: the privacy rule): the memory stick and the game folders on
    the first step, and a message with a path in it."""
    monkeypatch.setenv("HOME", str(tmp_path))
    window = _window(folders)
    assert window.folders_state.text() == "<b>~/Games/PSP</b>"
    assert window.folders_state.toolTip() == "~/Games/PSP\n1 game(s) on PPSSPP's memory stick, ~/ppsspp/PSP/GAME."
    assert str(tmp_path) not in window.folders_info.text_
    window._job_done((False, f"PPSSPP could not be installed: {tmp_path}/emulator is read-only"))
    assert window.running.text() == "PPSSPP could not be installed: ~/emulator is read-only"
    window.close()


def test_before_installing(qapp, folders):
    window = _window(folders)
    assert window.pill.text() == "Not installed"
    # The state alone, in the words every manager uses (owner, 07-11-2026); what Install does in the tip.
    assert window.emulator_state.text() == "Not installed. Install it with the Install button."
    assert f"Install downloads PPSSPP {emulator.VERSION}" in window.emulator_state.toolTip()
    assert window.install_pill.isEnabled() and not window.remove_pill.isEnabled()
    assert not window.ppsspp_button.isEnabled()
    for name in ("folder_button", "forget_button"):
        assert not hasattr(window, name), name                               # gone (owner, 03-11-2026): fixed folders
    assert [window.table.item(r, 1).text() for r in range(window.table.rowCount())] == ["One", "Two"]   # Games/PSP and the memory stick
    window.close()


def test_installed_with_games(qapp, folders):
    _install(folders["home"])
    window = _window(folders)
    assert window.pill.text() == "Ready" and window.emulator_box.value.text() == emulator.VERSION
    assert window.table.rowCount() == 2 and window.steam_box.value.text() == "0"
    assert window.emulator_state.text() == "Installed. Uninstall with the Uninstall button."
    assert window.emulator_state.toolTip() == f"PPSSPP {emulator.VERSION}, the release this version of the app was tried with"
    assert not window.install_pill.isEnabled() and window.remove_pill.isEnabled()
    assert not hasattr(window, "play_button")                   # a game is started from Steam (owner, 07-11-2026)
    assert not window.remove_game_pill.isEnabled()                            # nothing chosen yet
    window.table.selectRow(0)
    assert window.remove_game_pill.isEnabled() and window.chosen().title == "One"
    assert not window.steam_button.isEnabled()                                  # nothing to change
    assert window.table.item(0, 3).text() == "ISO" and window.table.item(1, 3).text() == "Memory Stick"
    window.close()


def test_the_apps_own_game_folders(qapp, folders, tmp_path, monkeypatch):
    """The games are put in Games/PSP in the home folder, made when the app opens, and in Games/PSP on a
    removable drive that has one (owner, 03-11-2026: fixed folders, no folder choosing); no folder is chosen or
    remembered any more."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _install(folders["home"])
    (tmp_path / "sd" / "Games" / "PSP").mkdir(parents=True)
    (tmp_path / "stick").mkdir()                                                # a drive without the folder
    window = _window({**folders, "drives": lambda: [tmp_path / "sd", tmp_path / "stick", tmp_path / "gone"]})
    assert window.folders == [tmp_path / "Games" / "PSP", tmp_path / "sd" / "Games" / "PSP"]
    text = window.folders_state.text()
    assert text == "<b>~/Games/PSP</b>, <b>~/sd/Games/PSP</b>"                 # what goes there: the info symbol
    assert window.folders_info.text_ == ("Drop your games in ~/Games/PSP, .ISO, .CSO or .CHD, folders with an "
                                         "EBOOT.PBP. A USB drive or an SD card with a Games/PSP folder is also "
                                         "checked for content.")
    assert str(tmp_path) not in text and "folders" not in window.settings.DEFAULTS
    window.close()


def test_rename_files_needs_a_disc_image(qapp, folders, tmp_path):
    _install(folders["home"])
    (tmp_path / "Games" / "PSP" / "one.iso").unlink()
    window = _window(folders)
    assert not window.rename_pill.isEnabled()                                   # only the memory stick game (a PBP)
    make_disc(tmp_path / "Games" / "PSP" / "one.iso", "One", "ULUS00001")
    window.refresh()
    assert window.rename_pill.isEnabled()
    window.close()


def test_a_chd_is_marked(qapp, folders, tmp_path):
    _install(folders["home"])
    (tmp_path / "Games" / "PSP" / "Lumines.chd").write_bytes(b"MComprHD")
    window = _window(folders)
    row = [window.table.item(r, 1).text() for r in range(window.table.rowCount())].index("Lumines")
    assert window.table.item(row, 3).text() == "CHD" and "not looked into" in window.table.item(row, 3).toolTip()
    window.close()


def test_install_runs_off_the_window(qapp, folders, monkeypatch):
    payload = b"#!/bin/sh\n"
    monkeypatch.setattr(emulator, "SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window = _window(folders, fetch=lambda url, dest, progress=None: dest.write_bytes(payload))
    window.on_install()
    assert not window.install_pill.isEnabled()                                  # busy
    _wait(window, qapp)
    assert window.running.text() == f"PPSSPP {emulator.VERSION} is installed."
    assert window.version == emulator.VERSION and window.pill.text() == "Ready"
    window.close()


def test_ppsspps_window(qapp, folders, tmp_path):
    """PPSSPP settings opens PPSSPP's own window, through the run wrapper and without a game."""
    _install(folders["home"])
    log = tmp_path / "args"
    folders["run"].write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n')
    folders["run"].chmod(0o755)
    window = _window(folders)
    window.ppsspp_button.click()
    deadline = time.monotonic() + 10
    while not log.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert log.read_text().splitlines() == [""]
    assert window.output.toPlainText().splitlines()[-1].endswith(" INFO PPSSPP's own window was opened.")
    window.close()


def test_the_steam_link(qapp, folders):
    """The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the
    boxes and Start game do, and Steam in it is a link the app opens itself."""
    opened = []
    window = _window(folders, open_url=lambda url: opened.append(url) or True)
    assert not hasattr(window, "steam_hint")
    window.show()
    window.steam_info.click()
    label = window.steam_info.popup.findChild(QLabel)
    assert re.sub(r"<[^>]+>", "", label.text()) == ("A checkmark before a game adds the game to Steam. When the Start "
                                                    "game button is clicked the game starts from Steam.")
    assert ">Steam</a>" in label.text() and not label.openExternalLinks()
    label.linkActivated.emit("steam://open/games")
    assert opened == ["steam://open/games"] and "Steam was opened." in window.output.toPlainText()
    window.close()


def test_steam_added_and_taken_out(qapp, folders, monkeypatch):
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    closed = []
    window = _window(folders, closed=closed)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    assert window.steam_button.isEnabled()
    add, remove = window.steam_plan()
    assert [g.title for g in add] == ["One"] and remove == []
    window.on_update_steam()
    _wait(window, qapp)
    assert closed == [1] and window.running.text().startswith("1 game(s) in Steam")
    assert list(shortcuts.in_steam(folders["steam_dir"]).values()) == ["[PSP] One"]
    assert window.steam_box.value.text() == "1" and window.table.item(0, 0).checkState() == Qt.CheckState.Checked
    window.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    add, remove = window.steam_plan()
    assert add == [] and [g.title for g in remove] == ["One"]
    window.on_update_steam()
    _wait(window, qapp)
    assert shortcuts.in_steam(folders["steam_dir"]) == {} and "1 taken out" in window.running.text()
    window.close()


def test_a_shortcut_named_before_the_system_prefix_is_renamed(qapp, folders, monkeypatch):
    """A shortcut named by the title alone, as before "[PSP] ": Update Steam is on for it and renames it, with
    its play time; the artwork under its old number goes."""
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window = _window(folders)
    game = window.games[0]
    old = steam.Change(shortcuts.entry(game, game.title, folders["run"], Path("/i.png")), shortcuts.for_game(game),
                       {"p": b"P"})
    steam.write_shortcuts(folders["steam_dir"], [old])
    config = steam.user_folders(folders["steam_dir"])[0]
    values = steam.read_vdf((config / "shortcuts.vdf").read_bytes())
    values["shortcuts"]["0"]["LastPlayTime"] = 1750000000
    (config / "shortcuts.vdf").write_bytes(steam.write_vdf(values))
    window.refresh()
    assert window.table.item(0, 0).checkState() == Qt.CheckState.Checked and window.steam_button.isEnabled()
    window.on_update_steam()
    _wait(window, qapp)
    [item] = steam.shortcuts(folders["steam_dir"])
    assert item["AppName"] == f"[PSP] {game.title}" and item["LastPlayTime"] == 1750000000
    assert not list((config / "grid").glob(f"{old.number}*")) and not window.steam_button.isEnabled()
    window.close()


def test_a_shortcut_of_a_game_no_longer_found_is_taken_out(qapp, folders):
    _install(folders["home"])
    gone = Game(Path("/old/games/gone.iso"), "Gone")
    steam.write_shortcuts(folders["steam_dir"], shortcuts.changes([gone], [], folders["run"], Path("/i.png"), {},
                                                                  art=False))
    window = _window(folders)
    add, remove = window.steam_plan()
    assert add == [] and [(str(g.file), g.title) for g in remove] == [(str(gone.file), "[PSP] Gone")]
    assert window.steam_button.isEnabled()
    window.close()


def test_no_steam_game_mode_or_no_wrapper(qapp, folders, monkeypatch):
    _install(folders["home"])
    monkeypatch.setattr(steam, "find_steam", lambda: None)                       # None: looked up, and not found
    window = _window({**folders, "steam_dir": None})
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    assert not window.steam_button.isEnabled() and "never started" in window.steam_button.toolTip()
    window.close()
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "gamescope")
    window = _window(folders)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    assert not window.steam_button.isEnabled() and "Desktop Mode" in window.steam_button.toolTip()
    window.close()
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    folders["run"].unlink()
    window = _window(folders)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    assert "install PS5 PPSSPP Manager through the portal first" in window.running.text()
    assert not window.worker.running
    window.close()


def test_the_blue_look(qapp, folders):
    """PS5 RPCS3 Manager's design (owner, 07-11-2026): the Refresh pill and the boxes in the header, the action pills
    under the introduction, the tabs."""
    _install(folders["home"])
    window = _window(folders)
    from bazzite_console_core.theme import OUTLINE
    assert style.BLUE in window.styleSheet()
    assert window.covers_button.property("primary") is None and window.steam_button.property("primary")
    assert window.ppsspp_button.property("primary") is None
    assert style.BLUE in window.emulator_box.styleSheet() and style.BLUE in window.refresh_pill.styleSheet()
    assert [(p.value.text(), p.caption.text()) for p in window.actions] == [
        ("Games", "Rename"), ("Games", "Uninstall")]
    assert [(p.value.text(), p.caption.text()) for p in window.header_pills[1:3]] == [
        ("PPSSPP", "Install"), ("PPSSPP", "Uninstall")]
    for pill in (*window.header_pills, *window.actions):
        sheet = pill.styleSheet()                       # the blue left edge only, also under the mouse (owner)
        assert sheet.rfind(f"border-left-color:{style.BLUE}") > sheet.rfind(OUTLINE) >= 0, pill.caption.text()
        assert style.HOVER_SHEEN in sheet and style.BLUE_TINT not in sheet
    assert "QTabBar::tab" in window.styleSheet() and "QComboBox" in window.styleSheet()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["Your games", "Start game",
                                                                            "Memory cards", "Settings",
                                                                            "View logs", "Clear logs"]
    window.close()


def test_a_newer_ppsspp_is_mentioned(qapp, folders):
    from bazzite_console_core.updates import ReleaseInfo
    _install(folders["home"])
    release = ReleaseInfo("1.21.0", "v1.21", "https://github.com/hrydgard/ppsspp/releases/tag/v1.21", "2026-11-30")
    window = _window(folders, newer_release=lambda: release)
    deadline = time.monotonic() + 10
    while window.newer is None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    tip = window.emulator_state.toolTip()                   # the line stays the state; the tip and the log say
    assert window.emulator_state.text() == "Installed. Uninstall with the Uninstall button."
    assert "PPSSPP 1.21.0 is out (2026-11-30)" in tip and "releases/tag/v1.21" in tip
    assert "PPSSPP 1.21.0 is out (2026-11-30)" in window.output.toPlainText()
    assert window.install_pill.isEnabled() is False                                # it never installs that one
    window.close()


def test_another_ppsspp_is_installed(qapp, folders):
    """Another release than the app brings: the line stays the state, the tip says Install puts the app's in, and
    the log says it once."""
    home = folders["home"]
    (home / "1.19.3").mkdir(parents=True)
    (home / "1.19.3" / emulator.MEMBER).write_text("")
    (home / "current").symlink_to("1.19.3")
    window = _window(folders)
    assert window.version == "1.19.3" and window.emulator_box.value.text() == "1.19.3"
    assert window.emulator_state.text() == "Installed. Uninstall with the Uninstall button."
    assert window.emulator_state.toolTip() == ("PPSSPP 1.19.3 is in use; it was not tried on the board. This "
                                               f"version of the app was tried with {emulator.VERSION}: Install puts "
                                               "it back in use.")
    assert window.install_pill.isEnabled()
    window.refresh()
    assert window.output.toPlainText().count("PPSSPP 1.19.3 is in use") == 1
    window.close()


def test_the_log_tab(qapp, folders):
    """What the window says goes to the Log tab with the time, after what the log file held already."""
    folders["log_path"].write_text("07-11-2026 22:14:00 INFO PS5 PPSSPP Manager 2.2.0 started\n")
    window = _window(folders)
    lines = window.output.toPlainText().splitlines()
    assert lines == ["07-11-2026 22:14:00 INFO PS5 PPSSPP Manager 2.2.0 started"]
    window.say("Steam was not changed: no Steam", ok=False)
    lines = window.output.toPlainText().splitlines()
    assert lines[-1][:19].count("-") == 2 and lines[-1][10] == " "               # DD-MM-YYYY HH:MM:SS
    assert lines[-1].endswith(" ERROR Steam was not changed: no Steam") and "c62828" in window.running.styleSheet()
    assert str(folders["log_path"]) in window.tabs.widget(4).findChildren(QLabel)[0].text()
    window.close()


def test_clear_logs_empties_the_log(qapp, folders):
    """Clear logs, the tab beside Log that is a button (owner, 18-11-2026): the log file emptied, the older ones
    beside it removed and the Log tab emptied with them, the open page kept."""
    log = folders["log_path"]
    log.write_text("18-11-2026 10:00:00 INFO PS5 PPSSPP Manager started\n")
    older = log.with_name(log.name + ".1")
    older.write_text("17-11-2026 10:00:00 INFO older\n")
    window = _window(folders)
    tabs, clear = window.tabs, window.clear_tab.index
    assert tabs.tabText(clear) == "Clear logs" and tabs.tabText(clear - 1) == "View logs"
    assert clear == tabs.count() - 1 and "Manager started" in window.output.toPlainText()
    tabs.setCurrentIndex(clear - 1)
    tabs.tabBarClicked.emit(clear)
    tabs.setCurrentIndex(clear)
    assert tabs.currentIndex() == clear - 1                                     # the Log tab stays open
    assert log.read_text() == "" and not older.exists() and window.output.toPlainText() == ""
    assert window.running.text() == "The log was cleared."
    window.close()


def test_the_play_time_ppsspp_counts(qapp, folders):
    """Play time, the last pill of the second row (owner, 18-11-2026: the header is full): all games together, from
    [PlayTime] in PPSSPP's settings, each game's time in the tip under its title."""
    window = _window(folders)
    # The owner's order (20-11-2026), as PS5 shadPS4 Manager's: the version, Install, Uninstall and Refresh in the
    # header, the games' pills, Available in Steam and Play time under it. The Your games box went.
    assert [b.caption.text() for b in window.header_pills] == ["PPSSPP version", "Install", "Uninstall",
                                                               "Click to refresh"]
    assert [b.caption.text() for b in window.second_row] == ["Rename", "Uninstall", "Available in Steam", "Play time"]
    assert not hasattr(window, "games_box") and not hasattr(window, "remove_game_button")
    # Two columns under the pills: the states, each name with a colon, and the installed version beside them
    names = [w.text() for w in window.centralWidget().findChildren(QLabel)
             if w.text().endswith(":") and w.styleSheet() == "font-weight:700;"]
    assert names == ["PPSSPP:", "Game folder:", "Installed version:"]
    assert window.version_state.text() == "—"
    window.show()
    qapp.processEvents()
    assert window.time_box.caption.text() == "Play time" and window.time_box.y() == window.rename_pill.y()
    assert window.time_box.x() > window.rename_pill.x() and abs(window.time_box.width()
                                                                - window.second_row[0].width()) <= 1
    assert window.time_box.value.text() == "—" and "none yet" in window.time_box.toolTip()
    ini = folders["memstick"] / "PSP" / "SYSTEM" / "ppsspp.ini"
    ini.write_text("\ufeff[General]\nFirstRun = False\n[PlayTime]\nULUS00001 = 5400,1795000000\nNPUH10000 = 65,0\n"
                   "broken = soon\n[Graphics]\nVSync = 3,4\n")
    window.refresh()
    assert window.time_box.value.text() == "1 h 31 min"
    tip = window.time_box.toolTip().splitlines()
    assert tip[1].startswith("One: 1 h 30 min, last played ") and tip[2] == "NPUH10000: 1 min 5 s"
    window.close()


def test_the_window_keeps_its_width(qapp, folders):
    """The window's width (owner, 18-11-2026): 900 when it opens, which is also its narrowest, and what is in it
    asks for no more than the header's four pills do; the six tabs share the whole width, the last one up to the
    margin; under the header's pills the two links alone, in the type of a pill's caption, each still a link."""
    window = _window(folders)
    window.show()
    qapp.processEvents()
    bar = window.tabs.tabBar()
    assert window.width() == 900 == window.minimumWidth() and window.height() == 606
    assert window.settings_scroll.widget() is window.settings_page          # the Settings tab scrolls: no higher
    window.time_box.hide(), window.tabs.hide()                                  # what the window had before
    qapp.processEvents()
    before = window.centralWidget().minimumSizeHint().width()
    window.time_box.show(), window.tabs.show()
    qapp.processEvents()
    assert window.centralWidget().minimumSizeHint().width() == before
    assert bar.count() == 6 and len({bar.tabRect(i).width() for i in range(6)}) <= 2    # equal but for a pixel
    assert not bar.drawBase()                                                   # no line over the tabs
    assert bar.tabRect(0).left() <= 1 and abs(bar.tabRect(5).right() - (window.tabs.width() - 1)) <= 1
    assert re.sub(r"<[^>]+>", "", window.intro.text()) == "PPSSPP's release notes · Wiki"
    assert window.intro.styleSheet() == window.refresh_pill.caption.styleSheet() == style.CAPTION
    assert f"href='{emulator.RELEASE_PAGE}'" in window.intro.text() and "text-decoration:none" in window.intro.text()
    assert style.BLUE not in window.intro.text() and window.intro.openExternalLinks()
    assert window.tabs.tabText(2) == "Memory cards" and window.tabs.widget(2) is window.saves_page
    window.close()


def test_covers_with_the_suites_key(qapp, folders, monkeypatch, tmp_path):
    """Steam artwork… keeps the suite's key; Update Steam then looks up the games and puts the cover on the portrait, and a
    game in Steam not looked up yet makes the button do something again."""
    from PyQt6.QtGui import QColor, QImage
    from PyQt6.QtWidgets import QInputDialog

    picture = QImage(600, 900, QImage.Format.Format_ARGB32)
    picture.fill(QColor("#0000ff"))
    picture.save(str(tmp_path / "blue.png"))
    asked = []

    def get(url: str, headers: dict[str, str]) -> bytes:
        asked.append(url)
        if "search/" in url:
            return json.dumps({"success": True, "data": [{"id": 1, "name": "Two"}]}).encode()
        if "/game/1?" in url:
            return json.dumps({"success": True, "data": [{"score": 1, "mime": "image/png",
                                                          "url": "https://cdn2.steamgriddb.com/p.png"}]}).encode()
        return (tmp_path / "blue.png").read_bytes()
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    key = tmp_path / "key"
    window = _window(folders, covers_home=tmp_path / "covers", covers_get=get, covers_key=key)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    _wait(window, qapp)
    assert asked == [] and not window.steam_button.isEnabled()                  # no key: nothing asked
    monkeypatch.setattr(QInputDialog, "exec", lambda self: (self.setTextValue("0123456789abcdef"), 1)[1])
    window.on_covers()
    assert key.read_text() == "0123456789abcdef\n"
    game = window.ticked()[0]
    assert window.no_cover == {str(game.file)} and window.steam_button.isEnabled()
    window.on_update_steam()
    _wait(window, qapp)
    assert window.running.text().startswith("Covers: SteamGridDB had pictures for 1 of 1 game(s).\n1 game(s) in")
    assert not any("heroes/" in url or "logos/" in url for url in asked)        # the portrait alone
    assert "0123456789abcdef" not in window.output.toPlainText()
    number = shortcuts.entry(game, "[PSP] One", folders["run"], LOGO_PATH)["appid"] & 0xFFFFFFFF
    grid = steam.user_folders(folders["steam_dir"])[0] / "grid"
    assert QImage(str(grid / f"{number}p.png")).pixelColor(300, 450).name() == "#0000ff"
    assert window.no_cover == set() and not window.steam_button.isEnabled()
    window.close()


def test_remove_game_asks_what_to_keep(qapp, folders, monkeypatch, tmp_path):
    """Games Uninstall (Remove game… until 20-11-2026; owner, 03-11-2026): the keep window lists what would go; Cancel deletes nothing, Delete marked
    deletes the rows still ticked off the window's thread and says what went and what stayed."""
    from PyQt6.QtWidgets import QDialog
    from bazzite_console_core.keep_dialog import KeepDialog
    _install(folders["home"])
    window = _window(folders)
    assert not window.remove_game_pill.isEnabled()                            # nothing chosen yet
    window.table.selectRow(0)
    game = window.chosen()
    assert game.title == "One" and window.remove_game_pill.isEnabled()
    target = tmp_path / "Games" / "PSP" / "one.iso"
    assert target.exists()
    seen = []
    monkeypatch.setattr(KeepDialog, "exec", lambda self: (seen.append(self.items), QDialog.DialogCode.Rejected)[1])
    window.on_remove_game()
    assert [item.label for item in seen[0]] == ["one.iso (the disc image)"] and target.exists()
    assert window.running.text() == "Nothing was deleted."

    def keep_it(self):
        self.items[0].delete = False
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(KeepDialog, "exec", keep_it)
    window.on_remove_game()
    _wait(window, qapp)
    assert target.exists() and window.running.text() == "One: deleted nothing. Kept: one.iso (the disc image)."
    window.table.selectRow(0)
    monkeypatch.setattr(KeepDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.on_remove_game()
    _wait(window, qapp)
    assert not target.exists() and window.running.text() == "One: deleted one.iso (the disc image)."
    assert "One" not in [window.table.item(r, 1).text() for r in range(window.table.rowCount())]
    window.close()


def test_the_settings_tab(qapp, folders):
    """The Settings tab holds PPSSPP's settings in the app (core's settings_page): the values as ppsspp.ini holds
    them, a change written into it at once, and nothing while PPSSPP runs."""
    ini = folders["memstick"] / "PSP" / "SYSTEM" / "ppsspp.ini"
    ini.write_text("[General]\n[Graphics]\nInternalResolution = 3\n")
    running = [False]
    window = _window(folders, ppsspp_running=lambda: running[0])
    page = window.settings_page
    assert window.tabs.widget(3).widget() is page and page.widgets["resolution"].currentData() == "3"
    assert page.widgets["renderer"].currentText() == "Vulkan" and page.widgets["volume"].value() == 100
    page.widgets["vsync"].setChecked(False)
    assert "VerticalSync = False" in ini.read_text() and page.status.text() == "VSync: off."
    running[0] = True
    page.widgets["fps"].setChecked(True)
    assert "iShowStatusFlags" not in ini.read_text() and "PPSSPP is running" in page.status.text()
    window.close()


def test_start_game_starts_the_chosen_game_through_steam(qapp, folders, monkeypatch):
    """The Start game tab (owner, 12-11-2026), a tab that is a button: a click starts the game chosen under Your
    games through Steam, by its shortcut's number, and the open tab stays open. Without a chosen game, or with one
    that is not in Steam yet, it says what to do first and starts nothing."""
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    opened = []
    window = _window(folders, open_url=lambda url: opened.append(url) or True)
    tabs, start = window.tabs, window.start_tab.index
    assert start == 1 and tabs.tabText(start) == "Start game" and "Steam" in tabs.tabToolTip(start)
    window.table.clearSelection()
    tabs.tabBarClicked.emit(start)                                           # no game chosen
    assert opened == [] and window.running.text().startswith("Choose a game under Your games first")
    window.table.selectRow(0)
    title = window.chosen().title
    tabs.tabBarClicked.emit(start)                                           # chosen, but not in Steam yet
    assert opened == [] and window.running.text() == (f"{title} is not in Steam yet: tick it and press Update Steam "
                                                      "first.")
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    _wait(window, qapp)
    window.table.selectRow(0)
    (name,) = shortcuts.in_steam(folders["steam_dir"]).values()
    tabs.setCurrentIndex(2)
    tabs.tabBarClicked.emit(start)                                           # a click on the tab
    tabs.setCurrentIndex(start)                                              # as the click goes on to select it
    assert window.running.text().startswith(f"Starting {title} through Steam")      # off the window's thread
    _wait(window, qapp)
    assert opened == [steam.play_url(steam.appid(f'"{folders["run"]}"', name))]
    assert opened[0].startswith("steam://rungameid/")
    assert window.running.text() == f"{title} runs, started through Steam."
    assert tabs.currentIndex() == 2                                          # Memory cards is still open
    window.table.selectRow(0)
    window.open_url = lambda url: False
    window.on_start_game()
    _wait(window, qapp)
    assert window.running.text() == f"{title} was not started: xdg-open is missing."
    window.close()


def test_the_controller_state_beside_the_title(qapp, folders, tmp_path):
    """Controller connected or No controller (owner, 18-11-2026: as the other managers show it), from the kernel's
    list of input devices, looked at again every few seconds; Steam's own virtual controller does not count."""
    devices = tmp_path / "devices"
    window = _window(folders, devices=devices)
    assert window.controller.text() == "No controller" and window.controller.kind == "warn"
    assert window.controller_timer.isActive() and window.controller_timer.interval() == window.CONTROLLER_POLL
    devices.write_text('I: Bus=0003 Vendor=28de Product=11ff Version=0001\nN: Name="Steam Virtual Gamepad"\n'
                       'H: Handlers=event9 js0\n\n'
                       'I: Bus=0005 Vendor=054c Product=0ce6 Version=8100\nN: Name="DualSense Wireless Controller"\n'
                       'H: Handlers=event10 js1\n\n'
                       'I: Bus=0005 Vendor=054c Product=0ce6 Version=8100\n'
                       'N: Name="DualSense Wireless Controller Motion Sensors"\nH: Handlers=event11 js2\n')
    window.show_controller()
    assert window.controller.text() == "Controller connected" and window.controller.kind == "ok"
    assert "DualSense Wireless Controller." in window.controller.toolTip()
    window.show()
    qapp.processEvents()
    assert window.pill.x() < window.controller.x()                              # after the app's own state
    window.close()
    assert not window.controller_timer.isActive()


def test_the_version_pill(qapp, folders, monkeypatch):
    """The version is a pill (owner, 20-11-2026, as shadPS4's own launcher): its menu lists the builds installed and
    puts another in use; Manage versions… opens the version manager (core's BuildsDialog) on the same folder."""
    from bazzite_console_core import builds_dialog
    home = folders["home"]
    for folder in (emulator.VERSION, "other"):
        (home / folder).mkdir(parents=True, exist_ok=True)
        (home / folder / emulator.MEMBER).write_text("")
    (home / "current").symlink_to(emulator.VERSION)
    window = _window(folders)
    assert window.emulator_box.isEnabled()
    window.on_versions_menu()
    actions = [a for a in window.versions_menu.actions() if not a.isSeparator()]
    labels = [a.text() for a in actions]
    assert sorted(labels[:-1]) == sorted([f"{emulator.VERSION} (tested)", "other"]) and labels[-1] == "Manage versions…"
    assert next(a for a in actions if a.text().endswith("(tested)")).isChecked()
    window.versions_menu.hide()
    next(a for a in actions if a.text() == "other").trigger()
    assert window.version == "other" and window.running.text().endswith("is in use. It was not tried on the board.")
    assert window.install_pill.isEnabled()                                      # puts the tested build back
    opened = []
    monkeypatch.setattr(builds_dialog.BuildsDialog, "exec",
                        lambda dialog: opened.append((dialog.home, dialog.tested.version, dialog.member)) or 0)
    actions[-1].trigger()
    assert opened == [(home, emulator.VERSION, emulator.MEMBER)]
    window.close()


def test_start_game_waits_for_a_steam_that_does_not_run(qapp, folders, monkeypatch):
    """Start game with Steam closed (owner, 20-11-2026, first in PS5 shadPS4 Manager: Steam came up and the game never
    started, while the line said it did): Steam is started and waited for before the game's address is given, and
    what went wrong is said. While PPSSPP runs, no second one is started."""
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    opened, ran, ready = [], [], iter([False, False, True])
    window = _window(folders, open_url=lambda url: opened.append(url) or True,
                     steam_play=lambda url, open_url, started: steam.play(
                         url, open_url, lambda: bool(opened), run=ran.append, running=lambda: False,
                         ready=lambda: next(ready), sleep=lambda seconds: None))
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    _wait(window, qapp)
    window.table.selectRow(0)
    title = window.chosen().title
    window.on_start_game()
    _wait(window, qapp)
    assert ran == [steam.start_command()] and len(opened) == 1
    assert window.running.text() == f"{title} runs, started through Steam."

    def never(url, open_url, started):
        raise steam.SteamError("Steam did not start within 120 seconds.")
    window.steam_play = never
    window.table.selectRow(0)
    window.on_start_game()
    _wait(window, qapp)
    assert window.running.text() == f"{title} was not started: Steam did not start within 120 seconds."
    window.ppsspp_running = lambda: True
    window.table.selectRow(0)
    window.on_start_game()
    assert window.running.text() == "PPSSPP is running: close it first, then start the game."
    window.close()


def test_a_game_in_steam_more_than_once_is_said_and_update_steam_leaves_one(qapp, folders, monkeypatch):
    """Owner, 20-11-2026 (first in PS5 shadPS4 Manager: "multiple entries for the same game in Steam ... a check for
    that and a feature to fix it"): the window says which game is there more than once, the box's tooltip too, and
    Update Steam, lit for it, leaves one shortcut."""
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window = _window(folders)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    _wait(window, qapp)
    assert window.doubles == {} and not window.steam_button.isEnabled()
    (path,) = folders["steam_dir"].glob("userdata/*/config/shortcuts.vdf")
    values = steam.read_vdf(path.read_bytes())
    items = list(values["shortcuts"].values())
    ours = next(item for item in items if shortcuts.ours(item))
    lower = {("exe" if k == "Exe" else "launchoptions" if k == "LaunchOptions" else k): v for k, v in ours.items()}
    path.write_bytes(steam.write_vdf({"shortcuts": {str(n): i for n, i in enumerate([*items, lower])}}))
    window.refresh()
    title = window.games[0].title
    assert list(window.doubles.values()) == [1]
    assert window.running.text() == f"In Steam more than once: {title} (2 times). Update Steam leaves one of each."
    assert window.table.item(0, 0).toolTip() == "In Steam 2 times: Update Steam leaves one"
    assert window.steam_button.isEnabled() and window.steam_box.value.text() == "1"
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (asked.append(a[2]),
                                                                  QMessageBox.StandardButton.Yes)[1])
    window.on_update_steam()
    _wait(window, qapp)
    assert "1 double shortcut(s) taken out" in asked[0]
    left = [i for i in steam.read_vdf(path.read_bytes())["shortcuts"].values() if shortcuts.ours(i)]
    assert len(left) == 1 and window.doubles == {} and not window.steam_button.isEnabled()
    assert window.table.item(0, 0).toolTip() == "In Steam"
    window.close()


def test_the_steam_state_follows_the_sign_in(qapp, folders, monkeypatch):
    """Steam beside the title (owner, 22-11-2026): a green dot while Steam runs and is signed in, a red one
    otherwise, looked at again with the controller."""
    import ppsspp_manager.main_window as module
    signed = [False]
    monkeypatch.setattr(module.steam, "signed_in", lambda folder: signed[0])
    window = _window(folders)
    assert window.steam_state.shown() == "Steam" and window.steam_state.kind == "bad"
    assert window.steam_state.toolTip() == "Steam not signed in\n" + module.STEAM_OFF
    assert window.pill.shown() == "Installed" and window.controller.shown() == "Controller"
    signed[0] = True
    window.show_steam()
    assert window.steam_state.kind == "ok" and window.steam_state.toolTip() == "Steam signed in\n" + module.STEAM_ON
    window.close()


def test_exit_ppsspp_is_on_while_ppsspp_runs_and_ends_it_at_once(qapp, folders):
    """Exit PPSSPP (owner, 22-11-2026): the first button of the row under Your games, on only while PPSSPP runs; a
    click ends it with no question and the line under the tabs says so."""
    runs = [True]
    ended: list[int] = []

    def end() -> list[int]:
        ended.append(1)
        runs[0] = False
        return [10]

    window = _window(folders, ppsspp_running=lambda: runs[0], ppsspp_end=end)
    row = window.exit_button.parentWidget().layout()
    buttons = next(row.itemAt(i).layout() for i in range(row.count())
                   if row.itemAt(i).layout() is not None and row.itemAt(i).layout().indexOf(window.exit_button) >= 0)
    assert buttons.indexOf(window.exit_button) + 1 == buttons.indexOf(window.ppsspp_button)
    assert window.exit_button.text() == "Exit PPSSPP"
    assert "without saving" in window.exit_button.toolTip()
    assert window.exit_button.isEnabled()
    window.exit_button.click()
    assert ended == [1]
    assert window.running.text() == "PPSSPP was ended."
    assert not window.exit_button.isEnabled()
    window.ppsspp_end = lambda: []
    window.on_exit_ppsspp()
    assert window.running.text() == "PPSSPP was not running."
    window.close()


def test_ppsspp_running_and_end_read_proc(tmp_path):
    """PPSSPP's process is found by its name, and ending it ends what it started first."""
    proc = tmp_path / "proc"
    for pid, comm, state, parent in ((10, emulator.MEMBER[:15], "S", 1), (20, "child", "S", 10), (30, "bash", "S", 1)):
        (proc / str(pid)).mkdir(parents=True)
        (proc / str(pid) / "comm").write_text(comm + "\n")
        (proc / str(pid) / "stat").write_text(f"{pid} ({comm}) {state} {parent} 0\n")
    assert emulator.running(proc)
    sent: list[int] = []
    assert processes.end(processes.find(emulator.is_ppsspp, proc), proc, kill=lambda pid, sig: sent.append(pid))
    assert sent == [20, 10]
    (proc / "10" / "stat").write_text(f"10 ({emulator.MEMBER[:15]}) Z 1 0\n")
    assert not emulator.running(proc)


def test_view_logs_shows_the_emulators_log_too(qapp, folders):
    """View logs (owner, 26-11-2026): two radio buttons above the log choose the app's log or what PPSSPP printed
    (emulator.log beside it, which the run wrapper writes). The hint names the file shown. A line the app logs
    shows only while its own log is shown. Clear logs empties the log shown, with its older ones."""
    from ppsspp_manager import APP_NAME
    log = folders["log_path"]
    log.write_text("26-11-2026 10:00:00 INFO the app's line\n")
    emulator_log = log.with_name("emulator.log")
    emulator_log.write_text("26-11-2026 10:00:01 INFO PPSSPP started: ~/game\nprinted\n")
    older = log.with_name("emulator.log.1")
    older.write_text("old\n")
    window = _window(folders)
    page = window.log_page
    assert page.app_button.text() == APP_NAME and page.emulator_button.text() == "PPSSPP"
    assert page.app_button.isChecked() and "the app's line" in window.output.toPlainText()
    assert log.name in page.hint.text() and "emulator.log" not in page.hint.text()
    page.emulator_button.click()
    assert window.output.toPlainText().endswith("printed") and "emulator.log" in page.hint.text()
    window.note("a line of the app's")
    assert "a line of the app's" not in window.output.toPlainText()
    window.tabs.tabBarClicked.emit(window.clear_tab.index)
    assert emulator_log.read_text() == "" and not older.exists() and window.output.toPlainText() == ""
    assert log.read_text().startswith("26-11-2026 10:00:00 INFO the app's line")          # the app's log kept
    page.app_button.click()
    assert "the app's line" in window.output.toPlainText()
    window.close()
    window.close()


def test_a_window_without_a_controller_says_so_on_the_desktop_once(qapp, folders, tmp_path, notifications):
    """Opened without a controller, the window sends one desktop notification (owner, 28-11-2026); a controller
    gone later, or a window opened with one, sends none."""
    devices = tmp_path / "devices"
    devices.write_text('I: Bus=0003 Vendor=054c Product=0ce6 Version=8111\nN: Name="DualSense"\n'
                       "H: Handlers=event3 js0\n")
    window = _window(folders, devices=devices)
    devices.write_text("")
    window.show_controller()
    assert notifications == []
    window.close()
    window = _window(folders, devices=devices)
    window.show_controller()
    assert [args[1] for args in notifications] == ["No controller connected"]
    assert "PS button" in notifications[0][2]
    window.close()
