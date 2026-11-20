# SPDX-License-Identifier: GPL-3.0-or-later
"""The main window, built as RPCS3 Manager's (owner, 07-11-2026: RPCS3 Manager's design is every manager's): the header
with the Refresh pill and the state boxes, a row of action pills (Install and Uninstall for PPSSPP, Rename for the
games), the state of each (PPSSPP, the game folder) in a line, then the tabs: the games found, each with a box for
Steam; PPSSPP's settings (core's settings_page over ppsspp_settings); the saves on its memory stick (Memory
cards, saves_page.py); and the app's log, with Clear logs beside it. Downloading PPSSPP, asking
GitHub for a newer one and changing Steam's files run off the GUI thread; nothing here needs root. The look is the
app's own blue (style.py). Steam artwork… takes the suite's SteamGridDB API key, with which Update Steam looks up a
cover for each game's portrait first (core's covers).

A game runs from Steam: the tab beside Your games, Start game, starts the chosen one there (owner, 12-11-2026).
PPSSPP's own window (PPSSPP settings, under the games) stays for what the Settings tab does not set. What the window
says it also writes to the app's log (core's applog), shown in the View logs tab.

The owner's order of 20-11-2026, shadPS4 Manager's, replaces the one above: the header's pills are PPSSPP's (its
version, Install, Uninstall) and Refresh; the row under them the games' pills and Available in Steam, with Play
time where the emulator counts it; then two columns, the state lines and the installed version beside them; then the
tabs, Memory cards before Settings and the log's as View logs."""

from __future__ import annotations

import time
from html import escape
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QTableWidget,
                             QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from bazzite_console_core import SUITE_MANUAL_URL, applog, covers, steam, window_title
from bazzite_console_core import __version__ as CORE_VERSION
from bazzite_console_core import keep, renamed
from bazzite_console_core import builds
from bazzite_console_core.action_tab import ActionTab
from bazzite_console_core.builds_dialog import BuildsDialog, fill_menu
from bazzite_console_core.keep_dialog import KeepDialog
from bazzite_console_core.platform import bin_home, private, xdg_open
from bazzite_console_core.settings import SettingsStore
from bazzite_console_core.settings_page import SettingsPage
from bazzite_console_core.updates import ReleaseInfo, UpdateChecker
from bazzite_console_core.widgets import AppHeader, InfoButton, MetricBox, StatusText, Terminal, WrappedLabel, hint_label

from . import (APP_ID, APP_NAME, INFO, LOGO_PATH, ROOT, __version__, controllers, emulator, library, ppsspp_settings,
               renamer, shortcuts, style, userdata)
from .games import Game, installed, memstick_game, ppsspp_home, scan
from .saves_page import SavesPage

MANUAL_URL = f"{SUITE_MANUAL_URL}apps/ppsspp/"
STEAM_TIP = "Add the ticked games to Steam and take out the others; Steam closes for it and starts again"
START_TIP = "Start the game chosen under Your games through Steam, as its shortcut in Steam does"
CLEAR_TIP = "Empty the app's log file, with the older ones kept beside it, and the View logs tab"
STEAM_URL = "steam://open/games"        # Steam's library; Steam starts when it does not run
KINDS = {"iso": "ISO", "cso": "CSO", "chd": "CHD", "pbp": "Memory Stick"}
STEAM, GAME, SERIAL, KIND, FILE = range(5)                  # the table's columns
WIDTH = 900                             # the window opens this wide, and is never narrower (owner, 18-11-2026)
HEIGHT = 606                            # the window opens this high (owner, 18-11-2026); it was 800
GAMES, START, SAVES, SETTINGS, LOG = range(5)               # the tabs
# The emulator's line: the state alone, the same words in every manager (owner, 07-11-2026); the version and the
# advice are in its tip.
NOT_INSTALLED = "Not installed. Install it with the Install button."
INSTALLED = "Installed. Uninstall with the Uninstall button."
VERSIONS_TIP = "Put another installed PPSSPP build in use, or download one in the version manager"

RUNNING_REMOVE = "PPSSPP is running: close it first, then remove the game."
RUNNING_START = "PPSSPP is running: close it first, then start the game."
UNINSTALL_GAME_TIP = ("Delete the game chosen under Your games from the disk: a window lists what would go, and you "
                      "untick what to keep; nothing is deleted before you confirm")


class PpssppSettings(SettingsStore):
    DEFAULTS: dict = {"rename_template": -1}    # the naming template of Rename files (-1: not chosen here yet)


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


class MainWindow(QMainWindow):
    CONTROLLER_POLL = 3000                  # ms: how often the window looks for a controller

    def __init__(self, home: Path | None = None, memstick: Path | None = None, steam_dir: Path | None = None,
                 run: Path | None = None, fetch: emulator.Download = emulator.download,
                 steam_closed=steam.with_steam_closed, steam_running=steam.steam_running,
                 newer_release=emulator.newer_release,
                 covers_home: Path | None = None, covers_get: covers.Get = covers._get,
                 covers_key: Path | None = None, ppsspp_running=emulator.running,
                 user_home: Path | None = None, drives: Callable[[], list[Path]] = library.removable_drives,
                 log_path: Path | None = None, open_url=xdg_open,
                 devices: Path = controllers.DEVICES,
                 steam_play=steam.play):
        """*home*: where the app installs PPSSPP; *memstick*: PPSSPP's own folder (its memory stick); *steam_dir*:
        Steam's folder (None: looked up); *run*: the run wrapper the shortcuts start; *fetch*: the download;
        *steam_closed* and *steam_running*: closing Steam for a change and asking whether it runs; *newer_release*:
        asks GitHub for a newer PPSSPP; *covers_home*, *covers_get* and *covers_key*: where the SteamGridDB
        pictures are kept, how SteamGridDB is asked and the suite's key file (tests never touch the real ones);
        *ppsspp_running*: whether PPSSPP runs (its settings are left alone then); *user_home*: the home folder with
        the app's own game folder (library.fixed); *drives*: the removable drives looked at for one; *log_path*: the
        app's log file, as the View logs tab shows it (__main__ set it up); *open_url*: opens a URL on the desktop (the
        Steam link).
        *steam_play*: starts a game by its Steam address and waits until it runs (Start game)."""
        super().__init__()
        self.setMinimumWidth(WIDTH)                     # never narrower (owner, 18-11-2026)
        self.resize(WIDTH, HEIGHT)
        self.home = home or emulator.emulator_home()
        self.memstick = memstick or ppsspp_home()
        self.steam_dir = steam_dir if steam_dir is not None else steam.find_steam()
        self.run_path = run or bin_home() / shortcuts.RUN_NAME
        self.fetch = fetch
        self.user_home = user_home or Path.home()
        self.drives = drives
        self.steam_closed = steam_closed
        self.steam_running = steam_running
        self.ppsspp_running = ppsspp_running
        self.covers_home = covers_home or covers.covers_home(APP_ID)
        self.covers_get = covers_get
        self.covers_key = covers_key
        self.log_path = log_path or applog.log_file(APP_ID)
        self.open_url = open_url
        self.steam_play = steam_play
        self.devices = devices                          # the kernel's list of input devices, for the controller state
        self.controllers: list[str] | None = None       # the controllers last seen; None before the first look
        self.log = applog.logger(APP_ID)
        self._pin_noted = False                         # another release installed than the app brings: logged once
        self.newer: ReleaseInfo | None = None           # PPSSPP's newest release, when newer than the pinned one
        self.release_check = UpdateChecker(self)        # apart from the worker: it runs while the window opens
        self.release_check.finished.connect(self._release_found)
        self.settings = PpssppSettings(INFO, self)
        self.worker = UpdateChecker(self)            # one job at a time off the GUI thread: a download or Steam
        self.worker.finished.connect(self._job_done)
        self.games: list[Game] = []
        self.in_steam: dict[str, str] = {}
        self.moved: dict[str, str] = {}               # a game found again under another name: its file in Steam
        self._moved_said: set[str] = set()
        self.no_cover: set[str] = set()               # games in Steam not yet looked up on SteamGridDB, with a key
        self.doubles: dict[str, int] = {}             # games in Steam more than once: how many shortcuts too many
        self._doubles_said: dict[str, int] = {}
        self.version = ""
        self.folders: list[Path] = []

        header = AppHeader(LOGO_PATH, APP_NAME, __version__)
        # The state on the right of the title row, ending at the middle of the last pill below it, as in RPCS3
        # Manager: a spacer of half that pill's width after it, set whenever the window's size changes.
        self.pill = StatusText()
        header.add_action(self.pill)
        self.controller = StatusText()                  # beside it: whether a controller is connected (owner,
        header.add_action(self.controller)              # 18-11-2026: as the other managers show it)
        self.controller_timer = QTimer(self)
        self.controller_timer.setInterval(self.CONTROLLER_POLL)
        self.controller_timer.timeout.connect(self.show_controller)
        self.controller_timer.start()
        self.states_spacer = QWidget()
        self.states_spacer.setFixedSize(0, 1)
        header.add_action(self.states_spacer)
        self.refresh_pill = style.action_pill("Refresh", "Click to refresh", "Read the state again and look for games")
        self.refresh_pill.clicked.connect(self.refresh)
        # The version is a pill (owner, 20-11-2026, as shadPS4's own launcher): its menu puts another installed
        # build in use, or opens the version manager (core's builds_dialog).
        self.emulator_box = style.action_pill("—", "PPSSPP version", VERSIONS_TIP)
        self.versions_menu = QMenu(self)
        self.emulator_box.clicked.connect(self.on_versions_menu)
        self.steam_box = MetricBox("Available in Steam", style.BLUE)
        # The two links alone (owner, 18-11-2026), in the type of a pill's caption (Click to refresh): what the
        # app is for is in the wiki.
        self.intro = hint_label(style.caption_link(self, emulator.RELEASE_PAGE, "PPSSPP's release notes") + " · "
                                + style.caption_link(self, MANUAL_URL, "Wiki"), follow_height=True)
        self.intro.setStyleSheet(style.CAPTION)

        # What there is to do, as pills the size of the header's, spread over the window's width: what it is for in
        # large type (PPSSPP, Games), what the pill does under it (Install, Uninstall, Rename).
        self.install_pill = style.action_pill("PPSSPP", "Install", f"Download PPSSPP {emulator.VERSION} from GitHub "
                                                                   f"(about {emulator.SIZE_MB} MB) and check it")
        self.install_pill.clicked.connect(self.on_install)
        self.remove_pill = style.action_pill("PPSSPP", "Uninstall", "Remove the installed PPSSPP; its own folder "
                                                                    "(saves, settings) stays")
        self.remove_pill.clicked.connect(self.on_remove)
        self.rename_pill = style.action_pill("Games", "Rename", "Rename the ISO and CSO images after their "
                                                                "PARAM.SFO: disc ID, title and version, with a "
                                                                "choice of naming templates")
        self.rename_pill.clicked.connect(self.on_rename)
        # Games Uninstall (owner, 20-11-2026): a pill in place of the Remove game… button under the table
        self.remove_game_pill = style.action_pill("Games", "Uninstall", UNINSTALL_GAME_TIP)
        self.remove_game_pill.clicked.connect(self.on_remove_game)
        # Play time (owner, 18-11-2026): all games together, as PPSSPP counts it
        self.time_box = MetricBox("Play time", style.BLUE)
        # The owner's order (20-11-2026), as shadPS4 Manager's. The header: PPSSPP's version, Install and
        # Uninstall, then Refresh. The row under it: the games' Rename and Uninstall, Available in Steam and Play time
        # (the Your games box went: the table lists them). Each row's pills share the width in equal parts.
        self.header_pills = [self.emulator_box, self.install_pill, self.remove_pill, self.refresh_pill]
        for box in self.header_pills:
            box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            header.add_second(box, 1)
        self.actions = [self.rename_pill, self.remove_game_pill]    # the row's pills that act
        self.second_row = [self.rename_pill, self.remove_game_pill, self.steam_box, self.time_box]
        actions = QHBoxLayout()
        actions.setSpacing(8)
        for pill in self.second_row:                    # each a quarter of the width, whatever the window's
            pill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            actions.addWidget(pill, 1)

        grid = QGridLayout()        # the state of each: PPSSPP, the game folder
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        self.emulator_state, self.folders_state = (self._state_label() for _ in range(2))
        # The game folders by name, what goes in them behind the info symbol (owner, 12-11-2026).
        self.folders_info = InfoButton("", "About the game folder")
        for row, (name, state) in enumerate((("PPSSPP", self.emulator_state), ("Game folder", self.folders_state))):
            grid.addWidget(self._name_label(name), row, 0)
            grid.addWidget(_with_info(state, self.folders_info) if state is self.folders_state else state, row, 1)
        # A second column beside the states (owner, 20-11-2026): the PPSSPP version installed
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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["In Steam", "Game title", "Id", "Kind", "File"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        head = self.table.horizontalHeader()
        for column, mode in enumerate((QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.Stretch,
                                       QHeaderView.ResizeMode.ResizeToContents,
                                       QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.Stretch)):
            head.setSectionResizeMode(column, mode)
        self.table.itemChanged.connect(lambda _item: self._update_buttons())
        self.table.itemSelectionChanged.connect(self._update_buttons)

        self.ppsspp_button = QPushButton("PPSSPP settings")
        self.ppsspp_button.setToolTip("Open PPSSPP's own window for what the Settings tab does not set: its other "
                                      "settings, the controllers and its game list")
        self.ppsspp_button.clicked.connect(self.on_open_ppsspp)
        self.covers_button = QPushButton("Steam artwork…")
        self.covers_button.setToolTip("The SteamGridDB API key, one for the whole suite: with it, Update Steam "
                                      "gives each game a cover from SteamGridDB in Steam's library")
        self.covers_button.clicked.connect(self.on_covers)
        self.steam_button = style.primary_button("Update Steam", STEAM_TIP)
        self.steam_button.clicked.connect(self.on_update_steam)
        buttons = QHBoxLayout()
        # What the boxes and Start game do, behind an info symbol (owner, 18-11-2026, in place of a line of text)
        self.steam_info = InfoButton("A checkmark before a game adds the game to Steam. When the Start game button "
                                     f"is clicked the game starts from {style.link(self, STEAM_URL, 'Steam')}.",
                                     "About the games and Steam")
        self.steam_info.opens = lambda _url: self.open_steam()      # the app opens Steam itself (open_steam)
        buttons.addWidget(self.steam_info)
        buttons.addStretch(1)
        buttons.addWidget(self.ppsspp_button)
        buttons.addWidget(self.covers_button)
        buttons.addWidget(self.steam_button)
        games_page = QWidget()
        games = QVBoxLayout(games_page)
        games.setContentsMargins(0, 8, 0, 0)
        games.addWidget(self.table, 1)
        games.addLayout(buttons)

        self.settings_page = SettingsPage("PPSSPP", ppsspp_settings.SETTINGS,
                                          lambda: ppsspp_settings.read_settings(self.memstick),
                                          lambda setting, value: ppsspp_settings.write_setting(self.memstick, setting,
                                                                                               value),
                                          self.ppsspp_running, log=self.log)
        # Memory cards (owner, 18-11-2026): the saves on PPSSPP's memory stick (saves_page.py)
        self.saves_page = SavesPage(self.memstick, self.ppsspp_running, self.log)
        self.output = Terminal()
        self.output.setPlaceholderText("What the app did, with the time, appears here.")
        self.output.set_text(applog.tail(self.log_path))
        log_page = QWidget()
        log = QVBoxLayout(log_page)
        log.setContentsMargins(0, 8, 0, 0)
        log.addWidget(hint_label(f"Everything the app said and did, newest last; the same lines are in "
                                 f"{escape(private(self.log_path))}, which turns over at 1 MB."))
        log.addWidget(self.output, 1)
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
        self.tabs.addTab(self.saves_page, "Memory cards")
        # Memory cards before Settings, and the log's tab is View logs (owner, 20-11-2026)
        self.tabs.addTab(self.settings_scroll, "Settings")
        self.tabs.addTab(log_page, "View logs")
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
        version = QLabel(f"{APP_NAME} {__version__} · core {CORE_VERSION} · PPSSPP {emulator.VERSION}")
        version.setStyleSheet("color:palette(placeholder-text);")
        lay.addWidget(version, 0, Qt.AlignmentFlag.AlignRight)
        self.setCentralWidget(central)
        style.apply(self)

        geometry = self.settings.window_state("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.refresh()
        self.release_check.start(newer_release)

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
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse
                                      | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        return label

    # --- State ------------------------------------------------------------------------------------------------

    def refresh(self) -> None:
        self.show_controller()
        self.version = emulator.installed_version(self.home)
        self.prepare_ppsspp()
        self.game_dir = memstick_game(self.memstick)
        self.folders = library.fixed(self.user_home, self.drives)
        self.games = scan(self.folders, self.game_dir)
        try:
            self.in_steam = shortcuts.in_steam(self.steam_dir) if self.steam_dir else {}
            self.doubles = shortcuts.doubles(self.steam_dir) if self.steam_dir else {}
            self.no_cover = ({str(g.file) for g in self.games if str(g.file) in self.in_steam
                              and not covers.known(self.covers_home, shortcuts.cover_name(g))}
                             if covers.read_key(self.covers_key) else set())
        except OSError:
            self.in_steam, self.no_cover = {}, set()
            self.doubles = {}
        # A game renamed or moved after it was put in Steam keeps its mark (owner, 03-11-2026;
        # core's renamed): known by its code, else its file's size.
        found = {str(g.file): renamed.identity(g.disc_id, g.file) for g in self.games}
        known = renamed.load(self.settings.qsettings)
        self.moved = renamed.follow(known, found, self.in_steam)
        renamed.remember(self.settings.qsettings, known, found, self.in_steam)
        self._show_state()
        self._fill_table()
        # The same game in Steam more than once (owner, 20-11-2026): said once, and Update Steam leaves one
        if self.doubles and self.doubles != self._doubles_said:
            titles = {str(g.file): g.title for g in self.games}
            names = [f"{titles.get(key) or self.in_steam.get(key) or key} ({extra + 1} times)"
                     for key, extra in self.doubles.items()]
            self.say(f"In Steam more than once: {', '.join(names)}. Update Steam leaves one of each.", ok=False)
        self._doubles_said = dict(self.doubles)
        if self.moved and set(self.moved) != self._moved_said:
            self._moved_said = set(self.moved)
            titles = [g.title for g in self.games if str(g.file) in self.moved]
            self.say(f"Found again under a new name or in another folder, with its Steam mark: {', '.join(titles)}. "
                     "Update Steam brings the shortcut in Steam up to date.")
        self.settings_page.load()
        self.saves_page.load()

    def prepare_ppsspp(self) -> None:
        """What the app owns in PPSSPP's settings (userdata.prepare), once PPSSPP is installed and while it does not
        run; what changed goes to the log."""
        if not self.version or self.ppsspp_running():
            return
        try:
            done = userdata.prepare(self.memstick)
        except OSError as exc:
            self.note(f"PPSSPP's settings could not be written: {exc}", ok=False)
            return
        if done:
            self.note("PPSSPP set up: " + ", ".join(done) + ".")

    def show_controller(self) -> None:
        """The controller state beside the title: a game started from Steam reads the controller that is there
        when it starts, so the window says when none is (switched off, asleep, not paired)."""
        found = controllers.connected(self.devices)
        if found == self.controllers:
            return
        self.controllers = found
        if found:
            self.controller.set_status("Controller connected" if len(found) == 1 else f"{len(found)} controllers",
                                       "ok", "Connected: " + ", ".join(found) + ". A game started from Steam "
                                       "reads it.")
        else:
            self.controller.set_status("No controller", "warn",
                                       "No controller is connected: switch it on, or press its PS button to wake "
                                       "it, before starting a game from Steam.")

    def say(self, text: str, ok: bool = True) -> None:
        """What the window has to say: the line under the tabs, the View logs tab and the log file."""
        self.running.setStyleSheet("font-weight:600;" + ("" if ok else "color:#c62828;"))
        self.running.setText(text)
        self.note(text, ok)

    def note(self, text: str, ok: bool = True) -> None:
        """Into the View logs tab and the log file only: something that happened, not what the window is doing now."""
        (self.log.info if ok else self.log.error)(text)
        stamp = time.strftime(applog.DATE)
        self.output.appendPlainText(f"{stamp} {'INFO' if ok else 'ERROR'} {text}")

    def on_clear_logs(self) -> None:
        """Clear logs (owner, 18-11-2026): the app's log file emptied, with the older ones kept beside it, and the
        View logs tab with them. Said in the line under the tabs only, so the log stays empty."""
        if not applog.clear(APP_ID, self.log_path):
            self.say(f"The log could not be cleared: {private(self.log_path)}", ok=False)
            return
        self.output.clear()
        self.running.setStyleSheet("font-weight:600;")
        self.running.setText("The log was cleared.")

    def _show_play_time(self) -> None:
        """The time spent in all games together, as PPSSPP counts it ([PlayTime] in its settings); per game in the
        tip."""
        times = userdata.play_times(self.memstick)
        total = sum(seconds for seconds, _ in times.values())
        if not total:
            self.time_box.set_value("—", "PPSSPP counts the time spent in each game; none yet.")
            return
        titles = {g.disc_id: g.title for g in self.games if g.disc_id}
        lines = [f"{titles.get(code, code)}: {userdata.played(seconds)}"
                 + (f", last played {time.strftime('%d-%m-%Y %H:%M', time.localtime(last))}" if last else "")
                 for code, (seconds, last) in sorted(times.items(), key=lambda t: -t[1][0]) if seconds]
        self.time_box.set_value(userdata.played(total), "The time spent in each game, as PPSSPP counts it:\n"
                                + "\n".join(lines))

    def _show_state(self) -> None:
        pinned = emulator.VERSION
        if not self.version:
            self.emulator_state.setText(NOT_INSTALLED)
            self.emulator_box.set_value("—")
            tip = (f"Install downloads PPSSPP {pinned}, the release this version of the app was tried with, and "
                   "checks it before installing it.")
        else:
            self.emulator_state.setText(INSTALLED)
            self.emulator_box.set_value(self.version)
            if self.version != pinned:
                tip = (f"PPSSPP {self.version} is in use; it was not tried on the board. This version of the app was "
                       f"tried with {pinned}: Install puts it back in use.")
                if not self._pin_noted:
                    self.note(tip)
                    self._pin_noted = True
            else:
                tip = f"PPSSPP {pinned}, the release this version of the app was tried with"
        if self.newer is not None:
            tip += (f"\nPPSSPP {self.newer.version} is out ({self.newer.published}). A later version of this app "
                    f"brings it, once it has been tried on the board: {self.newer.url}")
        self.emulator_state.setToolTip(tip)
        self.version_state.setText(escape(self.version) if self.version else "—")   # whole: the pill shortens it
        self.version_state.setToolTip(tip)

        # The app's own folders (owner, 03-11-2026): the home folder's, and a removable drive's when it has one.
        where = ", ".join(f"<b>{escape(private(f))}</b>" for f in self.folders)
        self.folders_state.setText(where)
        self.folders_info.set_text(f"Drop your games in {escape(private(self.user_home / library.GAMES_HOME))}, .ISO, "
                                   ".CSO or .CHD, folders with an EBOOT.PBP. A USB drive or an SD card with a "
                                   "Games/PSP folder is also checked for content.")
        self.folders_state.setToolTip("\n".join(private(f) for f in self.folders)
                                      + f"\n{len(installed(self.game_dir))} game(s) on PPSSPP's memory stick, "
                                      f"{private(self.game_dir)}.")
        found = {str(g.file) for g in self.games}
        self.steam_box.set_value(str(len(found & set(self.in_steam))))
        self._show_play_time()

        if not self.version:
            self.pill.set_status("Not installed", "warn", "Install PPSSPP first.")
        elif not self.games:
            self.pill.set_status("No games", "neutral", "Put your games in the game folder.")
        else:
            self.pill.set_status("Ready", "ok", "PPSSPP is installed and games were found.")

    def _release_found(self, release: ReleaseInfo | None) -> None:
        self.newer = release
        if release is not None:
            self._show_state()
            self.note(f"PPSSPP {release.version} is out ({release.published}); a later version of this app brings "
                      f"it, once it has been tried on the board: {release.url}")

    def _fill_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.games))
        for row, game in enumerate(self.games):
            box = QTableWidgetItem()
            box.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            box.setCheckState(Qt.CheckState.Checked if str(game.file) in self.in_steam or str(game.file) in self.moved
                              else Qt.CheckState.Unchecked)
            box.setToolTip(f"In Steam {self.doubles[str(game.file)] + 1} times: Update Steam leaves one"
                           if str(game.file) in self.doubles else "In Steam" if str(game.file) in self.in_steam else
                           "Not in Steam")
            self.table.setItem(row, STEAM, box)
            kind = KINDS.get(game.kind, game.kind)
            for column, text in ((GAME, game.title), (SERIAL, game.disc_id), (KIND, kind), (FILE, str(game.file))):
                self.table.setItem(row, column, QTableWidgetItem(text))
            if game.kind == "chd":
                self.table.item(row, KIND).setToolTip("A CHD is not looked into: the name is the file's, and Steam "
                                                      "gets no pictures from the game.")
        self.table.blockSignals(False)
        self._update_buttons()

    def ticked(self) -> list[Game]:
        return [g for row, g in enumerate(self.games)
                if self.table.item(row, STEAM).checkState() == Qt.CheckState.Checked]

    def chosen(self) -> Game | None:
        rows = self.table.selectionModel().selectedRows()
        return self.games[rows[0].row()] if rows and rows[0].row() < len(self.games) else None

    def steam_plan(self) -> tuple[list[Game], list[Game]]:
        """(games to add or bring up to date, games to take out): the ticked ones in, the others out, and the
        shortcuts of games no longer found out too."""
        add = self.ticked()
        found = {str(g.file) for g in self.games}
        remove = [g for g in self.games if str(g.file) in self.in_steam and g not in add]
        remove += [Game(Path(file), name) for file, name in self.in_steam.items() if file not in found]
        return add, remove

    def _update_buttons(self) -> None:
        idle = not self.worker.running
        installed_ = bool(self.version)
        self.refresh_pill.setEnabled(idle)
        self.install_pill.setEnabled(idle and self.version != emulator.VERSION)
        self.emulator_box.setEnabled(idle)
        self.remove_pill.setEnabled(idle and installed_)
        self.rename_pill.setEnabled(idle and bool(renamer.renamable(self.games)))
        self.covers_button.setEnabled(idle)
        self.remove_game_pill.setEnabled(idle and self.chosen() is not None)
        self.ppsspp_button.setEnabled(idle and installed_)
        add, remove = self.steam_plan()
        named = shortcuts.names(add)        # a name in Steam that differs (one from before the prefix) is renamed
        changed = bool(remove) or bool(self.doubles) or any(self.in_steam.get(str(g.file)) != named[g.file] or str(g.file) in self.no_cover
                                      for g in add)
        self.steam_button.setEnabled(idle and changed and self.steam_dir is not None and not steam.game_mode())
        if self.steam_dir is None:
            self.steam_button.setToolTip("Steam was never started on this system: start it once first")
        elif steam.game_mode():
            self.steam_button.setToolTip("In Game Mode Steam is the session itself: change it in Desktop Mode")
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
                "Install", f"Download PPSSPP {emulator.VERSION} from GitHub (about {emulator.SIZE_MB} MB)?\n\nIt is "
                f"checked against the SHA-256 this app was tried with before it is installed in {self.home}."):
            return
        home, fetch = self.home, self.fetch

        def job() -> tuple[bool, str]:
            try:
                return True, emulator.install(home, fetch)
            except (emulator.EmulatorError, OSError) as error:
                return False, f"PPSSPP was not installed: {error}"
        self._start(f"Downloading PPSSPP {emulator.VERSION}…", job)

    def on_versions_menu(self) -> None:
        """The version pill's menu: the builds installed, then Manage versions…."""
        fill_menu(self.versions_menu, self.home, emulator.MEMBER, emulator.VERSION, self.use_build,
                  self.on_versions)
        self.versions_menu.popup(self.emulator_box.mapToGlobal(self.emulator_box.rect().bottomLeft()))

    def use_build(self, folder: str) -> None:
        try:
            builds.use(self.home, folder, emulator.MEMBER)
        except (builds.BuildError, OSError) as error:
            self.say(f"PPSSPP {folder} was not put in use: {error}", ok=False)
            return
        self.refresh()
        self.say(f"PPSSPP {folder} is in use." + ("" if folder == emulator.VERSION else
                                                   " It was not tried on the board."))

    def on_versions(self) -> None:
        """The version manager (core's BuildsDialog): every build installed and every build on GitHub."""
        home, fetch = self.home, self.fetch
        dialog = BuildsDialog("PPSSPP", home, emulator.MEMBER, emulator.tested(), emulator.available,
                              lambda build: emulator.install_build(home, build, fetch), self,
                              pill=style.action_pill, running=self.ppsspp_running)
        dialog.changed.connect(self.refresh)
        style.apply(dialog)
        dialog.exec()
        self.refresh()

    def on_remove(self) -> None:
        text = ("Remove the installed PPSSPP, every build of it?\n\nIts own folder, with your saves, settings and "
                "memory stick games, stays.")
        if self.in_steam:
            text += "\nThe games in Steam no longer start until it is installed again."
        if self._ask("Remove", text):
            emulator.remove(self.home)
            self.refresh()
            self.say("PPSSPP was removed.")

    def ppsspp_command(self, *args: str) -> list[str]:
        """The installed PPSSPP through the run wrapper (from the app folder when it is not installed yet)."""
        run = self.run_path if self.run_path.is_file() else ROOT / shortcuts.RUN_NAME
        return [str(run), *args]

    def on_open_ppsspp(self) -> None:
        command = self.ppsspp_command()
        if QProcess.startDetached(command[0], command[1:])[0]:
            self.note("PPSSPP's own window was opened.")
        else:
            self.say(f"PPSSPP could not be started: {command[0]} did not run.", ok=False)

    def open_steam(self) -> None:
        """The Steam link: Steam's library on the desktop (Steam starts when it does not run)."""
        if self.open_url(STEAM_URL):
            self.note("Steam was opened.")
        else:
            self.say("Steam could not be opened: xdg-open is missing.", ok=False)

    def on_rename(self) -> None:
        """The Rename files window, on the disc images found. The list here follows after it closes: a renamed game
        that is in Steam shows up as a change for Update Steam (its shortcut names the file)."""
        from .rename_dialog import RenameDialog
        dialog = RenameDialog(renamer.renamable(self.games), self.settings, self)
        dialog.exec()
        if dialog.renamed:
            self.refresh()
            self.say("Files were renamed. A renamed game that is in Steam needs Update Steam: "
                                 "its shortcut names the file.")

    def on_remove_game(self) -> None:
        """Games Uninstall (Remove game… until 20-11-2026; owner, 03-11-2026: before deleting anything, let
        the user decide what to keep): a window lists what of the chosen game would go, a row each with its size,
        every row ticked; unticking keeps it, Delete marked deletes the rows still ticked (read-only files too) off
        the window's thread, its Steam shortcut through Steam, and Cancel deletes nothing. The saves on the memory stick
        stay."""
        game = self.chosen()
        if game is None:
            return
        if self.ppsspp_running():
            self.say(RUNNING_REMOVE, ok=False)
            return
        items, why = library.removal_items(game, [*self.folders, self.game_dir], self.games, str(game.file) in self.in_steam)
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
        the game runs only once PPSSPP does (owner, 20-11-2026, first in shadPS4 Manager: Steam, started with
        the address, came up and never started the game)."""
        game = self.chosen()
        if game is None:
            self.say("Choose a game under Your games first: Start game starts the chosen one in Steam.", ok=False)
            return
        if self.worker.running:
            self.say("Wait until what runs now has finished, then start the game.", ok=False)
            return
        number = (steam.shortcut_number(self.steam_dir, shortcuts.for_game(game))
                  if self.steam_dir is not None and str(game.file) in self.in_steam else None)
        if number is None:
            self.say(f"{game.title} is not in Steam yet: tick it and press Update Steam first.", ok=False)
            return
        if self.ppsspp_running():
            self.say(RUNNING_START, ok=False)
            return
        url, title = steam.play_url(number), game.title
        play, open_url, started = self.steam_play, self.open_url, self.ppsspp_running

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
            self.say("Install PPSSPP first: the games in Steam start it.", ok=False)
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
                missing = [g.title for g in add if str(g.file) not in found]
                if missing:
                    extra.append(f"Read back from Steam's file, {len(add) - len(missing)} of the {len(add)} game(s) "
                                 f"are there: not {', '.join(missing)}.")
            again = " Steam was closed for it and starts again in the background." if restarted else ""
            return True, "\n".join([*notes, f"{len(add)} game(s) in Steam, under Non-Steam in the library"
                                              f"{f'; {len(remove)} taken out' if remove else ''}.{again}", *extra])
        self._start("Looking up covers and changing Steam's shortcuts…" if key else "Changing Steam's shortcuts…",
                    job)

    def on_covers(self) -> None:
        """Asks for the suite's SteamGridDB API key; empty turns the lookup off (the pictures kept stay in use)."""
        if covers.edit_key(self, self.covers_key, "Update Steam"):
            self.refresh()
            self.say("The SteamGridDB key was changed." if covers.read_key(self.covers_key) else
                     "The SteamGridDB key was taken out; the pictures kept stay in use.")

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        QTimer.singleShot(0, self.place_states)         # once the pills below have their new width

    def place_states(self) -> None:
        """The state ends at the middle of the last header pill: the spacer after it is half its width."""
        self.states_spacer.setFixedWidth(max(0, self.header_pills[-1].width() // 2))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        if self.worker.running and not self._ask("Close", "A download or a change to Steam is still running. "
                                                          "Close anyway?"):
            event.ignore()
            return
        self.worker.stop()
        self.release_check.stop()
        self.controller_timer.stop()
        self.settings.set_window_state("geometry", self.saveGeometry())
        self.settings.sync()
        super().closeEvent(event)
