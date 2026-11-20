# SPDX-License-Identifier: GPL-3.0-or-later
"""The version manager of an emulator manager (owner, 20-11-2026: as shadPS4's own launcher has one): on the left
the builds installed (core's builds), the one in use ticked, with Use, Delete and Add custom; on the right the builds
that can be downloaded, with Refresh list and Download. The build the manager was tried with is marked Tested in
both lists; every other build is not tried on the board, and the window says so before it downloads one.

Asking GitHub and downloading run off the window's thread (core's UpdateChecker); what is downloaded is checked
against its SHA-256 before it is installed (builds.install). The manager passes what differs per emulator: the list
from GitHub (*available*) and how a build is installed (*install*, which may unpack a zip or take a catalog out)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QMenu, QMessageBox, QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import builds, window_title
from .builds import Build
from .platform import private
from .updates import UpdateChecker
from .widgets import ActionPill, WrappedLabel

USE, VERSION, NAME, DATE, KIND = range(5)               # the installed list's columns
R_VERSION, R_NAME, R_DATE, R_KIND = range(4)            # the download list's columns
PillFactory = Callable[[str, str, str], QWidget]        # value, caption, tooltip: the app's action pill


def _pill(value: str, caption: str, tooltip: str) -> QWidget:
    return ActionPill(value, caption, tooltip)


def _table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    head = table.horizontalHeader()
    for column in range(len(headers)):
        head.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
    head.setStretchLastSection(True)
    return table


class BuildsDialog(QDialog):
    """*emulator*: its name ("Vita3K"); *home* and *member*: where the builds are and the file in each; *tested*:
    the build the manager was tried with; *available*: the builds that can be downloaded, newest first (raises
    builds.BuildError; runs off the window's thread); *install*: installs one, not in use (runs off the window's
    thread; raises an exception with what went wrong); *pill*: the app's action pill; *running*: whether the
    emulator runs. changed is emitted after a build was installed, deleted or put in use."""

    changed = pyqtSignal()

    def __init__(self, emulator: str, home: Path, member: str, tested: Build,
                 available: Callable[[], list[Build]], install: Callable[[Build], None],
                 parent: QWidget | None = None, pill: PillFactory = _pill,
                 running: Callable[[], bool] = lambda: False, pick_file=None):
        super().__init__(parent)
        self.setWindowTitle(window_title(f"{emulator} versions"))
        self.setMinimumSize(900, 520)
        self.emulator, self.home, self.member, self.tested = emulator, home, member, tested
        self.available, self.install, self.running = available, install, running
        self.pick_file = pick_file or self._pick_file
        self.builds: list[Build] = []                   # installed
        self.remote: list[Build] = []                   # to download; the tested build until the list is asked
        self.worker = UpdateChecker(self)
        self.worker.finished.connect(self._done)
        self._after = None                              # what to do with the worker's result

        self.installed_table = _table(["In use", "Version", "Name", "Date", "Kind"])
        self.installed_table.itemSelectionChanged.connect(self._update_buttons)
        self.installed_table.itemDoubleClicked.connect(lambda _item: self.on_use())
        self.use_pill = pill("Use", "Put in use", f"Put the chosen build in use: {emulator} and the games in Steam "
                                                  "start it from then on")
        self.use_pill.clicked.connect(self.on_use)
        self.delete_pill = pill("Delete", "Remove build", "Delete the chosen build; the one in use stays")
        self.delete_pill.clicked.connect(self.on_delete)
        self.custom_pill = pill("Add", "Custom build", f"Add an {emulator} AppImage of your own as a build; it is "
                                                       "not checked")
        self.custom_pill.clicked.connect(self.on_custom)
        self.remote_table = _table(["Version", "Name", "Date", "Kind"])
        self.remote_table.itemSelectionChanged.connect(self._update_buttons)
        self.remote_table.itemDoubleClicked.connect(lambda _item: self.on_download())
        self.refresh_pill = pill("Refresh", "List from GitHub", f"Ask GitHub which {emulator} builds there are")
        self.refresh_pill.clicked.connect(self.on_refresh)
        self.download_pill = pill("Download", "Chosen build", "Download the chosen build, check it against its "
                                                              "SHA-256 and install it beside the others")
        self.download_pill.clicked.connect(self.on_download)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        for column, (title, table, pills) in enumerate(
                (("Installed", self.installed_table, [self.use_pill, self.delete_pill, self.custom_pill]),
                 ("Download", self.remote_table, [self.refresh_pill, self.download_pill]))):
            label = QLabel(title)
            label.setStyleSheet("font-weight:700;")
            grid.addWidget(label, 0, column)
            grid.addWidget(table, 1, column)
            row = QHBoxLayout()
            row.setSpacing(8)
            for each in pills:
                row.addWidget(each, 1)
            grid.addLayout(row, 2, column)
        grid.setRowStretch(1, 1)
        self.where = QLabel(f"Builds are kept in {private(home)}")
        self.where.setStyleSheet("color:palette(placeholder-text);")
        self.where.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status = WrappedLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet("font-weight:600;")
        lay = QVBoxLayout(self)
        lay.addWidget(self.where)
        lay.addLayout(grid, 1)
        lay.addWidget(self.status)
        for each in (self.use_pill, self.delete_pill, self.custom_pill, self.refresh_pill, self.download_pill):
            each.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            each.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)     # as the windows' pills
        self.remote = [tested]
        self.load()
        self._fill_remote()

    # --- Lists --------------------------------------------------------------------------------------------------

    def kind(self, build: Build) -> str:
        return builds.TESTED if build.version == self.tested.version else build.kind

    def load(self) -> None:
        """The builds installed, read again."""
        self.builds = builds.installed(self.home, self.member)
        in_use = builds.current(self.home, self.member)
        table = self.installed_table
        table.setRowCount(len(self.builds))
        for row, build in enumerate(self.builds):
            mark = QTableWidgetItem("✓" if build.folder == in_use else "")
            mark.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, USE, mark)
            for column, text in ((VERSION, build.version), (NAME, build.name), (DATE, build.published),
                                 (KIND, self.kind(build))):
                item = QTableWidgetItem(text)
                if build.page:
                    item.setToolTip(build.page)
                table.setItem(row, column, item)
        self._update_buttons()

    def _fill_remote(self) -> None:
        installed_ = {b.version for b in self.builds}
        table = self.remote_table
        table.setRowCount(len(self.remote))
        for row, build in enumerate(self.remote):
            size = f", about {round(build.size / (1 << 20))} MB" if build.size else ""
            for column, text in ((R_VERSION, build.version), (R_NAME, build.name), (R_DATE, build.published),
                                 (R_KIND, self.kind(build) + (", installed" if build.version in installed_ else ""))):
                item = QTableWidgetItem(text)
                item.setToolTip(f"{build.asset}{size}" + (f"\n{build.page}" if build.page else ""))
                table.setItem(row, column, item)
        self._update_buttons()

    def chosen(self) -> Build | None:
        rows = self.installed_table.selectionModel().selectedRows()
        return self.builds[rows[0].row()] if rows and rows[0].row() < len(self.builds) else None

    def chosen_remote(self) -> Build | None:
        rows = self.remote_table.selectionModel().selectedRows()
        return self.remote[rows[0].row()] if rows and rows[0].row() < len(self.remote) else None

    def _update_buttons(self) -> None:
        idle = not self.worker.running
        chosen = self.chosen()
        in_use = builds.current(self.home, self.member)
        self.use_pill.setEnabled(idle and chosen is not None and chosen.folder != in_use)
        self.delete_pill.setEnabled(idle and chosen is not None and chosen.folder != in_use)
        self.custom_pill.setEnabled(idle)
        self.refresh_pill.setEnabled(idle)
        remote = self.chosen_remote()
        self.download_pill.setEnabled(idle and remote is not None and remote.version not in
                                      {b.version for b in self.builds})

    def say(self, text: str, ok: bool = True) -> None:
        self.status.setStyleSheet("font-weight:600;" + ("" if ok else "color:#c62828;"))
        self.status.setText(text)

    # --- Actions ------------------------------------------------------------------------------------------------

    def _start(self, text: str, job, after) -> None:
        if self.worker.start(job):
            self._after = after
            self.say(text)
            self._update_buttons()

    def _done(self, result) -> None:
        after, self._after = self._after, None
        if after is not None:
            after(result)
        self._update_buttons()

    def on_use(self) -> None:
        build = self.chosen()
        if build is None or not self.use_pill.isEnabled():
            return
        try:
            builds.use(self.home, build.folder, self.member)
        except (builds.BuildError, OSError) as error:
            self.say(f"Build {build.version} was not put in use: {error}", ok=False)
            return
        self.load()
        self._fill_remote()
        note = "" if self.kind(build) == builds.TESTED else " It was not tried on the board."
        if self.running():
            note += f" {self.emulator} runs: the build in use starts the next time."
        self.say(f"{self.emulator} {build.version} is in use.{note}")
        self.changed.emit()

    def on_delete(self) -> None:
        build = self.chosen()
        if build is None or not self.delete_pill.isEnabled():
            return
        answer = QMessageBox.question(self, window_title("Delete build"),
                                      f"Delete {self.emulator} {build.version}?\n\n{self.emulator}'s own folders "
                                      "(saves, settings) stay.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            builds.delete(self.home, build.folder, self.member)
        except (builds.BuildError, OSError) as error:
            self.say(f"Build {build.version} was not deleted: {error}", ok=False)
            return
        self.load()
        self._fill_remote()
        self.say(f"{self.emulator} {build.version} was deleted.")
        self.changed.emit()

    def _pick_file(self) -> str:
        path, _ = QFileDialog.getOpenFileName(self, window_title(f"Add a custom {self.emulator} build"),
                                              str(Path.home()), "AppImage (*.AppImage *.appimage);;All files (*)")
        return path

    def on_custom(self) -> None:
        path = self.pick_file()
        if not path:
            return
        try:
            build = builds.add_custom(self.home, Path(path), self.member)
        except (builds.BuildError, OSError) as error:
            self.say(f"The file was not added: {error}", ok=False)
            return
        self.load()
        self._select(build.version)
        self.say(f"{build.version} was added; Use puts it in use. It is your own file and was not checked.")
        self.changed.emit()

    def on_refresh(self) -> None:
        available = self.available

        def job():
            try:
                return True, available()
            except builds.BuildError as error:
                return False, str(error)
        self._start(f"Asking GitHub for the {self.emulator} builds…", job, self._listed)

    def _listed(self, result) -> None:
        ok, value = result
        if not ok:
            self.say(f"The list could not be read: {value}", ok=False)
            return
        self.remote = builds.merged(value, [self.tested])        # GitHub's own name and date first
        self._fill_remote()
        self.say(f"{len(self.remote)} {self.emulator} builds can be downloaded.")

    def on_download(self) -> None:
        build = self.chosen_remote()
        if build is None or not self.download_pill.isEnabled():
            return
        size = f" (about {round(build.size / (1 << 20))} MB)" if build.size else ""
        text = f"Download {self.emulator} {build.version}{size} from GitHub?\n\nIt is checked against its SHA-256 " \
               f"before it is installed beside the other builds."
        if self.kind(build) != builds.TESTED:
            text += (f"\n\nThis build was not tried on the board: this version of the app was tried with "
                     f"{self.tested.version}, which stays one click away.")
        if QMessageBox.question(self, window_title("Download"), text) != QMessageBox.StandardButton.Yes:
            return
        install = self.install

        def job():
            try:
                install(build)
                return True, ""
            except Exception as error:  # noqa: BLE001 (the install's error, said in the window)
                return False, str(error)
        self._start(f"Downloading {self.emulator} {build.version}…", job, lambda result: self._installed(build, result))

    def _installed(self, build: Build, result) -> None:
        ok, error = result
        self.load()
        self._fill_remote()
        if not ok:
            self.say(f"{self.emulator} {build.version} was not installed: {private(error)}", ok=False)
            return
        self._select(build.version)
        self.say(f"{self.emulator} {build.version} is installed; Use puts it in use.")
        self.changed.emit()

    def _select(self, version: str) -> None:
        for row, build in enumerate(self.builds):
            if build.version == version:
                self.installed_table.selectRow(row)
                return

    def done(self, result: int) -> None:  # noqa: D401 (Qt override)
        """Closing waits for a download that runs (it would be cut off half way)."""
        if self.worker.running:
            self.say("Wait until the download is finished.", ok=False)
            return
        super().done(result)


def fill_menu(menu: QMenu, home: Path, member: str, tested: str, use: Callable[[str], None],
              manage: Callable[[], None]) -> None:
    """The menu of a manager's version pill (as the version list in shadPS4's toolbar): every build installed, the
    one in use ticked, a click on another puts it in use (*use*(folder)); then Manage versions… (*manage*)."""
    menu.clear()
    in_use = builds.current(home, member)
    for build in builds.installed(home, member):
        label = build.version + (" (tested)" if build.version == tested else "")
        action = menu.addAction(label)
        action.setCheckable(True)
        action.setChecked(build.folder == in_use)
        action.triggered.connect(lambda _on=False, folder=build.folder: use(folder))
    if not menu.isEmpty():
        menu.addSeparator()
    menu.addAction("Manage versions…", manage)
