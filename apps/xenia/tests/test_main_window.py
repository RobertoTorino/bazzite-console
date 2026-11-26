# SPDX-License-Identifier: GPL-3.0-or-later
"""The window on folders made in a temp folder: the states before and after installing, the games in the table, the
game folders, the plan for Steam, installing through the worker, Steam's shortcuts changed with a fake "close
Steam", a newer Xenia build, the Settings and Log tabs, and the blue look of RPCS3 Manager's design."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMessageBox

from conftest import make_iso, make_package

from bazzite_console_core import processes, steam
from xenia_manager import emulator, shortcuts, style
from xenia_manager.games import Game
from xenia_manager.main_window import MainWindow


@pytest.fixture
def folders(tmp_path):
    make_iso(tmp_path / "Games" / "XBOX360" / "One.iso")                        # the app's own folder
    make_package(tmp_path / "Games" / "XBOX360", "Two")
    config = tmp_path / "Steam" / "userdata" / "1000" / "config"
    config.mkdir(parents=True)
    run = tmp_path / "bin" / "ps5-xenia-run"
    run.parent.mkdir()
    run.write_text("#!/bin/sh\n")
    log = tmp_path / "data" / "ps5-xenia-manager" / "ps5-xenia-manager.log"
    log.parent.mkdir(parents=True)
    return {"home": tmp_path / "emulator", "steam_dir": tmp_path / "Steam", "run": run, "user_home": tmp_path,
            "drives": lambda: [], "log_path": log}


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
    kwargs.setdefault("xenia_running", lambda: False)
    # Start game: Steam takes the address at once and the game runs (never the real Steam in a test)
    kwargs.setdefault("steam_play", lambda url, open_url, started: steam.play(
        url, open_url, lambda: True, ready=lambda: True, sleep=lambda seconds: None))
    return MainWindow(**folders, steam_closed=lambda change: (closed.append(1), change())[0] and False,
                      steam_running=lambda: False, **kwargs)


def _titles(window) -> list[str]:
    return [window.table.item(r, 1).text() for r in range(window.table.rowCount())]


def test_before_installing(qapp, folders):
    window = _window(folders)
    assert window.pill.text() == "Not installed"
    # The state alone, in the words every manager uses (owner, 07-11-2026); what Install does in the tip.
    assert window.emulator_state.text() == "Not installed. Install it with the Install button."
    assert "Install downloads Xenia 54386cb" in window.emulator_state.toolTip()
    assert window.install_pill.isEnabled() and not window.remove_pill.isEnabled()
    assert not window.xenia_button.isEnabled() and not hasattr(window, "play_button")
    for name in ("folder_button", "forget_button"):
        assert not hasattr(window, name), name                               # gone (owner, 03-11-2026): fixed folders
    assert window.table.rowCount() == 2                                          # the games in Games/XBOX360
    window.close()


def test_installed_with_games(qapp, folders, tmp_path):
    _install(folders["home"])
    window = _window(folders)
    assert window.pill.text() == "Ready"                                       # the games in Games/XBOX360
    assert window.pill.text() == "Ready" and window.emulator_box.value.text() == emulator.VERSION
    assert window.emulator_state.text() == "Installed. Uninstall with the Uninstall button."
    assert "experimental on Linux" in window.emulator_state.toolTip()
    assert window.table.rowCount() == 2 and window.steam_box.value.text() == "0"
    assert not window.install_pill.isEnabled() and window.remove_pill.isEnabled()
    assert not window.remove_game_pill.isEnabled()                              # nothing chosen yet
    window.table.selectRow(0)
    assert window.remove_game_pill.isEnabled() and window.chosen().title == "One"
    assert not window.steam_button.isEnabled()                                    # nothing to change
    assert [window.table.item(r, 2).text() for r in range(2)] == ["", "4D5307E6"]
    assert [window.table.item(r, 3).text() for r in range(2)] == ["ISO", "Games on Demand"]
    window.close()


def test_an_older_build_is_offered_the_pinned_one(qapp, folders):
    (folders["home"] / "f42147a").mkdir(parents=True)
    (folders["home"] / "f42147a" / emulator.MEMBER).write_text("")
    (folders["home"] / "current").symlink_to("f42147a")
    window = _window(folders)
    assert window.emulator_state.text() == "Installed. Uninstall with the Uninstall button."
    assert "Xenia f42147a is in use; it was not tried on the board" in window.emulator_state.toolTip()
    assert "tried with 54386cb: Install puts it back in use" in window.emulator_state.toolTip()
    assert window.install_pill.isEnabled()
    window.refresh()
    assert window.output.toPlainText().count("Xenia f42147a is in use") == 1           # logged once
    window.close()


def test_the_apps_own_game_folders(qapp, folders, tmp_path, monkeypatch):
    """The games are put in Games/XBOX360 in the home folder, made when the app opens, and in Games/XBOX360 on a
    removable drive that has one (owner, 03-11-2026: fixed folders, no folder choosing); no folder is chosen or
    remembered any more."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _install(folders["home"])
    (tmp_path / "sd" / "Games" / "XBOX360").mkdir(parents=True)
    (tmp_path / "stick").mkdir()                                                # a drive without the folder
    window = _window({**folders, "drives": lambda: [tmp_path / "sd", tmp_path / "stick", tmp_path / "gone"]})
    assert window.folders == [tmp_path / "Games" / "XBOX360", tmp_path / "sd" / "Games" / "XBOX360"]
    text = window.folders_state.text()
    assert text == "<b>~/Games/XBOX360</b>, <b>~/sd/Games/XBOX360</b>"         # what goes there: the info symbol
    assert window.folders_info.text_ == ("Drop your games in ~/Games/XBOX360, .ISO, unpacked discs, .zar archives, "
                                         "Games on Demand and Arcade packages. A USB drive or an SD card with a "
                                         "Games/XBOX360 folder is also checked for content.")
    assert str(tmp_path) not in text and "folders" not in window.settings.DEFAULTS
    window.close()


def test_install_runs_off_the_window(qapp, folders, monkeypatch):
    payload = b"#!/bin/sh\n"
    monkeypatch.setattr(emulator, "SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window = _window(folders, fetch=lambda url, dest, progress=None: dest.write_bytes(payload))
    window.on_install()
    assert not window.install_pill.isEnabled()                                    # busy
    _wait(window, qapp)
    assert window.running.text() == f"Xenia {emulator.VERSION} is installed."
    assert window.version == emulator.VERSION and window.pill.text() == "Ready"
    window.close()


def test_a_failed_install_says_so(qapp, folders, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window = _window(folders, fetch=lambda url, dest, progress=None: dest.write_bytes(b"other"))
    window.on_install()
    _wait(window, qapp)
    assert "Xenia was not installed:" in window.running.text() and "SHA-256 differs" in window.running.text()
    assert not window.version
    window.close()


def test_remove(qapp, folders, monkeypatch):
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window = _window(folders)
    window.on_remove()
    assert not window.version and not window.home.exists() and window.pill.text() == "Not installed"
    window.close()


def test_xenias_window(qapp, folders, tmp_path):
    """Xenia settings opens Xenia's own window, through the run wrapper and without a game."""
    _install(folders["home"])
    log = tmp_path / "args"
    folders["run"].write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n')
    folders["run"].chmod(0o755)
    window = _window(folders)
    window.xenia_button.click()
    deadline = time.monotonic() + 10
    while not log.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert log.read_text().splitlines() == [""]
    assert window.output.toPlainText().splitlines()[-1].endswith(" INFO Xenia's own window was opened.")
    window.close()


def test_the_steam_link(qapp, folders):
    """The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the
    boxes and Start game do, and Steam in it is a link the app opens itself."""
    import re
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


def test_steam_added_and_taken_out(qapp, folders, tmp_path, monkeypatch):
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    closed = []
    window = _window(folders, closed=closed)
    window.table.item(1, 0).setCheckState(Qt.CheckState.Checked)
    assert window.steam_button.isEnabled()
    add, remove = window.steam_plan()
    assert [g.title for g in add] == ["Two"] and remove == []
    window.on_update_steam()
    _wait(window, qapp)
    assert closed == [1] and window.running.text().startswith("1 game(s) in Steam")
    assert list(shortcuts.in_steam(folders["steam_dir"]).values()) == ["[X360] Two"]
    assert window.steam_box.value.text() == "1" and window.table.item(1, 0).checkState() == Qt.CheckState.Checked
    window.table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
    add, remove = window.steam_plan()
    assert add == [] and [g.title for g in remove] == ["Two"]
    window.on_update_steam()
    _wait(window, qapp)
    assert shortcuts.in_steam(folders["steam_dir"]) == {} and "1 taken out" in window.running.text()
    window.close()


def test_a_shortcut_of_a_game_no_longer_found_is_taken_out(qapp, folders):
    _install(folders["home"])
    gone = Game(Path("/old/games/gone.iso"), "Gone")
    steam.write_shortcuts(folders["steam_dir"], shortcuts.changes([gone], [], folders["run"], Path("/i.png"), {},
                                                                  art=False))
    window = _window(folders)
    add, remove = window.steam_plan()
    assert add == [] and [(str(g.file), g.title) for g in remove] == [(str(gone.file), "[X360] Gone")]
    assert window.steam_button.isEnabled()
    window.close()


def test_games_need_xenia_for_game_mode(qapp, folders, tmp_path):
    window = _window(folders)
    window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    assert "Install Xenia first" in window.running.text() and not window.worker.running
    window.close()


def test_no_steam_game_mode_or_no_wrapper(qapp, folders, tmp_path, monkeypatch):
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
    assert "install Xenia Manager through the portal first" in window.running.text()
    assert not window.worker.running
    window.close()


def test_the_blue_look(qapp, folders):
    """RPCS3 Manager's design (owner, 07-11-2026): the Refresh pill and the boxes in the header, the action pills
    under the introduction, a third of the width each, the tabs."""
    _install(folders["home"])
    window = _window(folders)
    from bazzite_console_core.theme import OUTLINE
    assert style.BLUE in window.styleSheet()
    assert window.covers_button.property("primary") is None and window.steam_button.property("primary")
    assert window.xenia_button.property("primary") is None
    assert style.BLUE in window.emulator_box.styleSheet() and style.BLUE in window.refresh_pill.styleSheet()
    assert [(p.value.text(), p.caption.text()) for p in window.actions] == [("Games", "Uninstall")]
    assert [(p.value.text(), p.caption.text()) for p in window.header_pills[1:3]] == [
        ("Xenia", "Install"), ("Xenia", "Uninstall")]
    for pill in (*window.header_pills, *window.actions):
        sheet = pill.styleSheet()                       # the blue left edge only, also under the mouse (owner)
        assert sheet.rfind(f"border-left-color:{style.BLUE}") > sheet.rfind(OUTLINE) >= 0, pill.caption.text()
        assert style.HOVER_SHEEN in sheet and style.BLUE_TINT not in sheet
    assert "QTabBar::tab" in window.styleSheet() and "QComboBox" in window.styleSheet()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["Your games", "Start game",
                                                                            "Memory cards", "Settings",
                                                                            "View logs", "Clear logs"]
    window.show()
    qapp.processEvents()
    third = window.centralWidget().width() // 3
    assert all(abs(p.width() - third) < 12 for p in window.actions)               # the last third empty
    window.close()


def test_a_newer_build_is_mentioned(qapp, folders):
    from bazzite_console_core.updates import ReleaseInfo
    _install(folders["home"])
    release = ReleaseInfo("0a1b2c3", "0a1b2c3", "https://github.com/xenia-canary/xenia-canary/releases/tag/0a1b2c3",
                          "2026-11-30")
    window = _window(folders, newer_release=lambda: release)
    deadline = time.monotonic() + 10
    while window.newer is None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    tip = window.emulator_state.toolTip()                   # the line stays the state; the tip and the log say
    assert window.emulator_state.text() == "Installed. Uninstall with the Uninstall button."
    assert "Xenia 0a1b2c3 is out (2026-11-30)" in tip and "releases/tag/0a1b2c3" in tip
    assert "Xenia 0a1b2c3 is out (2026-11-30)" in window.output.toPlainText()
    assert window.install_pill.isEnabled() is False                                # it never installs that one
    window.close()


def test_the_log_tab(qapp, folders):
    """What the window says goes to the Log tab with the time, after what the log file held already."""
    folders["log_path"].write_text("07-11-2026 22:14:00 INFO Xenia Manager 2.2.0 started\n")
    window = _window(folders)
    assert window.output.toPlainText().splitlines() == ["07-11-2026 22:14:00 INFO Xenia Manager 2.2.0 started"]
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
    log.write_text("18-11-2026 10:00:00 INFO Xenia Manager started\n")
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


def test_the_blueprint_layout(qapp, folders):
    """The managers' design (owner, 18-11-2026, PPSSPP Manager's): the window 900 wide when it opens, which is also
    its narrowest, and what is in it asks for no more (no Play time: Xenia counts none); the six tabs
    share the whole width, the last one up to the margin, with no line over them; under the header's pills the two
    links alone, in the type of a pill's caption, each still a link."""
    import re
    window = _window(folders)
    window.show()
    qapp.processEvents()
    bar = window.tabs.tabBar()
    assert window.width() == 900 == window.minimumWidth()
    assert window.centralWidget().minimumSizeHint().width() <= 900 and window.height() == 606
    assert window.tabs.widget(3) is window.settings_scroll                      # the Settings tab scrolls: no higher
    assert window.settings_scroll.widget() is window.settings_page and window.settings_scroll.widgetResizable()
    assert window.tabs.tabText(2) == "Memory cards" and window.tabs.widget(2) is window.saves_page
    assert not hasattr(window, "time_box")
    assert bar.count() == 6 and len({bar.tabRect(i).width() for i in range(6)}) <= 2    # equal but for a pixel
    assert not bar.drawBase()
    assert bar.tabRect(0).left() <= 1 and abs(bar.tabRect(5).right() - (window.tabs.width() - 1)) <= 1
    assert re.sub(r"<[^>]+>", "", window.intro.text()) == "Xenia's release notes · Wiki"
    assert window.intro.styleSheet() == window.refresh_pill.caption.styleSheet() == style.CAPTION
    assert f"href='{emulator.RELEASE_PAGE}'" in window.intro.text() and "text-decoration:none" in window.intro.text()
    assert style.BLUE not in window.intro.text() and window.intro.openExternalLinks()
    window.close()



def test_covers_with_the_suites_key(qapp, folders, monkeypatch, tmp_path):
    """Steam artwork… keeps the suite's key; Update Steam then looks up the game by its title and puts
    SteamGridDB's pictures in place of all four drawn ones, and a game in Steam not looked up yet makes the button do
    something again."""
    import json

    from PyQt6.QtGui import QColor, QImage
    from PyQt6.QtWidgets import QInputDialog

    from xenia_manager import LOGO_PATH

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
                                                          "url": "https://cdn2.steamgriddb.com/x.png"}]}).encode()
        return (tmp_path / "blue.png").read_bytes()
    _install(folders["home"])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    key = tmp_path / "key"
    window = _window(folders, covers_home=tmp_path / "covers", covers_get=get, covers_key=key)
    row = _titles(window).index("Two")
    window.table.item(row, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    _wait(window, qapp)
    assert asked == [] and not window.steam_button.isEnabled()                  # no key: nothing asked
    monkeypatch.setattr(QInputDialog, "exec", lambda self: (self.setTextValue("0123456789abcdef"), 1)[1])
    window.on_covers()
    assert key.read_text() == "0123456789abcdef\n"
    game = window.games[row]
    assert window.no_cover == {str(game.file)} and window.steam_button.isEnabled()
    window.on_update_steam()
    _wait(window, qapp)
    assert window.running.text().startswith("Covers: SteamGridDB had pictures for 1 of 1 game(s).\n1 game(s) in")
    assert asked[0].endswith("search/autocomplete/Two")
    assert any("heroes/" in url for url in asked) and any("logos/" in url for url in asked)
    assert "0123456789abcdef" not in window.output.toPlainText()
    name = shortcuts.names([game])[game.file]
    number = shortcuts.entry(game, name, folders["run"], LOGO_PATH)["appid"] & 0xFFFFFFFF
    grid = steam.user_folders(folders["steam_dir"])[0] / "grid"
    for suffix in ("p", "", "_hero"):
        image = QImage(str(grid / f"{number}{suffix}.png"))
        assert image.pixelColor(image.width() // 2, image.height() // 2).name() == "#0000ff", suffix
    assert QImage(str(grid / f"{number}_logo.png")).size() == picture.size()
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
    target = tmp_path / "Games" / "XBOX360" / "One.iso"
    assert target.exists()
    seen = []
    monkeypatch.setattr(KeepDialog, "exec", lambda self: (seen.append(self.items), QDialog.DialogCode.Rejected)[1])
    window.on_remove_game()
    assert [item.label for item in seen[0]] == ["One.iso (the game)"] and target.exists()
    assert window.running.text() == "Nothing was deleted."

    def keep_it(self):
        self.items[0].delete = False
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(KeepDialog, "exec", keep_it)
    window.on_remove_game()
    _wait(window, qapp)
    assert target.exists() and window.running.text() == "One: deleted nothing. Kept: One.iso (the game)."
    window.table.selectRow(0)
    monkeypatch.setattr(KeepDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.on_remove_game()
    _wait(window, qapp)
    assert not target.exists() and window.running.text() == "One: deleted One.iso (the game)."
    assert "One" not in [window.table.item(r, 1).text() for r in range(window.table.rowCount())]
    window.close()


def test_the_settings_tab(qapp, folders, tmp_path):
    """The Settings tab holds Xenia's settings in the app (core's settings_page): Xenia's defaults while there is no
    file, a change written into Xenia's own folder at once, and nothing while Xenia runs."""
    xenia_home = tmp_path / "Xenia"
    running = [False]
    window = _window(folders, xenia_home=xenia_home, xenia_running=lambda: running[0])
    page = window.settings_page
    assert window.tabs.widget(3).widget() is page and page.widgets["gpu"].currentText() == "Automatic (Vulkan)"
    assert page.widgets["letterbox"].isChecked() and page.widgets["license"].currentData() == "0"
    page.widgets["scale"].setCurrentIndex(page.widgets["scale"].findData("2"))
    text = (xenia_home / emulator.CONFIG).read_text()
    assert "draw_resolution_scale_x = 2" in text and "draw_resolution_scale_y = 2" in text
    assert page.status.text() == "Resolution scale: 2x (1440p)."
    running[0] = True
    page.widgets["mute"].setChecked(True)
    assert "mute" not in (xenia_home / emulator.CONFIG).read_text() and "Xenia is running" in page.status.text()
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
    window.table.selectRow(1)
    title = window.chosen().title
    tabs.tabBarClicked.emit(start)                                           # chosen, but not in Steam yet
    assert opened == [] and window.running.text() == (f"{title} is not in Steam yet: tick it and press Update Steam "
                                                      "first.")
    window.table.item(1, 0).setCheckState(Qt.CheckState.Checked)
    window.on_update_steam()
    _wait(window, qapp)
    window.table.selectRow(1)
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
    window.table.selectRow(1)
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
    """Start game with Steam closed (owner, 20-11-2026, first in shadPS4 Manager: Steam came up and the game never
    started, while the line said it did): Steam is started and waited for before the game's address is given, and
    what went wrong is said. While Xenia runs, no second one is started."""
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
    window.xenia_running = lambda: True
    window.table.selectRow(0)
    window.on_start_game()
    assert window.running.text() == "Xenia is running: close it first, then start the game."
    window.close()


def test_a_game_in_steam_more_than_once_is_said_and_update_steam_leaves_one(qapp, folders, monkeypatch):
    """Owner, 20-11-2026 (first in shadPS4 Manager: "multiple entries for the same game in Steam ... a check for
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
    import xenia_manager.main_window as module
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


def test_exit_xenia_is_on_while_xenia_runs_and_ends_it_at_once(qapp, folders):
    """Exit Xenia (owner, 22-11-2026): the first button of the row under Your games, on only while Xenia runs; a
    click ends it with no question and the line under the tabs says so."""
    runs = [True]
    ended: list[int] = []

    def end() -> list[int]:
        ended.append(1)
        runs[0] = False
        return [10]

    window = _window(folders, xenia_running=lambda: runs[0], xenia_end=end)
    row = window.exit_button.parentWidget().layout()
    buttons = next(row.itemAt(i).layout() for i in range(row.count())
                   if row.itemAt(i).layout() is not None and row.itemAt(i).layout().indexOf(window.exit_button) >= 0)
    assert buttons.indexOf(window.exit_button) + 1 == buttons.indexOf(window.xenia_button)
    assert window.exit_button.text() == "Exit Xenia"
    assert "without saving" in window.exit_button.toolTip()
    assert window.exit_button.isEnabled()
    window.exit_button.click()
    assert ended == [1]
    assert window.running.text() == "Xenia was ended."
    assert not window.exit_button.isEnabled()
    window.xenia_end = lambda: []
    window.on_exit_xenia()
    assert window.running.text() == "Xenia was not running."
    window.close()


def test_xenia_running_and_end_read_proc(tmp_path):
    """Xenia's process is found by its name, and ending it ends what it started first."""
    proc = tmp_path / "proc"
    for pid, comm, state, parent in ((10, emulator.MEMBER[:15], "S", 1), (20, "child", "S", 10), (30, "bash", "S", 1)):
        (proc / str(pid)).mkdir(parents=True)
        (proc / str(pid) / "comm").write_text(comm + "\n")
        (proc / str(pid) / "stat").write_text(f"{pid} ({comm}) {state} {parent} 0\n")
    assert emulator.running(proc)
    sent: list[int] = []
    assert processes.end(processes.find(emulator.is_xenia, proc), proc, kill=lambda pid, sig: sent.append(pid))
    assert sent == [20, 10]
    (proc / "10" / "stat").write_text(f"10 ({emulator.MEMBER[:15]}) Z 1 0\n")
    assert not emulator.running(proc)


def test_view_logs_shows_the_emulators_log_too(qapp, folders):
    """View logs (owner, 26-11-2026): two radio buttons above the log choose the app's log or what Xenia printed
    (emulator.log beside it, which the run wrapper writes). The hint names the file shown. A line the app logs
    shows only while its own log is shown. Clear logs empties the log shown, with its older ones."""
    from xenia_manager import APP_NAME
    log = folders["log_path"]
    log.write_text("26-11-2026 10:00:00 INFO the app's line\n")
    emulator_log = log.with_name("emulator.log")
    emulator_log.write_text("26-11-2026 10:00:01 INFO Xenia started: ~/game\nprinted\n")
    older = log.with_name("emulator.log.1")
    older.write_text("old\n")
    window = _window(folders)
    page = window.log_page
    assert page.app_button.text() == APP_NAME and page.emulator_button.text() == "Xenia"
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
