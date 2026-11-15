# SPDX-License-Identifier: GPL-3.0-or-later
"""The helpers' windows. Each is the suite's window: the icon at 96 px, the helper's name with the version, its
state, the info symbol with what it contains and does, and Refresh; its status boxes and controls on the second row.
Game Memory Map and Persistent Journal are switches (SwitchWindow): Turn on when it is off, Turn off when the helper
turned it on, one password each (pkexec, system.py); what is on already cannot be turned on again. Boot Command Line
edits the PS5 loader's cmdline.txt one argument per row (kargs.py says what each does), and its Save changes asks
Yes, No or Cancel first."""

from __future__ import annotations

import datetime
import shlex
import tempfile
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

from bazzite_console_core import window_title
from bazzite_console_core.appinfo import SUITE_MANUAL_URL
from bazzite_console_core.platform import launch_in_terminal, show_in_folder
from bazzite_console_core.theme import GREEN, GREY, ORANGE
from bazzite_console_core.widgets import AppHeader, InfoButton, MetricBox, StatusText, hint_label

from . import LOGO_PATH, __version__, kargs, runner, state, system
from .catalog import BY_KEY, Helper

RootRunner = Callable[[list[str]], runner.Result]
BOARD = ("<br><br><b>Changes the board.</b> It asks for your password once (pkexec). It never touches the console's "
         "firmware, and Turn off undoes it.")


class HelperWindow(QMainWindow):
    """One helper's window: the header, then the page the helper fills (self.page)."""

    BOARD_NOTE = BOARD                  # the info's last paragraph, for a helper that changes the board

    def __init__(self, helper: Helper, info: str, run_root: RootRunner = runner.run_root,
                 root: Path = state.ROOT, home: Path | None = None) -> None:
        super().__init__()
        self.helper, self.run_root, self.root, self.home = helper, run_root, root, home or Path.home()
        self.setWindowTitle(helper.name)
        self.resize(820, 420)
        self.header = AppHeader(LOGO_PATH, helper.name, __version__)
        self.state = StatusText()
        self.header.add_state(self.state)
        self.info = InfoButton(info + (self.BOARD_NOTE if helper.changes_board else ""))
        self.header.add_state(self.info)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Read again")
        self.refresh_button.clicked.connect(self.refresh)
        self.header.add_action(self.refresh_button)
        contents = QWidget()
        self.page = QVBoxLayout(contents)
        self.page.addLayout(self.header)
        self.setCentralWidget(contents)

    def refresh(self) -> None:
        raise NotImplementedError

    def as_root(self, args: list[str], title: str) -> bool:
        """Runs system.py as root; a canceled password or a failure shows a message, and the window reads again."""
        result = self.run_root(system.command(args))
        problem = system.answer(result.code, result.out)
        if problem:
            QMessageBox.warning(self, window_title(title), problem)
        self.refresh()
        return not problem


# ------------------------------------------------------------------------------------------------- Test Extras
EXTRAS_INFO = ("<b>Test Extras</b> shows the optional tools PS5 Board Test's tests use, whether each one is "
               "there, and which tests use it. Board Test runs without them: a test whose tool is missing says so."
               "<br><br><b>Install…</b> runs Board Test's own installer, <code>install-requirements.sh</code>, "
               "for one group in a terminal: it asks for your password where it layers packages and skips what is "
               "there already. <b>Install all</b> installs every group but the development extras.<br><br>"
               "Layered RPM packages are active after a reboot (<code>systemctl reboot</code>). glmark2, "
               "vulkan-tools and smartmontools come with Bazzite.")


class ExtrasWindow(HelperWindow):
    def __init__(self, launch: Callable[[str], None] = launch_in_terminal, board_test: Path = state.BOARD_TEST,
                 **kwargs) -> None:
        super().__init__(BY_KEY["extras"], EXTRAS_INFO, **kwargs)
        self.launch, self.board_test = launch, board_test
        self.resize(900, 560)
        self.found_box = MetricBox("Tools found")
        self.header.add_second(self.found_box)
        self.all_button = QPushButton("Install all")
        self.all_button.setToolTip("Every group but the development extras, in a terminal (--all)")
        self.all_button.clicked.connect(lambda: self.install("--all"))
        self.header.add_second(self.all_button)
        self.header.add_second(QWidget(), 1)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(2, 1)
        self.page.addLayout(self.grid)
        self.page.addStretch(1)
        self.rows: dict[str, QLabel] = {}
        self.buttons: dict[str, QPushButton] = {}
        row = 0
        for group in state.GROUPS:
            title = QLabel(f"<b>{group.name}</b>")
            title.setToolTip(group.what)
            self.grid.addWidget(title, row, 0, 1, 3)
            button = QPushButton("Install…")
            button.setToolTip(f"{group.what} ({group.option})")
            button.clicked.connect(lambda _=False, o=group.option: self.install(o))
            self.grid.addWidget(button, row, 3)
            self.buttons[group.option] = button
            row += 1
            for tool in group.tools:
                row = self._tool_row(tool, row)
        title = QLabel("<b>With Bazzite</b>")
        title.setToolTip("Already on Bazzite: nothing to install.")
        self.grid.addWidget(title, row, 0, 1, 4)
        row += 1
        for tool in state.BUILT_IN:
            row = self._tool_row(tool, row)
        self.refresh()

    def _tool_row(self, tool: state.Tool, row: int) -> int:
        mark = QLabel()
        self.rows[tool.command] = mark
        self.grid.addWidget(mark, row, 0)
        self.grid.addWidget(QLabel(tool.package), row, 1)
        self.grid.addWidget(hint_label(f"Tests {tool.used_by}" if tool.used_by[0].isdigit() else tool.used_by),
                            row, 2, 1, 2)
        return row + 1

    def refresh(self) -> None:
        tools = [t for g in state.GROUPS for t in g.tools] + list(state.BUILT_IN)
        found = 0
        for tool in tools:
            where = state.find_tool(tool.command, self.home)
            found += bool(where)
            self.rows[tool.command].setText(f"<span style='color:{GREEN if where else GREY};'>"
                                            f"{'●' if where else '○'}</span>")
            self.rows[tool.command].setToolTip(where or f"{tool.command} is not on PATH")
        self.found_box.set_value(f"{found}/{len(tools)}", "The tools the tests can find now; a layered package "
                                 "counts after the reboot.")
        self.found_box.set_colour(GREEN if found == len(tools) else ORANGE)
        script = state.installer(self.board_test)
        for button in (*self.buttons.values(), self.all_button):
            button.setEnabled(script is not None)
        for group in state.GROUPS:
            if all(state.find_tool(t.command, self.home) for t in group.tools):
                self.buttons[group.option].setEnabled(False)
                self.buttons[group.option].setToolTip("Everything in this group is there.")
        if script is None:
            self.state.set_status("Board Test not found", "warn",
                                  f"Its installer is not in {self.board_test}: install Board Test from the portal.")
        else:
            self.state.set_status("Ready", "ok")

    def install(self, option: str) -> None:
        script = state.installer(self.board_test)
        if script is None:
            return
        try:
            self.launch(f"{shlex.quote(str(script))} {option}")
        except RuntimeError as exc:
            QMessageBox.warning(self, window_title("Install"), str(exc))


# --------------------------------------------------------------------------------------------- MangoHud Config
MANGOHUD_INFO = ("<b>MangoHud Config</b> opens MangoHud's own settings file, <code>~/.config/MangoHud/"
                 "MangoHud.conf</code>, to edit and save; a file that is not there yet is made on Save.<br><br>"
                 "<b>FPS log</b> sets the three lines PS5 Board Test needs to show a game's FPS: "
                 "<code>output_folder=~/mangohud-logs</code>, <code>autostart_log=1</code> and "
                 "<code>log_interval=500</code>; Save then makes the folder. MangoHud writes a log file per game "
                 "session while the game runs. Delete old logs removes the ones older than 30 days.<br><br>"
                 "MangoHud must be active for the game, for example with the Steam launch option "
                 "<code>mangohud %command%</code>. Without the log, Board Test still shows the game's name and its "
                 "CPU and GPU share.")
OLD_LOG_DAYS = 30


class MangoHudWindow(HelperWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(BY_KEY["mangohud"], MANGOHUD_INFO, **kwargs)
        self.resize(900, 640)
        self.path = state.mangohud_conf(self.home)
        self.folder = self.home / state.LOG_FOLDER
        self.file_box = MetricBox("File")
        self.log_box = MetricBox("FPS log")
        self.logs_box = MetricBox("Log files")
        self.log_button = QPushButton("FPS log")
        self.log_button.setToolTip("Set the three lines of the FPS log in the text; Save writes them")
        self.log_button.clicked.connect(self.add_logging)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save)
        self.revert_button = QPushButton("Revert")
        self.revert_button.setToolTip("Read the file again; your edits go")
        self.revert_button.clicked.connect(self.refresh)
        self.folder_button = QPushButton("Log folder")
        self.folder_button.setToolTip(f"Open {self.folder}")
        self.folder_button.clicked.connect(lambda: show_in_folder(self.folder))
        self.clean_button = QPushButton("Delete old logs")
        self.clean_button.setToolTip(f"Remove the log files older than {OLD_LOG_DAYS} days")
        self.clean_button.clicked.connect(self.delete_old_logs)
        for widget in (self.file_box, self.log_box, self.logs_box):
            self.header.add_second(widget)
        self.header.add_second(QWidget(), 1)
        for widget in (self.log_button, self.folder_button, self.clean_button, self.revert_button, self.save_button):
            self.header.add_second(widget)
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.textChanged.connect(self.show_changed)
        self.page.addWidget(self.editor, 1)
        self.saved = ""
        self.refresh()

    def refresh(self) -> None:
        try:
            self.saved = self.path.read_text(encoding="utf-8")
            exists = True
        except FileNotFoundError:
            self.saved, exists = "", False
        except OSError as exc:
            self.saved, exists = "", False
            self.state.set_status("Not readable", "bad", str(exc))
        self.editor.blockSignals(True)
        self.editor.setPlainText(self.saved)
        self.editor.blockSignals(False)
        self.file_box.set_value("There" if exists else "New", str(self.path) if exists else
                                f"{self.path} is not there yet: Save makes it.")
        self.file_box.set_colour(GREEN if exists else GREY)
        logs = state.log_files(self.folder)
        self.logs_box.set_value(str(len(logs)), f"In {self.folder}")
        self.folder_button.setEnabled(self.folder.is_dir())
        self.clean_button.setEnabled(bool(self.old_logs()))
        self.show_changed()

    def show_changed(self) -> None:
        text = self.editor.toPlainText()
        changed = text != self.saved
        self.save_button.setEnabled(changed)
        self.revert_button.setEnabled(changed)
        values = state.conf_values(text)
        on = state.logging_on(values)
        self.log_box.set_value("On" if on else "Off", f"Logs to {values['output_folder']}" if on else
                               "MangoHud writes no log: FPS log sets it.")
        self.log_box.set_colour(GREEN if on else GREY)
        self.log_button.setEnabled(state.with_logging(text, self.folder) != (text if text.endswith("\n") or not text
                                                                             else text + "\n"))
        self.state.set_status("Edited, not saved" if changed else "Saved", "warn" if changed else "ok")

    def add_logging(self) -> None:
        self.editor.setPlainText(state.with_logging(self.editor.toPlainText(), self.folder))

    def save(self) -> None:
        text = self.editor.toPlainText()
        if text and not text.endswith("\n"):
            text += "\n"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(self.path)
            folder = state.conf_values(text).get("output_folder", "")
            if folder:
                Path(folder).expanduser().mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, window_title("Save"), f"{self.path} could not be written: {exc}")
            return
        self.refresh()

    def old_logs(self) -> list[Path]:
        limit = datetime.datetime.now().timestamp() - OLD_LOG_DAYS * 86400
        return [p for p in state.log_files(self.folder) if p.stat().st_mtime < limit]

    def delete_old_logs(self) -> None:
        old = self.old_logs()
        if not old or QMessageBox.question(
                self, window_title("Delete old logs"), f"Delete the {len(old)} log files older than {OLD_LOG_DAYS} "
                f"days in {self.folder}?") != QMessageBox.StandardButton.Yes:
            return
        for path in old:
            path.unlink(missing_ok=True)
        self.refresh()


# -------------------------------------------------------------------------------------------------- the switches
class SwitchWindow(HelperWindow):
    """A helper that turns one thing on or off: its status boxes, Turn on and Turn off. A subclass reads its state
    in read() and returns what the window shows."""

    CHANGE = ""                         # system.py's change: mapcount, journal

    def __init__(self, helper: Helper, info: str, boxes: tuple[str, ...], **kwargs) -> None:
        super().__init__(helper, info, **kwargs)
        self.boxes = {caption: MetricBox(caption) for caption in boxes}
        for box in self.boxes.values():
            self.header.add_second(box)
        self.header.add_second(QWidget(), 1)
        self.on_button = QPushButton("Turn on")
        self.on_button.clicked.connect(self.turn_on)
        self.off_button = QPushButton("Turn off")
        self.off_button.clicked.connect(self.turn_off)
        self.header.add_second(self.on_button)
        self.header.add_second(self.off_button)
        self.note = hint_label("")
        self.page.addWidget(self.note)
        self.page.addStretch(1)

    def show_box(self, caption: str, value: str, tooltip: str, good: bool | None) -> None:
        box = self.boxes[caption]
        box.set_value(value, tooltip)
        box.set_colour(GREY if good is None else GREEN if good else ORANGE)

    def on_args(self) -> list[str]:
        return [self.CHANGE, "on"]

    def turn_on(self) -> None:
        self.as_root(self.on_args(), "Turn on")

    def turn_off(self) -> None:
        self.as_root([self.CHANGE, "off"], "Turn off")


MAPCOUNT_INFO = ("<b>Game Memory Map</b> raises <code>vm.max_map_count</code>, the number of memory areas one program "
                 "may map. Some games (and Proton) need many more than the kernel's default and crash without them; "
                 f"SteamOS and Bazzite set {system.MAPCOUNT}.<br><br>Turn on writes it to "
                 f"<code>/etc/{system.MAPCOUNT_CONF}</code> and sets it now. Turn off removes that file and reads the "
                 "system's settings again. PS5 Board Test's test 37 reports the value.")


class MapCountWindow(SwitchWindow):
    CHANGE = "mapcount"

    def __init__(self, **kwargs) -> None:
        super().__init__(BY_KEY["mapcount"], MAPCOUNT_INFO, ("vm.max_map_count", "Set by"), **kwargs)
        self.refresh()

    def refresh(self) -> None:
        m = state.mapcount(self.root)
        high = m.value >= system.MAPCOUNT
        self.show_box("vm.max_map_count", f"{m.value:,}" if m.value else "—",
                      f"{system.MAPCOUNT:,} or more is what games need", high if m.value else None)
        self.show_box("Set by", "This helper" if m.ours else "The system" if high else "—",
                      f"/etc/{system.MAPCOUNT_CONF}" if m.ours else "Another sysctl.d file, or the image's own"
                      if high else "The kernel's default", True if high else None)
        self.on_button.setEnabled(not high)
        self.off_button.setEnabled(m.ours)
        self.state.set_status("On" if high else "Off", "ok" if high else "info")


JOURNAL_INFO = ("<b>Persistent Journal</b> keeps the system journal on the disk, in <code>/var/log/journal</code>. "
                "Without that folder journald keeps it in memory only, and the logs of a boot that crashed or froze "
                "are gone after it: PS5 Board Test's test 34 cannot read the previous boot's.<br><br>Turn on makes "
                "the folder (<code>systemd-tmpfiles --create</code>) and moves the journal there "
                "(<code>journalctl --flush</code>). Turn off works only on a folder this helper made: it moves the "
                "journal back to memory and removes the folder, with the logs in it. journald keeps the folder's size "
                "within its own limits.")


class JournalWindow(SwitchWindow):
    CHANGE = "journal"

    def __init__(self, **kwargs) -> None:
        super().__init__(BY_KEY["journal"], JOURNAL_INFO, ("Journal", "Made by"), **kwargs)
        self.refresh()

    def refresh(self) -> None:
        j = state.journal(self.root)
        self.show_box("Journal", "On disk" if j.persistent else "In memory", "/var/log/journal", j.persistent)
        self.show_box("Made by", "This helper" if j.ours else "The system" if j.persistent else "—",
                      "The folder was there already" if j.persistent and not j.ours else "", True if j.persistent
                      else None)
        self.on_button.setEnabled(not j.persistent)
        self.off_button.setEnabled(j.ours)
        self.state.set_status("On" if j.persistent else "Off", "ok" if j.persistent else "info")

    def turn_off(self) -> None:
        if QMessageBox.question(self, window_title("Turn off"), "Remove /var/log/journal, with the logs of every "
                                "earlier boot in it?") == QMessageBox.StandardButton.Yes:
            super().turn_off()


# ------------------------------------------------------------------------------------------- Boot Command Line
CMDLINE_INFO = ("<b>Boot Command Line</b> edits <code>/boot/efi/cmdline.txt</code>, the kernel command line the PS5 "
                "loader starts Linux with, one argument per row, with what each one does. <b>All settings</b> lists "
                "every argument the PS5 Linux command lines use, with its values. The list above the table also "
                "opens the fallback lines beside it (<code>cmdline.txt.m2</code>, <code>cmdline.txt.usb</code>), "
                "which you copy over <code>cmdline.txt</code> to start another system.<br><br><b>Add</b> puts a "
                "known argument, or an empty row, under the selected one; <b>Remove</b>, <b>Up</b> and <b>Down</b> "
                "work on the selected row; a double click edits a row. <b>Save changes</b> asks first: <b>Yes</b> "
                "writes the line, after a dated backup of the file beside it "
                "(<code>cmdline.txt.bak-YYYYMMDD-HHMMSS</code>); <b>No</b> drops your edits; <b>Cancel</b> goes back "
                "to editing. A line without <code>root=</code> is not saved. The change applies from the next boot: "
                "restart the console (<code>systemctl reboot</code>). When your user may not read the file, "
                "<b>Read</b> shows it after your password.")
CMDLINE_BOARD = ("<br><br><b>Changes the board.</b> It changes the boot settings of PS5 Linux: a wrong argument can "
                 "keep Linux from starting. Save changes asks for your password (pkexec) and keeps a backup of the "
                 "file; it never touches the console's firmware.")
SAVE_QUESTION = ("Save the changes to /boot/efi/{name}?\n\nThis changes the boot settings of PS5 Linux: a wrong "
                 "argument can keep Linux from starting. A dated backup of the file is kept beside it, and the change "
                 "applies from the next boot.\n\nYes saves, No drops your edits, Cancel goes back to editing.")
BOOT_PARTITION_URL = SUITE_MANUAL_URL + "boot-partition/"
BOOT_PARTITION_INFO = ("The loader's partition, <code>/boot/efi</code>, holds what the PS5 starts Linux with: "
                       "<code>bzImage</code>, <code>initrd.img</code>, <code>cmdline.txt</code> and <code>vram.txt</code>"
                       ", with the fallback lines and backups beside them. <a href=\"{url}\">PS5 Linux boot partition"
                       "</a> in the wiki describes every file and every argument, and the way back when Linux does not "
                       "start after a change.").format(url=BOOT_PARTITION_URL)
ARGUMENT, MEANING = range(2)


class CmdlineWindow(HelperWindow):
    BOARD_NOTE = CMDLINE_BOARD

    def __init__(self, **kwargs) -> None:
        super().__init__(BY_KEY["cmdline"], CMDLINE_INFO, **kwargs)
        self.resize(1000, 560)
        self.file_box = MetricBox("File")
        self.args_box = MetricBox("Arguments")
        self.backups_box = MetricBox("Backups")
        for widget in (self.file_box, self.args_box, self.backups_box):
            self.header.add_second(widget)
        self.file_list = QComboBox()
        self.file_list.setToolTip("The command line to edit: cmdline.txt, or a fallback line beside it")
        self.file_list.currentTextChanged.connect(self.open_file)
        self.header.add_second(self.file_list)
        self.header.add_second(QWidget(), 1)
        self.read_button = QPushButton("Read")
        self.read_button.setToolTip("Read the file with your password: your user may not read it")
        self.read_button.clicked.connect(self.read_as_root)
        self.revert_button = QPushButton("Revert")
        self.revert_button.setToolTip("Read the file again; your edits go")
        self.revert_button.clicked.connect(self.refresh)
        self.save_button = QPushButton("Save changes")
        self.save_button.clicked.connect(self.save)
        for widget in (self.read_button, self.revert_button, self.save_button):
            self.header.add_second(widget)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Argument", "What it does"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(ARGUMENT, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(MEANING, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.argument_edited)
        self.table.itemSelectionChanged.connect(self.show_changed)
        self.page.addWidget(self.table, 1)

        rows = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.setToolTip("Add an argument under the selected row")
        menu = QMenu(self.add_button)
        for setting in kargs.SETTINGS:
            if setting.example:
                menu.addAction(setting.example, lambda arg=setting.example: self.add_row(arg))
        menu.addSeparator()
        menu.addAction("Empty row", lambda: self.add_row(""))
        self.add_button.setMenu(menu)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_row)
        self.up_button = QPushButton("Up")
        self.up_button.clicked.connect(lambda: self.move_row(-1))
        self.down_button = QPushButton("Down")
        self.down_button.clicked.connect(lambda: self.move_row(1))
        self.settings_button = QPushButton("All settings")
        self.settings_button.setToolTip("What every argument of the PS5 Linux command lines does")
        self.settings_button.clicked.connect(self.show_settings)
        for widget in (self.add_button, self.remove_button, self.up_button, self.down_button):
            rows.addWidget(widget)
        rows.addStretch(1)
        rows.addWidget(self.settings_button)
        self.partition_info = InfoButton(BOOT_PARTITION_INFO, "The PS5 Linux boot partition")
        rows.addWidget(self.partition_info)
        self.page.addLayout(rows)
        self.line = QLineEdit()
        self.line.setReadOnly(True)
        self.line.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.line.setToolTip("The line Save changes writes")
        self.page.addWidget(self.line)
        self.note = hint_label("")
        self.page.addWidget(self.note)
        self.name = system.CMDLINES[0]
        self.saved = ""                 # the file's text as last read or saved
        self.readable = True
        self.refresh()

    # ------------------------------------------------------------------------------------------ the rows
    def arguments(self) -> list[str]:
        args = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, ARGUMENT)
            args += kargs.split(item.text() if item else "")
        return args

    def text(self) -> str:
        return kargs.join(self.arguments())

    def set_row(self, row: int, arg: str) -> None:
        """The row's argument and what it does; the items stay, so an edit in progress keeps its item."""
        self.table.blockSignals(True)
        for column, text in ((ARGUMENT, arg),
                             (MEANING, kargs.describe(arg) or ("Not in the list of known arguments." if arg else ""))):
            item = self.table.item(row, column)
            if item is None:
                item = QTableWidgetItem()
                if column == MEANING:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)
            item.setText(text)
        self.table.blockSignals(False)
        self.table.resizeRowToContents(row)

    def show_text(self, text: str) -> None:
        args = kargs.split(" ".join(text.split("\n")))
        self.table.setRowCount(len(args))
        for row, arg in enumerate(args):
            self.set_row(row, arg)
        self.show_changed()

    def argument_edited(self, item: QTableWidgetItem) -> None:
        if item.column() == ARGUMENT:
            self.set_row(item.row(), item.text().strip())
            self.show_changed()

    def add_row(self, arg: str) -> None:
        row = self.table.currentRow() + 1 if self.table.currentRow() >= 0 else self.table.rowCount()
        self.table.insertRow(row)
        self.set_row(row, arg)
        self.table.selectRow(row)
        if not arg:
            self.table.editItem(self.table.item(row, ARGUMENT))
        self.show_changed()

    def remove_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.show_changed()

    def move_row(self, step: int) -> None:
        row = self.table.currentRow()
        if 0 <= row + step < self.table.rowCount() and row >= 0:
            args = [self.table.item(r, ARGUMENT).text() for r in range(self.table.rowCount())]
            args[row], args[row + step] = args[row + step], args[row]
            self.set_row(row, args[row])
            self.set_row(row + step, args[row + step])
            self.table.selectRow(row + step)
            self.show_changed()

    def show_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(window_title("All settings"))
        dialog.resize(760, 620)
        box = QVBoxLayout(dialog)
        text = QTextBrowser()
        text.setHtml(kargs.info_list())
        box.addWidget(text)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        box.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        dialog.open()
        self.settings_dialog = dialog

    # ------------------------------------------------------------------------------------------ the file
    def open_file(self, name: str) -> None:
        if name and name != self.name:
            self.name = name
            self.saved = ""
            self.refresh()

    def refresh(self) -> None:
        names = state.cmdline_files(self.root)
        if self.name not in names:
            self.name = names[0]
        self.file_list.blockSignals(True)
        self.file_list.clear()
        self.file_list.addItems(names)
        self.file_list.setCurrentText(self.name)
        self.file_list.blockSignals(False)
        c = state.cmdline(self.root, self.name)
        self.path, self.readable = c.path, c.text is not None
        if c.text is not None:
            self.saved = c.text
        exists = c.exists
        self.file_box.set_value("There" if exists and self.readable else "Locked" if exists else "Missing",
                                str(c.path) if exists and self.readable else
                                f"{c.path}: your user may not read it; Read shows it after your password"
                                if exists else f"{c.path} is not there: is the loader's partition mounted?")
        self.file_box.set_colour(GREEN if exists and self.readable else ORANGE)
        self.backups_box.set_value(str(c.backups), f"{c.path.name}.bak-* beside it")
        self.read_button.setEnabled(not self.readable)
        self.show_text(self.saved)

    def show_changed(self) -> None:
        text = self.text()
        changed = text != kargs.join(kargs.split(" ".join(self.saved.split("\n"))))
        problem = system.cmdline_problem(text) if changed else ""
        self.args_box.set_value(str(len(self.arguments())), "The kernel arguments on the line")
        self.line.setText(text)
        self.save_button.setEnabled(changed and not problem)
        self.revert_button.setEnabled(changed)
        self.file_list.setEnabled(not changed and self.file_list.count() > 1)
        self.file_list.setToolTip("Save or Revert your edits first" if changed else
                                  "The command line to edit: cmdline.txt, or a fallback line beside it")
        row = self.table.currentRow()
        self.remove_button.setEnabled(row >= 0)
        self.up_button.setEnabled(row > 0)
        self.down_button.setEnabled(0 <= row < self.table.rowCount() - 1)
        if problem:
            self.state.set_status("Not valid", "bad", problem)
        elif changed:
            self.state.set_status("Edited, not saved", "warn")
        elif not self.readable and not self.saved:
            self.state.set_status("Not readable", "warn", "Read shows the file after your password.")
        else:
            self.state.set_status("Saved", "ok")
        self.note.setText(problem)

    def read_as_root(self) -> None:
        result = self.run_root(system.command(["cmdline", "show", "--file", self.name]))
        problem = system.answer(result.code, result.out)
        if problem:
            QMessageBox.warning(self, window_title("Read"), problem)
            return
        self.saved = result.out
        self.show_text(self.saved)

    def save(self) -> None:
        buttons = (QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                   | QMessageBox.StandardButton.Cancel)
        answer = QMessageBox.question(self, window_title("Save changes"), SAVE_QUESTION.format(name=self.name),
                                      buttons, QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.No:
            self.show_text(self.saved)                      # the edits go
            return
        if answer != QMessageBox.StandardButton.Yes:
            return                                          # Cancel: back to editing
        text = self.text() + "\n"
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "cmdline.txt"
            source.write_text(text, encoding="utf-8")
            result = self.run_root(system.command(["cmdline", "save", "--text", str(source), "--file", self.name]))
        problem = system.answer(result.code, result.out)
        if problem:
            QMessageBox.warning(self, window_title("Save changes"), problem)    # the edits stay
            return
        self.saved = text
        self.refresh()
        self.note.setText("Saved. Restart the console to start Linux with it: <code>systemctl reboot</code>."
                          if self.name == system.CMDLINES[0] else
                          f"Saved. The loader starts Linux with it once it is copied over "
                          f"<code>{system.CMDLINES[0]}</code>.")


WINDOWS: dict[str, Callable[..., HelperWindow]] = {
    "extras": ExtrasWindow, "mangohud": MangoHudWindow, "mapcount": MapCountWindow, "journal": JournalWindow,
    "cmdline": CmdlineWindow,
}
