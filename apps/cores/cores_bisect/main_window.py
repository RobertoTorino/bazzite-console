# SPDX-License-Identifier: GPL-3.0-or-later

"""The one window of Core Unlock (owner, 24-11-2026: clear steps, a notification at the end, the window back after
each restart with the next step, as CU Unlock). It runs ps5-cores-bisect.sh itself (session.py) and leads through
five steps:

  1. Scan: reads the presence mask, the cores and what a test needs (--scan). Writes nothing.
  2. Test the stock cores: the control's rounds on the stock 6 cores. When it fails, the window stops here.
  3. Unlock and restart: the script's core unlock (one SMU write), then a warm restart that brings the new cores up.
     A full power off undoes it, so the step offers the unlock again when the new cores are gone.
  4. Test the new cores: post-control, each new core alone and both together.
  5. Install: ps5-cores-unlock.sh --install (runner.py), the boot service that keeps all 8 cores on. The cores are
     on already, so nothing waits for a restart. Or stay at 6 cores, which a full power off brings back.

Where the test stands is read from the script's own files every time (progress.py), and the cores online from sysfs,
so the window picks up where it was after a restart. While a test restarts the board, and after the unlock's restart,
the window opens again after each login (resume.py).

The layout is CU Unlock's (owner, 24-11-2026): the suite's header, the icon spanning the title with the version and a
row of status boxes, the filled info symbol and the round refresh symbol at the right end of the title row. Then the
five steps as rows, each with what came out of it or what to do now, and the button of the current step on its row;
a green bar over them when everything is done. Then a few short lines; the core map; one row with the other actions as
pills, the hint and what comes next, and the Details (the script's output) and Advanced (load, rounds, load tool,
Same boot, Hardware log) pills at its right end (owner, 24-11-2026)."""

from __future__ import annotations

import time

from PyQt6.QtCore import QByteArray, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QScrollArea,
    QSpinBox, QVBoxLayout, QWidget,
)

from . import APP_NAME, LOGO_PATH, __version__, notify, progress, resume
from .core_map import LEGEND, CoreMap
from .gate import check as gate_check
from .options import (
    DEFAULT_LOAD_TOOL, DEFAULT_ROUNDS, DEFAULT_TIME_SECS, LOAD_TIPS, LOAD_TOOLS, MAX_ROUNDS, MIN_ROUNDS, MIN_TIME_SECS,
    BisectOptions,
)
from .runner import UnlockRunner
from .session import ScriptSession
from .theme import ACCENT, BLUE, GREEN, GREY, ORANGE, RED, header_font, muted, surface_style
from .widgets import HelpDialog, InfoButton, MetricBox, Pill, RefreshButton, SudoDialog, TogglePill, same_width

TASKBAR = 80                            # the room kept free under the window, for a taskbar
WIDTH = 900                             # as CU Unlock: it opens this wide, and is never narrower
STEPS = ("Scan", "Test the stock cores", "Unlock and restart", "Test the new cores", "Install")
RESTART_SECS = 15                       # the countdown before the window restarts the board
GO_ON_SECS = 20                         # the countdown after a login before the next attempt
ALL_CORES = len(progress.CORES)

ABOUT = ("Core Unlock finds out whether the 2 switched-off CPU cores of your board are healthy. Then it keeps them "
         "on.<br><br>The steps:<br>1. The scan reads which cores are on now.<br>2. The 6 stock cores run a load, as "
         "a check of the board itself.<br>3. The unlock turns on all 8 cores, and the board restarts.<br>4. Each new "
         "core runs the load on its own, then both together.<br>5. Install keeps all 8 cores on at every boot.<br>"
         "<br><a href='https://robertotorino.github.io/bazzite-console/apps/cores/'>Core Unlock in the wiki</a>")

OUTCOMES = {
    "PASS": "passed",
    "CRASH-LOAD": "the system went down under load",
    "MCE": "the kernel logged machine-check errors",
    "VERIFY-FAIL": "stress-ng found wrong results",
    "LOAD-FAIL": "the load tool stopped early",
    "OFFLINE": "the cores' threads were offline",
    "MPRIME-FAIL": "mprime found wrong results",
    "RAS-ERROR": "rasdaemon recorded hardware errors",
}


def _minutes(attempts: int, secs: int, same_boot: bool, load_tool: str = DEFAULT_LOAD_TOOL) -> str:
    load = secs * (2 if load_tool == "both" else 1)
    total = attempts * (load + 20 + (30 if same_boot else 90)) // 60       # 30 s cool-down or a restart
    total = max(5, round(total / 5) * 5)
    if total < 60:
        return f"about {total} minutes"
    hours, minutes = divmod(total, 60)
    return f"about {hours} h {minutes} min" if minutes else f"about {hours} h"


def _cores(ids: list[int]) -> str:
    """"core 3", "cores 3 and 7", "cores 1, 3 and 7"; "the new cores" while they are not known, as when all 8 are on
    without results."""
    if not ids:
        return "the new cores"
    if len(ids) == 1:
        return f"core {ids[0]}"
    return "cores " + ", ".join(map(str, ids[:-1])) + f" and {ids[-1]}"


class StepRow(QFrame):
    """One step as a row (as CU Unlock's): a mark, "Step N · name" with its state, one line with what came out of it or
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


class MainWindow(QWidget):
    def __init__(self, script: str, unlock_script: str, resume_run: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.script = script
        self.unlock_script = unlock_script
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.session = ScriptSession(script, self)
        self.session.line.connect(self._on_line)
        self.session.notice.connect(self._on_notice)
        self.session.password.connect(self._on_password)
        self.session.finished.connect(self._on_finished)
        self.unlock = UnlockRunner(unlock_script, self)
        self.unlock.line.connect(self._log)
        self.unlock.auth_failed.connect(lambda: setattr(self, "_auth_failed", True))
        self.unlock.finished.connect(self._on_unlock_finished)

        self.scan: dict[str, str] | None = None     # the last scan's results in this window
        self.job = ""                                # what the session runs: scan, test, unlock, reset, report
        self.live: dict[str, str] = {}               # the attempt that runs now: round, item, phase, load
        self.errors: list[str] = []                  # the script's ERROR lines of the last job
        self.warnings: list[str] = []                # the lines under "Before you start"
        self._in_warnings = False
        self._wrong_password = False
        self._auth_failed = False
        self._unlock_action = ""
        self._unlock_args: list[str] = []
        self.restart_first = False                   # the script said an attempt ran in this boot already
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
        self.core_map = CoreMap()
        root.addWidget(self.core_map)
        self.legend = QLabel(LEGEND)
        self.legend.setStyleSheet(f"font-size:12px; color:{muted()};")
        root.addWidget(self.legend)
        # The step's pills on the left, what comes next and the hint beside them, and Details and Advanced at the
        # right end (owner, 24-11-2026: no "Other actions" label, and pills instead of the two buttons).
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
        self.output.setPlaceholderText("What ps5-cores-bisect.sh and ps5-cores-unlock.sh print appears here.")
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
        self.info = InfoButton(ABOUT, "What Core Unlock does")
        self.info.setStyleSheet(
            f"QToolButton {{ border:none; border-radius:{InfoButton.SIZE // 2}px; background:{ACCENT}; color:white; "
            "font-weight:800; font-family:Georgia, serif; font-style:italic; padding:0; }")
        title_row.addWidget(self.info)
        self.refresh_button = RefreshButton("Reads the test's results, the cores and the boot unlock again")
        self.refresh_button.clicked.connect(self.refresh)
        title_row.addWidget(self.refresh_button)
        right.addLayout(title_row)
        boxes = QHBoxLayout()
        boxes.setSpacing(8)
        self.cores_box = MetricBox("Cores on now", GREY)
        self.boot_box = MetricBox("Boot unlock", GREY)
        self.count_box = MetricBox("Attempts done", GREY)
        self.state_box = MetricBox("Test", GREY)
        self.boxes = [self.cores_box, self.boot_box, self.count_box, self.state_box]
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
        self.details_button = Pill("Details", "Show", "Shows or hides what the scripts print.", GREY)
        self.details_button.clicked.connect(lambda: self.show_details(self.output.isHidden()))
        self.advanced_button = Pill("Advanced", "Show", "Load time, rounds, the load tool and how the test restarts.",
                                    GREY)
        self.advanced_button.clicked.connect(lambda: self.show_advanced(self.advanced.isHidden()))
        row.addWidget(self.details_button)
        row.addWidget(self.advanced_button)
        same_width([self.details_button, self.advanced_button])
        return row

    def _build_advanced(self) -> QWidget:
        """Load per attempt, Rounds per item and Load tool on one line, Same boot and Hardware log under them."""
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.setContentsMargins(0, 0, 0, 0)
        settings = QSettings()
        row = QHBoxLayout()
        row.setSpacing(8)
        self.time_spin = QSpinBox()
        self.time_spin.setRange(MIN_TIME_SECS, 36000)
        self.time_spin.setSingleStep(60)
        self.time_spin.setSuffix(" s")
        self.time_spin.setValue(int(settings.value("advanced/time", DEFAULT_TIME_SECS)))
        self.time_spin.setToolTip(f"How long the load runs in each attempt (-t). At least {MIN_TIME_SECS} s, "
                                  f"{DEFAULT_TIME_SECS} s by default.")
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(MIN_ROUNDS, MAX_ROUNDS)
        self.rounds_spin.setValue(int(settings.value("advanced/rounds", DEFAULT_ROUNDS)))
        self.rounds_spin.setToolTip("Attempts per item (-r), interleaved so heat and the time of day favor none.")
        self.load_combo = QComboBox()
        self.load_combo.addItems(LOAD_TOOLS)
        for index, tool in enumerate(LOAD_TOOLS):
            self.load_combo.setItemData(index, LOAD_TIPS[tool], Qt.ItemDataRole.ToolTipRole)
        self.load_combo.setCurrentText(str(settings.value("advanced/load_tool", DEFAULT_LOAD_TOOL)))
        self.load_combo.setToolTip("The load tool (--load). " + " ".join(LOAD_TIPS.values()))
        for caption, field in (("Load per attempt", self.time_spin), ("Rounds per item", self.rounds_spin),
                               ("Load tool", self.load_combo)):
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
        switches.setSpacing(8)
        # On by default, as CU Unlock (owner, 23-11-2026): one password and no restarts.
        self.same_boot_pill = TogglePill("Same boot", "--same-boot: no restart between attempts, one password, and "
                                         "you can leave it running. Turn it off to give each attempt a boot of its "
                                         "own. A warm restart keeps the unlock.",
                                         settings.value("advanced/same_boot", "true") == "true")
        self.ras_pill = TogglePill("Hardware log", "--rasdaemon: also count hardware errors with ras-mc-ctl. It "
                                   "needs rasdaemon.", settings.value("advanced/rasdaemon", "false") == "true")
        for pill in (self.same_boot_pill, self.ras_pill):
            switches.addWidget(pill)
        same_width([self.same_boot_pill, self.ras_pill])
        switches.addStretch(1)
        box.addLayout(switches)
        for signal in (self.time_spin.valueChanged, self.rounds_spin.valueChanged, self.load_combo.currentTextChanged,
                       self.same_boot_pill.toggled, self.ras_pill.toggled):
            signal.connect(self._save_advanced)
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
        # As wide as the map's rows need, and as high as the page once it shows: before that, the page doesn't
        # know its height yet, and a first window cut half of it off (owner, 24-11-2026).
        self.resize(WIDTH, min(self.height(), self._room()))
        QTimer.singleShot(0, self._fit)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.session.busy and self.job == "test":
            answer = QMessageBox.question(self, APP_NAME, "An attempt is still running. Close anyway?\n\n"
                                          "The attempt stops and runs again later.")
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
        settings.setValue("advanced/time", self.time_spin.value())
        settings.setValue("advanced/rounds", self.rounds_spin.value())
        settings.setValue("advanced/load_tool", self.load_combo.currentText())
        settings.setValue("advanced/same_boot", "true" if self.same_boot_pill.isChecked() else "false")
        settings.setValue("advanced/rasdaemon", "true" if self.ras_pill.isChecked() else "false")

    def _take_run_settings(self) -> None:
        """A test that has started keeps its own load, rounds and load tool: the fields show them, so going on
        doesn't change them. The script asks first when you change them during a run."""
        p = self.p
        if not p.started or self.session.busy:
            return
        for field, value in ((self.time_spin, p.time_secs), (self.rounds_spin, p.rounds)):
            field.setValue(value)
        self.load_combo.setCurrentText(p.load_tool if p.load_tool in LOAD_TOOLS else DEFAULT_LOAD_TOOL)
        self.ras_pill.setChecked(p.ras)

    def options(self) -> BisectOptions:
        return BisectOptions(time_secs=self.time_spin.value(), rounds=self.rounds_spin.value(),
                             same_boot=self.same_boot_pill.isChecked(), load_tool=self.load_combo.currentText(),
                             rasdaemon=self.ras_pill.isChecked())

    # ---------------------------------------------------------------- state
    def refresh(self) -> None:
        """Reads the test's files, the cores online and the boot unlock again, and shows the step."""
        self.p = progress.load()
        self.wizard = progress.read_wizard()
        self.installed = progress.unlock_installed()
        self.online = progress.online_cores()
        self._take_run_settings()
        self.step = self._current_step()
        self._render()

    def _base(self) -> list[int]:
        """The stock cores: the run's, or the cores online now while fewer than all are."""
        if self.p.base_cores:
            return self.p.base_cores
        return self.online if 0 < len(self.online) < ALL_CORES else []

    def _new(self) -> list[int]:
        """The cores the unlock adds: the run's, or the ones missing from the stock cores."""
        if self.p.new_cores:
            return self.p.new_cores
        base = self._base()
        return [c for c in progress.CORES if c not in base] if base else []

    @property
    def unlocked(self) -> bool:
        """More cores are online now than the stock ones: the unlock is on in this boot."""
        base = self._base()
        return bool(base) and len(self.online) > len(base)

    def _stock(self) -> bool:
        return self.wizard.get("phase", "") == "stock"

    def _current_step(self) -> int:
        p = self.p
        if self._stock() or self.installed:
            return 4
        if not p.started:
            return 0
        if p.phase == "control":
            return 1 if p.control != "passed" else 2
        if p.phase == "unlock-pending":
            return 3 if self.unlocked else 2
        return 3 if p.next_attempt() else 4

    def _show_step(self, index: int) -> None:
        if index <= self.step:
            self.view = -1 if index == self.step else index
            self._render()

    def _map(self) -> list[str]:
        """The state of each of the 8 cores: on, not tested, testing, healthy, fails or random."""
        base, new = self._base(), self._new()
        if not base:
            return ["on" if c in self.online else "unknown" for c in progress.CORES]
        current = self.live.get("item", "") if self.job == "test" else ""
        states = []
        for core in progress.CORES:
            if core in new:
                if current in (f"core{core}", "combined"):
                    states.append("now")
                else:
                    states.append({"good": "ok", "bad": "bad", "random": "random"}.get(
                        self.p.verdict(f"core{core}"), "wait"))
            elif current == "post-control" and core == base[0]:
                states.append("now")
            elif current == "control" and core in base:
                states.append("now")
            else:
                states.append("on" if core in base else "unknown")
        return states

    # --------------------------------------------------------------- render
    def _finished(self) -> bool:
        """Nothing is left to do: all 8 cores are installed and on, or you stay at the stock cores and they are."""
        if self.step != 4:
            return False
        if self._stock():
            return not self.unlocked
        return self.installed and len(self.online) == ALL_CORES

    def _summary(self, index: int, state: str) -> str:
        """The line on a step's row that is not the current one: what came out of it, or what it will do."""
        if state == "later":
            return ("Reads which cores are on now. It writes nothing.",
                    "Runs a load on the stock cores, as a check of the board itself.",
                    "Turns on all 8 cores. Then the board restarts.",
                    "Runs the load on each new core, then on both together.",
                    "Keeps all 8 cores on at every boot.")[index]
        p = self.p
        base, new = self._base(), self._new()
        if index == 0:
            if base:
                return f"{len(base)} of {ALL_CORES} cores were on. {_cores(new).capitalize()} were switched off."
            return "The board was read."
        if index == 1:
            return f"Passed {p.rounds} of {p.rounds} rounds on the {len(base)} stock cores."
        if index == 2:
            if self._stock() and p.phase == "control":
                return "You chose to stay at the stock cores."
            return f"{_cores(new).capitalize()} came on with the unlock."
        if index == 3:
            if self._stock() and p.phase != "bisect":
                return "You chose to stay at the stock cores."
            bad = [it for it in p.items if p.verdict(it) == "bad"]
            random = [it for it in p.items if p.verdict(it) == "random"]
            if not bad and not random:
                return f"{_cores(new).capitalize()} passed, alone and together."
            parts = []
            if bad:
                parts.append(f"Failed every time: {', '.join(bad)}.")
            if random:
                parts.append(f"Failed at random: {', '.join(random)}.")
            return " ".join(parts)
        if self._stock():
            return "You chose to stay at the stock cores."
        return f"All {ALL_CORES} cores turn on at every boot."

    def _render(self) -> None:
        view = self.step if self.view < 0 else self.view
        finished = self._finished()
        for index, box in enumerate(self.step_boxes):
            if index == self.step:
                stopped = index == 1 and self.p.control == "failed"
                running = self.session.busy or self.unlock.busy or bool(self.countdown)
                state = "done" if finished else "stopped" if stopped else "running" if running else "now"
            else:
                state = "done" if index < self.step else "later"
            box.set_state(state, self._summary(index, state) if state in ("done", "later") else "",
                          selected=index == view != self.step)
            box.setEnabled(index <= self.step)
        if finished:
            self.finished_bar.setText(
                "✔  Finished. Your board stays at the stock cores. There is nothing left to do." if self._stock()
                else f"✔  Finished. Your board runs all {ALL_CORES} cores at every boot. There is nothing left to "
                     "do.")
        self.finished_bar.setVisible(finished)
        self._render_boxes()
        page = (self._page_scan, self._page_control, self._page_unlock, self._page_cores, self._page_install)[view]
        heading, lines, actions, hint, nxt = page()
        if self.countdown:
            what = "Restarting" if self.countdown_action == "restart" else "Going on"
            actions = [("Restart now" if self.countdown_action == "restart" else "Go on now",
                        "Don't wait", "", ACCENT, self._countdown_now),
                       ("Pause", "Stop here", "Stops the countdown. Go on later.", GREY, self._pause)]
            nxt = f"{what} in {self.countdown} s."
        elif self.session.busy and self.job == "test":
            actions = [("Stop", "Stop this attempt", "Stops the attempt as Ctrl+C does. It runs again later.", RED,
                        self.session.stop)]
        elif self.session.busy or self.unlock.busy:
            actions = [(a[0], a[1], a[2], a[3], a[4], False) for a in actions]
        todo, primary = self._todo(view, actions)
        if not finished:
            self.todo.setText(todo if view == self.step else "Click this row to go back to this step.")
        self.heading.setText(f"Step {view + 1} · {heading}")
        self.text.setText("<br>".join(lines))
        self.text.setVisible(bool(lines))
        self.core_map.set_states(self._map())
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
            return "Nothing to do. The test runs by itself, and a notification tells you when it ends.", ""
        if self.session.busy:
            return "Wait a moment, until the line beside the pills is gone.", ""
        if self.unlock.busy:
            return "Wait a moment. Type your password when you're asked.", ""
        enabled = [a[0] for a in actions if (a[5] if len(a) > 5 else True)]
        if view != self.step:
            return "This step is done. Click the step that says Do this now to go on.", ""
        words = {
            "Scan": "Click <b>Scan</b>. Type your password when you're asked.",
            "Start test": "Click <b>Start test</b>. A question opens. Answer <b>Yes</b>.",
            "Unlock": "Click <b>Unlock</b>. A question opens. Answer <b>Yes</b>. Then the board restarts.",
            "Start": (f"Click <b>Start</b>. The test of {_cores(self._new())} takes "
                      f"{self._estimate(self._cores_total())}."),
            "Go on": "Click <b>Go on</b> to run the next attempt.",
            "Restart": "Click <b>Restart</b>. After the login, the window opens again by itself.",
            "Install": "Every new core passed. Click <b>Install</b> and type your password.",
        }
        for value in ("Start test", "Scan", "Unlock", "Start", "Go on", "Restart", "Install"):
            if value in enabled:
                return words[value], value
        if "Stay at 6" in enabled:
            return "The test stopped. Click <b>Stay at 6</b>, or <b>Start over</b> to test again.", "Stay at 6"
        if "Scan again" in enabled:
            return "Fix what the text above names, then click <b>Scan again</b>.", "Scan again"
        if self._stock() and self.unlocked:
            return "Switch the board fully off once, then on. That puts back the stock cores.", ""
        if self._stock():
            return "Done. Your board stays at the stock cores.", ""
        if self.installed and len(self.online) == ALL_CORES:
            return "Done. All 8 cores are on at every boot.", ""
        return "Nothing to do in this step yet.", ""

    def _cores_total(self) -> int:
        """The attempts of the new cores' test: a stock core, each new core alone and both together."""
        new = self._new()
        return self.options().rounds * (1 + len(new) + (1 if len(new) > 1 else 0))

    def _estimate(self, attempts: int) -> str:
        opts = self.options()
        return _minutes(attempts, opts.time_secs, opts.same_boot, opts.load_tool)

    def _render_boxes(self) -> None:
        on = len(self.online)
        if on:
            self.cores_box.set_value(f"{on} of {ALL_CORES}", f"Cores online now: {' '.join(map(str, self.online))}")
            self.cores_box.set_colour(GREEN if on == ALL_CORES else BLUE)
        else:
            self.cores_box.set_value("—", "The cores could not be read.")
            self.cores_box.set_colour(GREY)
        if self.installed:
            self.boot_box.set_value("Installed", "ps5-cores-unlock.service turns all 8 cores on at every boot.")
            self.boot_box.set_colour(GREEN)
        else:
            self.boot_box.set_value("Not installed", "A full power off turns the new cores off.")
            self.boot_box.set_colour(GREY)
        if self.p.phase == "unlock-pending" and self.unlocked:
            self.count_box.set_value(f"0 of {self._cores_total()}", "The new cores' test has not started yet.")
            self.count_box.set_colour(BLUE)
        elif self.p.started:
            self.count_box.set_value(f"{self.p.done()} of {self.p.total()}",
                                     "Attempts done of the test that runs now: the stock cores, then the new ones.")
            self.count_box.set_colour(BLUE)
        else:
            self.count_box.set_value("—", "No test has started yet.")
            self.count_box.set_colour(GREY)
        if self.session.busy and self.job == "test":
            state, colour = "Testing", ACCENT
        elif self.countdown:
            state, colour = ("Restart" if self.countdown_action == "restart" else "Going on"), ACCENT
        elif self.p.control == "failed":
            state, colour = "Stopped", RED
        elif self.p.finished or self._stock():
            state, colour = "Done", GREEN
        elif self.p.started and resume.armed():
            state, colour = "Running", BLUE
        elif self.p.started and self.step == 2:
            state, colour = "Ready", ACCENT
        elif self.p.started and self.step == 3 and self.p.phase == "unlock-pending":
            state, colour = "Ready", ACCENT
        elif self.p.started:
            state, colour = "Paused", GREY
        else:
            state, colour = "Not started", GREY
        self.state_box.set_value(state, "Where the core test stands.")
        self.state_box.set_colour(colour)

    def _live_hint(self) -> str:
        if self.job != "test" or not self.live:
            return ""
        parts = [f"Now: round {self.live.get('round', '?')}, {self.live.get('item', '?')}"]
        if "load" in self.live:
            secs, total, temp, clock = (self.live["load"].split() + ["?"] * 4)[:4]
            parts += [f"{self.live.get('phase', 'load')} {secs} of {total} s", f"{temp} °C", f"{clock} MHz"]
        return " · ".join(parts)

    def _restart_needed(self) -> bool:
        return self.restart_first or (self.p.this_boot_used and not self.same_boot_pill.isChecked())

    def _go_on_actions(self, label: str) -> list[tuple]:
        """Go on, or Restart when an attempt ran in this boot already, with Pause, Report and Start over."""
        if self._restart_needed():
            first = ("Restart", "Then go on", "Restarts the board. The window opens again after the login and "
                     "goes on.", ACCENT, self._restart_and_go_on)
        else:
            first = ("Go on", label, "Runs the next attempt in this window.", ACCENT, self._go_on)
        actions = [first]
        if resume.armed():
            actions.append(("Pause", "Stop after this", "The window no longer opens and goes on after a login.",
                            GREY, self._pause))
        actions += [self._report_action(), self._start_over_action()]
        return actions

    def _report_action(self) -> tuple:
        return ("Report", "Save as a text file", "Writes the results so far to a text file on your Desktop.", BLUE,
                self._report)

    def _start_over_action(self) -> tuple:
        return ("Start over", "Delete results", "Asks first. Then deletes the test's results and logs.", RED,
                self._start_over)

    def _stay_action(self) -> tuple:
        return ("Stay at 6", "Keep the stock cores", "Ends the test here. Nothing is installed.", GREEN,
                self._stay_stock)

    # ---------------------------------------------------------------- pages
    def _page_scan(self) -> tuple:
        help_pill = ("Help", "How the test works", "The script's own help, as a page.", BLUE,
                     lambda: HelpDialog(self.script, self).exec())
        if self.job == "scan" and self.session.busy:
            return ("Scan", ["The scan reads the core presence mask and the cores.", "It writes nothing."],
                    [("Scan", "Reading...", "", ACCENT, self._scan, False), help_pill], "Reading the board...", "")
        if not self.scan:
            lines = ["The scan reads which cores your board runs now.", "It writes nothing.",
                     "You'll be asked for your password."]
            return ("Scan", lines, [("Scan", "Read the board", "Reads the core presence mask (--scan). Writes "
                                     "nothing.", ACCENT, self._scan), help_pill],
                    "", "Next: the scan, then the test of the stock cores.")
        mask = self.scan.get("mask", "?")
        cores = progress.ids(self.scan.get("cores", ""))
        off = [c for c in progress.CORES if c not in cores]
        opts = self.options()
        lines = [f"{len(cores)} of {ALL_CORES} cores are on." + (f" {_cores(off).capitalize()} are switched off."
                                                                  if off else ""),
                 f"The core presence mask is <b>{mask}</b>."]
        blockers = []
        if mask == "0xff":
            blockers.append("All 8 cores are on already, so an unlock is active. Switch the board fully off once, "
                            "then scan again.")
        elif mask != "0x77":
            blockers.append(f"The mask is not the usual 0x77. Your switched-off cores are very likely defective. "
                            "The test can't run.")
        tool = self.load_combo.currentText()
        if tool in ("stress-ng", "both") and self.scan.get("stress-ng", "-") == "-":
            blockers.append("stress-ng was not found. Install it, then scan again.")
        if blockers:
            lines += blockers
        else:
            control = opts.rounds
            later = opts.rounds * (1 + len(off) + (1 if len(off) > 1 else 0))     # before the run knows its cores
            lines.append(f"The stock cores run {control} rounds first, {self._estimate(control)}.")
            lines.append(f"After the unlock, the new cores run {later} attempts, {self._estimate(later)}.")
        hint = " · ".join([f"Load tool: {tool}", f"Load per attempt: {opts.time_secs} s",
                           f"Boot unlock: {'on' if self.installed else 'off'}"])
        start = ("Start test", "Go to step 2", "Asks first. Then tests the stock cores.", ACCENT, self._start_test,
                 not blockers and not self.p.started)
        return ("Scan", lines, [start, ("Scan again", "Read the board", "Reads the board again. Writes nothing.",
                                        BLUE, self._scan), help_pill], hint,
                "" if blockers else f"Next: the stock cores, {opts.rounds} rounds.")

    def _page_control(self) -> tuple:
        p = self.p
        rounds = p.rounds
        about = [f"The {len(self._base())} stock cores run a load together. Nothing is unlocked yet.",
                 "If this fails, the board, its power or its heat is at fault, not the new cores."]
        if p.control == "failed":
            bad = next(a for a in p.attempts if a.item == "control" and progress.FAIL_RE.match(a.outcome))
            lines = [about[0], f"Round {bad.round} ended with {bad.outcome}: {OUTCOMES.get(bad.outcome, 'it failed')}.",
                     "So the board itself is not stable. The unlock is not offered."]
            actions = [self._stay_action(), self._start_over_action(),
                       ("Details", "What the script saw", "Shows the script's results.", GREY, self._report)]
            return ("Test the stock cores", lines, actions, "Nothing changed on the board.",
                    "Advice: stay at 6 cores, and check power and cooling.")
        if self.session.busy and self.job == "test":
            return (f"Test the stock cores, round {self.live.get('round', '?')} of {rounds}", about, [],
                    self._live_hint(), "")
        nxt = p.next_attempt("control")
        if p.control == "passed":
            return ("Test the stock cores", [about[0], f"All {rounds} rounds passed."], [], "", "")
        if not p.started or nxt is None:
            return ("Test the stock cores", about, [], "", "")
        return ("Test the stock cores", [*about, f"{p.done('control')} of {rounds} rounds are done."],
                self._go_on_actions("Run the next round"), "", f"Next: round {nxt[0]} of the stock cores.")

    def _unlock_boot(self) -> bool:
        """The unlock was written in this boot, so a warm restart brings the new cores up."""
        return self.wizard.get("unlock_boot", "") == progress.boot_id()

    def _page_unlock(self) -> tuple:
        p = self.p
        new = self._new()
        if self.view >= 0 and self.step > 2:
            return ("Unlock and restart", [f"{_cores(new).capitalize()} came on with the unlock."], [], "", "")
        if self.job == "unlock" and self.session.busy:
            return ("Unlock and restart", ["Writing the unlock..."], [], "", "")
        others = [self._stay_action(), self._start_over_action()]
        if p.phase == "unlock-pending" and self._unlock_boot():
            lines = ["The unlock is written. A restart brings up the new cores.",
                     "Restart, don't switch off. A full power off undoes the unlock."]
            return ("Unlock and restart", lines,
                    [("Restart", "Bring up the cores", "Restarts the board. The window opens again after the login.",
                      ACCENT, self._restart_after_unlock), *others],
                    "Save your work in other apps first.", "Next: the test of the new cores.")
        if p.phase == "unlock-pending":
            lines = ["The new cores did not come up after the restart.",
                     "A full power off undoes the unlock. Unlock again, then the board restarts."]
        else:
            lines = [f"The stock cores passed all {p.rounds} rounds.",
                     f"The unlock turns on all {ALL_CORES} cores. That is one write, then a restart.",
                     "Until you install it in step 5, a full power off turns the new cores off again."]
        return ("Unlock and restart", lines,
                [("Unlock", "Then restart", "Asks first. Then writes the unlock and restarts the board.", ACCENT,
                  self._unlock), *others],
                "You'll be asked for your password.", "Next: the restart, then the test of the new cores.")

    def _page_cores(self) -> tuple:
        p = self.p
        new = self._new()
        lines = [f"{_cores(new).capitalize()} each run the load on their own, {p.rounds} rounds each.",
                 "Then they run it together. A stock core runs it too, for comparison."]
        if self.view >= 0 and self.step > 3:
            return ("Test the new cores", lines[:1], [], "", "")
        if self.session.busy and self.job == "test":
            return (f"Test the new cores, round {self.live.get('round', '?')} of {p.rounds}", lines, [],
                    self._live_hint(), "")
        if not self.unlocked:
            # A full power off undid the unlock in the middle of the test.
            return ("Test the new cores", ["The new cores are off. A full power off undoes the unlock.",
                                           "Unlock again. Then the board restarts, and the test goes on."],
                    [("Unlock", "Then restart", "Writes the unlock again and restarts the board.", ACCENT,
                      self._unlock_again), self._report_action(), self._start_over_action()],
                    "You'll be asked for your password.", "")
        if p.phase == "unlock-pending":
            total = self._cores_total()
            return ("Test the new cores", [f"{_cores(new).capitalize()} are on since the last restart.", *lines],
                    [("Start", "Test the new cores", "Asks first. Then runs the test in this window.", ACCENT,
                      self._start_cores), self._start_over_action()],
                    f"{total} attempts. A bad core can freeze the board.", "Next: Install, in step 5.")
        nxt = p.next_attempt()
        if nxt is None:
            return ("Test the new cores", lines[:1], [], "", "")
        left = p.total() - p.done()
        return ("Test the new cores", lines, self._go_on_actions("Run the next attempt"),
                f"{left} attempts left, {self._estimate(left)}.", f"Next: round {nxt[0]}, {nxt[1]}.")

    def _page_install(self) -> tuple:
        uninstall = ("Uninstall", "Back to 6 cores", "Removes the boot service. The stock cores come back after the "
                     "next full power off.", RED, self._uninstall, self.installed)
        if self._stock():
            lines = ["You chose to stay at the stock cores. Nothing is installed."]
            if self.unlocked:
                lines.append("The new cores are still on in this boot. A full power off turns them off.")
            return ("Install", lines, [self._start_over_action()], "", "")
        if self.installed:
            if len(self.online) == ALL_CORES:
                return ("Install", ["The boot service keeps all 8 cores on, also after a full power off.",
                                    "To go back to 6 cores, click Uninstall. Then switch the board fully off once."],
                        [uninstall, self._start_over_action()], "", "")
            if self.wizard.get("install_boot", "") == progress.boot_id():
                return ("Install", ["The boot service is installed. A restart brings up the new cores."],
                        [("Restart", "Bring up the cores", "Restarts the board.", ACCENT, self._restart_only),
                         uninstall], "Save your work in other apps first.", "")
            return ("Install", ["The boot service is installed, but not all 8 cores are on.",
                                "Root status shows what the service did at this boot."],
                    [("Root status", "What the service did", "Runs ps5-cores-unlock.sh --status.", BLUE,
                      self._root_status), uninstall], "", "")
        gate = gate_check(progress.state_dir())
        if gate.accepted:
            lines = ["Every new core passed, alone and together.",
                     "Install keeps all 8 cores on at every boot, also after a full power off."]
            return ("Install", lines,
                    [("Install", "All 8 cores at every boot", "Asks first. Then installs the boot service.", ACCENT,
                      self._install), self._stay_action(), self._report_action(), self._start_over_action()],
                    "Install asks for your password.", "")
        bad = [it for it in self.p.items if self.p.verdict(it) == "bad"]
        random = [it for it in self.p.items if self.p.verdict(it) == "random"]
        lines = []
        if bad:
            lines.append(f"Failed every time: {', '.join(bad)}. That points to a bad core.")
        if random:
            lines.append(f"Failed at random: {', '.join(random)}. That points to power, heat or the unlock itself.")
        lines.append("The unlock turns on all cores or none. So don't keep it.")
        if self.unlocked:
            lines.append("Click Stay at 6. Then switch the board fully off once.")
        return ("Install", lines, [self._stay_action(), self._report_action(), self._start_over_action()],
                "\n".join(gate.reasons[:2]), "Advice: stay at 6 cores.")

    # -------------------------------------------------------------- actions
    def _scan(self) -> None:
        self.scan = None
        self._run("scan", ["--scan"])

    def _start_test(self) -> None:
        opts = self.options()
        errors = opts.validate()
        if errors:
            QMessageBox.warning(self, APP_NAME, "\n".join(errors))
            return
        if opts.same_boot:
            how = (f"All {opts.rounds} rounds run in this boot, without a restart. That takes "
                   f"{self._estimate(opts.rounds)}.")
            password = "You'll be asked for your password once."
        else:
            how = (f"After each round, the board restarts by itself. That is {opts.rounds} restarts.\n"
                   "This window opens again after each login and goes on.")
            password = "You'll be asked for your password after each restart."
        answer = QMessageBox.question(
            self, APP_NAME,
            "Test the stock cores?\n\n"
            "The stock cores run a CPU load. Nothing is unlocked yet.\n"
            f"{how}\n"
            "After a freeze, turn the board off and on, and open the window. It asks what happened.\n"
            f"{password}")
        if answer != QMessageBox.StandardButton.Yes:
            return
        progress.forget()
        self.paused = False
        if not opts.same_boot:
            resume.arm(self.script, self.unlock_script)
        self._run_test()

    def _start_cores(self) -> None:
        new = self._new()
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Test {_cores(new)}?\n\n"
            "Each new core runs the load on its own, then both together.\n"
            "A bad core can freeze the board. Save your work in other apps first.\n"
            "After a freeze, switch the board off and on, and open the window. It turns the cores on again.\n"
            "You'll be asked for your password.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._go_on()

    def _test_args(self) -> list[str]:
        return self.options().to_args()

    def _run_test(self) -> None:
        self.restart_first = False
        self.live = {}
        self._run("test", self._test_args())

    def _go_on(self) -> None:
        if not self.same_boot_pill.isChecked():
            resume.arm(self.script, self.unlock_script)
        self.paused = False
        self._run_test()

    def _restart_and_go_on(self) -> None:
        resume.arm(self.script, self.unlock_script)
        self._restart_only()

    def _unlock(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Turn on all {ALL_CORES} cores?\n\n"
            "One write turns on the switched-off cores.\n"
            f"Then the board restarts by itself, {RESTART_SECS} s later. Save your work in other apps first.\n"
            "This window opens again after the login.\n"
            "A full power off turns the new cores off again.\n"
            "You'll be asked for your password.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.paused = False
        self._run("unlock", self._test_args())

    def _unlock_again(self) -> None:
        """The cores went off in the middle of the test: ps5-cores-unlock.sh --apply, then the restart."""
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Turn on all {ALL_CORES} cores again?\n\n"
            "One write turns on the new cores again.\n"
            f"Then the board restarts by itself, {RESTART_SECS} s later. Save your work in other apps first.\n"
            "This window opens again after the login, and the test goes on.\n"
            "You'll be asked for your password, unless sudo still has it.")
        if answer == QMessageBox.StandardButton.Yes:
            self._run_unlock(["--apply"], "apply")

    def _restart_after_unlock(self) -> None:
        resume.arm(self.script, self.unlock_script)
        self._restart_only()

    def _restart_only(self) -> None:
        if not resume.restart():
            self.note = "The window could not restart the board. Restart it by hand."
            self._render()

    def _resume(self) -> None:
        """Opened after a login by the autostart entry: a countdown and the next attempt, or the next step."""
        self.refresh()
        if not resume.armed():
            return
        p = self.p
        work = (p.started and p.control != "failed" and p.phase in ("control", "bisect") and self.step in (1, 3)
                and (p.phase == "control" or self.unlocked) and (p.next_attempt() is not None or p.crashed))
        if not work:
            resume.disarm()
            self._render()
            self._notify_end()                      # after the restart that ended a test
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

    def _stay_stock(self) -> None:
        progress.write_wizard({"phase": "stock"})
        resume.disarm()
        self.view = -1
        self.refresh()

    def _start_over(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            "Delete the core test results and start over?\n\n"
            "This deletes every result and log in ~/.local/share/ps5-cores-bisect.\n"
            "The boot unlock stays as it is.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        resume.disarm()
        progress.forget()
        self._run("reset", ["--reset"])

    def _report(self) -> None:
        self.show_details(True)
        self._run("report", ["--status"])

    # --------------------------------------------------------------- unlock
    def _install(self) -> None:
        if not gate_check(progress.state_dir()).accepted or self.installed:
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Keep all {ALL_CORES} cores on at every boot?\n\n"
            "A boot service checks the cores at every boot.\n"
            "After a full power off, it turns them on again and restarts the board once.\n"
            "Uninstall removes it. The stock cores come back after the next full power off.\n"
            "You'll be asked for your password, unless sudo still has it.")
        if answer == QMessageBox.StandardButton.Yes:
            progress.write_wizard({"install_boot": progress.boot_id()})
            self._run_unlock(["--install"], "install")

    def _uninstall(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            "Remove the boot service?\n\n"
            "The cores stay on until the next full power off. Then the board is back at the stock cores.\n"
            "You'll be asked for your password, unless sudo still has it.")
        if answer == QMessageBox.StandardButton.Yes:
            self._run_unlock(["--uninstall"], "uninstall")

    def _root_status(self) -> None:
        self.show_details(True)
        self._run_unlock(["--status"], "status")

    def _run_unlock(self, args: list[str], action: str, message: str = "") -> None:
        if self.unlock.busy:
            return
        self._unlock_action = action
        self._unlock_args = args
        if self.unlock.sudo_ready():
            self.unlock.run(args)
        else:
            entered = SudoDialog.ask(self, message) if message else SudoDialog.ask(self)
            if entered is None:
                return
            self.unlock.run(args, pw=entered)
        self._start_spin()
        self._render()

    def _on_unlock_finished(self, code: int) -> None:
        if self._auth_failed and code != 0:
            self._auth_failed = False
            self._run_unlock(self._unlock_args, self._unlock_action, "Incorrect password, try again.")
            return
        action = self._unlock_action
        self._unlock_action = ""
        self._log(f"({action} finished, exit code {code})")
        if code:
            self.note = f"{action.capitalize()} failed. Show details says why."
        else:
            self.note = {"install": "The boot service is installed.",
                         "uninstall": "The boot service is removed. A full power off puts back the stock cores."
                         }.get(action, "")
        self.refresh()
        if action == "apply" and not code:
            resume.arm(self.script, self.unlock_script)
            self._start_countdown("restart", RESTART_SECS)

    # -------------------------------------------------------------- session
    def _run(self, job: str, args: list[str]) -> None:
        if self.session.busy:
            return
        self.job = job
        self.errors = []
        self.note = ""
        self._log(f"$ ps5-cores-bisect.sh {' '.join(args)}")
        try:
            self.session.start(args, block_sleep=job == "test")    # a test keeps the board awake until it ends
            self._start_spin()
        except OSError as exc:
            self.job = ""
            self.note = f"Could not start ps5-cores-bisect.sh: {exc}"
        self._render()

    RUNNING = {"scan": "the scan", "test": "the test", "unlock": "the unlock", "reset": "deleting the results",
               "report": "the report"}

    def _on_spin(self) -> None:
        """Turns the symbol and counts the seconds while a script runs."""
        busy = self.session.busy or self.unlock.busy
        self.running.setVisible(busy)
        if not busy:
            self._spin.stop()
            return
        self._spin_frame = (self._spin_frame + 1) % 4
        what = self.RUNNING.get(self.job, "the script") if self.session.busy else "ps5-cores-unlock.sh"
        if self.job == "test" and self.live.get("item"):
            what = f"round {self.live.get('round', '?')}, {self.live['item']}"
        secs = int(time.monotonic() - self._busy_since)
        self.running.setText(f"{'◐◓◑◒'[self._spin_frame]}  Running: {what} · {secs} s")

    def _start_spin(self) -> None:
        self._busy_since = time.monotonic()
        self._spin.start()
        self._on_spin()

    def _log(self, text: str) -> None:
        self.output.appendPlainText(text)

    def _follow(self) -> None:
        """Reads the test's files again during a run, so the window shows the step that runs now."""
        self.p = progress.load()
        self.online = progress.online_cores()
        self.step = self._current_step()
        self.view = -1

    def _on_line(self, text: str) -> None:
        self._log(text)
        if text.startswith("ERROR:"):
            self.errors.append(text[6:].strip())
        if text.startswith("=== Before you start"):
            self._in_warnings, self.warnings = True, []
        elif self._in_warnings and text.startswith("- "):
            self.warnings.append(text[2:])
        if "Sorry, try again" in text:
            self._wrong_password = True

    def _on_notice(self, words: list[str]) -> None:
        name, args = words[0], words[1:]
        if name == "scan" and args:
            if self.scan is None:
                self.scan = {}
            self.scan[args[0]] = " ".join(args[1:])
        elif name == "attempt":
            self.live = {"round": args[0], "item": args[1]}
            self._follow()
        elif name == "phase":
            self.live["phase"] = args[0]
            self.live.pop("load", None)
        elif name == "load":
            self.live["load"] = " ".join(args)
        elif name == "result":
            self._follow()
        elif name == "restart-first":
            self.restart_first = True
        elif name == "unlocked":
            progress.write_wizard({"unlock_boot": progress.boot_id()})
            self.wizard = progress.read_wizard()
        elif name == "ask":
            self._answer(args[0] if args else "question")
            return
        self._render()

    def _answer(self, question: str) -> None:
        yes, no = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No
        if question == "unlock":
            self.session.send("y" if self.job == "unlock" else "n")   # only after a click on Unlock
        elif question == "restart":
            self.session.send("n")                  # the window restarts the board itself
        elif question == "reset":
            self.session.send("y")                  # the window asked already
        elif question == "crash":
            pending = self.p.pending
            what = f"Round {pending[0]}, {pending[1]}" if len(pending) >= 2 else "The last attempt"
            answer = QMessageBox.question(
                self, APP_NAME, "Did the board freeze, crash or restart by itself?\n\n"
                f"{what} did not finish.\n"
                "Yes records it as a crash of that attempt.\n"
                "No means you restarted it by hand. Then the attempt runs again.", yes | no, yes)
            self.session.send("y" if answer == yes else "n")
        elif question == "warnings":
            self._in_warnings = False
            text = " | ".join(self.warnings)
            if self.wizard.get("warnings") == text:
                self.session.send("y")
                return
            answer = QMessageBox.question(self, APP_NAME, "Go on despite these warnings?\n\n" + "\n".join(
                self.warnings) + "\n\nYou are asked once for this test.", yes | no, yes)
            if answer == yes:
                progress.write_wizard({"warnings": text})
                self.wizard = progress.read_wizard()
            self.session.send("y" if answer == yes else "n")
        elif question == "settings":
            answer = QMessageBox.question(self, APP_NAME, "Go on with the new settings?\n\n"
                                          "You changed the load, the rounds or the load tool during the test.\n"
                                          "The earlier attempts still count with their old settings.", yes | no, no)
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
            self.note = ("ps5-cores-bisect.sh stopped: " + self.errors[-1]) if self.errors else (
                f"ps5-cores-bisect.sh stopped with exit code {code}. Show details says why.")
            if job == "scan":
                self.scan = None
            self._render()
            if job == "test" and code != 130:       # 130 is Stop, which you pressed yourself
                notify.notify("Core test stopped", self.note)
            return
        if job == "reset":
            self.view = -1
            self.refresh()
            return
        if job == "report":
            report = next((line for line in reversed(self.output.toPlainText().splitlines())
                           if line.startswith("Report written to")), "")
            self.note = report.replace("Report written to", "The report is in", 1) if report else ""
            self._render()
            return
        if job == "unlock":
            if self.p.phase == "unlock-pending" and self._unlock_boot():
                resume.arm(self.script, self.unlock_script)
                self._start_countdown("restart", RESTART_SECS)
            else:
                self._render()
            return
        if job == "test":
            self.live = {}
            if self._restart_needed() and resume.armed() and not self.paused and self.p.next_attempt():
                self._start_countdown("restart", RESTART_SECS)
                return
            self._render()
            self._notify_end()
            return
        self._render()

    def _notify_end(self) -> None:
        """The desktop notification when a test has ended: the stock cores passed or failed, or the new cores' test
        is done. Nothing while attempts are left, so a pause or an attempt in between stays quiet."""
        p = self.p
        if not p.started:
            return
        if p.control == "failed":
            bad = next(a for a in p.attempts if a.item == "control" and progress.FAIL_RE.match(a.outcome))
            notify.notify("Core test stopped", f"The stock cores failed with {bad.outcome}: "
                          f"{OUTCOMES.get(bad.outcome, 'it failed')}. The unlock is not offered.")
        elif p.phase == "control" and p.control == "passed":
            notify.notify("Stock cores passed", f"All {p.rounds} rounds passed. Next: Unlock, in step 3 of Core "
                          "Unlock.")
        elif p.finished and p.healthy:
            notify.notify("Core test passed", f"{_cores(self._new()).capitalize()} passed, alone and together. "
                          "Next: Install, in step 5 of Core Unlock.")
        elif p.finished:
            bad = ", ".join(p.bad()) or "none"
            random = ", ".join(p.random()) or "none"
            notify.notify("Core test done", f"Fails every time: {bad}. Fails at random: {random}. Advice: stay at 6 "
                          "cores, in step 5 of Core Unlock.")
