# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: whether the recorder runs, since when and how much it holds; Start or Stop, At boot and Open as pills;
and a table with each value now, its lowest and its highest in the minutes around a time you type."""

from __future__ import annotations

import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QCloseEvent, QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
from . import reader, service
from .recorder import KEEP_DAYS, OUT

WIKI = "https://robertotorino.github.io/bazzite-console/development/dashboard/#flight-recorder"
ABOUT = ("Nexus Flight Recorder writes down what the board does, one line per second. Each line holds the load, the "
         "temperatures, the GPU clock, the fan, the memory and the busiest program. A system "
         "service does the recording, so it also runs before you log in. A line is on the disk within 2 seconds, so a "
         f"freeze keeps the last moments. The newest {KEEP_DAYS} days are kept.<br><br>"
         "After a crash, type its time in the window. The table then shows the minutes around it. "
         f"<a href='{WIKI}'>Wiki</a>")
COLUMNS = ("What", "Now", "Lowest", "Highest")
REFRESH_MS = 5000


def day_text(day: str) -> str:
    """2026-11-27 as 27-11-2026."""
    year, month, date = day.split("-")
    return f"{date}-{month}-{year}"


class MainWindow(QMainWindow):
    def __init__(self, out: Path = OUT, state=service.state, run=service.run):
        """*out*: the folder with the recordings; *state* and *run*: service.state and service.run, or a test's."""
        super().__init__()
        self.out, self.read_state, self.run_action = out, state, run
        self.now = service.State()
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 720)
        self.worker = UpdateChecker(self)               # one root action at a time off the window's thread
        self.worker.finished.connect(self._action_done)

        central = QWidget()
        layout = QVBoxLayout(central)
        header = nexus_header(LOGO_PATH, APP_NAME, CHECKOUT)  # the checkout's commit, never a version
        self.state = StatusText()
        header.add_state(self.state)
        header.add_action(InfoButton(ABOUT, "What Nexus Flight Recorder does"))
        self.refresh_button = RefreshButton("Read the recording again")
        self.refresh_button.clicked.connect(self.refresh)
        header.add_action(self.refresh_button)
        self.since_box = MetricBox("Recording since", GREY)
        self.today_box = MetricBox("Today's file", GREY)
        self.days_box = MetricBox("Days kept", GREY)
        self.run_pill = ActionPill("Start", "The recording", "")
        self.run_pill.clicked.connect(self.on_run)
        self.boot_pill = ActionPill("At boot", "Off", "")
        self.boot_pill.clicked.connect(self.on_boot)
        self.open_pill = ActionPill("Open", "The files", "Opens the folder with the recordings")
        self.open_pill.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.out))))
        boxes = [self.since_box, self.today_box, self.days_box, self.run_pill, self.boot_pill, self.open_pill]
        same_width(boxes)
        for box in boxes:
            header.add_second(box)
        header.second_row.addStretch(1)                 # the boxes and the pills side by side, not spread
        layout.addLayout(header)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("<b>Show the minutes around</b>"))
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("now")
        self.time_edit.setFixedWidth(90)
        self.time_edit.setToolTip("A time such as 00:46. Empty shows the last 10 minutes.")
        self.time_edit.editingFinished.connect(self.show_window)
        bar.addWidget(self.time_edit)
        bar.addWidget(QLabel("of"))
        self.day_box = QComboBox()
        self.day_box.currentIndexChanged.connect(lambda _index: self.show_window())
        bar.addWidget(self.day_box)
        bar.addStretch(1)
        layout.addLayout(bar)

        self.table = QTableWidget(len(reader.VALUES), len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.busiest = QLabel()
        self.busiest.setWordWrap(True)
        layout.addWidget(self.busiest)
        layout.addWidget(hint_label(f"The table covers {reader.MINUTES} minutes before and after the time. Type a "
                                    "time, such as 00:46, to see the minutes around a crash."))
        self.line = QLabel()
        self.line.setWordWrap(True)
        layout.addWidget(self.line)
        self.setCentralWidget(central)

        self.timer = QTimer(self)                       # the last minutes move on while the window is open
        self.timer.setInterval(REFRESH_MS)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.refresh()

    # --- reading ---------------------------------------------------------------------------------------------
    def refresh(self) -> None:
        self.now = self.read_state()
        days = reader.days(self.out)
        chosen = self.day_box.currentData()
        self.day_box.blockSignals(True)
        self.day_box.clear()
        for day in days:
            self.day_box.addItem(day_text(day), day)
        if chosen in days:
            self.day_box.setCurrentIndex(days.index(chosen))
        self.day_box.blockSignals(False)
        self._show_state(days)
        self.show_window()

    def _tick(self) -> None:
        if not self.worker.running and not self.time_edit.text().strip() and self.day_box.currentIndex() <= 0:
            self.refresh()

    def _show_state(self, days: list[str]) -> None:
        now = self.now
        if not now.installed:
            self.state.set_status("Not installed", "neutral", "The recorder is not on this board yet.")
        elif now.running:
            self.state.set_status("Recording", "ok", "One line per second.")
        else:
            self.state.set_status("Stopped", "warn", "Nothing is recorded now.")
        self.since_box.set_value(now.since or "—")
        self.since_box.set_colour(GREEN if now.running else GREY)
        today = self.out / f"{datetime.date.today():%Y-%m-%d}.csv"
        self.today_box.set_value(reader.size_text(today.stat().st_size) if today.is_file() else "None")
        self.days_box.set_value(f"{len(days)} of {KEEP_DAYS}")
        if not now.installed:
            self.run_pill.set_value("Install", "Installs the recorder as a system service and starts it. It asks "
                                               "for your password")
        elif now.running:
            self.run_pill.set_value("Stop", "Stops the recording. It asks for your password")
        else:
            self.run_pill.set_value("Start", "Starts the recording. It asks for your password")
        self.boot_pill.caption.setText("On" if now.at_boot else "Off")
        self.boot_pill.setToolTip("The recorder starts with the board. Click to turn that off."
                                  if now.at_boot else "The recorder does not start with the board. Click to turn "
                                                      "that on.")
        self.boot_pill.setEnabled(now.installed and not self.worker.running)
        self.run_pill.setEnabled(not self.worker.running)
        if now.installed and not now.current:
            self.say("The installed recorder differs from this checkout's. Stop it, then Start installs this one.", ok=False)

    def show_window(self) -> None:
        day = self.day_box.currentData()
        text = self.time_edit.text().strip()
        at = reader.parse_time(text) if text else None
        if text and at is None:
            self.say("Type the time as hours and minutes, such as 00:46.", ok=False)
            return
        window = reader.around(day, at, self.out) if day else reader.around("", None, self.out)
        for r, stat in enumerate(window.stats):
            for c, value in enumerate((stat.name, stat.text(stat.last), stat.text(stat.low), stat.text(stat.high))):
                item = QTableWidgetItem(value)
                if c:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.setHorizontalHeaderLabels(("What", "Now" if at is None else "Last", "Lowest", "Highest"))
        if not window.lines:
            self.busiest.setText("No lines were recorded in these minutes.")
        else:
            top = ", ".join(f"{name} ({seconds} s)" for name, seconds in window.busiest[:5])
            boots = "" if window.boots <= 1 else f" The board restarted {window.boots - 1} time(s) in them."
            self.busiest.setText(f"<b>{window.start} to {window.end}, busiest programs:</b> {top}.{boots}")
        if text or not (self.now.installed and not self.now.current):
            self.say("")

    # --- the service -----------------------------------------------------------------------------------------
    def _start(self, action: str, doing: str) -> None:
        run = self.run_action
        if self.worker.start(lambda: (action, run(action))):
            self.state.set_status(doing, "neutral", "Waiting for the system.")
            self.run_pill.setEnabled(False)
            self.boot_pill.setEnabled(False)

    def on_run(self) -> None:
        if self.worker.running:
            return
        if not self.now.installed:
            answer = QMessageBox.question(
                self, APP_NAME,
                "Install the flight recorder?\n\n"
                "It becomes a system service that starts with the board.\n"
                f"It writes one line per second to {self.out}.\n"
                f"The newest {KEEP_DAYS} days are kept, about 13 MB a day.\n"
                "You'll be asked for your password.")
            if answer == QMessageBox.StandardButton.Yes:
                self._start("install", "Installing")
        elif self.now.running:
            self._start("stop", "Stopping")
        else:
            self._start("install" if not self.now.current else "start", "Starting")

    def on_boot(self) -> None:
        if not self.worker.running and self.now.installed:
            self._start("boot-off" if self.now.at_boot else "boot-on", "Changing")

    def _action_done(self, result: tuple[str, str]) -> None:
        _action, problem = result
        self.refresh()
        if problem:
            self.say(problem, ok=problem == "Canceled.")

    # --- the window ------------------------------------------------------------------------------------------
    def say(self, text: str, ok: bool = True) -> None:
        self.line.setText(text)
        self.line.setStyleSheet("font-weight:600;" + ("" if ok else f"color:{RED};"))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        self.timer.stop()
        self.worker.stop()
        super().closeEvent(event)
