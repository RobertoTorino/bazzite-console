# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: every place that holds garbage, with its size and the command that empties it, each row checked to
go; uncheck what you keep, then Delete empties the checked places after a question."""

from __future__ import annotations

from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bazzite_console_core.nexus import header as nexus_header
from bazzite_console_core.theme import GREEN, GREY, RED
from bazzite_console_core.updates import UpdateChecker
from bazzite_console_core.widgets import ActionPill, InfoButton, MetricBox, RefreshButton, StatusText, hint_label, same_width

from . import APP_NAME, CHECKOUT, LOGO_PATH
from .garbage import Garbage, find, remove, size_text

WIKI = "https://robertotorino.github.io/bazzite-console/development/dashboard/#garbage-remover"
ABOUT = ("Nexus Garbage Remover finds the files on this machine that nobody needs again. They are crash dumps, "
         "Steam's crash reports, the Trash and caches that fill up. It shows each place with its size and the command that "
         "empties it. Uncheck what you keep, then <b>Delete</b> empties the checked places after it asks. Crash "
         "dumps belong to the system, so deleting them asks for your password. An hourly check sends a "
         "notification when there is 1 GB or more. "
         f"<a href='{WIKI}'>Wiki</a>")
COLUMNS = ("Delete", "What", "Where", "Size", "Removed with")


def home_text(path: Path) -> str:
    """A path with the home folder written as ~."""
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home):] if text == home or text.startswith(home + "/") else text


class MainWindow(QMainWindow):
    def __init__(self, finder=find, remover=remove):
        """*finder* and *remover*: garbage.find and garbage.remove, or a test's own."""
        super().__init__()
        self.finder, self.remover = finder, remover
        self.found: list[Garbage] = []
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 560)
        self.worker = UpdateChecker(self)               # one job at a time off the window's thread
        self.worker.finished.connect(self._job_done)

        central = QWidget()
        layout = QVBoxLayout(central)
        header = nexus_header(LOGO_PATH, APP_NAME, CHECKOUT)  # the checkout's commit, never a version
        self.state = StatusText()
        header.add_state(self.state)
        header.add_action(InfoButton(ABOUT, "What Nexus Garbage Remover does"))
        self.refresh_button = RefreshButton("Look for garbage again")
        self.refresh_button.clicked.connect(self.refresh)
        header.add_action(self.refresh_button)
        self.total_box = MetricBox("Can be removed", GREY)
        self.checked_box = MetricBox("Checked", GREY)
        self.delete_pill = ActionPill("Delete", "The checked places", "Empty the checked places. It asks first")
        self.delete_pill.clicked.connect(self.on_delete)
        same_width([self.total_box, self.checked_box, self.delete_pill])
        for box in (self.total_box, self.checked_box, self.delete_pill):
            header.add_second(box)
        header.second_row.addStretch(1)                 # the boxes and the pill side by side, not spread
        layout.addLayout(header)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        heading = self.table.horizontalHeader()
        for column, mode in enumerate((QHeaderView.ResizeMode.ResizeToContents,) * 4
                                      + (QHeaderView.ResizeMode.Stretch,)):
            heading.setSectionResizeMode(column, mode)
        self.table.itemChanged.connect(lambda _item: self._show_checked())
        layout.addWidget(self.table, 1)
        layout.addWidget(hint_label("Every row is checked. Uncheck a place to keep it. Hold the pointer over a "
                                    "row to see what it is."))
        self.line = QLabel()
        self.line.setWordWrap(True)
        layout.addWidget(self.line)
        self.setCentralWidget(central)
        self.refresh()

    # --- looking ---------------------------------------------------------------------------------------------
    def refresh(self) -> None:
        if not self.worker.start(lambda: ("found", self.finder())):
            return
        self.state.set_status("Looking", "neutral", "Measuring the places that fill up with garbage.")
        self._busy(True)

    def _job_done(self, result: tuple[str, object]) -> None:
        kind, value = result
        self._busy(False)
        if kind == "found":
            self._show(value)
            return
        self.say("Deleted." if not value else "Not everything went:\n" + "\n".join(value), ok=not value)
        self.refresh()

    def _show(self, found: list[Garbage]) -> None:
        self.found = found
        self.table.blockSignals(True)
        self.table.setRowCount(len(found))
        for row, place in enumerate(found):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(Qt.CheckState.Checked)
            cells = [check, QTableWidgetItem(place.what), QTableWidgetItem(home_text(place.where)),
                     QTableWidgetItem(size_text(place.size)),
                     QTableWidgetItem(place.command_text.replace(str(Path.home()), "~"))]
            cells[3].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tip = f"{place.why}\n{place.files} files." + ("\nIt asks for your password." if place.root else "")
            for column, cell in enumerate(cells):
                cell.setToolTip(tip)
                self.table.setItem(row, column, cell)
        self.table.blockSignals(False)
        total = sum(place.size for place in found)
        self.total_box.set_value(size_text(total) if found else "Nothing")
        self.total_box.set_colour(RED if total >= 1 << 30 else GREEN if not found else GREY)
        if found:
            self.state.set_status(f"{size_text(total)} found", "warn" if total >= 1 << 30 else "info",
                                  f"{len(found)} places hold garbage.")
        else:
            self.state.set_status("Clean", "ok", "No place holds 1 MB of garbage or more.")
        self._show_checked()

    def chosen(self) -> list[Garbage]:
        return [place for row, place in enumerate(self.found)
                if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.CheckState.Checked]

    def _show_checked(self) -> None:
        chosen = self.chosen()
        self.checked_box.set_value(size_text(sum(place.size for place in chosen)) if chosen else "None")
        self.delete_pill.setEnabled(bool(chosen) and not self.worker.running)

    # --- deleting --------------------------------------------------------------------------------------------
    def on_delete(self) -> None:
        chosen = self.chosen()
        if not chosen or self.worker.running:
            return
        lines = [f"{place.what}: {size_text(place.size)} in {home_text(place.where)}" for place in chosen]
        if any(place.root for place in chosen):
            lines.append("You will be asked for your password.")
        answer = QMessageBox.question(self, "Delete", "Delete the checked garbage?\n\n" + "\n".join(lines))
        if answer != QMessageBox.StandardButton.Yes:
            return
        remover = self.remover
        if self.worker.start(lambda: ("removed", remover(chosen))):
            self.state.set_status("Deleting", "neutral", "Emptying the checked places.")
            self._busy(True)

    # --- the window ------------------------------------------------------------------------------------------
    def _busy(self, busy: bool) -> None:
        self.refresh_button.setEnabled(not busy)
        self.delete_pill.setEnabled(not busy and bool(self.chosen()))

    def say(self, text: str, ok: bool = True) -> None:
        self.line.setText(escape(text).replace("\n", "<br>"))
        self.line.setStyleSheet("font-weight:600;" + ("" if ok else f"color:{RED};"))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        self.worker.stop()
        super().closeEvent(event)
