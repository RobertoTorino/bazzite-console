# SPDX-License-Identifier: GPL-3.0-or-later
"""The Memory cards tab (owner, 18-11-2026: as PS5 PCSX2 Manager has one): the saves shadPS4 keeps, each under its
game's title, the selected save's picture and what the game says of it, and export, import and delete (saves.py).
A PS4 keeps each save as a folder, so there is no card to choose or to format. Nothing is taken in or deleted while
shadPS4 runs."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from bazzite_console_core import window_title
from bazzite_console_core.platform import private
from bazzite_console_core.theme import surface_style
from bazzite_console_core.widgets import hint_label

from . import saves, style
from .saves import Save, SaveError

PICTURE = 96                            # the save's picture at this width at most (icon0.png is 228 by 128)
RUNNING = "shadPS4 is running: close it before changing a save, it would write its own copy over the change."
GAME, SAVE, FOLDER, SIZE, SAVED = range(5)


class SavesPage(QWidget):
    """*home*: shadPS4's own folder; *titles*: the games found, code to title, for the Game column; *running*:
    whether shadPS4 runs; *log*: the app's log, for what the page does."""

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

        # The selected save beside the table: its picture and a few lines about it, as PS5 PCSX2 Manager's tab.
        self.picture = QLabel()
        self.picture.setFixedSize(PICTURE, PICTURE)
        self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setFixedWidth(PICTURE)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.side = QFrame()
        self.side.setObjectName("side")
        self.side.setStyleSheet(surface_style(style.BLUE, "QFrame#side")
                                + "#side QLabel { background:transparent; border:none; }")
        side = QVBoxLayout(self.side)
        side.setContentsMargins(9, 12, 12, 12)
        side.setSpacing(10)
        side.addWidget(self.picture, 0, Qt.AlignmentFlag.AlignHCenter)
        side.addWidget(self.details, 1)
        self.side.setFixedWidth(PICTURE + 9 + 12 + 5)           # the margins and the border
        middle = QHBoxLayout()
        middle.setSpacing(10)
        middle.addWidget(self.table, 1)
        middle.addWidget(self.side, 0, Qt.AlignmentFlag.AlignTop)

        self.import_button = style.primary_button("Import…", "Put the saves from a .zip in shadPS4's save folder")
        self.import_button.clicked.connect(self.on_import)
        self.export_button = QPushButton("Export…")
        self.export_button.setToolTip("Save the selected saves as one .zip, to keep or to share")
        self.export_button.clicked.connect(self.on_export)
        self.delete_button = QPushButton("Delete…")
        self.delete_button.setToolTip("Delete the selected saves from shadPS4's save folder, after it asks")
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
        lay.addLayout(middle, 1)
        lay.addLayout(buttons)
        lay.addWidget(self.status)
        self.load()

    # --- State ------------------------------------------------------------------------------------------------

    def load(self) -> None:
        """Reads the disk again; the saves that were selected stay selected."""
        keep = {save.name for save in self.chosen()}
        self.saves = saves.find_saves(self.home)
        titles = self.titles()
        self.hint.setText("A PS4 game keeps each save as a folder in shadPS4's own folder: "
                          f"{escape(private(saves.save_folder(self.home)))}. Nothing is changed while shadPS4 runs.")
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.saves))
        for row, save in enumerate(self.saves):
            texts = (titles.get(save.title_id, save.title_id), save.label, save.name,
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
        self.side.setVisible(bool(chosen))
        if not chosen:
            return
        save = chosen[0]
        pixmap = QPixmap()
        data = saves.icon(save)
        if data and pixmap.loadFromData(data):
            self.picture.setPixmap(pixmap.scaled(PICTURE, PICTURE, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))
        else:
            self.picture.setPixmap(QPixmap())
            self.picture.setText("No picture")
        lines = [f"<b>{escape(save.label)}</b>"]
        if save.detail:
            lines.append(escape(save.detail))
        if len(chosen) > 1:
            lines.append(f"and {len(chosen) - 1} more")
        self.details.setText("<br>".join(lines))

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
                                              "PS4 saves in a .zip (*.zip)")
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
        there = [name for name in names if saves.save_folder(self.home).joinpath(*name.split('/')).exists()]
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
        name = chosen[0].name.replace("/", "-") if len(chosen) == 1 else "ps4-saves"
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
        if self._ask("Delete saves", f"Delete {len(chosen)} save(s) from shadPS4's save folder?\n\n{listed}\n\n"
                                     "A deleted save is gone: export it first to keep a copy."):
            self.delete(chosen)

    def delete(self, chosen: list[Save]) -> None:
        if self._refuse_while_running():
            return
        self._do(lambda: saves.delete_saves(chosen))
