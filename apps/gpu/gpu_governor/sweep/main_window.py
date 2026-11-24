# SPDX-License-Identifier: GPL-3.0-or-later

"""The GPU sweep window of GPU Manager (owner, 24-11-2026: PS5 GPU OC Bisect merged into GPU Manager, its sweep in a
step window as Core Unlock and CU Unlock have). It runs ps5-gpu-sweep.sh itself (session.py) and leads through five
steps:

  1. Scan: reads the GPU, the governor (smu or tt), its config's top safe-point and the load tool (--scan). Writes
     nothing and needs no password.
  2. Test the current top point: the control's rounds at the config's own top point. When it fails, the window stops
     here.
  3. Raise the clock: the clock ladder (--only oc), one step up at a time at a fixed voltage.
  4. Lower the voltage: the voltage ladder (--only uv), one step down at a time at the top clock.
  5. Install: --install writes the best step that passed every round into the governor's config, with a
     config.toml.bak-<stamp> backup that GPU Manager's Backups page restores. Or keep your own config.

Where the sweep stands is read from the script's own files every time (progress.py), so the window picks up where it
was after a freeze and a restart. With one boot per attempt, the window opens again after each login (resume.py).

The layout is Core Unlock's: the icon spanning the title with the version and a row of status boxes, the filled info
symbol and the round refresh symbol at the right end of the title row. Then the five steps as rows, with the button of
the current step on its row, a green bar over them when everything is done. Then a few short lines, the ladder as a
table, one row with the other actions as pills, the hint and what comes next, and the Details and Advanced pills at
its right end."""

from __future__ import annotations

import time

from PyQt6.QtCore import QByteArray, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPlainTextEdit,
    QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..theme import ACCENT, BLUE, GREEN, GREY, ORANGE, RED, header_font, muted, surface_style
from . import APP_NAME, LOGO_PATH, WIKI_URL, __version__, notify, progress, resume
from .options import (
    DEFAULT_FREQ_STEP, DEFAULT_MAX_FREQ, DEFAULT_MIN_VOLT, DEFAULT_ROUNDS, DEFAULT_TIME_SECS, DEFAULT_VOLT_STEP,
    HARD_MAX_FREQ, HARD_MAX_VOLT, HARD_MIN_VOLT, MAX_ROUNDS, MIN_FREQ_STEP, MIN_ROUNDS, MIN_TIME_SECS, MIN_VOLT_STEP,
    SweepOptions,
)
from .session import ScriptSession
from .widgets import HelpDialog, InfoButton, MetricBox, Pill, RefreshButton, SudoDialog, TogglePill, same_width

TASKBAR = 80                            # the room kept free under the window, for a taskbar
WIDTH = 900                             # as Core Unlock: it opens this wide, and is never narrower
STEPS = ("Scan", "Test the current top point", "Raise the clock", "Lower the voltage", "Install")
PART_OF_STEP = {1: "control", 2: "oc", 3: "uv"}
RESTART_SECS = 15                       # the countdown before the window restarts the board
GO_ON_SECS = 20                         # the countdown after a login before the next attempt

ABOUT = ("The GPU sweep finds the highest GPU clock and the lowest voltage your board holds. Then it can write them "
         "into the governor's config.<br><br>The steps:<br>1. The scan reads the GPU, the governor and the load "
         "tool.<br>2. Your config's top point runs a load, as a check of the board itself.<br>3. The clock goes up "
         "one step at a time.<br>4. The voltage goes down one step at a time.<br>5. Install writes the best step "
         f"into the config.<br><br><a href='{WIKI_URL}'>GPU Manager in the wiki</a>")

OUTCOMES = {
    "PASS": "passed",
    "CRASH-LOAD": "the board went down under load",
    "FAULT": "the kernel logged a GPU fault",
    "ERRORS": "memtest_vulkan found wrong results",
    "LOAD-FAIL": "the load tool stopped early",
    "NO-REACH": "the clock did not reach the step",
    "GOV-FAIL": "the governor did not start with the step",
    "SKIPPED": "skipped, an easier step fails every time",
}
WORDS = {"PASS": "Passed", "SKIPPED": "Skipped"}
LEGEND = ("Passed: the step held the load for the whole round. A failure is a freeze, a GPU fault in the kernel log, "
          "wrong results, a clock that falls short, or 97 °C.")


def _minutes(attempts: int, secs: int, per_boot: bool) -> str:
    total = attempts * (secs + 20 + (90 if per_boot else 30)) // 60        # a restart, or the 30 s cool-down
    total = max(5, round(total / 5) * 5)
    if total < 60:
        return f"about {total} minutes"
    hours, minutes = divmod(total, 60)
    return f"about {hours} h {minutes} min" if minutes else f"about {hours} h"


def _point(point: tuple[int, int] | None) -> str:
    return f"{point[0]} MHz @ {point[1]} mV" if point else "—"


def _points(points: list[tuple[int, int]]) -> str:
    return ", ".join(_point(p) for p in points)


def _step_name(item: str, top: tuple[int, int] | None) -> str:
    """"Control", "Clock +2 steps", "Voltage −1 step"."""
    name, _, value = item.partition(":")
    if name == "control" or not top:
        return "Control"
    diff = int(value) - top[0] if name == "oc" else top[1] - int(value)
    return ("Clock +" if name == "oc" else "Voltage −") + f"{diff} {'MHz' if name == 'oc' else 'mV'}"


class StepRow(QFrame):
    """One step as a row (Core Unlock's): a mark, "Step N · name" with its state, one line with what came out of it or
    what to do now, and on the current step's row its button. A click shows the step."""

    clicked = pyqtSignal()
    MARKS = {"done": "✔", "now": "▶", "running": "▶", "stopped": "✖"}
    WORDS = {"done": "Done", "now": "Do this now", "running": "Running", "stopped": "Stopped", "later": "Later"}

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.setObjectName("steprow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)
        self.mark = QLabel()
        self.mark.setFixedWidth(30)
        self.mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mark)
        text = QVBoxLayout()
        text.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(10)
        self.title = QLabel()
        self.caption = QLabel()
        top.addWidget(self.title)
        top.addWidget(self.caption)
        top.addStretch(1)
        text.addLayout(top)
        self.line = QLabel()
        self.line.setWordWrap(True)
        text.addWidget(self.line)
        layout.addLayout(text, 1)
        self.slot = QHBoxLayout()                   # the step's button, on the current step's row only
        layout.addLayout(self.slot)
        self.set_state("later", "")

    def set_state(self, state: str, line: str, selected: bool = False) -> None:
        colour = {"done": GREEN, "now": ACCENT, "running": ORANGE, "stopped": RED, "later": GREY}[state]
        later = state == "later"
        self.mark.setText(self.MARKS.get(state, str(self.index + 1)))
        self.mark.setStyleSheet(f"font-size:22px; font-weight:800; color:{muted() if later else colour};")
        self.title.setText(f"Step {self.index + 1} · {STEPS[self.index]}")
        self.title.setStyleSheet(header_font() + "font-size:17px; font-weight:800;"
                                 + (f"color:{muted()};" if later else ""))
        self.caption.setText(self.WORDS[state])
        self.caption.setStyleSheet(f"font-size:13px; font-weight:700; color:{muted() if later else colour};")
        self.line.setText(line)
        self.line.setStyleSheet("font-size:14px;" + ("font-weight:600;" if state in ("now", "running", "stopped") else
                                                     f"color:{muted()};"))
        edge = f"#steprow {{ border:2px solid {ACCENT}; border-left:4px solid {colour}; }}" if selected else ""
        self.setStyleSheet(surface_style(colour, "#steprow") + edge + "QLabel { background:transparent; border:none; }")

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class Ladder(QTableWidget):
    """The sweep's steps as a table: each step's clock and voltage and the outcome of every round."""

    def __init__(self):
        super().__init__(0, 3)
        self.verticalHeader().hide()
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_rows(self, rounds: int, rows: list[tuple[str, str, str, list[str]]]) -> None:
        """(step, clock, voltage, the outcome of each round) per row."""
        self.setColumnCount(3 + rounds)
        self.setHorizontalHeaderLabels(["Step", "Clock", "Voltage", *(f"Round {r}" for r in range(1, rounds + 1))])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setRowCount(len(rows))
        for r, (step, clock, volt, outcomes) in enumerate(rows):
            for c, value in enumerate([step, clock, volt, *outcomes]):
                item = QTableWidgetItem(value)
                if c >= 3 and value and value not in ("Passed", "Later", "Skipped", "Running"):
                    item.setForeground(Qt.GlobalColor.red)
                self.setItem(r, c, item)
        self.setFixedHeight(self.verticalHeader().length() + self.horizontalHeader().height() + 6)


class MainWindow(QWidget):
    def __init__(self, script: str, resume_run: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.script = script
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.session = ScriptSession(script, self)
        self.session.line.connect(self._on_line)
        self.session.notice.connect(self._on_notice)
        self.session.password.connect(self._on_password)
        self.session.finished.connect(self._on_finished)

        self.scan: dict[str, str] | None = None     # the last scan's results in this window
        self.job = ""                                # what the session runs: scan, test, install, reset, report
        self.live: dict[str, str] = {}               # the attempt that runs now: round, item, phase, load
        self.errors: list[str] = []                  # the script's ERROR lines of the last job
        self._wrong_password = False
        self.restart_first = False                   # one boot per attempt: the next one needs a restart
        self.paused = False
        self.note = ""                               # a line about what just happened, over the hint
        self.countdown = 0
        self.countdown_action = ""                   # restart or go
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        # The page scrolls when the window is lower than it, so the window can always shrink to fit the screen.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.body = QWidget()
        self.scroll.setWidget(self.body)
        outer.addWidget(self.scroll)
        root = QVBoxLayout(self.body)
        root.setSpacing(10)
        root.addLayout(self._build_header())
        # When everything is done, a green bar over the steps.
        self.finished_bar = QLabel()
        self.finished_bar.setWordWrap(True)
        self.finished_bar.setStyleSheet(f"background:{GREEN}; color:white; font-size:17px; font-weight:800; "
                                        "padding:12px; border-radius:8px;")
        self.finished_bar.hide()
        root.addWidget(self.finished_bar)
        root.addLayout(self._build_steps())
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setStyleSheet("font-size:14px;")
        root.addWidget(self.text)
        self.ladder = Ladder()
        root.addWidget(self.ladder)
        self.legend = QLabel(LEGEND)
        self.legend.setWordWrap(True)
        self.legend.setStyleSheet(f"font-size:12px; color:{muted()};")
        root.addWidget(self.legend)
        # The step's pills on the left, what comes next and the hint beside them, and Details and Advanced at the
        # right end.
        actions = QHBoxLayout()
        actions.setSpacing(16)
        self.actions_row = QHBoxLayout()
        self.actions_row.setSpacing(8)
        actions.addLayout(self.actions_row)
        side = QVBoxLayout()
        side.setSpacing(4)
        self.next_label = QLabel()
        self.next_label.setWordWrap(True)
        self.next_label.setStyleSheet(f"font-size:13px; font-weight:600; color:{ACCENT};")
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(f"font-size:12px; color:{muted()};")
        # While a script runs: a turning symbol, what runs and for how long.
        self.running = QLabel()
        self.running.setStyleSheet(f"font-size:14px; font-weight:700; color:{ORANGE};")   # orange stands out
        self.running.hide()
        self._spin = QTimer(self)
        self._spin.setInterval(250)
        self._spin.timeout.connect(self._on_spin)
        self._spin_frame = 0
        self._busy_since = 0.0
        side.addStretch(1)
        side.addWidget(self.running)
        side.addWidget(self.next_label)
        side.addWidget(self.hint)
        side.addStretch(1)
        actions.addLayout(side, 1)
        actions.addLayout(self._build_buttons())
        root.addLayout(actions)
        self.actions: list[Pill] = []
        self.advanced = self._build_advanced()
        self.advanced.hide()
        root.addWidget(self.advanced)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(4000)
        self.output.setMinimumHeight(200)
        self.output.setPlaceholderText("What ps5-gpu-sweep.sh prints appears here.")
        self.output.hide()
        root.addWidget(self.output, 1)
        root.addStretch(0)

        self.view = -1                               # the step shown; -1 follows the current step
        self.setMinimumWidth(WIDTH)
        self._restore_geometry()
        self.refresh()
        if resume_run:
            QTimer.singleShot(0, self._resume)

    # ------------------------------------------------------------------ UI
    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(14)
        if LOGO_PATH.is_file():
            logo = QLabel()
            logo.setPixmap(QPixmap(str(LOGO_PATH)).scaled(
                96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignTop)
            header.addWidget(logo)
        right = QVBoxLayout()
        right.setSpacing(6)
        title_row = QHBoxLayout()
        title = QLabel(f"{APP_NAME}  <span style='color:{muted()}; font-size:14px;'>v{__version__}</span>")
        title.setStyleSheet(header_font() + "font-size:24px; font-weight:800;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self.info = InfoButton(ABOUT, "What the GPU sweep does")
        self.info.setStyleSheet(
            f"QToolButton {{ border:none; border-radius:{InfoButton.SIZE // 2}px; background:{ACCENT}; color:white; "
            "font-weight:800; font-family:Georgia, serif; font-style:italic; padding:0; }")
        title_row.addWidget(self.info)
        self.refresh_button = RefreshButton("Reads the sweep's results and the governor's config again")
        self.refresh_button.clicked.connect(self.refresh)
        title_row.addWidget(self.refresh_button)
        right.addLayout(title_row)
        boxes = QHBoxLayout()
        boxes.setSpacing(8)
        self.governor_box = MetricBox("Governor", GREY)
        self.top_box = MetricBox("Top point now", GREY)
        self.count_box = MetricBox("Attempts done", GREY)
        self.state_box = MetricBox("Sweep", GREY)
        self.boxes = [self.governor_box, self.top_box, self.count_box, self.state_box]
        for box in self.boxes:
            boxes.addWidget(box)
        same_width(self.boxes)
        boxes.addStretch(1)
        right.addLayout(boxes)
        header.addLayout(right, 1)
        return header

    def _build_steps(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(6)
        self.step_boxes: list[StepRow] = []
        for index in range(len(STEPS)):
            box = StepRow(index)
            box.clicked.connect(lambda i=index: self._show_step(i))
            column.addWidget(box)
            self.step_boxes.append(box)
        return column

    @property
    def heading(self) -> QLabel:
        """The title on the row of the step shown."""
        return self.step_boxes[self.step if self.view < 0 else self.view].title

    @property
    def todo(self) -> QLabel:
        """The line on the current step's row: what to do now."""
        return self.step_boxes[self.step].line

    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        self.details_button = Pill("Details", "Show", "Shows or hides what the script prints.", GREY)
        self.details_button.clicked.connect(lambda: self.show_details(self.output.isHidden()))
        self.advanced_button = Pill("Advanced", "Show", "Load time, rounds, the ladders' limits and steps, and how "
                                    "the sweep restarts.", GREY)
        self.advanced_button.clicked.connect(lambda: self.show_advanced(self.advanced.isHidden()))
        row.addWidget(self.details_button)
        row.addWidget(self.advanced_button)
        same_width([self.details_button, self.advanced_button])
        return row

    def _spin_box(self, low: int, high: int, step: int, suffix: str, key: str, default: int, tip: str) -> QSpinBox:
        field = QSpinBox()
        field.setRange(low, high)
        field.setSingleStep(step)
        field.setSuffix(suffix)
        field.setValue(int(QSettings().value(f"advanced/{key}", default)))
        field.setToolTip(tip)
        return field

    def _build_advanced(self) -> QWidget:
        """The load, the rounds and the ladders' limits and steps on two lines, One boot each under them."""
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.setContentsMargins(0, 0, 0, 0)
        self.time_spin = self._spin_box(MIN_TIME_SECS, 36000, 60, " s", "time", DEFAULT_TIME_SECS,
                                        f"How long the load runs in each attempt (-t). At least {MIN_TIME_SECS} s, "
                                        f"{DEFAULT_TIME_SECS} s by default.")
        self.rounds_spin = self._spin_box(MIN_ROUNDS, MAX_ROUNDS, 1, "", "rounds", DEFAULT_ROUNDS,
                                          "Attempts per step (-r). Every round of a step runs before the next step.")
        self.max_freq_spin = self._spin_box(500, HARD_MAX_FREQ, 25, " MHz", "max_freq", DEFAULT_MAX_FREQ,
                                            f"The highest clock the clock ladder tries (--max-freq). At most "
                                            f"{HARD_MAX_FREQ} MHz.")
        self.min_volt_spin = self._spin_box(HARD_MIN_VOLT, HARD_MAX_VOLT, 5, " mV", "min_volt", DEFAULT_MIN_VOLT,
                                            f"The lowest voltage the voltage ladder tries (--min-volt). At least "
                                            f"{HARD_MIN_VOLT} mV.")
        self.freq_step_spin = self._spin_box(MIN_FREQ_STEP, 500, 25, " MHz", "freq_step", DEFAULT_FREQ_STEP,
                                             "How far each clock step goes up (--freq-step).")
        self.volt_step_spin = self._spin_box(MIN_VOLT_STEP, 200, 5, " mV", "volt_step", DEFAULT_VOLT_STEP,
                                             "How far each voltage step goes down (--volt-step).")
        self.oc_volt_spin = self._spin_box(0, HARD_MAX_VOLT, 5, " mV", "oc_volt", 0,
                                           "The voltage of the clock ladder (--oc-volt). 0 uses your config's top "
                                           f"voltage. At most {HARD_MAX_VOLT} mV.")
        self.oc_volt_spin.setSpecialValueText("Top point's")
        rows = ((("Load per attempt", self.time_spin), ("Rounds per step", self.rounds_spin),
                 ("Clock ladder voltage", self.oc_volt_spin)),
                (("Highest clock", self.max_freq_spin), ("Clock step", self.freq_step_spin),
                 ("Lowest voltage", self.min_volt_spin), ("Voltage step", self.volt_step_spin)))
        for fields in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            for caption, field in fields:
                label = QLabel(caption)
                label.setStyleSheet("font-weight:600;")
                label.setBuddy(field)
                label.setToolTip(field.toolTip())
                row.addWidget(label)
                row.addWidget(field)
                row.addSpacing(10)
            row.addStretch(1)
            box.addLayout(row)
        switches = QHBoxLayout()
        self.per_boot_pill = TogglePill("One boot each", "--per-boot: the board restarts after each attempt, and the "
                                        "window opens again after the login and goes on. Off: every attempt runs in "
                                        "this boot, with a 30 s cool-down in between.",
                                        QSettings().value("advanced/per_boot", "false") == "true")
        switches.addWidget(self.per_boot_pill)
        switches.addStretch(1)
        box.addLayout(switches)
        for field in (self.time_spin, self.rounds_spin, self.max_freq_spin, self.min_volt_spin, self.freq_step_spin,
                      self.volt_step_spin, self.oc_volt_spin):
            field.valueChanged.connect(self._save_advanced)
        self.per_boot_pill.toggled.connect(self._save_advanced)
        return panel

    def show_details(self, shown: bool) -> None:
        self.output.setVisible(shown)
        self.details_button.caption.setText("Hide" if shown else "Show")
        self._fit()

    def show_advanced(self, shown: bool) -> None:
        self.advanced.setVisible(shown)
        self.advanced_button.caption.setText("Hide" if shown else "Show")
        self._fit()

    def _fit(self) -> None:
        """The window as high as its page, at its width, but never higher than the screen leaves room for."""
        self.body.layout().activate()
        self.resize(self.width(), min(self.body.sizeHint().height() + 2, self._room()))

    def _room(self) -> int:
        """The screen's free height, less room for a taskbar (Wayland doesn't say where it is)."""
        screen = self.screen() or QApplication.primaryScreen()
        return screen.availableGeometry().height() - TASKBAR if screen else 800

    def _set_actions(self, actions: list[tuple], primary: str = "") -> None:
        """(value, caption, tooltip, colour, slot[, enabled]) for each pill of the step; *primary* is the pill of
        the line "Do this now", with an accent border all round, on the current step's row. The others sit at the
        bottom, on the left."""
        for pill in self.actions:
            self.actions_row.removeWidget(pill)
            pill.hide()
            pill.setParent(None)
            pill.deleteLater()
        while self.actions_row.count():
            self.actions_row.takeAt(0)
        self.actions = []
        for value, caption, tip, colour, slot, *enabled in actions:
            pill = Pill(value, caption, tip, colour)
            pill.clicked.connect(lambda p=pill, s=slot: p.isEnabled() and s())
            pill.setEnabled(enabled[0] if enabled else True)
            if value == primary:
                pill.setStyleSheet(pill.styleSheet() + f"#pill {{ border:2px solid {ACCENT}; }}")
                pill.primary = True
                self.step_boxes[self.step].slot.addWidget(pill)
            else:
                self.actions_row.addWidget(pill)
            self.actions.append(pill)
        bottom = [p for p in self.actions if not getattr(p, "primary", False)]
        if bottom:
            same_width(bottom)

    def pill(self, value: str) -> Pill | None:
        return next((p for p in self.actions if p.value.text() == value), None)

    # --------------------------------------------------------------- window
    def _restore_geometry(self) -> None:
        geometry = QSettings().value("main_window/geometry")
        if isinstance(geometry, QByteArray):
            self.restoreGeometry(geometry)                  # where it was; its size comes from the page
        # As wide as the steps need, and as high as the page once it shows: before that, the page doesn't know its
        # height yet.
        self.resize(WIDTH, min(self.height(), self._room()))
        QTimer.singleShot(0, self._fit)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.session.busy and self.job == "test":
            answer = QMessageBox.question(self, APP_NAME, "An attempt is still running. Close anyway?\n\n"
                                          "The attempt stops, your own config comes back, and the attempt runs "
                                          "again later.")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.session.stop()
        self.session.close()
        self._tick.stop()
        QSettings().setValue("main_window/geometry", self.saveGeometry())
        super().closeEvent(event)

    # ------------------------------------------------------------- advanced
    def _save_advanced(self) -> None:
        settings = QSettings()
        for key, field in (("time", self.time_spin), ("rounds", self.rounds_spin), ("max_freq", self.max_freq_spin),
                           ("min_volt", self.min_volt_spin), ("freq_step", self.freq_step_spin),
                           ("volt_step", self.volt_step_spin), ("oc_volt", self.oc_volt_spin)):
            settings.setValue(f"advanced/{key}", field.value())
        settings.setValue("advanced/per_boot", "true" if self.per_boot_pill.isChecked() else "false")

    def _take_run_settings(self) -> None:
        """A sweep that has started keeps its own ladder: the fields show it, so going on doesn't change it. The
        script refuses another ladder until a reset."""
        p = self.p
        if not p.started or self.session.busy:
            return
        for field, value in ((self.time_spin, p.time_secs), (self.rounds_spin, p.rounds),
                             (self.max_freq_spin, p.max_freq), (self.min_volt_spin, p.min_volt),
                             (self.freq_step_spin, p.freq_step), (self.volt_step_spin, p.volt_step)):
            field.setValue(value)
        top_v = p.top[1] if p.top else 0
        self.oc_volt_spin.setValue(0 if p.oc_volt in (0, top_v) else p.oc_volt)
        for field in (self.max_freq_spin, self.min_volt_spin, self.freq_step_spin, self.volt_step_spin,
                      self.oc_volt_spin):
            field.setEnabled(False)                      # Start over changes them

    def options(self) -> SweepOptions:
        return SweepOptions(time_secs=self.time_spin.value(), rounds=self.rounds_spin.value(),
                            max_freq=self.max_freq_spin.value(), min_volt=self.min_volt_spin.value(),
                            freq_step=self.freq_step_spin.value(), volt_step=self.volt_step_spin.value(),
                            oc_volt=self.oc_volt_spin.value(), per_boot=self.per_boot_pill.isChecked())

    # ---------------------------------------------------------------- state
    def refresh(self) -> None:
        """Reads the sweep's files and the governor's config again, and shows the step."""
        self.p = progress.load()
        self.wizard = progress.read_wizard()
        self.governor = progress.find_governor()
        self.config_points = (progress.read_points(progress.config_path(self.governor)) if self.governor else [])
        for field in (self.max_freq_spin, self.min_volt_spin, self.freq_step_spin, self.volt_step_spin,
                      self.oc_volt_spin):
            field.setEnabled(True)
        self._take_run_settings()
        self.step = self._current_step()
        self._render()

    def _kept(self) -> bool:
        return self.wizard.get("keep", "") == "1"

    def _current_step(self) -> int:
        p = self.p
        if p.installed or self._kept():
            return 4
        if not p.started:
            return 0
        if p.state("control") != "passed":
            return 1
        if p.next_attempt("oc") is not None:
            return 2
        if p.next_attempt("uv") is not None:
            return 3
        return 4

    def _show_step(self, index: int) -> None:
        if index <= self.step:
            self.view = -1 if index == self.step else index
            self._render()

    # --------------------------------------------------------------- render
    def _finished(self) -> bool:
        return self.step == 4 and bool(self.p.installed or self._kept())

    def _ladder_rows(self) -> list[tuple[str, str, str, list[str]]]:
        """The rows of the ladder table: the run's plan, or before the run the plan the Advanced options make."""
        p = self.p
        if not p.started:
            top = self._scan_top()
            if not top:
                return []
            opts = self.options()
            p = progress.Progress(top=top, rounds=opts.rounds, max_freq=opts.max_freq, min_volt=opts.min_volt,
                                  freq_step=opts.freq_step, volt_step=opts.volt_step, oc_volt=opts.oc_volt)
        current = (self.live.get("round", ""), self.live.get("item", "")) if self.job == "test" else ("", "")
        rows = []
        for item in p.items:
            f, v = p.point(item)
            outcomes = []
            for rnd in range(1, p.rounds + 1):
                if (str(rnd), item) == current:
                    outcomes.append("Running")
                    continue
                o = p.outcome(rnd, item)
                outcomes.append(WORDS.get(o, o) if o else ("Skipped" if p.pruned(item) else "Later"))
            rows.append((_step_name(item, p.top), f"{f} MHz", f"{v} mV", outcomes))
        return rows

    def _scan_top(self) -> tuple[int, int] | None:
        if self.p.top:
            return self.p.top
        return self.config_points[-1] if self.config_points else None

    def _summary(self, index: int, state: str) -> str:
        """The line on a step's row that is not the current one: what came out of it, or what it will do."""
        if state == "later":
            return ("Reads the GPU, the governor, its config and the load tool. It writes nothing.",
                    "Runs your config's top point under load, as a check of the board itself.",
                    "Raises the clock one step at a time at a fixed voltage.",
                    "Lowers the voltage one step at a time at your top clock.",
                    "Writes the best step into the governor's config, or keeps your own.")[index]
        p = self.p
        if index == 0:
            gov = p.governor or self.governor
            return f"The governor is cyan-skillfish-governor-{gov}. Its top point is {_point(p.top)}." if gov else \
                "The board was read."
        if index == 1:
            return f"Passed {p.rounds} of {p.rounds} rounds at {_point(p.top)}."
        if index in (2, 3):
            name = PART_OF_STEP[index]
            if not p.items_of(name):
                return "This ladder was not part of the sweep."
            good = [it for it in p.items_of(name) if p.verdict(it) == "good"]
            if not good:
                return "No step passed every round."
            return f"Best step that passed every round: {_point(p.point(good[-1]))}."
        if p.installed:
            f, v, *_ = p.installed.split() + ["", ""]
            return f"Installed {f} MHz @ {v} mV as the top point."
        return "You kept your own config."

    def _render(self) -> None:
        view = self.step if self.view < 0 else self.view
        finished = self._finished()
        for index, box in enumerate(self.step_boxes):
            if index == self.step:
                stopped = index == 1 and self.p.state("control") == "failed"
                running = self.session.busy or bool(self.countdown)
                state = "done" if finished else "stopped" if stopped else "running" if running else "now"
            else:
                state = "done" if index < self.step else "later"
            box.set_state(state, self._summary(index, state) if state in ("done", "later") else "",
                          selected=index == view != self.step)
            box.setEnabled(index <= self.step)
        if finished:
            self.finished_bar.setText("✔  Finished. Your own config stays. There is nothing left to do." if self._kept()
                                      else "✔  Finished. The best step is in the governor's config. There is nothing "
                                           "left to do.")
        self.finished_bar.setVisible(finished)
        self._render_boxes()
        page = (self._page_scan, self._page_control, lambda: self._page_ladder("oc"),
                lambda: self._page_ladder("uv"), self._page_install)[view]
        heading, lines, actions, hint, nxt = page()
        if self.countdown:
            what = "Restarting" if self.countdown_action == "restart" else "Going on"
            actions = [("Restart now" if self.countdown_action == "restart" else "Go on now",
                        "Don't wait", "", ACCENT, self._countdown_now),
                       ("Pause", "Stop here", "Stops the countdown. Go on later.", GREY, self._pause)]
            nxt = f"{what} in {self.countdown} s."
        elif self.session.busy and self.job == "test":
            actions = [("Stop", "Stop this attempt", "Stops the attempt as Ctrl+C does. Your own config comes back, "
                        "and the attempt runs again later.", RED, self.session.stop)]
        elif self.session.busy:
            actions = [(a[0], a[1], a[2], a[3], a[4], False) for a in actions]
        todo, primary = self._todo(view, actions)
        if not finished:
            self.todo.setText(todo if view == self.step else "Click this row to go back to this step.")
        self.heading.setText(f"Step {view + 1} · {heading}")
        self.text.setText("<br>".join(lines))
        self.text.setVisible(bool(lines))
        rows = self._ladder_rows()
        self.ladder.set_rows(self.p.rounds if self.p.started else self.options().rounds, rows)
        self.ladder.setVisible(bool(rows))
        self.legend.setVisible(bool(rows))
        self._set_actions(actions, primary)
        self.hint.setText(self.note or hint)
        self.next_label.setText(nxt)

    def _todo(self, view: int, actions: list[tuple]) -> tuple[str, str]:
        """The one thing to do now, in words, and the pill that does it (empty when there is nothing to click)."""
        if self.countdown:
            if self.countdown_action == "restart":
                return (f"Nothing to do. The board restarts by itself in {self.countdown} s. The window opens again "
                        "after the login."), "Restart now"
            return f"Nothing to do. The next attempt starts by itself in {self.countdown} s.", "Go on now"
        if self.session.busy and self.job == "test":
            return "Nothing to do. The sweep runs by itself, and a notification tells you when it ends.", ""
        if self.session.busy:
            return "Wait a moment, until the line beside the pills is gone.", ""
        enabled = [a[0] for a in actions if (a[5] if len(a) > 5 else True)]
        if view != self.step:
            return "This step is done. Click the step that says Do this now to go on.", ""
        words = {
            "Scan": "Click <b>Scan</b>. It needs no password.",
            "Start": "Click <b>Start</b>. A question opens. Answer <b>Yes</b>, then type your password.",
            "Go on": "Click <b>Go on</b> to run the next attempt.",
            "Restart": "Click <b>Restart</b>. After the login, the window opens again by itself.",
            "Install": "Click <b>Install</b> to write the best step, or <b>Keep my config</b>.",
        }
        for value in ("Scan", "Start", "Go on", "Restart", "Install"):
            if value in enabled:
                return words[value], value
        if "Keep my config" in enabled:
            return "Click <b>Keep my config</b>. Nothing better than your top point passed.", "Keep my config"
        if "Scan again" in enabled:
            return "Fix what the text above names, then click <b>Scan again</b>.", "Scan again"
        if "Start over" in enabled:
            return "The sweep stopped. Click <b>Start over</b> to test again.", ""
        return "Nothing to do in this step yet.", ""

    def _estimate(self, attempts: int) -> str:
        opts = self.options()
        return _minutes(attempts, opts.time_secs, opts.per_boot)

    def _render_boxes(self) -> None:
        gov = self.governor or self.p.governor
        if gov:
            self.governor_box.set_value(gov, f"cyan-skillfish-governor-{gov}")
            self.governor_box.set_colour(BLUE)
        else:
            self.governor_box.set_value("—", "No cyan-skillfish governor config was found, or both are there and "
                                             "neither runs.")
            self.governor_box.set_colour(GREY)
        top = self.config_points[-1] if self.config_points else None
        # The clock as the value and the voltage under it: four boxes fit the window's 900 px that way.
        self.top_box.set_value(f"{top[0]} MHz" if top else "—", "The highest safe-point of the governor's config now.")
        self.top_box.caption.setText(f"Top point now, {top[1]} mV" if top else "Top point now")
        self.top_box.set_colour(BLUE if top else GREY)
        if self.p.started:
            self.count_box.set_value(f"{self.p.done()} of {self.p.total()}", "Attempts done of the whole sweep.")
            self.count_box.set_colour(BLUE)
        else:
            self.count_box.set_value("—", "No sweep has started yet.")
            self.count_box.set_colour(GREY)
        if self.session.busy and self.job == "test":
            state, colour = "Running", ORANGE
        elif self.countdown:
            state, colour = ("Restart" if self.countdown_action == "restart" else "Going on"), ACCENT
        elif self.p.state("control") == "failed":
            state, colour = "Stopped", RED
        elif self._finished() or self.p.finished:
            state, colour = "Done", GREEN
        elif self.p.started:
            state, colour = "Paused", GREY
        else:
            state, colour = "Not started", GREY
        self.state_box.set_value(state, "Where the GPU sweep stands.")
        self.state_box.set_colour(colour)

    def _live_hint(self) -> str:
        if self.job != "test" or not self.live:
            return ""
        parts = [f"Now: round {self.live.get('round', '?')}, {_step_name(self.live.get('item', ''), self.p.top)}"]
        if "load" in self.live:
            secs, total, temp, clock, busy = (self.live["load"].split() + ["?"] * 5)[:5]
            parts += [f"{secs} of {total} s", f"{temp} °C", f"{clock} MHz", f"busy {busy} %"]
        elif "phase" in self.live:
            parts.append({"idle": "waiting for an idle GPU", "governor": "starting the governor with the step",
                          "cooldown": "cooling down 30 s"}.get(self.live["phase"], self.live["phase"]))
        return " · ".join(parts)

    def _go_on_actions(self, part: str, label: str) -> list[tuple]:
        """Go on, or Restart with one boot per attempt, with Pause, Report and Start over."""
        if self.restart_first or (self.per_boot_pill.isChecked() and self.p.done()):
            first = ("Restart", "Then go on", "Restarts the board. The window opens again after the login and goes "
                     "on.", ACCENT, self._restart_and_go_on)
        else:
            first = ("Go on", label, "Runs the next attempts in this window.", ACCENT, lambda: self._go_on(part))
        actions = [first]
        if resume.armed():
            actions.append(("Pause", "Stop after this", "The window no longer opens and goes on after a login.",
                            GREY, self._pause))
        return actions + [self._report_action(), self._start_over_action()]

    def _report_action(self) -> tuple:
        return ("Report", "Save as a text file", "Writes the results so far to a text file on your Desktop.", BLUE,
                self._report)

    def _start_over_action(self) -> tuple:
        return ("Start over", "Delete results", "Asks first. Then deletes the sweep's results and logs. Your config "
                "stays as it is.", RED, self._start_over)

    def _keep_action(self) -> tuple:
        return ("Keep my config", "Install nothing", "Ends the sweep here. The governor's config stays as it is.",
                GREEN, self._keep)

    # ---------------------------------------------------------------- pages
    def _page_scan(self) -> tuple:
        help_pill = ("Help", "How the sweep works", "The script's own help, as a page.", BLUE,
                     lambda: HelpDialog(self.script, self).exec())
        if self.job == "scan" and self.session.busy:
            return ("Scan", ["The scan reads the GPU, the governor and the load tool.", "It writes nothing."],
                    [("Scan", "Reading...", "", ACCENT, self._scan, False), help_pill], "Reading the board...", "")
        if not self.scan:
            lines = ["The scan reads the GPU, the governor, its config and the load tool.", "It writes nothing.",
                     "It needs no password."]
            return ("Scan", lines, [("Scan", "Read the board", "Reads what a sweep needs (--scan). Writes nothing.",
                                     ACCENT, self._scan), help_pill],
                    "", "Next: the scan, then the test of your config's top point.")
        s = self.scan
        lines, blockers = [], []
        if s.get("gpu", "-") == "-":
            blockers.append("No PS5 GPU was found.")
        gov = s.get("governor", "-")
        if gov == "-":
            blockers.append("No cyan-skillfish governor config was found, or both are there and neither runs. Start "
                            "the governor you use.")
        else:
            lines.append(f"The governor is <b>cyan-skillfish-governor-{gov}</b>. Its service is "
                         f"{s.get('service', '-')}.")
            if s.get("service") != "active":
                blockers.append("The governor's service is not running. Start it on GPU Manager's Service page.")
            top = s.get("top", "- -").split()
            lines.append(f"Its top point is <b>{top[0]} MHz @ {top[1]} mV</b>, one of {s.get('points', '?')} "
                         "safe-points." if top[0] != "-" else "Its config has no safe-points.")
            if top[0] == "-":
                blockers.append("The governor's config has no safe-points.")
            saved = s.get("saved-governor", "")
            if saved and saved != gov:
                blockers.append(f"The results are for the {saved} governor. Start over to sweep this one.")
            if s.get("snapshot") == "changed":
                blockers.append("The governor's config changed since the sweep started. Start over to sweep the new "
                                "config.")
        load = s.get("load", "-")
        if load == "-":
            blockers.append("No GPU load tool was found. Put memtest_vulkan in ~/.local/bin, then scan again.")
        else:
            lines.append(f"The load tool is <b>{load}</b>." + ("" if load == "memtest_vulkan" else
                                                               " It only shows crashes. memtest_vulkan also finds "
                                                               "wrong results."))
        opts = self.options()
        if blockers:
            lines += blockers
        else:
            lines.append(f"The top point runs {opts.rounds} rounds first, {self._estimate(opts.rounds)}.")
        hint = " · ".join([f"Load per attempt: {opts.time_secs} s", f"Rounds per step: {opts.rounds}"])
        start = ("Start", "Go to step 2", "Asks first. Then tests your config's top point.", ACCENT, self._start,
                 not blockers and not self.p.started)
        return ("Scan", lines, [start, ("Scan again", "Read the board", "Reads the board again. Writes nothing.",
                                        BLUE, self._scan), help_pill], hint,
                "" if blockers else f"Next: your config's top point, {opts.rounds} rounds.")

    def _page_control(self) -> tuple:
        p = self.p
        about = [f"Your config's top point, {_point(p.top)}, runs a load. Nothing else changes.",
                 "If this fails, the board, its power, its heat or the load tool is at fault, not a step."]
        if p.state("control") == "failed":
            bad = next(a for a in p.attempts if a.item == "control" and progress.FAIL_RE.match(a.outcome))
            lines = [about[0], f"Round {bad.round} ended with {bad.outcome}: {OUTCOMES.get(bad.outcome, 'it failed')}.",
                     "So no step of the sweep can be trusted. The ladders are not offered."]
            return ("Test the current top point", lines, [self._report_action(), self._start_over_action()],
                    "Your own config is back.", "Advice: check power and cooling, then start over.")
        if self.session.busy and self.job == "test":
            return (f"Test the current top point, round {self.live.get('round', '?')} of {p.rounds}", about, [],
                    self._live_hint(), "")
        if p.state("control") == "passed":
            return ("Test the current top point", [about[0], f"All {p.rounds} rounds passed."], [], "", "")
        nxt = p.next_attempt("control")
        if nxt is None:
            return ("Test the current top point", about, [], "", "")
        return ("Test the current top point", [*about, f"{p.done('control')} of {p.rounds} rounds are done."],
                self._go_on_actions("control", "Run the next round"), "", f"Next: round {nxt[0]} of the top point.")

    def _page_ladder(self, name: str) -> tuple:
        p = self.p
        title = STEPS[2] if name == "oc" else STEPS[3]
        top_f, top_v = p.top or (0, 0)
        if name == "oc":
            about = [f"The clock goes up {p.freq_step} MHz at a time, up to {p.max_freq} MHz, at "
                     f"{p.oc_volt or top_v} mV.",
                     "Steps above a step that fails every time are skipped."]
        else:
            about = [f"The voltage goes down {p.volt_step} mV at a time, down to {p.min_volt} mV, at {top_f} MHz.",
                     "Steps below a step that fails every time are skipped."]
        if not p.items_of(name):
            return (title, ["This ladder is not part of the sweep."], [], "", "")
        if self.session.busy and self.job == "test":
            return (title, about, [], self._live_hint(), "")
        nxt = p.next_attempt(name)
        if nxt is None:
            good = [it for it in p.items_of(name) if p.verdict(it) == "good"]
            return (title, [about[0], f"Best step that passed every round: {_point(p.point(good[-1]))}."
                            if good else "No step passed every round."], [], "", "")
        left = p.total(name) - p.done(name)
        if not p.done(name):
            start = ("Start", title, "Asks first. Then runs the ladder in this window.", ACCENT,
                     lambda: self._start_ladder(name))
            return (title, about, [start, self._report_action(), self._start_over_action()],
                    f"{left} attempts, {self._estimate(left)}. A step past the limit can freeze the board.",
                    "Next: " + ("the voltage ladder." if name == "oc" else "Install, in step 5."))
        return (title, [*about, f"{p.done(name)} of {p.total(name)} attempts are done."],
                self._go_on_actions(name, "Run the next attempt"), f"{left} attempts left, {self._estimate(left)}.",
                f"Next: round {nxt[0]}, {_step_name(nxt[1], p.top)}.")

    def _page_install(self) -> tuple:
        p = self.p
        if p.installed:
            f, v, backup = (p.installed.split() + ["", "", ""])[:3]
            lines = [f"The governor's top point is <b>{f} MHz @ {v} mV</b> now.",
                     f"The config of before is in {backup}.",
                     "To undo it, restore that backup on GPU Manager's Backups page."]
            return ("Install", lines, [self._report_action(), self._start_over_action()], "", "")
        if self._kept():
            return ("Install", ["You kept your own config. Nothing was installed."], [self._start_over_action()], "",
                    "")
        best = p.best()
        if best is None:
            return ("Install", ["Nothing better than your top point passed every round.",
                                "Your own config stays as it is."],
                    [self._keep_action(), self._report_action(), self._start_over_action()], "", "")
        keep, drop = p.install_plan()
        lines = [f"The best step is <b>{_point(best)}</b>, one step back from the edge as a margin.",
                 f"Install makes it the top point and keeps the points below it: {_points(keep) or 'none'}."]
        if drop:
            lines.append(f"These points go, as their voltage is above {best[1]} mV: {_points(drop)}.")
        lines.append("Install backs up the config first. GPU Manager's Backups page restores it.")
        install = ("Install", "Write the best step", "Asks first. Then writes the step into the governor's config.",
                   ACCENT, self._install, bool(keep))
        return ("Install", lines, [install, self._keep_action(), self._report_action(), self._start_over_action()],
                "Install asks for your password." if keep else
                "Every lower point has a higher voltage, so only one point would be left. Install is off.", "")

    # -------------------------------------------------------------- actions
    def _scan(self) -> None:
        self.scan = None
        self._run("scan", ["--scan"])

    def _confirm(self, question: str, facts: list[str]) -> bool:
        opts = self.options()
        errors = opts.validate()
        if errors:
            QMessageBox.warning(self, APP_NAME, "\n".join(errors))
            return False
        if opts.per_boot:
            facts.append("After each attempt, the board restarts by itself. This window opens again after each "
                         "login and goes on.")
        facts.append("After a freeze, turn the board off and on, and open the window. It asks what happened.")
        facts.append("You'll be asked for your password.")
        return QMessageBox.question(self, APP_NAME, f"{question}\n\n" + "\n".join(facts)) == \
            QMessageBox.StandardButton.Yes

    def _start(self) -> None:
        if not self._confirm("Test your config's top point?", [
                "The top point runs a GPU load. Nothing else changes.",
                f"{self.options().rounds} rounds take {self._estimate(self.options().rounds)}."]):
            return
        progress.forget()
        self._go_on("control")

    def _start_ladder(self, name: str) -> None:
        left = self.p.total(name) - self.p.done(name)
        question = "Raise the clock one step at a time?" if name == "oc" else "Lower the voltage one step at a time?"
        if self._confirm(question, [
                "Each step is written into the governor's config for its attempt. Your own config comes back after.",
                f"{left} attempts take {self._estimate(left)}.",
                "A step past the limit can freeze the board. Save your work in other apps first."]):
            self._go_on(name)

    def _part(self) -> str:
        return PART_OF_STEP.get(self.step, "")

    def _go_on(self, part: str) -> None:
        if self.per_boot_pill.isChecked():
            resume.arm(self.script)
        self.paused = False
        self._run_test(part)

    def _run_test(self, part: str = "") -> None:
        self.restart_first = False
        self.live = {}
        self._run("test", self.options().to_args(part or self._part()))

    def _restart_and_go_on(self) -> None:
        resume.arm(self.script)
        self._restart_only()

    def _restart_only(self) -> None:
        if not resume.restart():
            self.note = "The window could not restart the board. Restart it by hand."
            self._render()

    def _resume(self) -> None:
        """Opened after a login by the autostart entry: a countdown and the next attempt."""
        self.refresh()
        if not resume.armed():
            return
        part = self._part()
        if not part or self.p.state("control") == "failed" or (self.p.next_attempt(part) is None
                                                                 and not self.p.crashed):
            resume.disarm()
            self._render()
            self._notify_end()
            return
        self._start_countdown("go", GO_ON_SECS)

    def _pause(self) -> None:
        self._tick.stop()
        self.countdown = 0
        self.paused = True
        resume.disarm()
        self.note = "Paused. Go on whenever you like."
        self._render()

    def _start_countdown(self, action: str, secs: int) -> None:
        self.countdown_action = action
        self.countdown = secs
        self._tick.start()
        self._render()

    def _on_tick(self) -> None:
        self.countdown -= 1
        if self.countdown <= 0:
            self._countdown_now()
            return
        self._render()

    def _countdown_now(self) -> None:
        self._tick.stop()
        self.countdown = 0
        action, self.countdown_action = self.countdown_action, ""
        self.note = ""
        if action == "restart":
            self._restart_only()
        else:
            self._run_test()

    def _keep(self) -> None:
        progress.write_wizard({"keep": "1"})
        resume.disarm()
        self.view = -1
        self.refresh()

    def _start_over(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            "Delete the sweep's results and start over?\n\n"
            "This deletes every result and log in ~/.local/share/ps5-gpu-sweep.\n"
            "The governor's config stays as it is.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        resume.disarm()
        progress.forget()
        self._run("reset", ["--reset"])

    def _report(self) -> None:
        self.show_details(True)
        self._run("report", ["--status"])

    def _install(self) -> None:
        best = self.p.best()
        if best is None:
            return
        keep, drop = self.p.install_plan()
        facts = [f"{_point(best)} becomes the top point of the governor's config.",
                 f"The points below it stay: {_points(keep)}."]
        if drop:
            facts.append(f"These points go, as their voltage is above {best[1]} mV: {_points(drop)}.")
        facts += ["The config of before is backed up. GPU Manager's Backups page restores it.",
                  "The governor restarts with the new config.", "You'll be asked for your password."]
        answer = QMessageBox.question(self, APP_NAME, "Write the best step into the governor's config?\n\n"
                                      + "\n".join(facts))
        if answer == QMessageBox.StandardButton.Yes:
            self._run("install", ["--install"])

    # -------------------------------------------------------------- session
    def _run(self, job: str, args: list[str]) -> None:
        if self.session.busy:
            return
        self.job = job
        self.errors = []
        self.note = ""
        self._log(f"$ ps5-gpu-sweep.sh {' '.join(args)}")
        try:
            self.session.start(args, block_sleep=job == "test")    # a sweep keeps the board awake until it ends
            self._start_spin()
        except OSError as exc:
            self.job = ""
            self.note = f"Could not start ps5-gpu-sweep.sh: {exc}"
        self._render()

    RUNNING = {"scan": "the scan", "test": "the sweep", "install": "Install", "reset": "deleting the results",
               "report": "the report"}

    def _on_spin(self) -> None:
        """Turns the symbol and counts the seconds while the script runs."""
        busy = self.session.busy
        self.running.setVisible(busy)
        if not busy:
            self._spin.stop()
            return
        self._spin_frame = (self._spin_frame + 1) % 4
        what = self.RUNNING.get(self.job, "the script")
        if self.job == "test" and self.live.get("item"):
            what = f"round {self.live.get('round', '?')}, {_step_name(self.live['item'], self.p.top)}"
        secs = int(time.monotonic() - self._busy_since)
        self.running.setText(f"{'◐◓◑◒'[self._spin_frame]}  Running: {what} · {secs} s")

    def _start_spin(self) -> None:
        self._busy_since = time.monotonic()
        self._spin.start()
        self._on_spin()

    def _log(self, text: str) -> None:
        self.output.appendPlainText(text)

    def _follow(self) -> None:
        """Reads the sweep's files again during a run, so the window shows the step that runs now."""
        self.p = progress.load()
        self.step = self._current_step()
        self.view = -1

    def _on_line(self, text: str) -> None:
        self._log(text)
        if text.startswith("ERROR:"):
            self.errors.append(text[6:].strip())
        if "Sorry, try again" in text:
            self._wrong_password = True

    def _on_notice(self, words: list[str]) -> None:
        name, args = words[0], words[1:]
        if name == "scan" and args:
            if self.scan is None:
                self.scan = {}
            self.scan[args[0]] = " ".join(args[1:])
        elif name == "attempt" and len(args) >= 2:
            self.live = {"round": args[0], "item": args[1]}
            self._follow()
        elif name == "phase" and args:
            self.live["phase"] = args[0]
            self.live.pop("load", None)
        elif name == "load":
            self.live["load"] = " ".join(args)
        elif name in ("result", "plan", "installed"):
            self._follow()
        elif name == "restart-first":
            self.restart_first = True
        elif name == "ask":
            self._answer(args[0] if args else "question")
            return
        self._render()

    def _answer(self, question: str) -> None:
        yes, no = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No
        if question == "start":
            self.session.send("y" if self.job == "test" else "n")      # the window asked before it started
        elif question == "reset":
            self.session.send("y" if self.job == "reset" else "n")
        elif question == "install":
            self.session.send("y" if self.job == "install" else "n")
        elif question == "crash":
            pending = self.p.pending
            what = (f"Round {pending[0]}, {_step_name(pending[1], self.p.top)}" if len(pending) >= 2
                    else "The last attempt")
            answer = QMessageBox.question(
                self, APP_NAME, "Did the board freeze, crash or restart by itself?\n\n"
                f"{what} did not finish.\n"
                "Yes records it as a crash of that step.\n"
                "No means you restarted it by hand. Then the attempt runs again.", yes | no, yes)
            self.session.send("y" if answer == yes else "n")
        else:
            self.session.send("")

    def _on_password(self) -> None:
        message = "Incorrect password, try again." if self._wrong_password else ""
        self._wrong_password = False
        entered = SudoDialog.ask(self, message) if message else SudoDialog.ask(self)
        if entered is None:
            self.session.cancel()
        else:
            self.session.send(entered)

    def _on_finished(self, code: int) -> None:
        job, self.job = self.job, ""
        self._log(f"(exit code {code})")
        self.refresh()
        if code != 0 and job != "report":
            self.note = ("ps5-gpu-sweep.sh stopped: " + self.errors[-1]) if self.errors else (
                f"ps5-gpu-sweep.sh stopped with exit code {code}. Details says why.")
            if job == "scan":
                self.scan = self.scan or None
            self._render()
            if job == "test" and code != 130:       # 130 is Stop, which you pressed yourself
                notify.notify("GPU sweep stopped", self.note)
            return
        if job == "reset":
            self.view = -1
            self.scan = None
            self.refresh()
            return
        if job == "report":
            report = next((line for line in reversed(self.output.toPlainText().splitlines())
                           if line.startswith("Report written to")), "")
            self.note = report.replace("Report written to", "The report is in", 1) if report else ""
            self._render()
            return
        if job == "install":
            self.note = "The best step is in the governor's config, and the governor restarted."
            self._render()
            return
        if job == "test":
            self.live = {}
            part = self._part()
            if (self.restart_first and resume.armed() and not self.paused and part
                    and self.p.next_attempt(part) is not None):
                self._start_countdown("restart", RESTART_SECS)
                return
            if not part or self.p.next_attempt(part) is None:
                resume.disarm()
            self._render()
            self._notify_end()
            return
        self._render()

    def _notify_end(self) -> None:
        """The desktop notification when a part of the sweep has ended. Nothing while attempts are left, so a pause
        or an attempt in between stays quiet."""
        p = self.p
        if not p.started:
            return
        if p.state("control") == "failed":
            bad = next(a for a in p.attempts if a.item == "control" and progress.FAIL_RE.match(a.outcome))
            notify.notify("GPU sweep stopped", f"Your config's top point failed with {bad.outcome}: "
                          f"{OUTCOMES.get(bad.outcome, 'it failed')}. The ladders are not offered.")
        elif self.step == 2 and not p.done("oc"):
            notify.notify("Top point passed", f"All {p.rounds} rounds passed. Next: Raise the clock, in step 3 of the "
                          "GPU sweep.")
        elif self.step == 3 and not p.done("uv"):
            notify.notify("Clock ladder done", "Next: Lower the voltage, in step 4 of the GPU sweep.")
        elif self.step == 4 and not p.installed and not self._kept():
            best = p.best()
            notify.notify("GPU sweep done", f"Best step: {_point(best)}. Next: Install, in step 5 of the GPU sweep."
                          if best else "Nothing better than your top point passed. Next: step 5 of the GPU sweep.")
