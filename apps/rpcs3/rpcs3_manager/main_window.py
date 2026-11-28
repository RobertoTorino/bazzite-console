# SPDX-License-Identifier: GPL-3.0-or-later
"""The main window, built as PS5 PCSX2 Manager's (owner, 24-10-2026: the manager that works is the pattern for the others):
the header with the Refresh pill and the state boxes, a row of action pills (Install and Uninstall for RPCS3, Install
for the firmware, Install for the games, Account for RPCN) in place of the three numbered steps with buttons, the state of each (RPCS3,
the firmware, the disc games, the PKG games) in a line, then the tabs: the games found, each with a box for Steam and
how it fills the screen; RPCS3's settings (settings_page.py); the saves on its hard disk (Memory cards, saves_page.py);
and the app's log, with Clear logs beside it. Downloading RPCS3, asking GitHub for a newer one and changing Steam's
files run off the GUI thread; nothing here needs root. The look is the app's own blue (style.py). Steam artwork… takes
the suite's SteamGridDB API key, with which Update Steam looks up the cover for each game first (core's covers).

A game runs from Steam: the tab beside Your games, Start game, starts the chosen one there (owner, 12-11-2026). While
RPCS3 is installed and not running, the window keeps what the app owns in RPCS3's files (userdata.py): its welcome
dialog and update check off, player 1 on the first controller. RPCS3's own window is opened only for RPCS3's settings
(RPCS3 settings, under the games). The packages RPCS3 installs without its window (--headless --installpkg, one run per
file, the window's job meanwhile; owner, 24-10-2026), and the firmware too (--headless --installfw; owner, 11-11-2026:
RPCS3's window and its Success! box came up when the firmware was dropped in its folder); the result is read from
RPCS3's log. The window also reads the volume Bazzite remembers for RPCS3 and says when it is muted (found on the
board). What the window says it also writes to the app's log (core's applog), shown in the View logs tab.

The owner's order of 20-11-2026, PS5 shadPS4 Manager's, replaces the one above: the header's pills are RPCS3's (its
version, Install, Uninstall) and Refresh; the row under them the games' pills and Available in Steam, with Play
time where the emulator counts it; then two columns, the state lines and the installed version beside them; then the
tabs, Memory cards before Settings and the log's as View logs."""

from __future__ import annotations

import subprocess
import time
from html import escape
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QBrush, QCloseEvent, QColor, QResizeEvent
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QLabel, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
                             QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from bazzite_console_core import SUITE_MANUAL_URL, applog, covers, sound, steam, window_title
from bazzite_console_core import __version__ as CORE_VERSION
from bazzite_console_core import keep, renamed
from bazzite_console_core import builds
from bazzite_console_core.action_tab import ActionTab
from bazzite_console_core.builds_dialog import BuildsDialog, fill_menu
from bazzite_console_core.keep_dialog import KeepDialog
from bazzite_console_core.log_page import LogPage
from bazzite_console_core.platform import bin_home, notify, private, xdg_open
from bazzite_console_core.settings import SettingsStore
from bazzite_console_core.updates import ReleaseInfo, UpdateChecker
from bazzite_console_core.widgets import AppHeader, InfoButton, MetricBox, StatusText, WrappedLabel, hint_label

from . import (APP_ID, APP_NAME, INFO, LOGO_PATH, ROOT, __version__, controllers, emulator, library, rpcn, shortcuts,
               style, userdata)
from .games import Game, installed, scan
from . import settings_page
from .settings_page import SettingsPage
from .rpcn_dialog import RpcnDialog
from .saves_page import SavesPage

MANUAL_URL = f"{SUITE_MANUAL_URL}apps/rpcs3/"
STEAM_TIP = "Add the ticked games to Steam and take out the others; Steam closes for it and starts again"
START_TIP = "Start the game chosen under Your games through Steam, as its shortcut in Steam does"
EXIT_TIP = "End RPCS3 at once, with no question. A game that is running ends without saving"
RPCN_WATCH_MS = 5000
CLEAR_TIP = "Empty the app's log file, with the older ones kept beside it, and the View logs tab"
STEAM_ON = "Steam runs and is signed in. The games in Steam can start."
STEAM_OFF = "Steam does not run or is not signed in. Start Steam and sign in before you start a game."
NO_SFB = "PS3_DISC.SFB is missing or damaged in this disc game's folder: RPCS3 does not start it without"
RUNNING = "RPCS3 is running: close it first, it writes its own settings over the change when it closes."
RUNNING_INSTALL = "RPCS3 is running: close it first; packages are installed while RPCS3 is closed."
STEAM_URL = "steam://open/games"        # Steam's library; Steam starts when it does not run
STEAM, GAME, SERIAL, VERSION, FOLDER, SCREEN = range(6)     # the table's columns (the screen last; owner)
WIDTH = 900                             # the window opens this wide, and is never narrower (owner, 18-11-2026)
HEIGHT = 606                            # the window opens this high (owner, 18-11-2026); it was 800
GAMES, START, SAVES, SETTINGS, LOG = range(5)               # the tabs
# The emulator's line: the state alone, the same words in every manager (owner, 07-11-2026); the version and the
# advice are in its tip.
NOT_INSTALLED = "Not installed. Install it with the Install button."
INSTALLED = "Installed. Uninstall with the Uninstall button."
VERSIONS_TIP = "Put another installed RPCS3 build in use, or download one in the version manager"


def _packages_in(hdd0_game: Path) -> tuple[set[str], set[str]]:
    """(the installed games, the licenses) in RPCS3's folder: compared before and after an install."""
    return ({str(g.eboot) for g in installed(hdd0_game)},
            {p.name for p in userdata.licenses(hdd0_game.parent)})


def install_message(report: userdata.InstallReport, new_games: int, new_licenses: int, folder: str,
                    log_path: Path) -> tuple[bool, str]:
    """What to say after an install, from RPCS3's log (the titles) and what came into RPCS3's folders (the counts,
    when the log says nothing of them)."""
    def named(items: list[tuple[str, str]]) -> str:
        return ", ".join(f"{title} ({serial})" if serial else title for title, serial in items)
    parts = []
    if report.installed:
        parts.append(f"{len(report.installed)} game(s) installed in RPCS3: {named(report.installed)}")
    elif new_games:
        parts.append(f"{new_games} game(s) installed in RPCS3")
    copied = len(report.copied) or new_licenses
    if copied:
        parts.append(f"{copied} license(s) copied into RPCS3")
    if report.failed:
        parts.append(f"{len(report.failed)} package(s) RPCS3 could not install: {named(report.failed)}")
    if report.invalid:
        parts.append(f"{report.invalid} file(s) that are no PS3 package")
    if report.not_copied:
        parts.append(f"{len(report.not_copied)} license(s) RPCS3 could not copy: " + ", ".join(report.not_copied))
    if not parts:
        return False, f"RPCS3 installed nothing from {folder}. RPCS3's log: {log_path}"
    text = "; ".join(parts) + "."
    if report.problems:
        return False, f"{text} RPCS3's log: {log_path}"
    return True, text


RUNNING_REMOVE = "RPCS3 is running: close it first, then remove the game."
RUNNING_START = "RPCS3 is running: close it first, then start the game."
UNINSTALL_GAME_TIP = ("Delete the game chosen under Your games from the disk: a window lists what would go, and you "
                      "untick what to keep; nothing is deleted before you confirm")


def _with_info(state: QLabel, info: InfoButton) -> QWidget:
    """A state line with its info symbol right after it, at the top of its first line. The line is short, so it
    keeps to one line: wrapped, it took the narrowest width beside the symbol."""
    state.setWordWrap(False)
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(state)
    layout.addWidget(info, 0, Qt.AlignmentFlag.AlignTop)
    layout.addStretch(1)
    return row


def _version_key(version: str) -> tuple[int, ...]:
    """A firmware version for comparing ("4.92" < "4.93"); the parts that are no number count as 0."""
    return tuple(int(part) if part.isdigit() else 0 for part in version.split("."))


class RpcsSettings(SettingsStore):
    DEFAULTS: dict = {"pads_for": [],           # the controllers (the kernel's names) the pad file was written for
                      "firmware_given": ""}     # the PUP in Games/PS3/Firmware given to RPCS3 last (library.file_key)


class MainWindow(QMainWindow):
    CONTROLLER_POLL = 3000                  # ms: how often the window looks for a controller
    # The desktop notification when the window opens without a controller (owner, 28-11-2026); another in the tests.
    notify_desktop = staticmethod(notify)

    def __init__(self, home: Path | None = None, rpcs3_home: Path | None = None, steam_dir: Path | None = None,
                 run: Path | None = None, fetch: emulator.Download = emulator.download,
                 steam_closed=steam.with_steam_closed, steam_running=steam.steam_running,
                 newer_release=emulator.newer_release, rpcn_connect: rpcn.Connect = rpcn._connect,
                 covers_home: Path | None = None,
                 covers_get: covers.Get = covers._get, covers_key: Path | None = None,
                 log_path: Path | None = None, devices: Path = controllers.DEVICES,
                 rpcs3_running=userdata.rpcs3_running, rpcs3_end=userdata.end_rpcs3,
                 sdl_names=controllers.sdl_names, open_url=xdg_open,
                 rpcs3_log: Path | None = None, sound_state: Path | None = None,
                 user_home: Path | None = None, drives: Callable[[], list[Path]] = library.removable_drives,
                 steam_play=steam.play):
        """*home*: where the app installs RPCS3; *rpcs3_home*: RPCS3's own folder; *steam_dir*: Steam's folder
        (None: looked up); *run*: the run wrapper the shortcuts start; *fetch*: the download; *steam_closed* and
        *steam_running*: closing Steam for a change and asking whether it runs; *newer_release*: asks GitHub for a
        newer RPCS3; *covers_home*, *covers_get* and *covers_key*: where the covers are kept, how SteamGridDB is asked
        and the suite's key file (tests never touch the real ones); *log_path*: the app's log file, as the View logs tab
        shows it (__main__ set it up); *devices*: the kernel's list of input devices, for the controller state;
        *rpcs3_running*: whether RPCS3 runs (its files are not written then); *sdl_names*: the controllers as SDL
        names them, for RPCS3's pad file; *open_url*: opens a URL on the desktop (the Steam link); *rpcs3_log*:
        RPCS3's own log, read for what a headless install did; *sound_state*: WirePlumber's file with the volume
        the desktop remembers for RPCS3 (tests pass their own); *user_home*: the home
        folder with the app's own game folder, Games/PS3 (library.fixed); *drives*: the removable drives looked at
        for one.
        *steam_play*: starts a game by its Steam address and waits until it runs (Start game)."""
        super().__init__()
        self.setMinimumWidth(WIDTH)                     # never narrower (owner, 18-11-2026)
        self.resize(WIDTH, HEIGHT)
        self.home = home or emulator.emulator_home()
        self.rpcs3_home = rpcs3_home or userdata.rpcs3_home()
        self.steam_dir = steam_dir if steam_dir is not None else steam.find_steam()
        self.run_path = run or bin_home() / shortcuts.RUN_NAME
        self.fetch = fetch
        self.user_home = user_home or Path.home()
        self.drives = drives
        self.steam_closed = steam_closed
        self.steam_running = steam_running
        self.covers_home = covers_home or covers.covers_home(APP_ID)
        self.covers_get = covers_get
        self.covers_key = covers_key
        self.log_path = log_path or applog.log_file(APP_ID)
        self.devices = devices
        self.rpcs3_running = rpcs3_running
        self.rpcs3_end = rpcs3_end
        self.sdl_names = sdl_names
        self.open_url = open_url
        self.steam_play = steam_play
        self.rpcs3_log = rpcs3_log or userdata.rpcs3_log()
        self.sound_state = sound_state or sound.stream_properties()
        self.sound: tuple[float, bool] | None = None    # (volume, muted) Bazzite remembers for RPCS3; None: unknown
        self._sound_said = False                        # said once while it stays off
        self._pin_noted = False                         # another build installed than the app brings: logged once
        self.controllers: list[str] | None = None       # the controllers last seen; None before the first look
        self.log = applog.logger(APP_ID)
        self._newer_release = newer_release
        self.newer: ReleaseInfo | None = None           # RPCS3's newest landmark, when newer than the pinned one
        self.rpcn_connect = rpcn_connect                # opens a connection to an RPCN server (tests pass fakes)
        self.rpcn_account = rpcn.Account()
        self._rpcs3_was_running = False
        self.rpcn_check = UpdateChecker(self)           # whether the RPCN server answers, off the GUI thread
        self.rpcn_check.finished.connect(self._rpcn_checked)
        self.rpcn_watch = QTimer(self)                  # while RPCS3 runs: its log says whether it signed in
        self.rpcn_watch.setInterval(RPCN_WATCH_MS)
        self.rpcn_watch.timeout.connect(self._watch_rpcn)
        self.release_check = UpdateChecker(self)        # apart from the worker: it runs while the window opens
        self.release_check.finished.connect(self._release_found)
        self.settings = RpcsSettings(INFO, self)
        self.worker = UpdateChecker(self)            # one job at a time off the GUI thread: a download, an
        #                                              install of packages or Steam
        self.worker.finished.connect(self._job_done)
        self.games: list[Game] = []
        self.in_steam: dict[str, str] = {}
        self.moved: dict[str, str] = {}               # a game found again under another name: its file in Steam
        self._moved_said: set[str] = set()
        self.no_cover: set[str] = set()               # games in Steam not yet looked up on SteamGridDB, with a key
        self.doubles: dict[str, int] = {}             # games in Steam more than once: how many shortcuts too many
        self._doubles_said: dict[str, int] = {}
        self.version = ""
        self.replaced = False                       # RPCS3 updated itself to a build the app was not tried with
        self.firmware = ""
        self.folders: list[Path] = []

        header = AppHeader(LOGO_PATH, APP_NAME, __version__)
        # The states on the right of the title row, ending at the middle of the last pill below them (owner,
        # 24-10-2026): a spacer of half that pill's width after them, set whenever the window's size changes.
        self.pill = StatusText(name="Installed")
        header.add_action(self.pill)
        self.rpcn_pill = StatusText(name="RPCN")          # RPCN Online, Offline or Off (owner, 18-11-2026)
        header.add_action(self.rpcn_pill)
        self.controller = StatusText(name="Controller")   # beside it: whether a controller is connected
        header.add_action(self.controller)
        self.steam_state = StatusText(name="Steam")       # and whether Steam runs and is signed in (owner,
        header.add_action(self.steam_state)               # 22-11-2026): a game in Steam starts only then
        self._steam_on: bool | None = None
        self.states_spacer = QWidget()
        self.states_spacer.setFixedSize(0, 1)
        header.add_action(self.states_spacer)
        self.controller_timer = QTimer(self)
        self.controller_timer.setInterval(self.CONTROLLER_POLL)
        self.controller_timer.timeout.connect(self.show_controller)
        self.controller_timer.timeout.connect(self.show_steam)
        self.controller_timer.timeout.connect(self.show_exit)
        self.show_steam()
        self.controller_timer.start()
        self.refresh_pill = style.action_pill("Refresh", "Click to refresh", "Read the state again and look for games")
        self.refresh_pill.clicked.connect(self.refresh)
        # The version is a pill (owner, 20-11-2026, as shadPS4's own launcher): its menu puts another installed
        # build in use, or opens the version manager (core's builds_dialog).
        self.emulator_box = style.action_pill("—", "RPCS3 version", VERSIONS_TIP)
        self.versions_menu = QMenu(self)
        self.emulator_box.clicked.connect(self.on_versions_menu)
        self.steam_box = MetricBox("Available in Steam", style.BLUE)
        # The two links alone (owner, 18-11-2026), in the type of a pill's caption (Click to refresh): what the
        # app is for is in the wiki.
        self.intro = hint_label(style.caption_link(self, emulator.RELEASE_PAGE, "RPCS3's release notes") + " · "
                                + style.caption_link(self, MANUAL_URL, "Wiki"), follow_height=True)
        self.intro.setStyleSheet(style.CAPTION)

        # What there is to do, as pills the size of the header's, spread over the window's width (owner,
        # 24-10-2026): what it is for in large type (RPCS3, Games), what the pill does under it (Install, Uninstall).
        # The disc games and the firmware are put in the app's own folder, Games/PS3 (owner, 03-11-2026: fixed
        # folders, no folder choosing); the packages are still chosen from a folder.
        self.install_pill = style.action_pill("RPCS3", "Install", f"Download RPCS3 {emulator.VERSION} from GitHub "
                                                                  f"(about {emulator.SIZE_MB} MB) and check it")
        self.install_pill.clicked.connect(self.on_install)
        self.remove_pill = style.action_pill("RPCS3", "Uninstall", "Remove the installed RPCS3; its own folder "
                                                                   "(firmware, saves, settings, installed games) "
                                                                   "stays")
        self.remove_pill.clicked.connect(self.on_remove)
        self.package_pill = style.action_pill("Games", "Install", "Choose the folder with your .pkg files (and "
                                                                  "the .rap license of a PSN game); RPCS3 installs "
                                                                  "them, without opening its window")
        self.package_pill.clicked.connect(self.on_install_packages)
        # RPCN Account (owner, 18-11-2026: RPCS3 has RPCN as shadPS4 has shadNet)
        self.account_pill = style.action_pill("RPCN", "Account", "Your RPCN account: create one, try it, and "
                                                                "have RPCS3 sign in with it")
        self.account_pill.clicked.connect(self.on_rpcn)
        # Games Uninstall (owner, 20-11-2026): a pill in place of the Remove game… button under the table
        self.remove_game_pill = style.action_pill("Games", "Uninstall", UNINSTALL_GAME_TIP)
        self.remove_game_pill.clicked.connect(self.on_remove_game)
        # Play time (owner, 18-11-2026): all games together, as RPCS3 counts it
        self.time_box = MetricBox("Play time", style.BLUE)
        # The owner's order (20-11-2026), as PS5 shadPS4 Manager's. The header: RPCS3's version, Install and
        # Uninstall, then Refresh. The row under it: the games' Install and Uninstall, Available in Steam, RPCN's Account and Play time
        # (the Your games box went: the table lists them). Each row's pills share the width in equal parts.
        self.header_pills = [self.emulator_box, self.install_pill, self.remove_pill, self.refresh_pill]
        for box in self.header_pills:
            box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            header.add_second(box, 1)
        self.actions = [self.package_pill, self.remove_game_pill, self.account_pill]    # the row's pills that act
        self.second_row = [self.package_pill, self.remove_game_pill, self.steam_box, self.account_pill,
                           self.time_box]
        actions = QHBoxLayout()
        actions.setSpacing(8)
        for pill in self.second_row:                    # each a fifth of the width, whatever the window's
            pill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            actions.addWidget(pill, 1)

        grid = QGridLayout()        # the state of each: RPCS3, the firmware, the disc games, the PKG games (owner)
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        self.emulator_state, self.firmware_state, self.disc_state, self.pkg_state, self.rpcn_state = (
            self._state_label() for _ in range(5))
        self.disc_state.setOpenExternalLinks(False)     # a folder's name is a link that takes it out
        # The firmware's state and the game folders by name, what to do behind the info symbol (owner, 11-11-2026).
        self.firmware_info = InfoButton("", "About the firmware")
        self.disc_info = InfoButton("", "About the game folders")
        infos = {id(self.firmware_state): self.firmware_info, id(self.disc_state): self.disc_info}
        for row, (name, state) in enumerate((("RPCS3", self.emulator_state), ("Firmware", self.firmware_state),
                                             ("Disc games", self.disc_state), ("PKG games", self.pkg_state),
                                             ("RPCN", self.rpcn_state))):
            grid.addWidget(self._name_label(name), row, 0)
            info = infos.get(id(state))
            grid.addWidget(_with_info(state, info) if info else state, row, 1)
        # A second column beside the states (owner, 20-11-2026): the RPCS3 version installed
        self.version_state = self._state_label()
        second = QGridLayout()
        second.setColumnStretch(1, 1)
        second.setHorizontalSpacing(14)
        second.setVerticalSpacing(6)
        second.addWidget(self._name_label("Installed version"), 0, 0)
        second.addWidget(self.version_state, 0, 1)
        second.setRowStretch(1, 1)
        columns = QHBoxLayout()
        columns.setSpacing(14)
        columns.addLayout(grid, 1)
        columns.addLayout(second, 1)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["In Steam", "Game title", "Id", "Version", "Folder", "Screen setting"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        head = self.table.horizontalHeader()
        for column, mode in enumerate((QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.Stretch,
                                       QHeaderView.ResizeMode.ResizeToContents,
                                       QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.Stretch,
                                       QHeaderView.ResizeMode.ResizeToContents)):
            head.setSectionResizeMode(column, mode)
        self.table.itemChanged.connect(lambda _item: self._update_buttons())

        # Exit RPCS3 (owner, 22-11-2026): the first button of the row, on while RPCS3 runs; a click ends it at once
        self.exit_button = QPushButton("Exit RPCS3")
        self.exit_button.setToolTip(EXIT_TIP)
        self.exit_button.clicked.connect(self.on_exit_rpcs3)
        self.show_exit()
        self.rpcs3_button = QPushButton("RPCS3 settings")
        self.rpcs3_button.setToolTip("Open RPCS3's own window for what the app does not set yet: its settings, "
                                     "the controllers (Pads) and game updates (File > Install Packages)")
        self.rpcs3_button.clicked.connect(self.on_open_rpcs3)
        self.covers_button = QPushButton("Steam artwork…")
        self.covers_button.setToolTip("The SteamGridDB API key, one for the whole suite: with it, Update Steam "
                                      "gives each game its cover from SteamGridDB in Steam; the wide picture, the "
                                      "banner and the logo stay the game's own")
        self.covers_button.clicked.connect(self.on_covers)
        self.steam_button = style.primary_button("Update Steam", STEAM_TIP)
        self.steam_button.clicked.connect(self.on_update_steam)
        buttons = QHBoxLayout()
        # What the boxes, Screen setting and Start game do, behind an info symbol (owner, 18-11-2026, in place of a
        # line of text)
        self.steam_info = InfoButton("A checkmark before a game adds the game to Steam. Screen setting sets how it "
                                     "fills the screen. When the Start game button is clicked the game starts from "
                                     f"{style.link(self, STEAM_URL, 'Steam')}.", "About the games and Steam")
        self.steam_info.opens = lambda _url: self.open_steam()      # the app opens Steam itself (open_steam)
        buttons.addWidget(self.steam_info)
        buttons.addStretch(1)
        buttons.addWidget(self.exit_button)
        buttons.addWidget(self.rpcs3_button)
        buttons.addWidget(self.covers_button)
        buttons.addWidget(self.steam_button)
        games_page = QWidget()
        games = QVBoxLayout(games_page)
        games.setContentsMargins(0, 8, 0, 0)
        games.addWidget(self.table, 1)
        games.addLayout(buttons)

        self.settings_page = SettingsPage(self.rpcs3_home, self.rpcs3_running, self.log)
        self.settings_page.sound_path = self.sound_state
        self.settings_page.sound_changed.connect(self.show_sound)
        # View logs (owner, 26-11-2026): the app's own log or what RPCS3 printed, chosen above it (core's
        # log_page)
        self.log_page = LogPage(APP_NAME, "RPCS3", self.log_path,
                                "Everything the app said and did, newest last, and each game started from Steam.")
        self.output = self.log_page.output
        self.tabs = QTabWidget()
        # The six tabs share the whole width, the last one up to the window\'s margin (owner, 18-11-2026)
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setDrawBase(False)           # no line over the tabs, which that mode draws
        self.tabs.addTab(games_page, "Your games")
        # Start game (owner, 12-11-2026): a tab that is a button, which starts the chosen game in Steam; beside
        # Your games, where the game is chosen (owner, 18-11-2026)
        self.start_tab = ActionTab(self.tabs, "Start game", START_TIP, self.on_start_game)
        # The Settings tab scrolls when it is higher than the window (owner, 18-11-2026): it never makes the window
        # higher than it opens.
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll.setWidget(self.settings_page)
        # Memory cards (owner, 18-11-2026): the saves on RPCS3's hard disk (saves_page.py)
        self.saves_page = SavesPage(lambda: getattr(self, "hdd0_game", self.rpcs3_home / "dev_hdd0" / "game").parent,
                                    self.rpcs3_running, self.log)
        self.tabs.addTab(self.saves_page, "Memory cards")
        # Memory cards before Settings, and the log's tab is View logs (owner, 20-11-2026)
        self.tabs.addTab(self.settings_scroll, "Settings")
        self.tabs.addTab(self.log_page, "View logs")
        # Clear logs (owner, 18-11-2026): beside the View logs tab, a tab that is a button and empties the log
        self.clear_tab = ActionTab(self.tabs, "Clear logs", CLEAR_TIP, self.on_clear_logs)

        self.running = WrappedLabel()
        self.running.setStyleSheet("font-weight:600;")
        self.running.setWordWrap(True)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addLayout(header)
        lay.addWidget(self.intro)
        lay.addSpacing(4)
        lay.addLayout(actions)
        lay.addSpacing(4)
        lay.addLayout(columns)
        lay.addSpacing(6)
        lay.addWidget(self.tabs, 1)
        lay.addWidget(self.running)
        version = QLabel(f"{APP_NAME} {__version__} · core {CORE_VERSION} · RPCS3 {emulator.VERSION}")
        version.setStyleSheet("color:palette(placeholder-text);")
        lay.addWidget(version, 0, Qt.AlignmentFlag.AlignRight)
        self.setCentralWidget(central)
        style.apply(self)

        geometry = self.settings.window_state("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.refresh()
        self.release_check.start(self._newer_release)

    @staticmethod
    def _name_label(name: str) -> QLabel:
        """What a state line is about, bold, with a colon (owner, 20-11-2026)."""
        label = QLabel(f"{name}:")
        label.setStyleSheet("font-weight:700;")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        return label

    @staticmethod
    def _state_label() -> QLabel:
        label = WrappedLabel()                  # its lines count in the window's minimum height
        # Its links take a click too: without the second flag a click on one did nothing (owner, 24-10-2026, in
        # PS5 shadPS4 Manager's window, built the same way).
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse
                                      | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        return label

    # --- State ------------------------------------------------------------------------------------------------

    def refresh(self) -> None:
        self.version = emulator.installed_version(self.home)
        self.replaced = bool(self.version) and emulator.replaced(self.home)
        vfs = userdata.read_map(self.rpcs3_home / "vfs.yml")
        self.dev_flash = userdata.drive(self.rpcs3_home, vfs, "/dev_flash/")
        self.hdd0_game = userdata.drive(self.rpcs3_home, vfs, "/dev_hdd0/") / "game"
        self.firmware = userdata.firmware_version(self.dev_flash)
        self.known = list(userdata.known_games(self.rpcs3_home).values())
        self.folders = library.fixed(self.user_home, self.drives)
        self.games = scan(self.folders, self.hdd0_game, self.known)
        self.prepare_rpcs3()
        self.sync_firmware()
        try:
            self.in_steam = shortcuts.in_steam(self.steam_dir) if self.steam_dir else {}
            self.doubles = shortcuts.doubles(self.steam_dir) if self.steam_dir else {}
            self.no_cover = ({str(g.eboot) for g in self.games if str(g.eboot) in self.in_steam
                              and not covers.known(self.covers_home, shortcuts.cover_name(g))}
                             if covers.read_key(self.covers_key) else set())
        except OSError:
            self.in_steam, self.no_cover = {}, set()
            self.doubles = {}
        # A game renamed or moved after it was put in Steam keeps its mark (owner, 03-11-2026;
        # core's renamed): known by its code, else its file's size.
        found = {str(g.eboot): renamed.identity(g.title_id, g.eboot) for g in self.games}
        known = renamed.load(self.settings.qsettings)
        self.moved = renamed.follow(known, found, self.in_steam)
        renamed.remember(self.settings.qsettings, known, found, self.in_steam)
        self._show_state()
        self._fill_table()
        # The same game in Steam more than once (owner, 20-11-2026): said once, and Update Steam leaves one
        if self.doubles and self.doubles != self._doubles_said:
            titles = {str(g.eboot): g.title for g in self.games}
            names = [f"{titles.get(key) or self.in_steam.get(key) or key} ({extra + 1} times)"
                     for key, extra in self.doubles.items()]
            self.say(f"In Steam more than once: {', '.join(names)}. Update Steam leaves one of each.", ok=False)
        self._doubles_said = dict(self.doubles)
        if self.moved and set(self.moved) != self._moved_said:
            self._moved_said = set(self.moved)
            titles = [g.title for g in self.games if str(g.eboot) in self.moved]
            self.say(f"Found again under a new name or in another folder, with its Steam mark: {', '.join(titles)}. "
                     "Update Steam brings the shortcut in Steam up to date.")
        self.settings_page.load()
        self.saves_page.load()
        self.show_controller()
        self.show_sound()

    def show_sound(self) -> None:
        """The volume Bazzite remembers for RPCS3 (muted or turned down, a game plays without a sound): in the
        Settings tab's Sound box, and said once while it stays off."""
        self.sound = sound.stream_sound(settings_page.STREAM, self.sound_state)
        text, off = self.settings_page.show_sound(self.sound)
        if off and not self._sound_said:
            self.say(text, ok=False)
        self._sound_said = off

    def show_steam(self) -> None:
        """Steam's state beside the title, green while it runs and is signed in, red otherwise."""
        on = steam.signed_in(self.steam_dir)
        if on == self._steam_on:
            return
        self._steam_on = on
        self.steam_state.set_status("Steam signed in" if on else "Steam not signed in", "ok" if on else "bad",
                                    STEAM_ON if on else STEAM_OFF)

    def show_controller(self) -> None:
        """The controller state beside the title: a game started from Steam reads the controller that is there
        when it starts, so the window says when none is (switched off, asleep, not paired)."""
        found = controllers.connected(self.devices)
        if found == self.controllers:
            return
        first = self.controllers is None                # the window's first look
        self.controllers = found
        if found:
            self.controller.set_status("Controller connected" if len(found) == 1 else f"{len(found)} controllers",
                                       "ok", "Connected: " + ", ".join(found) + ". A game started from Steam "
                                       "reads it; Share + Options together open RPCS3's menu in the game, with "
                                       "Exit Game in it.")
            self.prepare_pads()
        else:
            self.controller.set_status("No controller", "warn",
                                       "No controller is connected: switch it on, or press its PS button to wake "
                                       "it, before starting a game from Steam. Without one, RPCS3 plays with the "
                                       "keyboard only.")
            if first:           # said on the desktop too, as the run wrappers do (owner, 28-11-2026)
                self.notify_desktop(APP_NAME, "No controller connected",
                                    "Switch your controller on, or press its PS button to wake it, before you "
                                    "start a game.")
                self.log.warning("No controller was connected when the window opened.")

    def prepare_rpcs3(self) -> bool:
        """RPCS3's files brought to what the app owns (its GUI settings; the pad file follows the controllers,
        prepare_pads), while RPCS3 is installed and does not run; what changed goes to the log. Whether RPCS3's
        files may be written now."""
        if not self.version or self.rpcs3_running():
            return False
        try:
            done = userdata.prepare_gui(self.rpcs3_home)
        except OSError as error:
            self.say(f"RPCS3's settings could not be written: {error}", ok=False)
            return False
        if done:
            self.say(f"RPCS3 set up: {', '.join(done)}.")
        if self.controllers:
            self.prepare_pads()
        return True

    def prepare_pads(self) -> None:
        """Player 1 (and 2) on the controllers connected, in RPCS3's pad file, while the app may write it (RPCS3
        installed and not running, the file not RPCS3's own): the controllers as SDL names them, asked once per
        change of the controllers connected (the kernel's names)."""
        if not self.controllers or not self.version or self.rpcs3_running():
            return
        if not userdata.pads_ours(self.rpcs3_home):
            return
        if (self.settings.get("pads_for") == self.controllers
                and userdata.pad_device(self.rpcs3_home)):           # written for these already
            return
        names = self.sdl_names()
        if names is None:                   # no SDL3 on the system: the kernel's names, which may differ from SDL's
            names = list(self.controllers)
            how = " (as the kernel names it; SDL3 was not found to ask)"
        else:
            how = ""
        devices = userdata.pad_devices(names)
        if not devices:
            return
        try:
            written = userdata.write_pads(self.rpcs3_home, devices)
        except OSError as error:
            self.say(f"RPCS3's pad settings could not be written: {error}", ok=False)
            return
        self.settings.set("pads_for", list(self.controllers))
        if written:
            players = "; ".join(f"player {n} on {device}" for n, device in enumerate(devices, 1))
            self.say(f"RPCS3 set up: {players}{how}.")

    def say(self, text: str, ok: bool = True) -> None:
        """What the window has to say: the line under the tabs, the View logs tab and the log file."""
        self.running.setStyleSheet("font-weight:600;" + ("" if ok else "color:#c62828;"))
        self.running.setText(text)
        self.note(text, ok)

    def note(self, text: str, ok: bool = True) -> None:
        """Into the View logs tab and the log file only: something that happened, not what the window is doing now."""
        (self.log.info if ok else self.log.error)(text)
        stamp = time.strftime(applog.DATE)
        self.log_page.add_line(f"{stamp} {'INFO' if ok else 'ERROR'} {text}")

    def on_clear_logs(self) -> None:
        """Clear logs (owner, 18-11-2026): the log the View logs tab shows emptied, the app's or the emulator's
        (owner, 26-11-2026), with the older ones kept beside it, and the tab with it. Said in the line under the
        tabs only, so the log stays empty."""
        failed = self.log_page.clear(APP_ID)
        if failed is not None:
            self.say(f"The log could not be cleared: {private(failed)}", ok=False)
            return
        self.running.setStyleSheet("font-weight:600;")
        self.running.setText("The log was cleared.")

    def _show_state(self) -> None:
        pinned = emulator.VERSION
        # The state alone in the line (owner, 07-11-2026), the version and the advice in the tip and the log once.
        self.emulator_state.setText(INSTALLED if self.version else NOT_INSTALLED)
        if not self.version:
            self.emulator_box.set_value("—")
            tip = (f"Install downloads RPCS3 {pinned}, the build this version of the app was tried with, and checks "
                   "it before installing it. The app says when a newer RPCS3 is out.")
        elif self.version != pinned:
            self.emulator_box.set_value(self.version.split("-")[0])     # the landmark: the box is not wide enough
            tip = (f"RPCS3 {self.version} is in use; it was not tried on the board. This version of the app was "
                   f"tried with {pinned}: Install puts it back in use.")
            if not self._pin_noted:
                self.note(tip)
                self._pin_noted = True
        elif self.replaced:
            self.emulator_box.set_value("other")
            tip = ("RPCS3 updated itself in its own window to a build this version of the app was not tried with. "
                   f"Install puts back {pinned}.")
        else:
            self.emulator_box.set_value(emulator.LANDMARK)
            tip = f"RPCS3 {pinned}, the build this version of the app was tried with"
        if self.newer is not None:              # in the tip and the log, so the line stays the state (owner)
            tip += (f"\nRPCS3 {self.newer.version} is out ({self.newer.published}). A later version of this app "
                    f"brings it, once it has been tried on the board: {self.newer.url}")
        self.emulator_state.setToolTip(tip)
        self.version_state.setText(escape(self.version) if self.version else "—")   # whole: the pill shortens it
        self.version_state.setToolTip(tip)
        self.emulator_state.setOpenExternalLinks(True)

        page = style.link(self, userdata.FIRMWARE_PAGE, "PlayStation's firmware page")
        # The version alone (owner, 18-11-2026), as PS5 PCSX2 Manager's BIOS line is the dump's name alone
        self.firmware_state.setText(f"<b>{escape(self.firmware)}</b>" if self.firmware else "Uninstalled.")
        self.firmware_info.set_text(f"Download PS3UPDAT.PUP from {page} and drop it in "
                                    f"<b>{escape(private(library.firmware_home(self.user_home)))}</b>: the app "
                                    "installs it. RPCS3 needs the PS3's firmware to start any game.")
        self.firmware_state.setToolTip(f"PS3 firmware {self.firmware or 'none'} in RPCS3's firmware folder: "
                                       f"{self.dev_flash}")

        discs = [g for g in self.games if g.disc]
        pkgs = [g for g in self.games if not g.disc]
        # The app's own folders (owner, 03-11-2026): the home folder's, and a removable drive's when it has one.
        where = ", ".join(f"<b>{escape(private(f))}</b>" for f in self.folders)
        self.disc_state.setText(where)
        self.disc_state.setToolTip("\n".join(private(f) for f in self.folders) + f"\n{len(discs)} disc game(s) found.")
        self.disc_info.set_text(f"Drop your games in {escape(private(self.user_home / library.GAMES_HOME))}, each in a "
                                "folder of its own (with PS3_GAME and PS3_DISC.SFB). A USB drive or an SD card with a "
                                "Games/PS3 folder is also checked for content.")
        # RPCS3's games folder by its path within RPCS3's own folder (dev_hdd0/game/; the whole path when it is
        # elsewhere) while a game is installed in it, "—" while none is (owner, 24-10-2026); the count and what
        # Install takes in the tip.
        if pkgs:
            self.pkg_state.setText(f"<b>{escape(self._games_folder_name())}</b>")
        else:
            self.pkg_state.setText("—")
        self.pkg_state.setToolTip(f"{len(pkgs)} game(s) installed in RPCS3's games folder: {self.hdd0_game}\n"
                                  "Install takes the folder with your .pkg files (a PSN game also needs its .rap "
                                  "license beside them); RPCS3 installs them without opening its window.")
        found = {str(g.eboot) for g in self.games}
        self.steam_box.set_value(str(len(found & set(self.in_steam))))
        self._show_play_time()
        self._show_rpcn()

        if not self.version:
            self.pill.set_status("Not installed", "warn", "Install RPCS3 first.")
        elif not self.firmware:
            self.pill.set_status("No firmware", "warn", "RPCS3 needs the PS3's firmware to start a game.")
        elif not self.games:
            self.pill.set_status("No games", "neutral", "Add the folder with your games.")
        else:
            self.pill.set_status("Ready", "ok", "RPCS3 and its firmware are installed and games were found.")

    def _games_folder_name(self) -> str:
        try:
            return f"{self.hdd0_game.relative_to(self.rpcs3_home).as_posix()}/"
        except ValueError:                      # kept elsewhere (RPCS3's Virtual File System settings)
            return str(self.hdd0_game)

    def _show_play_time(self) -> None:
        """The time spent in all games together, as RPCS3 counts it (its persistent_settings.dat); per game in the
        tip."""
        times = userdata.play_times(self.rpcs3_home)
        total = sum(seconds for seconds, _ in times.values())
        if not total:
            self.time_box.set_value("—", "RPCS3 counts the time spent in each game; none yet.")
            return
        titles = {g.title_id: g.title for g in self.games if g.title_id}
        lines = [f"{titles.get(serial, serial)}: {userdata.played(seconds)}"
                 + (f", last played {time.strftime('%d-%m-%Y %H:%M', time.localtime(last))}" if last else "")
                 for serial, (seconds, last) in sorted(times.items(), key=lambda t: -t[1][0])]
        self.time_box.set_value(userdata.played(total), "The time spent in each game, as RPCS3 counts it:\n"
                                + "\n".join(lines))

    def _release_found(self, release: ReleaseInfo | None) -> None:
        self.newer = release
        if release is not None:
            self._show_state()
            self._update_buttons()
            self.note(f"RPCS3 {release.version} is out ({release.published}); a later version of this app brings "
                      f"it, once it has been tried on the board: {release.url}")

    def chosen(self) -> Game | None:
        """The game whose row is selected."""
        rows = self.table.selectionModel().selectedRows()
        return self.games[rows[0].row()] if rows and rows[0].row() < len(self.games) else None

    def _fill_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.games))
        for row, game in enumerate(self.games):
            box = QTableWidgetItem()
            box.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            box.setCheckState(Qt.CheckState.Checked if str(game.eboot) in self.in_steam or str(game.eboot) in self.moved
                              else Qt.CheckState.Unchecked)
            box.setToolTip(f"In Steam {self.doubles[str(game.eboot)] + 1} times: Update Steam leaves one"
                           if str(game.eboot) in self.doubles else "In Steam" if str(game.eboot) in self.in_steam else
                           f"Found again under a new name: in Steam as {self.in_steam.get(self.moved[str(game.eboot)], '?')}; "
                           "Update Steam brings the shortcut up to date" if str(game.eboot) in self.moved else "Not in Steam")
            self.table.setItem(row, STEAM, box)
            for column, text in ((GAME, game.title), (SERIAL, game.title_id), (VERSION, game.version),
                                 (FOLDER, game.folder.name or str(game.folder))):
                self.table.setItem(row, column, QTableWidgetItem(text))
            folder = self.table.item(row, FOLDER)           # the folder's name; the whole path as the tip
            folder.setToolTip(str(game.folder))
            if not game.startable:
                folder.setForeground(QBrush(QColor("#c62828")))
                folder.setToolTip(f"{NO_SFB} it.\n{game.folder}")
            self.table.setCellWidget(row, SCREEN, self._screen_box(game))
        self.table.blockSignals(False)
        self._update_buttons()

    def _screen_box(self, game: Game) -> QComboBox:
        """How the game fills the screen: the PS3's picture for a wide screen, for a 4:3 one, or stretched to fill
        the window; kept in the game's own settings in RPCS3 (owner, 24-10-2026: as PS5 PCSX2 Manager's)."""
        box = QComboBox()
        for key, text in userdata.SCREENS.items():
            box.addItem(text, key)
        if not game.title_id:
            box.setEnabled(False)
            box.setToolTip("Without an Id in its PARAM.SFO the game has no settings of its own in RPCS3")
            return box
        current = userdata.read_screen(userdata.game_config(self.rpcs3_home, game.title_id))
        box.setCurrentIndex(max(box.findData(current), 0))
        box.setToolTip("16:9: the PS3's picture for a wide screen, RPCS3's default. 4:3: the picture for a 4:3 "
                       "screen, with borders on a wide one. Fill screen: the picture stretched to fill the window.")
        box.currentIndexChanged.connect(lambda _index, g=game, b=box: self.set_screen(g, b.currentData()))
        return box

    def ticked(self) -> list[Game]:
        return [g for row, g in enumerate(self.games)
                if self.table.item(row, STEAM).checkState() == Qt.CheckState.Checked]

    def steam_plan(self) -> tuple[list[Game], list[Game]]:
        """(games to add or bring up to date, games to take out): the ticked ones in, the others out, and the
        shortcuts of games no longer found out too."""
        add = self.ticked()
        found = {str(g.eboot) for g in self.games}
        remove = [g for g in self.games if str(g.eboot) in self.in_steam and g not in add]
        remove += [Game(Path(eboot), name) for eboot, name in self.in_steam.items() if eboot not in found]
        return add, remove

    def _update_buttons(self) -> None:
        idle = not self.worker.running
        installed_ = bool(self.version)
        self.refresh_pill.setEnabled(idle)
        self.install_pill.setEnabled(idle and (self.version != emulator.VERSION or self.replaced))
        self.emulator_box.setEnabled(idle)
        self.remove_pill.setEnabled(idle and installed_)
        self.package_pill.setEnabled(idle and installed_)
        self.rpcs3_button.setEnabled(idle and installed_)
        self.covers_button.setEnabled(idle)
        self.remove_game_pill.setEnabled(idle and self.chosen() is not None)
        add, remove = self.steam_plan()
        named = shortcuts.names(add)        # a name in Steam that differs (one from before the prefix) is renamed
        changed = bool(remove) or bool(self.doubles) or any(self.in_steam.get(str(g.eboot)) != named[g.eboot]
                                      or str(g.eboot) in self.no_cover for g in add)
        self.steam_button.setEnabled(idle and changed and self.steam_dir is not None and not steam.game_mode())
        if self.steam_dir is None:
            self.steam_button.setToolTip("Steam was never started on this system: start it once first")
        elif steam.game_mode():
            self.steam_button.setToolTip("In Game Mode (a handheld's Steam session) Steam is the session itself: "
                                         "change it in Desktop Mode")
        else:
            self.steam_button.setToolTip(STEAM_TIP)

    # --- Actions ----------------------------------------------------------------------------------------------

    def _ask(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(self, window_title(title), text)
        return answer == QMessageBox.StandardButton.Yes

    def _start(self, text: str, job) -> None:
        if self.worker.start(job):
            self.running.setStyleSheet("font-weight:600;")
            self.running.setText(text)
            self.log.info(text)
            self._update_buttons()

    def _job_done(self, result: tuple[bool, str]) -> None:
        ok, message = result[0], private(result[1])     # a path in an error: the user's folders as ~
        self.refresh()
        self.say(message, ok)

    def on_install(self) -> None:
        if not (self.home / emulator.VERSION / emulator.MEMBER).is_file() and not self._ask(
                "Install", f"Download RPCS3 {emulator.VERSION} from GitHub (about {emulator.SIZE_MB} MB)?\n\nIt is "
                f"checked against the SHA-256 this app was tried with before it is installed in {self.home}."):
            return
        home, fetch = self.home, self.fetch

        def job() -> tuple[bool, str]:
            try:
                return True, emulator.install(home, fetch)
            except (emulator.EmulatorError, OSError) as error:
                return False, f"RPCS3 was not installed: {error}"
        self._start(f"Downloading RPCS3 {emulator.VERSION}…", job)

    def on_versions_menu(self) -> None:
        """The version pill's menu: the builds installed, then Manage versions…."""
        fill_menu(self.versions_menu, self.home, emulator.MEMBER, emulator.VERSION, self.use_build,
                  self.on_versions)
        self.versions_menu.popup(self.emulator_box.mapToGlobal(self.emulator_box.rect().bottomLeft()))

    def use_build(self, folder: str) -> None:
        try:
            builds.use(self.home, folder, emulator.MEMBER)
        except (builds.BuildError, OSError) as error:
            self.say(f"RPCS3 {folder} was not put in use: {error}", ok=False)
            return
        self.refresh()
        self.say(f"RPCS3 {folder} is in use." + ("" if folder == emulator.VERSION else
                                                   " It was not tried on the board."))

    def on_versions(self) -> None:
        """The version manager (core's BuildsDialog): every build installed and every build on GitHub."""
        home, fetch = self.home, self.fetch
        dialog = BuildsDialog("RPCS3", home, emulator.MEMBER, emulator.tested(), emulator.available,
                              lambda build: emulator.install_build(home, build, fetch), self,
                              pill=style.action_pill, running=self.rpcs3_running)
        dialog.changed.connect(self.refresh)
        style.apply(dialog)
        dialog.exec()
        self.refresh()

    def on_remove(self) -> None:
        text = ("Remove the installed RPCS3, every build of it?\n\nIts own folder, with the firmware, your saves, "
                "settings and installed games, stays.")
        if self.in_steam:
            text += "\nThe games in Steam no longer start until it is installed again."
        if self._ask("Remove", text):
            emulator.remove(self.home)
            self.refresh()
            self.say("RPCS3 was removed.")

    def sync_firmware(self) -> None:
        """The PS3's firmware put in Games/PS3/Firmware given to RPCS3 by itself (owner, 03-11-2026:
        firmware taken in automatically), once RPCS3 is installed and while
        it does not run: a file whose version (read from the PUP) is installed already is left alone, and so is the
        file given last as it is (its name, size and time in the settings), so a file RPCS3 refused is not given
        again until it changes. The file stays."""
        if not self.version or self.rpcs3_running() or self.worker.running:
            return
        pup = library.firmware_file(self.user_home)
        if pup is None:
            return
        key = library.file_key(pup)
        if not key or key == self.settings.get("firmware_given"):
            return
        version = userdata.pup_version(pup)
        if version and self.firmware and version.lstrip("0") == self.firmware.lstrip("0"):
            self.settings.set("firmware_given", key)        # installed already: left alone
            return
        if version and self.firmware and _version_key(version) < _version_key(self.firmware):
            # RPCS3's window asked before it installed an older firmware; without its window nothing asks.
            self.settings.set("firmware_given", key)
            self.note(f"PS3 firmware {version} in {private(library.firmware_home(self.user_home))} is older than the "
                      f"installed {self.firmware}: not given to RPCS3.")
            return
        self.settings.set("firmware_given", key)
        self.note(f"PS3 firmware {version or pup.name} found in {private(library.firmware_home(self.user_home))}: "
                  "given to RPCS3.")
        self.install_firmware(pup)

    def install_firmware(self, pup: Path) -> None:
        """Through RPCS3 itself, without its window (--headless --installfw; owner, 11-11-2026), as the window's job:
        RPCS3 then asks nothing and shows no Success! box. Its exit code says nothing of the outcome, so the result is
        read from RPCS3's log, and the firmware's version from its folder."""
        self.prepare_rpcs3()
        command = self.rpcs3_command("--headless", "--installfw", str(pup))
        dev_flash, log_path, name = self.dev_flash, self.rpcs3_log, pup.name

        def job() -> tuple[bool, str]:
            try:
                subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)
            except OSError as error:
                return False, f"RPCS3 could not be started: {error}"
            installed, error = userdata.read_firmware_report(log_path)
            now = userdata.firmware_version(dev_flash)
            if installed and now:
                return True, f"PS3 firmware {now} is installed."
            detail = error or "see RPCS3's log"
            return False, f"RPCS3 did not install {name}: {detail} ({private(log_path)})."
        self._start(f"RPCS3 installs the PS3 firmware from {name}, without its window…", job)

    def on_install_packages(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, window_title("Install packages from a folder"),
                                                  str(self.folders[0] if self.folders else Path.home()))
        if folder:
            self.install_packages(Path(folder))

    def install_packages(self, folder: Path) -> None:
        """Through RPCS3 itself, without its window (--headless --installpkg; owner, 24-10-2026), once per file:
        the licenses (.rap, .edat) first, which RPCS3 copies into its exdata, then the packages in
        userdata.install_order (the games and DLC, then the updates: an update needs its game installed), each
        into RPCS3's dev_hdd0/game. It runs as the window's job, off the GUI thread. RPCS3's exit code says
        nothing of the outcome (this build ends a headless run with an error of its own once the work is done),
        so each run's result is read from RPCS3's log, and the games and licenses that came are counted."""
        pkgs, licenses = userdata.packages(folder)
        if not pkgs and not licenses:
            self.say(f"No .pkg, .rap or .edat file in {folder.name or folder}.", ok=False)
            return
        if self.rpcs3_running():
            self.say(RUNNING_INSTALL, ok=False)
            return
        self.prepare_rpcs3()
        files = [*licenses, *(info.path for info in userdata.install_order(pkgs))]
        commands = [self.rpcs3_command("--headless", "--installpkg", str(f)) for f in files]
        what = " and ".join(part for part in (f"{len(pkgs)} package(s)" if pkgs else "",
                                              f"{len(licenses)} license(s)" if licenses else "") if part)
        name, hdd0, log_path = folder.name or str(folder), self.hdd0_game, self.rpcs3_log
        before = _packages_in(hdd0)

        def job() -> tuple[bool, str]:
            report = userdata.InstallReport()
            for command in commands:
                try:
                    subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, check=False)
                except OSError as error:
                    return False, f"RPCS3 could not be started: {error}"
                report.extend(userdata.read_install_report(log_path))
            games, copied = _packages_in(hdd0)
            return install_message(report, len(games - before[0]), len(copied - before[1]), name, log_path)
        self._start(f"RPCS3 installs {what} from {name}, without its window… RPCS3 starts once per file, and a "
                    "large package takes minutes.", job)

    def set_screen(self, game: Game, screen: str) -> None:
        if self.rpcs3_running():
            self.say(RUNNING, ok=False)
            self._fill_table()
            return
        try:
            userdata.write_screen(userdata.game_config(self.rpcs3_home, game.title_id), screen)
        except OSError as error:
            self.say(f"{game.title}'s screen was not changed: {error}", ok=False)
            return
        self.say(f"{game.title}: {userdata.SCREENS[screen]}.")

    def open_steam(self) -> None:
        """The Steam link: Steam's library on the desktop (Steam starts when it does not run)."""
        if self.open_url(STEAM_URL):
            self.note("Steam was opened.")
        else:
            self.say("Steam could not be opened: xdg-open is missing.", ok=False)

    def rpcs3_command(self, *args: str) -> list[str]:
        """The installed RPCS3 through the run wrapper (from the app folder when it is not installed yet)."""
        run = self.run_path if self.run_path.is_file() else ROOT / shortcuts.RUN_NAME
        return [str(run), *args]

    def _show_rpcn(self) -> None:
        """The name that signs in alone, as PS5 shadPS4 Manager's shadNet line; the rest in the tooltip."""
        self.rpcn_account = rpcn.read_account(self.rpcs3_home)
        account = self.rpcn_account
        if account.signs_in:
            self.rpcn_state.setText(f"<b>{escape(account.npid)}</b>")
            self.rpcn_state.setToolTip(f"{account.npid} signs in to {account.host} when a game starts.")
        else:
            self.rpcn_state.setText("Off")
            self.rpcn_state.setToolTip("RPCS3's online service, for online play, friends and scores in the games it "
                                       "supports: RPCN Account sets it up.")
        self._show_rpcn_pill()

    def _show_rpcn_pill(self) -> None:
        """RPCN Online, Offline or Off. While RPCS3 runs, from its log: whether it signed in. Otherwise whether the
        server answers (without signing in), so that RPCS3 can sign in."""
        account = self.rpcn_account
        if not account.signs_in:
            self.rpcn_watch.stop()
            self.rpcn_pill.set_status("RPCN Off", "neutral", "RPCN is off: set it up with RPCN Account.")
            return
        self.rpcn_watch.start()
        self._rpcs3_was_running = self.rpcs3_running()
        if self._rpcs3_was_running:
            state, detail = rpcn.session(self.rpcs3_log)
            if state == "online":
                self.rpcn_pill.set_status("RPCN Online", "ok", f"RPCS3 is signed in to {account.host} as {detail}.")
            elif state == "offline":
                self.rpcn_pill.set_status("RPCN Offline", "bad", f"{detail}.")
            else:
                self.rpcn_pill.set_status("RPCN …", "neutral",
                                          f"RPCS3 runs; it signs in as {account.npid} when a game starts.")
            return
        try:
            target = rpcn.parse_server(account.host)
        except rpcn.RpcnError as error:
            self.rpcn_pill.set_status("RPCN Offline", "bad", str(error))
            return
        connect, npid = self.rpcn_connect, account.npid

        def job() -> tuple[bool, str]:
            try:
                rpcn.server_answers(target, connect)
            except rpcn.RpcnError as error:
                return False, f"{error} RPCS3 cannot sign in now."
            return True, f"{target} answers: RPCS3 signs in as {npid} when a game starts."
        if self.rpcn_check.start(job) and self.rpcn_pill.kind not in ("ok", "bad"):
            self.rpcn_pill.set_status("RPCN …", "neutral", f"Asking {target}…")

    def _rpcn_checked(self, result: tuple[bool, str]) -> None:
        if self._rpcs3_was_running or not self.rpcn_account.signs_in:
            return                                      # RPCS3's own session says more, or RPCN is off now
        ok, detail = result
        self.rpcn_pill.set_status("RPCN Online" if ok else "RPCN Offline", "ok" if ok else "bad", detail)

    def _watch_rpcn(self) -> None:
        """While RPCS3 runs, and once when it has ended (then the server again)."""
        if self.rpcs3_running() or self._rpcs3_was_running:
            self._show_rpcn_pill()

    def on_rpcn(self) -> None:
        """RPCN Account: the account window; what it saved shows in the RPCN line and the header."""
        dialog = RpcnDialog(self.rpcs3_home, self, self.rpcn_connect, self.rpcs3_running)
        if dialog.exec():
            self.refresh()
            self.say("RPCN settings saved in RPCS3's own files.")

    def show_exit(self) -> None:
        """Exit RPCS3 is on while RPCS3 runs."""
        self.exit_button.setEnabled(self.rpcs3_running())

    def on_exit_rpcs3(self) -> None:
        """Exit RPCS3 (owner, 22-11-2026): RPCS3 and everything it started end at once, with no question."""
        if self.rpcs3_end():
            self.say("RPCS3 was ended.")
        else:
            self.say("RPCS3 was not running.")
        self.show_exit()

    def on_open_rpcs3(self) -> None:
        self.prepare_rpcs3()                    # RPCS3's window opens: its welcome dialog off first
        command = self.rpcs3_command()
        if QProcess.startDetached(command[0], command[1:])[0]:
            self.note("RPCS3's own window was opened.")
        else:
            self.say(f"RPCS3 could not be started: {command[0]} did not run.", ok=False)

    def on_remove_game(self) -> None:
        """Games Uninstall (Remove game… until 20-11-2026; owner, 03-11-2026: before deleting anything, let
        the user decide what to keep): a window lists what of the chosen game would go, a row each with its size,
        every row ticked; unticking keeps it, Delete marked deletes the rows still ticked (read-only files too) off
        the window's thread, its Steam shortcut through Steam, and Cancel deletes nothing. The saves and the licenses
        stay."""
        game = self.chosen()
        if game is None:
            return
        if self.rpcs3_running():
            self.say(RUNNING_REMOVE, ok=False)
            return
        items, why = library.removal_items(game, self.folders, self.games, self.hdd0_game, str(game.eboot) in self.in_steam)
        if not items:
            self.say(why, ok=False)
            return
        if KeepDialog(f"Remove {game.title}", items, self).exec() != QDialog.DialogCode.Accepted:
            self.say("Nothing was deleted.")
            return
        chosen = keep.chosen(items)
        kept = [item.label for item in items if not item.delete]
        paths = [path for item in chosen for path in item.paths]
        take_out = any(item.key == library.STEAM_ITEM for item in chosen)
        folder, closed, run, existing = self.steam_dir, self.steam_closed, self.run_path, self.in_steam
        title = game.title

        def job() -> tuple[bool, str]:
            failed = keep.delete(paths)
            gone = [item.label for item in chosen if item.paths and not any(item.label.startswith(f.split(" (")[0])
                                                                                for f in failed)]
            if take_out and folder is not None:
                try:
                    closed(lambda: steam.write_shortcuts(folder, shortcuts.changes([], [game], run, LOGO_PATH, existing)))
                    gone.append("its shortcut in Steam")
                except (steam.SteamError, steam.ShortcutError, OSError) as error:
                    failed.append(f"its Steam shortcut ({error})")
            text = f"{title}: deleted {', '.join(gone) if gone else 'nothing'}."
            if kept:
                text += f" Kept: {', '.join(kept)}."
            if failed:
                text += f" Not deleted: {', '.join(failed)}."
            return not failed, text
        self._start(f"Deleting {title}…", job)

    def on_start_game(self) -> None:
        """The Start game tab (owner, 12-11-2026): the chosen game started through Steam, as its shortcut there
        starts it (steam://rungameid/ with the shortcut's number). Off the window's thread, with core's play(): a
        Steam that does not run is started and waited for before the game's address is given, and the line says
        the game runs only once RPCS3 does (owner, 20-11-2026, first in PS5 shadPS4 Manager: Steam, started with
        the address, came up and never started the game)."""
        game = self.chosen()
        if game is None:
            self.say("Choose a game under Your games first: Start game starts the chosen one in Steam.", ok=False)
            return
        if self.worker.running:
            self.say("Wait until what runs now has finished, then start the game.", ok=False)
            return
        number = (steam.shortcut_number(self.steam_dir, shortcuts.for_game(game))
                  if self.steam_dir is not None and str(game.eboot) in self.in_steam else None)
        if number is None:
            self.say(f"{game.title} is not in Steam yet: tick it and press Update Steam first.", ok=False)
            return
        if self.rpcs3_running():
            self.say(RUNNING_START, ok=False)
            return
        url, title = steam.play_url(number), game.title
        play, open_url, started = self.steam_play, self.open_url, self.rpcs3_running

        def job() -> tuple[bool, str]:
            try:
                play(url, open_url, started)
            except steam.SteamError as error:
                return False, f"{title} was not started: {error}"
            return True, f"{title} runs, started through Steam."
        self._start(f"Starting {title} through Steam (Steam starts first when it does not run)…", job)

    def on_update_steam(self) -> None:
        if self.steam_dir is None:
            return
        if not self.run_path.is_file():
            self.say(f"The shortcuts run {self.run_path}, which is not there: install {APP_NAME} through the "
                     "portal first.", ok=False)
            return
        add, remove = self.steam_plan()
        if add and not self.version:
            self.say("Install RPCS3 first: the games in Steam start it.", ok=False)
            return
        text = f"{len(add)} game(s) in Steam" + (f", {len(remove)} taken out." if remove else ".")
        if self.doubles:
            text += f"\n{sum(self.doubles.values())} double shortcut(s) taken out: each game stays in Steam once."
        if self.steam_running():
            text += "\n\nSteam closes for it and starts again in the background."
        if not self._ask("Steam", text):
            return
        folder, closed, run, existing = self.steam_dir, self.steam_closed, self.run_path, self.in_steam
        key, home, get = covers.read_key(self.covers_key), self.covers_home, self.covers_get

        def job() -> tuple[bool, str]:
            # The covers first, off the GUI thread; the artwork is drawn here too, on QImage only.
            notes = (covers.fetch([(shortcuts.cover_name(g), g.title) for g in add], shortcuts.COVERS, key, home,
                                  get) if key else [])
            changes = shortcuts.changes(add, remove, run, LOGO_PATH, existing,
                                        found=lambda g: covers.art(home, shortcuts.cover_name(g), shortcuts.COVERS))
            found: dict[str, str] | None = {}
            extra: list[str] = []

            def change() -> None:
                # Read back right after the write, while Steam is still closed (owner, 03-11-2026:
                # "it still says 0 games in Steam"): whether the shortcuts were written
                # as the app reads them, before Steam touches the file. A failed read is said, not passed over.
                nonlocal found
                steam.write_shortcuts(folder, changes)
                try:
                    found = shortcuts.in_steam(folder)
                except OSError as error:
                    found = None
                    extra.append(f"Steam's file could not be read back: {error}")

            try:
                restarted = closed(change)
            except (steam.SteamError, steam.ShortcutError, OSError) as error:
                return False, "\n".join([*notes, f"Steam was not changed: {error}"])
            if found is not None:
                missing = [g.title for g in add if str(g.eboot) not in found]
                if missing:
                    extra.append(f"Read back from Steam's file, {len(add) - len(missing)} of the {len(add)} game(s) "
                                 f"are there: not {', '.join(missing)}.")
            again = " Steam was closed for it and starts again in the background." if restarted else ""
            return True, "\n".join([*notes, f"{len(add)} game(s) in Steam, under Non-Steam in the library"
                                              f"{f'; {len(remove)} taken out' if remove else ''}.{again}", *extra])
        self._start("Looking up covers and changing Steam's shortcuts…" if key else "Changing Steam's shortcuts…",
                    job)

    def on_covers(self) -> None:
        """Asks for the suite's SteamGridDB API key; empty turns the lookup off (the covers kept stay in use)."""
        if covers.edit_key(self, self.covers_key, "Update Steam"):
            self.refresh()
            self.say("The SteamGridDB key was changed." if covers.read_key(self.covers_key) else
                     "The SteamGridDB key was taken out; the covers kept stay in use.")

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        QTimer.singleShot(0, self.place_states)         # once the pills below have their new width

    def place_states(self) -> None:
        """The states end at the middle of the last header pill: the spacer after them is half its width."""
        self.states_spacer.setFixedWidth(max(0, self.header_pills[-1].width() // 2))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        if self.worker.running and not self._ask("Close", "A download, an install of packages or a change to "
                                                          "Steam is still running. Close anyway?"):
            event.ignore()
            return
        self.worker.stop()
        self.release_check.stop()
        self.controller_timer.stop()
        self.rpcn_watch.stop()
        self.rpcn_check.stop()
        self.settings_page.unmuting.stop()
        self.settings.set_window_state("geometry", self.saveGeometry())
        self.settings.sync()
        super().closeEvent(event)
