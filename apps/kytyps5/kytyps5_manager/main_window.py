# SPDX-License-Identifier: GPL-3.0-or-later
"""The main window, built as PS5 shadPS4 Manager's (owner, 27-11-2026: take shadPS4 as the example). The header's pills
are the emulator's (its version, Install, Uninstall) and Refresh; the row under them the games' Uninstall, Available
in Steam, the emulator's optional GPU helper and what the board has of what the emulator asks; then two columns, the
state of each (KytyPS5-Native, the board, the game folders, the GPU helper) in a short line and the installed version
beside them; then the tabs: the games found, each with a box for Steam, Start game, and the app's log (View logs),
with Clear logs beside it. The look is the gaming apps' blue (style.py).

The app only checks the board (board.py) and sets nothing on it.
The GPU helper is an option, off unless you install it (owner, 27-11-2026)."""

from __future__ import annotations

import os
import subprocess
import time
from html import escape
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMainWindow,
                             QMessageBox, QPushButton, QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from bazzite_console_core import SUITE_MANUAL_URL, applog, covers, keep, steam, window_title
from bazzite_console_core import __version__ as CORE_VERSION
from bazzite_console_core.action_tab import ActionTab
from bazzite_console_core.keep_dialog import KeepDialog
from bazzite_console_core.log_page import LogPage
from bazzite_console_core.platform import bin_home, notify, private, xdg_open
from bazzite_console_core.theme import GREEN, RED
from bazzite_console_core.settings import SettingsStore
from bazzite_console_core.updates import ReleaseInfo, UpdateChecker
from bazzite_console_core.widgets import AppHeader, InfoButton, MetricBox, StatusText, WrappedLabel, hint_label

from . import (APP_ID, APP_NAME, INFO, LOGO_PATH, ROOT, __version__, board, controllers, emulator, library,
               shortcuts, style)
from .games import MAX_DEPTH, Game, scan

MANUAL_URL = f"{SUITE_MANUAL_URL}apps/kytyps5/"
STEAM_TIP = "Add the checked games to Steam and take out the others. Steam closes for it and starts again"
START_TIP = "Start the game chosen under Your games through Steam, as its shortcut in Steam does"
EXIT_TIP = "End KytyPS5-Native at once, with no question. A game that is running ends without saving"
CLEAR_TIP = "Empty the app's log file, the older ones beside it and the View logs tab"
STEAM_ON = "Steam runs and is signed in. The games in Steam can start."
STEAM_OFF = "Steam does not run or is not signed in. Start Steam and sign in before you start a game."
STEAM_URL = "steam://open/games"        # Steam's library; Steam starts when it does not run
STEAM, GAME, SERIAL, VERSION, FOLDER = range(5)             # the table's columns
WIDTH = 900                             # as PS5 shadPS4 Manager's window
HEIGHT = 606
NOT_INSTALLED = "Not installed. Install it with the Install button."
INSTALLED = "Installed. Uninstall with the Uninstall button."
UNINSTALL_GAME_TIP = ("Delete the game chosen under Your games from the disk. A window first lists what would go, "
                      "and you uncheck what to keep. Nothing is deleted before you confirm")
RUNNING_REMOVE = "KytyPS5-Native is running. Close it first, then remove the game."
RUNNING_START = "KytyPS5-Native is running. Close it first, then start the game."
NOT_AUTHORISED = (126, 127)             # pkexec: the password dialog was canceled or refused
HELPER_TIMEOUT = 300                    # s: the password dialog waits for the user
HELPER_UNIT = Path("/etc/systemd/system/kyty-lodhw.service")    # where the emulator's install-helper.sh puts it
HELPER_ABOUT = ("The GPU helper is a part of KytyPS5-Native that runs as a system service. For a game, it writes "
                "PS5 values to the GPU's registers and puts the old ones back afterward. The emulator runs without "
                "it. Installing it changes the board and asks for your password.")


def run_helper(script: Path, remove: bool) -> tuple[int, str]:
    """KytyPS5-Native's own install-helper.sh as root, through polkit: (exit code, what it printed). The script
    gives the helper's socket to the group in SUDO_GID, so the user's own group is passed in it."""
    command = ["pkexec", "/usr/bin/env", f"SUDO_GID={os.getgid()}", "/bin/sh", str(script)]
    try:
        done = subprocess.run(command + (["--remove"] if remove else []), capture_output=True, text=True,
                              timeout=HELPER_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return done.returncode, (done.stdout + done.stderr).strip()


def _with_info(state: QLabel, info: InfoButton) -> QWidget:
    """A state line with its info symbol right after it, at the top of its first line."""
    state.setWordWrap(False)
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(state)
    layout.addWidget(info, 0, Qt.AlignmentFlag.AlignTop)
    layout.addStretch(1)
    return row


class KytySettings(SettingsStore):
    DEFAULTS: dict = {}


class MainWindow(QMainWindow):
    CONTROLLER_POLL = 3000                  # ms: how often the window looks for a controller
    # The desktop notification when the window opens without a controller (owner, 28-11-2026); another in the tests.
    notify_desktop = staticmethod(notify)

    def __init__(self, home: Path | None = None, steam_dir: Path | None = None, run: Path | None = None,
                 fetch: emulator.Download = emulator.download, steam_closed=steam.with_steam_closed,
                 steam_running=steam.steam_running, newer_release=emulator.newer_release,
                 kyty_running=emulator.running, kyty_end=emulator.end, covers_home: Path | None = None,
                 covers_get: covers.Get = covers._get, covers_key: Path | None = None,
                 log_path: Path | None = None, devices: Path = controllers.DEVICES, open_url=xdg_open,
                 user_home: Path | None = None, drives: Callable[[], list[Path]] = library.removable_drives,
                 steam_play=steam.play, sys_root: Path = board.SYS, helper_unit: Path = HELPER_UNIT,
                 helper_run=run_helper):
        """*home*: where the app installs KytyPS5-Native; *steam_dir*: Steam's folder (None: looked up); *run*: the
        run wrapper the shortcuts start; *fetch*: the download; *steam_closed* and *steam_running*: closing Steam
        for a change and asking whether it runs; *newer_release*: asks GitHub for a newer KytyPS5-Native;
        *kyty_running* and *kyty_end*: whether the emulator runs, and ending it; *covers_home*, *covers_get* and
        *covers_key*: where the covers are kept, how SteamGridDB is asked and the suite's key file; *log_path*: the
        app's log file, as the View logs tab shows it; *devices*: the kernel's list of input devices, for the
        controller state; *open_url*: opens a URL on the desktop; *user_home*: the home folder with the app's own
        game folder, Games/PS5; *drives*: the removable drives looked at for one; *steam_play*: starts a game by
        its Steam address and waits until it runs; *sys_root*: the kernel's /sys, for the board's figures;
        *helper_unit*: the GPU helper's service file; *helper_run*: runs the emulator's install-helper.sh as root
        (tests never touch the real ones)."""
        super().__init__()
        self.setMinimumWidth(WIDTH)
        self.resize(WIDTH, HEIGHT)
        self.home = home or emulator.emulator_home()
        self.steam_dir = steam_dir if steam_dir is not None else steam.find_steam()
        self.log_path = log_path or applog.log_file(APP_ID)
        self.devices = devices
        self.open_url = open_url
        self.user_home = user_home or Path.home()
        self.drives = drives
        self.sys_root = sys_root
        self.helper_unit = helper_unit
        self.helper_run = helper_run
        self.run_path = run or bin_home() / shortcuts.RUN_NAME
        self.fetch = fetch
        self.steam_closed = steam_closed
        self.steam_running = steam_running
        self.kyty_running = kyty_running
        self.kyty_end = kyty_end
        self.covers_home = covers_home or covers.covers_home(APP_ID)
        self.covers_get = covers_get
        self.covers_key = covers_key
        self.steam_play = steam_play
        self._newer_release = newer_release
        self.newer: ReleaseInfo | None = None           # a newer KytyPS5-Native release than the pinned one
        self.release_check = UpdateChecker(self)        # apart from the worker: it runs while the window opens
        self.release_check.finished.connect(self._release_found)
        self.worker = UpdateChecker(self)               # one job at a time off the GUI thread
        self.worker.finished.connect(self._job_done)
        self.no_cover: set[str] = set()                 # games in Steam not yet looked up on SteamGridDB, with a key
        self.doubles: dict[str, int] = {}               # games in Steam more than once: how many shortcuts too many
        self.controllers: list[str] | None = None       # the controllers last seen; None before the first look
        self.log = applog.logger(APP_ID)
        self.settings = KytySettings(INFO, self)
        self.games: list[Game] = []
        self.in_steam: dict[str, str] = {}
        self.version = ""
        self.folders: list[Path] = []
        self.board = board.read(self.sys_root)

        header = AppHeader(LOGO_PATH, APP_NAME, __version__)
        self.pill = StatusText(name="Installed")
        header.add_action(self.pill)
        self.controller = StatusText(name="Controller")   # beside it: whether a controller is connected
        header.add_action(self.controller)
        self.steam_state = StatusText(name="Steam")       # and whether Steam runs and is signed in
        header.add_action(self.steam_state)
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
        self.emulator_box = MetricBox("KytyPS5 version", style.BLUE)
        self.steam_box = MetricBox("Available in Steam", style.BLUE)
        self.intro = hint_label(style.caption_link(self, emulator.RELEASE_PAGE, "KytyPS5-Native's release notes")
                                + " · " + style.caption_link(self, MANUAL_URL, "Wiki"), follow_height=True)
        self.intro.setStyleSheet(style.CAPTION)

        self.install_pill = style.action_pill("KytyPS5", "Install", f"Download KytyPS5-Native {emulator.VERSION} "
                                                                    f"from GitHub (about {emulator.SIZE_MB} MB) and "
                                                                    "check it")
        self.install_pill.clicked.connect(self.on_install)
        self.remove_pill = style.action_pill("KytyPS5", "Uninstall", "Remove the installed KytyPS5-Native. Its own "
                                                                     "folders stay, with saves and settings")
        self.remove_pill.clicked.connect(self.on_remove)
        self.remove_game_pill = style.action_pill("Games", "Uninstall", UNINSTALL_GAME_TIP)
        self.remove_game_pill.clicked.connect(self.on_remove_game)
        # The GPU helper (owner, 27-11-2026): an option, so the app changes nothing on the board by itself
        self.helper_pill = style.action_pill("GPU helper", "Install", HELPER_ABOUT)
        self.helper_pill.clicked.connect(self.on_helper)
        self.board_box = MetricBox("Board settings", style.BLUE)
        self.header_pills = [self.emulator_box, self.install_pill, self.remove_pill, self.refresh_pill]
        for box in self.header_pills:
            box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            header.add_second(box, 1)
        self.second_row = [self.remove_game_pill, self.steam_box, self.board_box, self.helper_pill]
        actions = QHBoxLayout()
        actions.setSpacing(8)
        for pill in self.second_row:                    # each a quarter of the width, whatever the window's
            pill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            actions.addWidget(pill, 1)

        # Two columns under the pills, as PS5 shadPS4 Manager's. The first: the state of each, each name with a colon.
        # The second: the KytyPS5-Native version installed.
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        self.emulator_state, self.board_state, self.folders_state, self.helper_state = (self._state_label()
                                                                                        for _ in range(4))
        self.board_info = InfoButton("", "What KytyPS5-Native asks of the board")
        self.folders_info = InfoButton("", "About the game folders")
        self.helper_info = InfoButton(f"{HELPER_ABOUT} {style.link(self, MANUAL_URL, 'Wiki')}", "About the GPU helper")
        infos = {self.board_state: self.board_info, self.folders_state: self.folders_info,
                 self.helper_state: self.helper_info}
        for row, (name, state) in enumerate((("KytyPS5-Native", self.emulator_state), ("Board", self.board_state),
                                             ("Game folders", self.folders_state),
                                             ("GPU helper", self.helper_state))):
            grid.addWidget(self._name_label(name), row, 0)
            grid.addWidget(_with_info(state, infos[state]) if state in infos else state, row, 1)
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
        self.table.setHorizontalHeaderLabels(["In Steam", "Game title", "ID", "Version", "Folder"])
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
                                       QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.Stretch)):
            head.setSectionResizeMode(column, mode)
        self.table.itemChanged.connect(lambda _item: self._update_buttons())

        self.exit_button = QPushButton("Exit KytyPS5")
        self.exit_button.setToolTip(EXIT_TIP)
        self.exit_button.clicked.connect(self.on_exit_kyty)
        self.show_exit()
        self.kyty_button = QPushButton("KytyPS5 settings")
        self.kyty_button.setToolTip("Open KytyPS5-Native's own window for what the app does not set. That is the "
                                    "controller, the screen and a game's own settings")
        self.kyty_button.clicked.connect(self.on_open_kyty)
        self.covers_button = QPushButton("Steam artwork…")
        self.covers_button.setToolTip("The SteamGridDB API key, one for the whole suite. With it, Update Steam "
                                      "gives each game its cover from SteamGridDB in Steam")
        self.covers_button.clicked.connect(self.on_covers)
        self.steam_button = style.primary_button("Update Steam", STEAM_TIP)
        self.steam_button.clicked.connect(self.on_update_steam)
        buttons = QHBoxLayout()
        self.steam_info = InfoButton("A checkmark before a game adds the game to Steam. When you click the Start "
                                     f"game button, the game starts from {style.link(self, STEAM_URL, 'Steam')}.",
                                     "About the games and Steam")
        self.steam_info.opens = lambda _url: self.open_steam()      # the app opens Steam itself (open_steam)
        buttons.addWidget(self.steam_info)
        buttons.addStretch(1)
        buttons.addWidget(self.exit_button)
        buttons.addWidget(self.kyty_button)
        buttons.addWidget(self.covers_button)
        buttons.addWidget(self.steam_button)
        games_page = QWidget()
        games = QVBoxLayout(games_page)
        games.setContentsMargins(0, 8, 0, 0)
        games.addWidget(self.table, 1)
        games.addLayout(buttons)

        self.log_page = LogPage(APP_NAME, "KytyPS5-Native", self.log_path,
                                "Everything the app said and did, newest last, and each game started from Steam.")
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setDrawBase(False)           # no line over the tabs, which that mode draws
        self.tabs.addTab(games_page, "Your games")
        self.start_tab = ActionTab(self.tabs, "Start game", START_TIP, self.on_start_game)
        self.tabs.addTab(self.log_page, "View logs")
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
        version = QLabel(f"{APP_NAME} {__version__} · core {CORE_VERSION} · KytyPS5-Native {emulator.VERSION}")
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
        """What a state line is about, bold, with a colon."""
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
        self.version = emulator.installed_version(self.home)
        self.folders = library.fixed(self.user_home, self.drives)
        self.board = board.read(self.sys_root)
        self.games = scan(self.folders)
        try:
            self.in_steam = shortcuts.in_steam(self.steam_dir) if self.steam_dir else {}
            self.doubles = shortcuts.doubles(self.steam_dir) if self.steam_dir else {}
            self.no_cover = ({str(g.eboot) for g in self.games if str(g.eboot) in self.in_steam
                              and not covers.known(self.covers_home, shortcuts.cover_name(g))}
                             if covers.read_key(self.covers_key) else set())
        except OSError:
            self.in_steam, self.doubles, self.no_cover = {}, {}, set()
        self._show_state()
        self._fill_table()
        self.show_controller()

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
                                       "reads it.")
        else:
            self.controller.set_status("No controller", "warn",
                                       "No controller is connected. Switch it on, or press its PS button to wake "
                                       "it, before you start a game from Steam.")
            if first:           # said on the desktop too, as the run wrappers do (owner, 28-11-2026)
                self.notify_desktop(APP_NAME, "No controller connected",
                                    "Switch your controller on, or press its PS button to wake it, before you "
                                    "start a game.")
                self.log.warning("No controller was connected when the window opened.")

    def helper_installed(self) -> bool:
        """Whether the emulator's GPU helper is installed as a system service."""
        try:
            return self.helper_unit.is_file()
        except OSError:
            return False

    def _show_board(self) -> None:
        """What the board has of what the emulator asks, each figure as the system gives it. The app sets none."""
        b = self.board
        if not b.found:
            self.board_state.setText("Not read")
            self.board_box.set_value("—", "No GPU that runs the amdgpu driver answered.")
            self.board_info.set_text("No GPU that runs the amdgpu driver answered, so the app cannot read the "
                                     "memory settings.")
            return
        wrong = [name for name, ok in (("VRAM split", b.vram_ok), ("GTT limit", b.gtt_ok),
                                       ("GPU driver options", b.options_ok)) if not ok]
        if wrong:
            self.board_state.setText(f"<b style='color:{RED};'>Not as KytyPS5-Native asks</b>")
            self.board_box.set_value(f"{len(wrong)} to set", "Not as KytyPS5-Native asks: " + ", ".join(wrong))
        else:
            self.board_state.setText(f"<b style='color:{GREEN};'>Ok</b>")
            self.board_box.set_value("Ok", "The board has the settings KytyPS5-Native asks.")
        options = " ".join(f"{name}={'?' if value is None else value}" for name, value in b.options.items())
        asked = " ".join(f"{name}={value}" for name, value in board.OPTIONS.items())
        mark = lambda ok: "ok" if ok else "to set"      # noqa: E731
        self.board_info.set_text(
            "KytyPS5-Native asks three things of the board. The app only reads them.<br><br>"
            f"VRAM split: {b.vram_mib} MB, asked {board.VRAM_MIB} MB ({mark(b.vram_ok)})<br>"
            f"GTT limit: {b.gtt_mib} MiB, asked {board.GTT_MIB} MiB ({mark(b.gtt_ok)})<br>"
            f"GPU driver options: {escape(options)}, asked {asked} ({mark(b.options_ok)})<br><br>"
            "KytyPS5-Native's README asks them for the AMD BC-250. "
            + style.link(self, MANUAL_URL, "Wiki"))

    def _show_state(self) -> None:
        self.emulator_state.setText(INSTALLED if self.version else NOT_INSTALLED)
        tip = f"KytyPS5-Native {emulator.VERSION}, the release this version of the app was tried with"
        if not self.version:
            tip = (f"Install downloads KytyPS5-Native {emulator.VERSION}, the release this version of the app was "
                   "tried with, and checks it before unpacking.")
        if self.newer is not None:              # in the tip and the log, so the line stays the state
            tip += (f"\nKytyPS5-Native {self.newer.tag} is out ({self.newer.published}). A later version of this "
                    f"app brings it, once it has been tried on the board: {self.newer.url}")
        self.emulator_state.setToolTip(tip)
        self.version_state.setToolTip(tip)
        self.emulator_box.set_value(self.version[:10] if self.version else "—",     # the date; the commit in the tip
                                    f"KytyPS5-Native {self.version or emulator.VERSION}")
        self.version_state.setText(escape(self.version) if self.version else "—")
        self._show_board()
        where = ", ".join(f"<b>{escape(private(f))}</b>" for f in self.folders)
        self.folders_state.setText(where)
        self.folders_info.set_text(f"Drop your games in {escape(private(self.user_home / library.GAMES_HOME))}, each "
                                   "in a folder of its own (with eboot.bin). A USB drive or an SD card with a "
                                   "Games/PS5 folder is also checked for content.")
        self.folders_state.setToolTip("\n".join(private(f) for f in self.folders)
                                      + f"\n{len(self.games)} game(s) found, up to {MAX_DEPTH} folders deep.")
        helper = self.helper_installed()
        self.helper_state.setText("Installed" if helper else "Not installed. The emulator runs without it.")
        self.helper_pill.caption.setText("Uninstall" if helper else "Install")
        found = {str(g.eboot) for g in self.games}
        self.steam_box.set_value(str(len(found & set(self.in_steam))))
        if not self.version:
            self.pill.set_status("Not installed", "warn", "Install KytyPS5-Native first.")
        elif not self.games:
            self.pill.set_status("No games", "neutral", "Put your games in Games/PS5.")
        elif not self.board.ok:
            self.pill.set_status("Check the board", "warn", "The board is not set as KytyPS5-Native asks.")
        else:
            self.pill.set_status("Ready", "ok", "KytyPS5-Native is installed and games were found.")

    def _fill_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.games))
        for row, game in enumerate(self.games):
            box = QTableWidgetItem()
            box.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            box.setCheckState(Qt.CheckState.Checked if str(game.eboot) in self.in_steam else Qt.CheckState.Unchecked)
            box.setToolTip(f"In Steam {self.doubles[str(game.eboot)] + 1} times: Update Steam leaves one"
                           if str(game.eboot) in self.doubles else "In Steam" if str(game.eboot) in self.in_steam
                           else "Not in Steam")
            self.table.setItem(row, STEAM, box)
            for column, text in ((GAME, game.title), (SERIAL, game.title_id), (VERSION, game.version),
                                 (FOLDER, game.folder.name or str(game.folder))):
                self.table.setItem(row, column, QTableWidgetItem(text))
            self.table.item(row, FOLDER).setToolTip(str(game.folder))     # the folder's name; the path as the tip
        self.table.blockSignals(False)
        self._update_buttons()

    def chosen(self) -> Game | None:
        row = self.table.currentRow()
        return self.games[row] if 0 <= row < len(self.games) else None

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
        installed = bool(self.version)
        self.refresh_pill.setEnabled(idle)
        self.install_pill.setEnabled(idle and self.version != emulator.VERSION)
        self.remove_pill.setEnabled(idle and installed)
        self.helper_pill.setEnabled(idle and (installed or self.helper_installed()))
        self.kyty_button.setEnabled(idle and installed)
        self.covers_button.setEnabled(idle)
        self.remove_game_pill.setEnabled(idle and self.chosen() is not None)
        add, remove = self.steam_plan()
        stale = self.no_cover | set(self.doubles)
        named = shortcuts.names(add)
        changed = bool(remove) or any(self.in_steam.get(str(g.eboot)) != named[g.eboot] or str(g.eboot) in stale
                                      for g in add)
        self.steam_button.setEnabled(idle and changed and self.steam_dir is not None and not steam.game_mode())
        if self.steam_dir is None:
            self.steam_button.setToolTip("Steam was never started on this system. Start it once first")
        elif steam.game_mode():
            self.steam_button.setToolTip("In Game Mode (a handheld's Steam session), Steam is the session itself. "
                                         "Change it in Desktop Mode")
        else:
            self.steam_button.setToolTip(STEAM_TIP)

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
        """Clear logs: the log the View logs tab shows emptied, the app's or the emulator's, with the older ones
        kept beside it, and the tab with it. Said in the line under the tabs only, so the log stays empty."""
        failed = self.log_page.clear(APP_ID)
        if failed is not None:
            self.say(f"The log could not be cleared: {private(failed)}", ok=False)
        else:
            self.running.setStyleSheet("font-weight:600;")
            self.running.setText("The log was cleared.")

    def _release_found(self, release: ReleaseInfo | None) -> None:
        self.newer = release
        if release is not None:
            self.note(f"KytyPS5-Native {release.tag} is out ({release.published}): {release.url}. A later version "
                      "of this app brings it, once it has been tried on the board.")
        self._show_state()

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
                "Install", f"Download KytyPS5-Native {emulator.VERSION} from GitHub (about {emulator.SIZE_MB} MB)?"
                "\n\nIt is checked against the SHA-256 this app was tried with before it is unpacked into "
                f"{private(self.home)}."):
            return
        home, fetch = self.home, self.fetch

        def job() -> tuple[bool, str]:
            try:
                return True, emulator.install(home, fetch)
            except (emulator.EmulatorError, OSError) as error:
                return False, f"KytyPS5-Native was not installed: {error}"
        self._start(f"Downloading KytyPS5-Native {emulator.VERSION}…", job)

    def on_remove(self) -> None:
        if self.kyty_running():
            self.say("KytyPS5-Native is running. Close it first, then remove it.", ok=False)
            return
        text = "Remove the installed KytyPS5-Native?\n\nIts own folders, with your saves and settings, stay."
        if self.in_steam:
            text += "\nThe games in Steam no longer start until it is installed again."
        if self.helper_installed():
            text += "\nThe GPU helper stays installed. Uninstall it first with its own pill."
        if self._ask("Remove", text):
            emulator.remove(self.home)
            self.refresh()
            self.say("KytyPS5-Native was removed.")

    def on_helper(self) -> None:
        """The GPU helper's pill (owner, 27-11-2026: an option, never on by itself): the emulator's own
        install-helper.sh, as root through polkit, installs the helper as a system service or removes it."""
        remove = self.helper_installed()
        script = self.home / "current" / emulator.HELPER_INSTALL
        if not script.is_file():
            self.say("Install KytyPS5-Native first: the GPU helper comes with it.", ok=False)
            return
        if self.kyty_running():
            self.say("KytyPS5-Native is running. Close it first, then change the GPU helper.", ok=False)
            return
        if remove:
            text = ("Uninstall the GPU helper?\n\nThe system service kyty-lodhw stops and is removed.\n"
                    "The emulator runs without it.\n\nYou are asked for your password.")
        else:
            text = ("Install the GPU helper?\n\nIt runs as a system service, kyty-lodhw, from every start of the "
                    "board.\nFor a game, it writes PS5 values to the GPU's registers.\nThe emulator runs without "
                    "it.\nUninstall removes it again.\n\nYou are asked for your password.")
        if not self._ask("GPU helper", text):
            return
        run = self.helper_run

        def job() -> tuple[bool, str]:
            code, output = run(script, remove)
            if code in NOT_AUTHORISED:
                return False, "The GPU helper was not changed: no password was given."
            if code:
                return False, f"The GPU helper was not changed: {output or f'exit code {code}'}"
            return True, "The GPU helper was uninstalled." if remove else "The GPU helper is installed and runs."
        self._start("Removing the GPU helper…" if remove else "Installing the GPU helper…", job)

    def kyty_command(self, *args: str) -> list[str]:
        """The installed KytyPS5-Native through the run wrapper (from the app folder when it is not installed
        yet)."""
        run = self.run_path if self.run_path.is_file() else ROOT / shortcuts.RUN_NAME
        return [str(run), *args]

    def open_steam(self) -> None:
        """The Steam link: Steam's library on the desktop (Steam starts when it does not run)."""
        if self.open_url(STEAM_URL):
            self.note("Steam was opened.")
        else:
            self.say("Steam could not be opened, because xdg-open is missing.", ok=False)

    def show_exit(self) -> None:
        """Exit KytyPS5 is on while KytyPS5-Native runs."""
        self.exit_button.setEnabled(self.kyty_running())

    def on_exit_kyty(self) -> None:
        """Exit KytyPS5: KytyPS5-Native and everything it started end at once, with no question."""
        if self.kyty_end():
            self.say("KytyPS5-Native was ended.")
        else:
            self.say("KytyPS5-Native was not running.")
        self.show_exit()

    def on_open_kyty(self) -> None:
        command = self.kyty_command("--launcher")
        if QProcess.startDetached(command[0], command[1:])[0]:
            self.note("KytyPS5-Native's own window was opened.")
        else:
            self.say(f"KytyPS5-Native could not be started: {private(command[0])} did not run.", ok=False)

    def on_remove_game(self) -> None:
        """Games Uninstall, as PS5 shadPS4 Manager's: a window lists what of the chosen game would go, a row each with
        its size; unticking keeps it, and nothing is deleted before the user confirms. The saves stay."""
        game = self.chosen()
        if game is None:
            return
        if self.kyty_running():
            self.say(RUNNING_REMOVE, ok=False)
            return
        items, why = library.removal_items(game, self.folders, self.games, str(game.eboot) in self.in_steam)
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
                    closed(lambda: steam.write_shortcuts(folder, shortcuts.changes([], [game], run, LOGO_PATH,
                                                                                   existing)))
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
        """The Start game tab, as PS5 shadPS4 Manager's: the chosen game started through Steam, as its shortcut there
        starts it. Off the window's thread, with core's play(): a Steam that does not run is started and waited
        for, and the line says the game runs only once KytyPS5-Native does."""
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
            self.say(f"{game.title} is not in Steam yet: check it and press Update Steam first.", ok=False)
            return
        if self.kyty_running():
            self.say(RUNNING_START, ok=False)
            return
        url, title = steam.play_url(number), game.title
        play, open_url, started = self.steam_play, self.open_url, self.kyty_running

        def job() -> tuple[bool, str]:
            try:
                play(url, open_url, started)
            except steam.SteamError as error:
                return False, f"{title} was not started: {error}"
            return True, f"{title} runs, started through Steam."
        self._start(f"Starting {title} through Steam, which starts first when it does not run…", job)

    def on_update_steam(self) -> None:
        if self.steam_dir is None:
            return
        if not self.run_path.is_file():
            self.say(f"The shortcuts run {private(self.run_path)}, which is not there. Install {APP_NAME} through "
                     "the portal first.", ok=False)
            return
        add, remove = self.steam_plan()
        if add and not self.version:
            self.say("Install KytyPS5-Native first: the games in Steam start it.", ok=False)
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
                # Read back right after the write, while Steam is still closed: whether the shortcuts were written
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
                                 f"are there. Missing: {', '.join(missing)}.")
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
                     "The SteamGridDB key was taken out. The app still uses the covers it kept.")

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        QTimer.singleShot(0, self.place_states)         # once the pills below have their new width

    def place_states(self) -> None:
        """The states end at the middle of the last header pill: the spacer after them is half its width."""
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
