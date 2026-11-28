# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: the suite's text check (tools/text_check.py) on the whole suite or on a file or folder you choose, the
files it found problems in worst first with their counts per check, and the problems of the file you select. Start
and Stop keep the tool's shared LanguageTool server running for many checks, or end it. The tool runs as a process
of its own, so a long check never holds up the window (owner, 28-11-2026: "Text check alone, build it")."""

from __future__ import annotations

import os
import signal
import sys
import tempfile
from html import escape
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bazzite_console_core.nexus import header as nexus_header
from bazzite_console_core.platform import private
from bazzite_console_core.theme import GREEN, GREY, ORANGE, RED
from bazzite_console_core.updates import UpdateChecker
from bazzite_console_core.widgets import (ActionPill, InfoButton, MetricBox, RefreshButton, StatusText, hint_label,
                                          same_width)

from . import APP_ID, APP_NAME, CHECKOUT, LOGO_PATH, TEXT_CHECK
from .results import CHECKS, FileResult, Server, last_lines, probe, read_problems, results, summary

WIKI = "https://robertotorino.github.io/bazzite-console/development/dashboard/#text-check"
ABOUT = ("Nexus Text Check runs the suite's text check, tools/text_check.py, and shows what it finds. The check "
         "reads the wiki, the READMEs and the text in the apps' windows. Three checks read it. The rules come from "
         "the suite's writing guide. LanguageTool checks spelling and grammar. Vale checks style and readability. "
         "<b>Check all</b> checks the whole suite. <b>Check…</b> checks a file or a folder that you choose. "
         "The table lists the files worst first. Select a file to see its problems. "
         "LanguageTool runs in a podman container on this machine. Its first run downloads about 250 MB. "
         "<b>Start</b> keeps one LanguageTool server running for many checks. <b>Stop</b> ends it. "
         f"<a href='{WIKI}'>Wiki</a>")
NOT_DOWNLOADED = "The first check or Start downloads LanguageTool, about 250 MB, once."
FILE_COLUMNS = ("File", "To fix", "Per 1000 words", "Advice", "Rules", "LanguageTool", "Vale")
PROBLEM_COLUMNS = ("Line", "Check", "Kind", "Problem", "Text", "Suggestion")


def _number(value: int | str) -> QTableWidgetItem:
    item = QTableWidgetItem(str(value))
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item


def _table(columns: tuple[str, ...]) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setWordWrap(False)
    return table


class MainWindow(QMainWindow):
    def __init__(self, tool: Path = TEXT_CHECK, prober=probe):
        """*tool*: tools/text_check.py, or a test's fake of it. *prober*: results.probe, or a test's own."""
        super().__init__()
        self.tool, self.prober = tool, prober
        self.process: QProcess | None = None
        self.kind = ""                              # what runs: check, start or stop
        self.output = ""                            # what the running tool printed
        self.json_path: Path | None = None          # the --json file of the running check
        self.server: Server | None = None           # None until the first look
        self.found: list[FileResult] = []
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 720)
        self.worker = UpdateChecker(self)           # the look at the server, off the window's thread
        self.worker.finished.connect(self._looked)

        central = QWidget()
        layout = QVBoxLayout(central)
        header = nexus_header(LOGO_PATH, APP_NAME, CHECKOUT)  # the checkout's commit, never a version
        self.state = StatusText("Looking")
        header.add_state(self.state)
        header.add_action(InfoButton(ABOUT, "What Nexus Text Check does"))
        self.refresh_button = RefreshButton("Look at the LanguageTool server again")
        self.refresh_button.clicked.connect(self.look)
        header.add_action(self.refresh_button)
        self.all_pill = ActionPill("Check all", "The whole suite", "Check every text of the suite")
        self.all_pill.clicked.connect(lambda: self.check([]))
        self.check_pill = ActionPill("Check…", "A file or folder", "Check a file or a folder of this checkout")
        menu = QMenu(self)
        menu.addAction("A file…", self.choose_file)
        menu.addAction("A folder…", self.choose_folder)
        self.check_pill.setMenu(menu)
        self.server_box = MetricBox("LanguageTool server", GREY)
        self.start_pill = ActionPill("Start", "The server", "Keep one LanguageTool server running for many checks")
        self.start_pill.clicked.connect(lambda: self._run("start", ["--server", "start"], "Starting the server"))
        self.stop_pill = ActionPill("Stop", "The server", "Stop the LanguageTool server")
        self.stop_pill.clicked.connect(lambda: self._run("stop", ["--server", "stop"], "Stopping the server"))
        boxes = [self.all_pill, self.check_pill, self.server_box, self.start_pill, self.stop_pill]
        same_width(boxes)
        for box in boxes:
            header.add_second(box)
        header.second_row.addStretch(1)
        layout.addLayout(header)
        layout.addWidget(hint_label("<b>Check all</b> checks the whole suite. <b>Check…</b> checks a file or folder "
                                    "that you choose. Select a file to see its problems."))

        self.files = _table(FILE_COLUMNS)
        heading = self.files.horizontalHeader()
        heading.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(FILE_COLUMNS)):
            heading.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.files.itemSelectionChanged.connect(self._show_problems)
        self.problems = _table(PROBLEM_COLUMNS)
        heading = self.problems.horizontalHeader()
        for column, mode in enumerate((QHeaderView.ResizeMode.ResizeToContents,) * 3
                                      + (QHeaderView.ResizeMode.Stretch,) * 2
                                      + (QHeaderView.ResizeMode.ResizeToContents,)):
            heading.setSectionResizeMode(column, mode)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.files)
        splitter.addWidget(self.problems)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([300, 300])
        layout.addWidget(splitter, 1)
        self.line = QLabel()
        self.line.setWordWrap(True)
        layout.addWidget(self.line)
        self.setCentralWidget(central)
        self._enable()
        self.look()

    # --- the server --------------------------------------------------------------------------------------------
    def look(self) -> None:
        """Looks at podman, LanguageTool's image and the shared server, off the window's thread."""
        tool, prober = self.tool, self.prober
        if self.process is None and self.worker.start(lambda: prober(tool)):
            self._enable()

    def _looked(self, server: Server) -> None:
        self.server = server
        if not server.podman:
            self.server_box.set_value("No podman", "The text check runs LanguageTool in podman.")
            self.server_box.set_colour(RED)
            self.state.set_status("No podman", "bad", "The text check needs podman.")
            self.say("The text check needs podman. Install it, then look again with the round symbol.", ok=False)
        elif server.url:
            self.server_box.set_value("Running", f"LanguageTool runs at {server.url}. Every check uses it.")
            self.server_box.set_colour(GREEN)
        elif not server.image:
            self.server_box.set_value("Not downloaded", NOT_DOWNLOADED)
            self.server_box.set_colour(ORANGE)
            if not self.line.text():
                self.say(NOT_DOWNLOADED)
        else:
            self.server_box.set_value("Off", "Each check starts LanguageTool and stops it afterward. Start keeps "
                                             "one running for many checks.")
            self.server_box.set_colour(GREY)
        if server.podman and self.state.text() in ("Looking", "No podman"):
            self.state.set_status("Ready", "neutral", "Check all or a file or folder.")
        self._enable()

    # --- checking ----------------------------------------------------------------------------------------------
    def choose_file(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, "Check a file", str(CHECKOUT))
        if chosen:
            self.check_path(chosen)

    def choose_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Check a folder", str(CHECKOUT))
        if chosen:
            self.check_path(chosen)

    def check_path(self, chosen: str | Path) -> None:
        """Checks a file or folder of this checkout. The tool takes paths from the repository's root."""
        try:
            relative = Path(chosen).resolve().relative_to(CHECKOUT)
        except ValueError:
            self.say(f"{private(chosen)} is not in this checkout. Choose a file or folder in "
                     f"{private(CHECKOUT)}.", ok=False)
            return
        self.check([] if str(relative) == "." else [str(relative)])

    def check(self, paths: list[str]) -> None:
        if self.process is not None:
            return
        handle, name = tempfile.mkstemp(prefix=f"{APP_ID}-", suffix=".json")
        os.close(handle)
        self.json_path = Path(name)
        self._run("check", [*paths, "--json", name], f"Checking {paths[0]}" if paths else "Checking the whole suite")

    def _checked(self, code: int, output: str) -> None:
        text = ""
        if self.json_path is not None:
            try:
                text = self.json_path.read_text(encoding="utf-8")
            except OSError:
                pass
            self.json_path.unlink(missing_ok=True)
            self.json_path = None
        try:
            problems = read_problems(text) if code == 0 and text.strip() else None
        except (ValueError, TypeError):
            problems = None
        if problems is None:
            self.state.set_status("Failed", "bad", "The text check failed.")
            self.say("The text check failed.\n" + private(last_lines(output)), ok=False)
            return
        self.found = results(output, problems)
        self._fill()
        to_fix = sum(r.to_fix for r in self.found)
        line = summary(output)
        self.state.set_status(f"{to_fix} to fix" if to_fix else "Nothing to fix", "warn" if to_fix else "ok", line)
        self.say(line or "The text check finished.")

    def _fill(self) -> None:
        self.files.setRowCount(len(self.found))
        for row, result in enumerate(self.found):
            per_1000 = f"{result.per_1000:.1f}" if result.per_1000 is not None else "—"
            cells = [QTableWidgetItem(result.path), _number(result.to_fix), _number(per_1000),
                     _number(result.advice), *(_number(result.count(check)) for check in CHECKS)]
            cells[0].setToolTip(f"{result.path}\n{result.words} words." if result.words else result.path)
            for column, cell in enumerate(cells):
                self.files.setItem(row, column, cell)
        self.problems.setRowCount(0)
        if self.found:
            self.files.selectRow(0)

    def _show_problems(self) -> None:
        rows = self.files.selectionModel().selectedRows()
        found = self.found[rows[0].row()].problems if rows and rows[0].row() < len(self.found) else []
        self.problems.setRowCount(len(found))
        for row, problem in enumerate(found):
            cells = [_number(problem.line), QTableWidgetItem(problem.check), QTableWidgetItem(problem.kind),
                     QTableWidgetItem(problem.message), QTableWidgetItem(problem.text),
                     QTableWidgetItem(problem.suggestion)]
            for column, cell in enumerate(cells):
                if column >= 3 and cell.text():
                    cell.setToolTip(cell.text())
                self.problems.setItem(row, column, cell)

    # --- the tool ----------------------------------------------------------------------------------------------
    def _run(self, kind: str, args: list[str], doing: str) -> None:
        """Runs the tool with *args* as a process of its own. Its last line shows under the tables."""
        if self.process is not None:
            return
        self.kind, self.output = kind, ""
        process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(CHECKOUT))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._done)
        process.errorOccurred.connect(self._failed_to_start)
        self.process = process
        tip = NOT_DOWNLOADED if self.server is not None and not self.server.image and kind != "stop" else ""
        self.state.set_status(doing, "neutral", tip)
        self.say(doing + ".")
        self._enable()
        process.start(sys.executable, [str(self.tool), *args])

    def _read(self) -> None:
        if self.process is None:
            return
        self.output += bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        last = last_lines(self.output, 1)
        if last:
            self.say(private(last))

    def _failed_to_start(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart and self.process is not None:
            self.output += f"\n{private(sys.executable)} did not start."
            self._done(-1, None)

    def _done(self, code: int, _status) -> None:
        self._read()
        process, self.process = self.process, None
        if process is not None:
            process.deleteLater()
        if self.kind == "check":
            self._checked(code, self.output)
        elif code:
            what = "did not start" if self.kind == "start" else "did not stop"
            self.state.set_status("Failed", "bad", f"The LanguageTool server {what}.")
            self.say(f"The LanguageTool server {what}.\n" + private(last_lines(self.output)), ok=False)
        else:
            started = self.kind == "start"
            self.state.set_status("Ready", "neutral", "Check all or a file or folder.")
            self.say("The LanguageTool server runs. Every check uses it until you stop it." if started
                     else "The LanguageTool server is off.")
        self._enable()
        self.look()

    # --- the window --------------------------------------------------------------------------------------------
    def _enable(self) -> None:
        busy = self.process is not None
        looking = self.worker.running
        podman = self.server is not None and self.server.podman
        running = podman and self.server.url is not None
        self.refresh_button.setEnabled(not busy and not looking)
        self.all_pill.setEnabled(not busy and podman)
        self.check_pill.setEnabled(not busy and podman)
        # what runs cannot be started again, and what is off cannot be stopped
        self.start_pill.setEnabled(not busy and not looking and podman and not running)
        self.stop_pill.setEnabled(not busy and not looking and running)

    def say(self, text: str, ok: bool = True) -> None:
        self.line.setText(escape(text).replace("\n", "<br>"))
        self.line.setStyleSheet("font-weight:600;" + ("" if ok else f"color:{RED};"))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        process, self.process = self.process, None
        if process is not None:
            process.finished.disconnect(self._done)
            if process.processId():
                # as Ctrl+C: the tool stops the LanguageTool it started for this check on its way out
                os.kill(process.processId(), signal.SIGINT)
            if not process.waitForFinished(5000):
                process.kill()
                process.waitForFinished(2000)
        if self.json_path is not None:
            self.json_path.unlink(missing_ok=True)
        self.worker.stop()
        super().closeEvent(event)
