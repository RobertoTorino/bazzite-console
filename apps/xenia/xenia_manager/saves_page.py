# SPDX-License-Identifier: GPL-3.0-or-later
"""The Memory cards tab (owner, 18-11-2026: as PCSX2 Manager has one): the saved games Xenia keeps, each under its
game's title, and export, import and delete (saves.py). The console keeps each saved game as a folder, so there is
no card to choose or to format. Nothing is taken in or deleted while Xenia runs."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from bazzite_console_core import window_title
from bazzite_console_core.platform import private
from bazzite_console_core.widgets import hint_label

from . import saves, style
from .saves import Save, SaveError

RUNNING = "Xenia is running: close it before changing a save, it would write its own copy over the change."
GAME, SAVE, FOLDER, SIZE, SAVED = range(5)


class SavesPage(QWidget):
    """*home*: Xenia's own folder; *titles*: the games found, code to title, for the Game column; *running*: whether
    Xenia runs; *log*: the app's log, for what the page does."""

    def __init__(self, home: Path, titles: Callable[[], dict[str, str]], running: Callable[[], bool],
                 log: logging.Logger | None = None, parent=None):
        super().__init__(parent)
        self.home = home
        self.titles = titles
        self.running = running
        self.log = log or logging.getLogger(__name__)
        self.saves: list[Save] = []

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Game", "Save", "Folder", "Size", "Saved"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        head = self.table.horizontalHeader()
        for column, mode in enumerate((QHeaderView.ResizeMode.Stretch, QHeaderView.ResizeMode.Stretch,
                                       QHeaderView.ResizeMode.ResizeToContents,
                                       QHeaderView.ResizeMode.ResizeToContents,
                                       QHeaderView.ResizeMode.ResizeToContents)):
            head.setSectionResizeMode(column, mode)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        self.import_button = style.primary_button("Import…", "Put the saved games from a .zip in Xenia's content "
                                                             "folder")
        self.import_button.clicked.connect(self.on_import)
        self.export_button = QPushButton("Export…")
        self.export_button.setToolTip("Save the selected saves as one .zip, to keep or to share")
        self.export_button.clicked.connect(self.on_export)
        self.delete_button = QPushButton("Delete…")
        self.delete_button.setToolTip("Delete the selected saved games from Xenia's content folder, after it asks")
        self.delete_button.clicked.connect(self.on_delete)
        self.space = QLabel()
        buttons = QHBoxLayout()
        for button in (self.import_button, self.export_button, self.delete_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.space)

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status.hide()                              # takes its line once it has something to say

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        self.hint = hint_label("")
        lay.addWidget(self.hint)
        lay.addWidget(self.table, 1)
        lay.addLayout(buttons)
        lay.addWidget(self.status)
        self.load()

    # --- State ------------------------------------------------------------------------------------------------

    def load(self) -> None:
        """Reads the disk again; the saves that were selected stay selected."""
        keep = {save.name for save in self.chosen()}
        self.saves = saves.find_saves(self.home)
        titles = self.titles()
        place = saves.save_folder(self.home)
        self.hint.setText("An XBOX 360 game keeps each saved game as a folder in Xenia's content folder, under a "
                          f"profile: {escape(private(place or saves.content_folder(self.home)))}. Nothing is changed "
                          "while Xenia runs." + ("" if place else " Xenia has no profile yet: start it once to make "
                                                                  "one."))
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.saves))
        for row, save in enumerate(self.saves):
            texts = (titles.get(save.title_id, save.title_id), save.title, save.name,
                     saves.size_text(save.size),
                     time.strftime("%d-%m-%Y %H:%M", time.localtime(save.saved)))
            for column, text in enumerate(texts):
                item = QTableWidgetItem(text)
                if column == SIZE:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
        self.table.clearSelection()
        mode = self.table.selectionMode()
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for row, save in enumerate(self.saves):
            if save.name in keep:
                self.table.selectRow(row)
        self.table.setSelectionMode(mode)
        self.table.blockSignals(False)
        total = sum(save.size for save in self.saves)
        self.space.setText(f"{len(self.saves)} save(s), {saves.size_text(total)}" if self.saves else "No saves yet")
        self._selection_changed()

    def chosen(self) -> list[Save]:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        return [self.saves[row] for row in rows if row < len(self.saves)]

    def _selection_changed(self) -> None:
        chosen = self.chosen()
        self.export_button.setEnabled(bool(chosen))
        self.delete_button.setEnabled(bool(chosen))

    # --- Actions ----------------------------------------------------------------------------------------------

    def _say(self, text: str, ok: bool = True) -> None:
        text = private(text)                            # a path in it: the user's folders as ~
        self.status.setStyleSheet("" if ok else "font-weight:600;color:#c62828;")
        self.status.setText(text)
        self.status.show()
        (self.log.info if ok else self.log.error)("Memory cards: %s", text)

    def _do(self, job: Callable[[], str]) -> None:
        try:
            message, ok = job(), True
        except SaveError as error:
            message, ok = str(error), False
        self.load()
        self._say(message, ok)

    def _refuse_while_running(self) -> bool:
        if self.running():
            self._say(RUNNING, ok=False)
            return True
        return False

    def _ask(self, title: str, text: str) -> bool:
        return QMessageBox.question(self, window_title(title), text) == QMessageBox.StandardButton.Yes

    def on_import(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, window_title("Import saves"), str(Path.home()),
                                              "XBOX 360 saves in a .zip (*.zip)")
        if file:
            self.import_file(Path(file))

    def import_file(self, file: Path) -> None:
        """The saves of a .zip onto the disk; a save that is there already is replaced after it asks."""
        if self._refuse_while_running():
            return
        try:
            names = saves.zip_saves(file)
        except SaveError as error:
            self._say(str(error), ok=False)
            return
        place = saves.save_folder(self.home)
        there = [name for name in names if (place is not None and place.joinpath(*name.split('/')).exists())]
        if there and not self._ask("Import saves", f"{len(there)} save(s) in {file.name} are on the disk "
                                                   "already:\n\n" + "\n".join(f"  {name}" for name in there[:10])
                                                   + ("\n  …" if len(there) > 10 else "")
                                                   + "\n\nReplace them with the ones in the file?"):
            self._say("Nothing was imported.")
            return
        self._do(lambda: saves.import_saves(self.home, file))

    def on_export(self) -> None:
        chosen = self.chosen()
        if not chosen:
            return
        name = chosen[0].label.replace(" · ", "-") if len(chosen) == 1 else "xbox360-saves"
        file, _ = QFileDialog.getSaveFileName(self, window_title("Export saves"), str(Path.home() / f"{name}.zip"),
                                              "Zip file (*.zip)")
        if file:
            self.export_to(chosen, Path(file))

    def export_to(self, chosen: list[Save], target: Path) -> None:
        if target.suffix.lower() != ".zip":
            target = target.with_name(target.name + ".zip")
        self._do(lambda: saves.export_saves(chosen, target))

    def on_delete(self) -> None:
        chosen = self.chosen()
        if not chosen:
            return
        listed = "\n".join(f"  {s.label}" for s in chosen[:10]) + ("\n  …" if len(chosen) > 10 else "")
        if self._ask("Delete saves", f"Delete {len(chosen)} save(s) from Xenia's content folder?\n\n{listed}\n\n"
                                     "A deleted save is gone: export it first to keep a copy."):
            self.delete(chosen)

    def delete(self, chosen: list[Save]) -> None:
        if self._refuse_while_running():
            return
        self._do(lambda: saves.delete_saves(chosen))
