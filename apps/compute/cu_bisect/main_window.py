# SPDX-License-Identifier: GPL-3.0-or-later

"""The one window of CU Unlock (owner, 23-11-2026: clear steps in the window, no terminal). It runs
ps5-cu-bisect.sh itself (session.py) and leads through four steps:

  1. Scan: reads the live masks and what a test needs (--scan). Writes nothing.
  2. Safety check: the control's rounds (--only control), the unlock's register writes with the stock masks. When it
     fails, the unlock method breaks on this board, and the window stops here.
  3. Test each WGP: every locked WGP on its own, a restart after each attempt.
  4. Choose and install: the even levels the healthy WGPs allow (24, 32 or 40 CUs), a combined test of the chosen
     level (--reset, then --baseline <mask> --control-only -r 1), then Install with ps5-cu-unlock.sh (runner.py).
     Install writes nothing to the GPU: the boot service turns the unlock on at the next restart.

Where the test stands is read from the script's own files every time (progress.py), so the window picks up where it
was after a restart. Before step 2 the window asks once; then it restarts the board by itself after each attempt and
opens again after each login (resume.py), with a countdown you can pause.

The layout (owner, 23-11-2026): the suite's header, the icon spanning the title with the version and a row of status
boxes, the filled info symbol and the round refresh symbol at the right end of the title row. Then the four steps as
rows, each with what came out of it or what to do now, and the button of the current step on its row; a green bar
over them when everything is done (owner, 24-11-2026). Then a few short lines; the CU map; one row with the other
actions as pills, the hint and what comes next, and the Details (the script's output) and Advanced (load, rounds, Same
boot, No watch) pills at its right end (owner, 24-11-2026). The baseline
is always the board's own masks, read at the start (owner, 23-11-2026): no field picks or types one."""

from __future__ import annotations

import time

from PyQt6.QtCore import QByteArray, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QScrollArea, QSizePolicy,
    QSpinBox, QVBoxLayout, QWidget,
)

from . import APP_NAME, LOGO_PATH, __version__, notify, progress, resume
from .cu_map import LEGEND, CuMap
from .gate import check as gate_check
from .options import BisectOptions
from .runner import UnlockRunner
from .session import ScriptSession
from .theme import ACCENT, BLUE, GREEN, GREY, ORANGE, RED, header_font, muted, surface_style
from .widgets import HelpDialog, InfoButton, MetricBox, Pill, RefreshButton, SudoDialog, TogglePill, same_width

TASKBAR = 80                            # the room kept free under the window, for a taskbar
WIDTH = 900                             # as the suite's other apps: it opens this wide, and is never narrower
STEPS = ("Scan", "Safety check", "Test each WGP", "Choose and install")
RESTART_SECS = 15                       # the countdown before the window restarts the board
GO_ON_SECS = 20                         # the countdown after a login before the next attempt

WHY_EVEN = "https://robertotorino.github.io/bazzite-console/apps/compute/#cu-levels"
ABOUT = ("CU Unlock finds out how many of your GPU's 40 CUs work, and turns on the healthy ones. A CU is a compute "
         "unit. Two CUs make a WGP.<br><br>The steps:<br>1. The scan reads which CUs are on now.<br>2. The safety "
         "check tests the unlock method itself.<br>3. Each locked WGP is tested on its own.<br>4. You choose 24, "
         "32 or 40 CUs, and the app installs it.<br><br>"
         "<a href='https://robertotorino.github.io/bazzite-console/apps/compute/'>CU Unlock in the wiki</a>")

OUTCOMES = {
    "PASS": "passed",
    "ERRORS": "memtest_vulkan found wrong results",
    "FAULT": "the GPU reset or faulted",
    "LOAD-FAIL": "the load tool stopped early",
    "CRASH-LOAD": "the system went down under load",
    "CRASH-APPLY": "the system went down while the masks were written",
    "DRIFT": "the masks changed after they were written",
    "MISMATCH": "the masks did not read back as written",
}


def _minutes(attempts: int, secs: int, same_boot: bool) -> str:
    total = attempts * (secs + 20 + (30 if same_boot else 90)) // 60       # 30 s cool-down or a restart
    total = max(5, round(total / 5) * 5)
    if total < 60:
        return f"about {total} minutes"
    hours, minutes = divmod(total, 60)
    return f"about {hours} h {minutes} min" if minutes else f"about {hours} h"


class StepRow(QFrame):
    """One step as a row (owner, 24-11-2026: every step says clearly what to do): a mark, "Step N · name" with its
    state, one line with what came out of it or what to do now, and on the current step's row its button. A click
    shows the step."""

    clicked = pyqtSignal()
    MARKS = {"done": "\u2714", "now": "\u25b6", "running": "\u25b6", "stopped": "\u2716"}
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
        self.title.setText(f"Step {self.index + 1} \u00b7 {STEPS[self.index]}")
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
        self.job = ""                                # what the session runs: scan, test, reset, report
        self.live: dict[str, str] = {}               # the attempt that runs now: round, item, phase, load
        self.errors: list[str] = []                  # the script's ERROR lines of the last job
        self.warnings: list[str] = []                # the lines under "Before you start"
        self._in_warnings = False
        self._wrong_password = False
        self._auth_failed = False
        self._unlock_action = ""
        self._after_reset: list[str] | None = None   # the combined test's arguments, started when --reset is done
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
        # When everything is done, a green bar over the steps (owner, 24-11-2026: the end was not clear).
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
        self.cu_map = CuMap()
        root.addWidget(self.cu_map)
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
        # While a script runs: a turning symbol, what runs and for how long (owner, 24-11-2026: see that it runs).
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
        self.uneven_row = self._build_uneven()
        root.addWidget(self.uneven_row)
        self.advanced = self._build_advanced()
        self.advanced.hide()
        root.addWidget(self.advanced)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(4000)
        self.output.setMinimumHeight(200)
        self.output.setPlaceholderText("What ps5-cu-bisect.sh and ps5-cu-unlock.sh print appears here.")
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
        self.info = InfoButton(ABOUT, "What CU Unlock does")
        self.info.setStyleSheet(
            f"QToolButton {{ border:none; border-radius:{InfoButton.SIZE // 2}px; background:{ACCENT}; color:white; "
            "font-weight:800; font-family:Georgia, serif; font-style:italic; padding:0; }")
        title_row.addWidget(self.info)
        self.refresh_button = RefreshButton("Reads the test's results and the boot unlock again")
        self.refresh_button.clicked.connect(self.refresh)
        title_row.addWidget(self.refresh_button)
        right.addLayout(title_row)
        boxes = QHBoxLayout()
        boxes.setSpacing(8)
        self.active_box = MetricBox("Active now", GREY)
        self.boot_box = MetricBox("Boot unlock", GREY)
        self.count_box = MetricBox("Attempts done", GREY)
        self.state_box = MetricBox("Test", GREY)
        self.boxes = [self.active_box, self.boot_box, self.count_box, self.state_box]
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
        for index in range(4):
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

    def _build_uneven(self) -> QWidget:
        """Step 4's uneven counts between the highest even level and every healthy WGP, as status boxes, for comparison
        with other tools (owner, 23-11-2026). They can't be applied; the link says why."""
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(8)
        label = QLabel(f"For comparison,<br>can't be applied.<br><a href='{WHY_EVEN}'>Why uneven CUs don't help</a>")
        label.setOpenExternalLinks(True)
        label.setStyleSheet(f"color:{muted()}; font-size:12px;")
        box.addWidget(label)
        self.uneven_boxes: list[MetricBox] = []
        self.uneven_layout = box
        box.addStretch(1)
        row.hide()
        return row

    def _set_uneven(self, counts: list[tuple[int, list[int]]]) -> None:
        for old in self.uneven_boxes:
            self.uneven_layout.removeWidget(old)
            old.hide()
            old.setParent(None)
            old.deleteLater()
        self.uneven_boxes = []
        for cus, rows in counts:
            box = MetricBox("\u00b7".join(map(str, rows)) + " WGPs", GREY)
            box.set_value(f"{cus} CUs", f"{cus} CUs with {'/'.join(map(str, rows))} WGPs on the rows SE0.SH0 to "
                          "SE1.SH1. "
                          "It runs as fast as its smallest row, so it can't be installed.")
            self.uneven_layout.insertWidget(self.uneven_layout.count() - 1, box)
            self.uneven_boxes.append(box)
        if self.uneven_boxes:
            same_width(self.uneven_boxes)
        self.uneven_row.setVisible(bool(counts))

    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        self.details_button = Pill("Details", "Show", "Shows or hides what the scripts print.", GREY)
        self.details_button.clicked.connect(lambda: self.show_details(self.output.isHidden()))
        self.advanced_button = Pill("Advanced", "Show", "Load time, rounds and how the test restarts.", GREY)
        self.advanced_button.clicked.connect(lambda: self.show_advanced(self.advanced.isHidden()))
        row.addWidget(self.details_button)
        row.addWidget(self.advanced_button)
        same_width([self.details_button, self.advanced_button])
        return row

    def _build_advanced(self) -> QWidget:
        """Load per attempt and Rounds per item on one line, Same boot and No watch under them."""
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.setContentsMargins(0, 0, 0, 0)
        settings = QSettings()
        row = QHBoxLayout()
        row.setSpacing(8)
        self.time_spin = QSpinBox()
        self.time_spin.setRange(60, 36000)
        self.time_spin.setSingleStep(30)
        self.time_spin.setSuffix(" s")
        self.time_spin.setValue(int(settings.value("advanced/time", 180)))
        self.time_spin.setToolTip("How long the load runs on the GPU in each attempt (-t). At least 60 s, 180 s by "
                                  "default.")
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(2, 9)
        self.rounds_spin.setValue(int(settings.value("advanced/rounds", 3)))
        self.rounds_spin.setToolTip("Attempts per item (-r), interleaved so heat and the time of day favor none. "
                                    "At least 2.")
        for caption, field in (("Load per attempt", self.time_spin), ("Rounds per item", self.rounds_spin)):
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
        # On by default (owner, 23-11-2026): one password and no restarts. A WGP that fails or is random is
        # tested again with Same boot off, one restart per attempt.
        self.same_boot_pill = TogglePill("Same boot", "--same-boot: no restart between attempts, one password, and "
                                         "you can leave it running. Every attempt inherits the one before. Turn it "
                                         "off to test a failing WGP again with a restart per attempt.",
                                         settings.value("advanced/same_boot", "true") == "true")
        self.no_watch_pill = TogglePill("No watch", "--no-watch: the registers are not read back during the load.",
                                        settings.value("advanced/no_watch", "false") == "true")
        for pill in (self.same_boot_pill, self.no_watch_pill):
            switches.addWidget(pill)
        same_width([self.same_boot_pill, self.no_watch_pill])
        switches.addStretch(1)
        box.addLayout(switches)
        for signal in (self.time_spin.valueChanged, self.rounds_spin.valueChanged,
                       self.same_boot_pill.toggled, self.no_watch_pill.toggled):
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
        settings.setValue("advanced/same_boot", "true" if self.same_boot_pill.isChecked() else "false")
        settings.setValue("advanced/no_watch", "true" if self.no_watch_pill.isChecked() else "false")

    def options(self) -> BisectOptions:
        return BisectOptions(time_secs=self.time_spin.value(), rounds=self.rounds_spin.value(),
                             same_boot=self.same_boot_pill.isChecked(), no_watch=self.no_watch_pill.isChecked())

    # ---------------------------------------------------------------- state
    def refresh(self) -> None:
        """Reads the test's files and the boot unlock again, and shows the step."""
        self.p = progress.load()
        self.wizard = progress.read_wizard()
        self.installed = progress.installed_masks()
        self.unlock_on = progress.unlock_on()
        self.step = self._current_step()
        self._render()

    def _phase(self) -> str:
        phase = self.wizard.get("phase", "")
        if not phase and self.p.started and self.p.control_only and min(
                progress.popcount(m) for m in progress.masks_of(self.p.base)) >= 4:
            return "combined"                       # a retest of a combined mask, started outside the window
        return phase

    def _terminal_check(self) -> bool:
        """A control-only run at the stock level from the terminal: a safety check, not a test the window can go
        on with."""
        return self.p.started and self.p.control_only and self._phase() == ""

    def _current_step(self) -> int:
        if self._phase() in ("combined", "stock"):
            return 3
        if not self.p.started or self._terminal_check():
            return 0
        if self.p.control != "passed":
            return 1
        return 2 if self.p.next_attempt() else 3

    def _bisect(self) -> progress.Progress:
        """The bisect run: the copy the combined test keeps, or the run itself."""
        if self._phase() == "combined":
            return progress.kept_bisect() or progress.Progress()
        return self.p

    def _show_step(self, index: int) -> None:
        if index <= self.step or index == 3:
            self.view = -1 if index == self.step else index
            self._render()

    def _map(self, bisect: progress.Progress, base: str = "") -> list[list[str]]:
        base = base or bisect.base or (self.scan or {}).get("live", "")
        if not base:
            return [["unknown"] * 5 for _ in progress.ROWS]
        rows = progress.masks_of(base)
        current = self.live.get("item", "") if self.job == "test" else ""
        states = []
        for r, row in enumerate(progress.ROWS):
            cells = []
            for b in range(5):
                item = f"{row}.WGP{b}"
                if rows[r] >> b & 1:
                    cells.append("on")
                elif item == current:
                    cells.append("now")
                else:
                    cells.append({"good": "ok", "bad": "bad", "random": "random"}.get(bisect.verdict(item), "wait"))
            states.append(cells)
        return states

    # --------------------------------------------------------------- render
    def _finished(self) -> bool:
        """Nothing is left to do: you chose the stock CUs, or the unlock is installed and on since this boot."""
        return self.step == 3 and (self._phase() == "stock" or (bool(self.installed) and self.unlock_on))

    def _summary(self, index: int, state: str) -> str:
        """The line on a step's row that is not the current one: what came out of it, or what it will do."""
        if state == "later":
            return ("Reads which CUs your GPU runs now. It writes nothing.",
                    "Tests the unlock method with your own masks. It adds no CUs.",
                    "Tests each locked WGP on its own.",
                    "You choose 24, 32 or 40 CUs. The level is tested as a whole and then installed.")[index]
        bisect = self._bisect()
        if index == 0:
            base = bisect.base or (self.scan or {}).get("live", "")
            return f"Your GPU ran {progress.cu_count(base)} CUs at the start." if base else "The board was read."
        if index == 1:
            return f"Passed {bisect.rounds} of {bisect.rounds} rounds. The unlock method works on this board."
        if index == 2:
            items = [it for it, _ in bisect.items if it != "control"]
            good = sum(1 for it in items if bisect.verdict(it) == "good")
            bad = [it for it in items if bisect.verdict(it) == "bad"]
            random = [it for it in items if bisect.verdict(it) == "random"]
            parts = [f"{good} WGP{'' if good == 1 else 's'} passed."]
            if bad:
                parts.append(f"{', '.join(bad)} failed every time and stay{'s' if len(bad) == 1 else ''} off.")
            if random:
                parts.append(f"{', '.join(random)} failed at random.")
            return " ".join(parts)
        if self._phase() == "stock":
            return "You chose to stay at the stock CUs."
        return f"{progress.cu_count(self.installed)} CUs are installed and on since the last restart."

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
            box.setEnabled(index <= self.step or index == 3)
        if finished:
            self.finished_bar.setText("\u2714  Finished. Your board stays at the stock CUs. There is nothing left "
                                      "to do." if self._phase() == "stock" else
                                      f"\u2714  Finished. Your board runs {progress.cu_count(self.installed)} CUs "
                                      "at every boot. There is nothing left to do.")
        self.finished_bar.setVisible(finished)
        self._render_boxes()
        page = (self._page_scan, self._page_control, self._page_wgps, self._page_choose)[view]
        self.uneven: list[tuple[int, list[int]]] = []    # step 4 fills it
        heading, lines, states, actions, hint, nxt = page()
        self._set_uneven(self.uneven)
        if self.countdown:
            what = "Restarting" if self.countdown_action == "restart" else "Going on"
            actions = [("Restart now" if self.countdown_action == "restart" else "Go on now",
                        "Don't wait", "", ACCENT, self._countdown_now),
                       ("Pause", "Stop the test here", "Stops the countdown. Go on later with Go on.", GREY,
                        self._pause)]
            nxt = f"{what} in {self.countdown} s."
        elif self.session.busy and self.job == "test":
            actions = [("Stop", "Stop this attempt", "Stops the attempt as Ctrl+C does. It runs again later.", RED,
                        self.session.stop)]
        elif self.session.busy or self.unlock.busy:
            actions = [(a[0], a[1], a[2], a[3], a[4], False) for a in actions]
        todo, primary = self._todo(view, actions)
        if not finished:
            self.todo.setText(todo if view == self.step else "Click this row to go back to this step.")
        self.heading.setText(f"Step {view + 1} \u00b7 {heading}")
        self.text.setText("<br>".join(lines))
        self.text.setVisible(bool(lines))
        self.cu_map.set_states(states)
        self._set_actions(actions, primary)
        self.hint.setText(self.note or hint)
        self.next_label.setText(nxt)

    def _todo(self, view: int, actions: list[tuple]) -> tuple[str, str]:
        """The one thing to do now, in words, and the pill that does it (empty when there is nothing to click)."""
        if self.countdown:
            if self.countdown_action == "restart":
                return f"Nothing to do. The board restarts by itself in {self.countdown} s.", "Restart now"
            return f"Nothing to do. The next attempt starts by itself in {self.countdown} s.", "Go on now"
        if self.session.busy and self.job == "test":
            return "Nothing to do. The test runs by itself, and a notification tells you when it ends.", ""
        if self.session.busy:
            return "Wait a moment, until the line beside the pills is gone.", ""
        if self.unlock.busy:
            return "Wait a moment. Type your password when you're asked.", ""
        enabled = [a[0] for a in actions if (a[5] if len(a) > 5 else True)]
        if view != self.step:
            return "This step is done. Click the step that says Now to go on.", ""
        if "Restart" in enabled and self._restart_turns_on():
            return (f"Restart the board to turn on {progress.cu_count(self.installed)} CUs. Save your work in other "
                    "apps first.", "Restart")
        words = {
            "Scan": "Click <b>Scan</b>. Type your password when you're asked.",
            "Start test": "Click <b>Start test</b>. A question opens. Answer <b>Yes</b>.",
            "Go on": "Click <b>Go on</b> to run the next attempt.",
            "Restart": "Click <b>Restart</b>. After the login, the window goes on by itself.",
            "Install": (f"{self.wizard.get('level', '')} CUs passed the combined test. Click <b>Install</b> and "
                        "type your password. Then restart the board."),
        }
        for value in ("Start test", "Scan", "Go on", "Install"):
            if value in enabled:
                return words[value], value
        if self._terminal_check() and "Start over" in enabled:
            return "Click <b>Start over</b> and answer <b>Yes</b>. Then click <b>Scan</b>.", "Start over"
        if "Stay at 24" in enabled:
            return "The test stopped. Click <b>Stay at 24</b>, or <b>Start over</b> to test again.", "Stay at 24"
        levels = [v for v in ("32 CUs", "40 CUs") if v in enabled]
        if levels:
            names = " or ".join(f"<b>{v}</b>" for v in levels)
            return (f"Click {names} to test that level as a whole, or <b>24 CUs</b> to stay stock.",
                    levels[-1])
        if "Restart" in enabled:
            return words["Restart"], "Restart"
        if "Scan again" in enabled:
            return "Fix what the text above names, then click <b>Scan again</b>.", "Scan again"
        if self._phase() == "stock":
            return "Done. Your board stays at the stock CUs.", ""
        if self.installed and self.installed == self.p.base:
            return "Done. The unlock is installed and on at every boot.", ""
        return "Nothing to do in this step yet.", ""

    def _render_boxes(self) -> None:
        live = (self.scan or {}).get("live", "")
        if live:
            self.active_box.set_value(f"{progress.cu_count(live)} CUs", f"Live masks at the scan: {live}")
            self.active_box.set_colour(GREEN)
        elif self.unlock_on:
            self.active_box.set_value(f"{progress.cu_count(self.installed)} CUs",
                                      f"ps5-cu-unlock.service applied {self.installed} at this boot.")
            self.active_box.set_colour(GREEN)
        else:
            self.active_box.set_value("—", "Scan in step 1 to read the live masks.")
            self.active_box.set_colour(GREY)
        if self.installed:
            self.boot_box.set_value(f"{progress.cu_count(self.installed)} CUs",
                                    f"ps5-cu-unlock.service applies {self.installed} at every boot.")
            self.boot_box.set_colour(BLUE)
        else:
            self.boot_box.set_value("Stock", "No unlock is installed. Every boot starts with the stock CUs.")
            self.boot_box.set_colour(GREY)
        if self.p.started:
            only = "control" if self.step == 1 else ""
            self.count_box.set_value(f"{self.p.done(only)} of {self.p.total(only)}",
                                     "Attempts done of this test, with the safety check's rounds in step 2.")
            self.count_box.set_colour(BLUE)
        else:
            self.count_box.set_value("—", "No test has started yet.")
            self.count_box.set_colour(GREY)
        if self.session.busy and self.job == "test":
            state, colour = "Testing", ACCENT
        elif self.countdown:
            state, colour = ("Restart" if self.countdown_action == "restart" else "Going on"), ACCENT
        elif self.p.control == "failed" or self._combined_failed():
            state, colour = "Stopped", RED
        elif self.step == 3 and not self.p.next_attempt():
            state, colour = "Done", GREEN
        elif self.p.started and resume.armed():
            state, colour = "Running", BLUE
        elif self.p.started:
            state, colour = "Paused", GREY
        else:
            state, colour = "Not started", GREY
        self.state_box.set_value(state, "Where the CU test stands.")
        self.state_box.set_colour(colour)

    def _live_hint(self) -> str:
        if self.job != "test" or not self.live:
            return ""
        parts = [f"Now: round {self.live.get('round', '?')}, {self.live.get('item', '?')}"]
        phase = self.live.get("phase", "")
        if phase == "write":
            parts.append("writing the masks")
        elif phase == "settle":
            parts.append("15 s on the idle GPU")
        elif "load" in self.live:
            secs, total, temp, clock, _busy = (self.live["load"].split() + ["?"] * 5)[:5]
            parts += [f"{(self.scan or {}).get('load', 'load')} {secs} of {total} s", f"{temp} °C",
                      f"{clock} MHz"]
        return " · ".join(parts)

    def _go_on_actions(self, label: str) -> list[tuple]:
        """Go on, or Restart when an attempt ran in this boot already, with Pause, Report and Start over."""
        if self.restart_first or (self.p.this_boot_used and not self.same_boot_pill.isChecked()):
            first = ("Restart", "Then go on", "Restarts the board. The window opens again after the login and "
                     "goes on.", ACCENT, self._restart_and_go_on)
        else:
            first = ("Go on", label, "Runs the next attempt in this window.", ACCENT, self._go_on)
        actions = [first]
        if resume.armed():
            actions.append(("Pause", "Stop after this", "The window no longer opens and goes on after a login.",
                            GREY, self._pause))
        actions += [("Report", "Save as a text file", "Writes the results so far to a text file on your Desktop.",
                     BLUE, self._report),
                    ("Start over", "Delete results", "Asks first. Then deletes the test's results and logs.", RED,
                     self._start_over)]
        return actions

    # ---------------------------------------------------------------- pages
    def _page_scan(self) -> tuple:
        help_pill = ("Help", "How the test works", "The script's own help, as a page.", BLUE,
                     lambda: HelpDialog(self.script, self).exec())
        if self.job == "scan" and self.session.busy:
            return ("Scan", ["The scan reads the GPU's masks.", "It writes nothing to the board."],
                    self._map(self.p), [("Scan", "Reading...", "", ACCENT, self._scan, False), help_pill],
                    "Reading the board...", "")
        if self._terminal_check():
            verdict = {"passed": "passed", "failed": "failed"}.get(self.p.control, "is not finished")
            return ("Scan", [f"A safety check from the terminal {verdict}, with {self.p.base}.",
                             "Its results are only the safety check. Start over to run the full test here."],
                    self._map(self.p), [("Start over", "Delete results", "Asks first. Then deletes the results, so "
                                         "the full test can start.", RED, self._start_over), help_pill], "", "")
        if not self.scan:
            lines = ["The scan reads which CUs your GPU runs now.", "It writes nothing to the board.",
                     "You'll be asked for your password."]
            if self.p.started:
                lines = ["The test has started already. The scan reads the board again.", *lines[1:]]
            return ("Scan", lines, self._map(self.p),
                    [("Scan", "Read the board", "Reads the live masks with umr (--scan). Writes nothing.", ACCENT,
                      self._scan), help_pill], "", "Next: the scan, then the safety check.")
        live = self.scan["live"]
        rows = progress.masks_of(live)
        on = sum(progress.popcount(m) for m in rows)
        locked = 20 - on
        opts = self.options()
        attempts = opts.rounds * (1 + locked)
        lines = [f"Your GPU runs {progress.cu_count(live)} of 40 CUs. {on} WGPs are on and {locked} are locked.",
                 f"Your masks are <b>{live}</b>, one value per row of the map, SE0.SH0 to SE1.SH1."]
        blockers = []
        if self.scan.get("at-boot") == "yes" or self.installed:
            blockers.append("A CU unlock is active from the boot. Remove it in step 4 and restart, then scan again.")
        if self.scan.get("load", "-") == "-":
            blockers.append("No GPU load tool was found. Put memtest_vulkan in ~/.local/bin, then scan again.")
        if locked == 0:
            blockers.append("Every WGP is on already, so there is nothing to test.")
        if blockers:
            lines += blockers
        else:
            lines.append(f"The test checks each locked WGP. That is {attempts} attempts, "
                         f"{_minutes(attempts, opts.time_secs, opts.same_boot)}"
                         f"{'' if opts.same_boot else ' with the restarts'}.")
        gov = self.scan.get("gov-max", "-")
        if gov.isdigit() and int(gov) > 1500:
            lines.append(f"The GPU may clock up to {gov} MHz. Cap it at 1500 MHz, so heat doesn't hide the result.")
        hint = " · ".join([f"Load tool: {self.scan.get('load', '-').replace('-', 'none')}",
                                f"GPU ceiling: {gov.replace('-', 'not set')} MHz",
                                f"Boot unlock: {'on' if self.installed else 'off'}"])
        start = ("Start test", "Go to step 2", "Asks first. Then starts the safety check.", ACCENT, self._start_test,
                 not blockers and not self.p.started)
        return ("Scan", lines, self._map(self.p),
                [start, ("Scan again", "Read the board", "Reads the live masks again. Writes nothing.", BLUE,
                         self._scan), help_pill], hint,
                "" if blockers else f"Next: the safety check. It takes {opts.rounds} attempts.")

    def _page_control(self) -> tuple:
        p = self.p
        rounds = p.rounds
        about = ["The safety check writes your stock masks the way the unlock does. It adds no CUs.",
                 "If it fails, the unlock method breaks on this board, not your CUs."]
        if p.control == "failed":
            bad = next(a for a in p.attempts if a.item == "control" and progress.FAIL_RE.match(a.outcome))
            lines = [about[0], f"Round {bad.round} ended with {bad.outcome}: {OUTCOMES.get(bad.outcome, 'it failed')}.",
                     "So the unlock method itself fails on this board. Your CUs were not tested."]
            actions = [("Stay at 24", "Keep the stock board", "Ends the test here. Nothing is installed.", GREEN,
                        self._stay_stock),
                       ("Start over", "Delete results", "Asks first. Then deletes the results, to test again.", RED,
                        self._start_over),
                       ("Details", "What the script saw", "Shows the script's results and the kernel's lines.", GREY,
                        self._report)]
            if p.this_boot_used:
                actions.insert(1, ("Restart", "Back to stock", "Restarts the board. The masks go back to stock.",
                                   BLUE, self._restart_only))
            hint = ("Restart before you use the board normally." if p.this_boot_used else
                    "Nothing stays on the board. A restart puts back the stock CUs.")
            return ("Safety check stopped", lines, self._map(p), actions, hint,
                    "Advice: stay at 24 CUs. Testing single WGPs means nothing while this check fails.")
        if self.session.busy and self.job == "test":
            return (f"Safety check, round {self.live.get('round', '?')} of {rounds}", about, self._map(p), [],
                    self._live_hint(), "")
        nxt = p.next_attempt("control")
        if p.control == "passed":
            return ("Safety check", [about[0], f"All {rounds} rounds passed. The unlock method works on this board."],
                    self._map(self._bisect()), [], "", "")
        if not p.started or nxt is None:
            return ("Safety check", about, self._map(p), [], "", "")
        return ("Safety check", [*about, f"{p.done('control')} of {rounds} rounds are done."], self._map(p),
                self._go_on_actions("Run the next round"), "", f"Next: round {nxt[0]} of the safety check.")

    def _page_wgps(self) -> tuple:
        p = self.p
        lines = [f"Each locked WGP is tested on its own, {p.rounds} rounds each.",
                 "All attempts run in this boot. Your own masks are written back between them."
                 if self.same_boot_pill.isChecked() else
                 "The board restarts after each attempt. This window opens again after the login and goes on."]
        if self.view >= 0 and self.step > 2 or not p.started:
            return ("Test each WGP", lines[:1], self._map(self._bisect()), [], "", "")
        if self.session.busy and self.job == "test":
            return (f"Test each WGP, round {self.live.get('round', '?')} of {p.rounds}", lines, self._map(p), [],
                    self._live_hint(), "")
        nxt = p.next_attempt()
        if nxt is None:
            return ("Test each WGP", lines[:1], self._map(p), [], "", "")
        left = p.total() - p.done()
        return ("Test each WGP", lines, self._map(p), self._go_on_actions("Run the next attempt"),
                f"{left} attempts left, {_minutes(left, p.time_secs, self.same_boot_pill.isChecked())}.",
                f"Next: round {nxt[0]}, {nxt[1]}.")

    def _combined_failed(self) -> bool:
        return self._phase() == "combined" and self.p.control == "failed"

    def _page_choose(self) -> tuple:
        phase = self._phase()
        bisect = self._bisect()
        uninstall = ("Uninstall", "Stock next restart", "Turns the boot unlock off and removes its files. The board "
                     "is back to the stock CUs from the next restart.", RED, self._uninstall, bool(self.installed))
        installed_line = (f"The boot unlock applies {self.installed}, {progress.cu_count(self.installed)} CUs, at "
                          "every boot." if self.installed else "No boot unlock is installed.")
        if phase == "stock":
            return ("Choose and install", ["You chose to stay at the stock CUs.", installed_line],
                    self._map(bisect), [uninstall, ("Start over", "Delete results", "Asks first. Then deletes the "
                                                    "test's results and logs.", RED, self._start_over)], "", "")
        levels = bisect.levels() if bisect.started else {}
        bad = [it for it, _ in bisect.items if bisect.verdict(it) == "bad"]
        random = [it for it, _ in bisect.items if bisect.verdict(it) == "random"]
        lines = []
        if bad:
            lines.append(f"Fails every time: {', '.join(bad)}. Leave these WGPs locked.")
        if random:
            lines.append(f"Fails at random: {', '.join(random)}. That points to power or heat, not a bad WGP.")
        top = max(levels) if levels else 0
        if phase == "combined":
            level = int(self.wizard.get("level", "0") or 0)
            if self.session.busy and self.job in ("test", "reset"):
                return (f"Combined test of {level} CUs", ["The combined test runs the chosen mask as a whole."],
                        self._map(bisect, self.p.base), [], self._live_hint(), "")
            if self.p.control == "failed":
                lines = [f"The combined test of {level} CUs failed. WGPs that pass alone can fail together.",
                         "Pick a lower level, or stay at the stock CUs."]
                actions = self._level_actions({c: m for c, m in levels.items() if c < level}, level)
                if self.p.this_boot_used:
                    actions.insert(0, ("Restart", "Back to stock", "Restarts the board. The masks go back to stock.",
                                       BLUE, self._restart_only))
                return ("Choose and install", lines, self._map(bisect), actions, "",
                        "Restart before you use the board normally." if self.p.this_boot_used else "")
            if self.p.next_attempt():
                return (f"Combined test of {level} CUs", ["The combined test runs the chosen mask as a whole.",
                                                          "Then Install keeps it on at every boot."],
                        self._map(bisect, self.p.base), self._go_on_actions("Run the combined test"), "",
                        f"Next: the combined test of {self.p.base}.")
            gate = gate_check()
            done = self.installed == self.p.base
            start_over = ("Start over", "Delete results", "Asks first. Then deletes the test's results and logs.", RED,
                          self._start_over)
            if done and self.unlock_on:
                return ("Choose and install", [], self._map(bisect, self.p.base), [uninstall, start_over], "", "")
            if done:
                return ("Choose and install", [], self._map(bisect, self.p.base),
                        [("Restart", f"Turn on {level} CUs", "Asks first. Then restarts the board.", ACCENT,
                          self._restart_to_turn_on), uninstall, start_over],
                        "The boot service turns the unlock on before the desktop starts.", "")
            actions = [("Install", f"{level} CUs at every boot", "Saves the mask for every boot. It turns on after a "
                        "restart.", ACCENT, self._install, gate.accepted), uninstall, start_over]
            hint = "Install asks for your password." if gate.accepted else "\n".join(gate.reasons)
            return ("Choose and install", [], self._map(bisect, self.p.base), actions, hint, "")
        if not bisect.started or bisect.control != "passed" or bisect.next_attempt():
            return ("Choose and install", ["Finish the test first. Then you choose the CUs here.", installed_line],
                    self._map(bisect, self.installed), [uninstall], "", "")
        actions = [*self._level_actions(levels), uninstall]
        if self.p.this_boot_used and not self.same_boot_pill.isChecked():
            actions.insert(0, ("Restart", "Back to stock", "Restarts the board. The masks go back to stock.", BLUE,
                               self._restart_only))
        self.uneven = bisect.uneven()
        if top > 24:
            lines.append(f"Every row has enough healthy WGPs for {top} CUs.")
            lines.append("Before the unlock is installed, a combined test runs it for one round.")
        else:
            lines.append("No level above the stock CUs is healthy on every row.")
        return ("Choose and install", lines, self._map(bisect), actions, installed_line,
                f"Highest healthy level: {top} CUs." if top else "")

    def _level_actions(self, levels: dict[int, str], failed: int = 0) -> list[tuple]:
        """24 CUs, 32 CUs and 40 CUs; a level is on only when the healthy WGPs reach it on every row."""
        actions = [("24 CUs", "Stay stock", "Ends the test. Nothing is installed.", GREY, self._stay_stock)]
        for cus in (32, 40):
            mask = levels.get(cus)
            if mask:
                caption, tip = "Test, then apply", f"A combined test of {mask}, then Install."
            elif failed and cus >= failed:
                caption, tip = "Failed together", f"The combined test of {failed} CUs failed."
            else:
                caption, tip = "Not healthy", f"Not every row has {cus // 8} healthy WGPs."
            actions.append((f"{cus} CUs", caption, tip, ACCENT if mask else RED,
                            lambda c=cus, m=mask: self._choose(c, m), bool(mask)))
        return actions

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
        locked = 20 - sum(progress.popcount(m) for m in progress.masks_of((self.scan or {}).get("live", "0,0,0,0")))
        attempts = opts.rounds * (1 + locked)
        if opts.same_boot:
            how = (f"All {attempts} attempts run in this boot, without a restart. That takes "
                   f"{_minutes(attempts, opts.time_secs, True)}.\n"
                   "You can leave the board alone until the test is done.")
            password = "You'll be asked for your password once."
        else:
            how = (f"After each attempt, the board restarts by itself. That is {attempts} restarts.\n"
                   "This window opens again after each login and goes on.")
            password = "You'll be asked for your password after each restart."
        answer = QMessageBox.question(
            self, APP_NAME,
            "Start the CU test?\n\n"
            "The test writes GPU registers. The board can freeze.\n"
            f"{how}\n"
            "After a freeze, turn the board off and on, and open the window. It asks what happened.\n"
            f"{password}")
        if answer != QMessageBox.StandardButton.Yes:
            return
        progress.forget()
        progress.write_wizard({"phase": ""})
        self.paused = False
        if not opts.same_boot:
            resume.arm(self.script, self.unlock_script)
        self._run_test()

    def _test_args(self) -> list[str]:
        opts = self.options()
        args = ["-t", str(opts.time_secs)]
        if self._phase() == "combined":
            return args + (["--same-boot"] if opts.same_boot else [])
        args += ["-r", str(opts.rounds)]
        if self.p.control != "passed":
            args += ["--only", "control"]
        if opts.same_boot:
            args.append("--same-boot")
        if opts.no_watch:
            args.append("--no-watch")
        return args

    def _run_test(self) -> None:
        self.restart_first = False
        self.live = {}
        self._run("test", self._test_args())

    def _go_on(self) -> None:
        if not self.same_boot_pill.isChecked() and self._phase() != "stock":
            resume.arm(self.script, self.unlock_script)
        self.paused = False
        self._run_test()

    def _restart_and_go_on(self) -> None:
        resume.arm(self.script, self.unlock_script)
        self._restart_only()

    def _restart_turns_on(self) -> bool:
        """The unlock is installed in this boot and waits for a restart."""
        return self.step == 3 and bool(self.installed) and not self.unlock_on and self._phase() == "combined"

    def _restart_to_turn_on(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            "Restart the board now?\n\n"
            f"The boot service turns on {progress.cu_count(self.installed)} CUs.\n"
            "Save your work in other apps first. Unsaved work is lost.")
        if answer == QMessageBox.StandardButton.Yes:
            self._restart_only()

    def _restart_only(self) -> None:
        if not resume.restart():
            self.note = "The window could not restart the board. Restart it by hand."
            self._render()

    def _resume(self) -> None:
        """Opened after a login by the autostart entry: a countdown, then the next attempt."""
        self.refresh()
        if not resume.armed():
            return
        work = self.p.started and self.p.control != "failed" and not self._combined_failed() and (
            self.p.next_attempt(self._only()) is not None or self.p.crashed)
        if not work:
            resume.disarm()
            self._render()
            self._notify_end()                      # after the restart that ended the test
            return
        self._start_countdown("go", GO_ON_SECS)

    def _only(self) -> str:
        return "control" if self._phase() != "combined" and self.p.control != "passed" else ""

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

    def _choose(self, cus: int, mask: str | None) -> None:
        if not mask:
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Test {cus} CUs as a whole?\n\n"
            f"The combined test runs {mask} for one round.\n"
            "The bisect results stay for this window. The script's own copy is cleared for the new test.\n"
            "After the test the board restarts. Then you can install the unlock.\n"
            "You'll be asked for your password.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.p.this_boot_used and not self.same_boot_pill.isChecked():
            QMessageBox.information(self, APP_NAME, "Restart the board first.\n\n"
                                    "The last attempt's masks are still active in this boot.\n"
                                    "After the restart, choose the level again.")
            return
        if self._phase() != "combined":
            progress.keep_bisect()
        progress.write_wizard({"phase": "combined", "level": str(cus)})
        self.wizard = progress.read_wizard()
        if not self.same_boot_pill.isChecked():
            resume.arm(self.script, self.unlock_script)
        self._after_reset = ["-t", str(self.options().time_secs), "--baseline", mask, "--control-only", "-r", "1",
                             *(["--same-boot"] if self.same_boot_pill.isChecked() else [])]
        self._run("reset", ["--reset"])

    def _start_over(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            "Delete the CU test results and start over?\n\n"
            "This deletes every result and log in ~/.local/share/ps5-cu-bisect.\n"
            "The boot unlock stays as it is.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        resume.disarm()
        progress.forget()
        self._after_reset = None
        self._run("reset", ["--reset"])

    def _report(self) -> None:
        self.show_details(True)
        self._run("report", ["--status"])

    # --------------------------------------------------------------- unlock
    def _install(self) -> None:
        mask = self.p.base
        if not gate_check().accepted or self.installed == mask:
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Install the {progress.cu_count(mask)}-CU unlock?\n\n"
            f"A service applies {mask} at every boot.\n"
            "It turns on after a restart. Nothing changes before that.\n"
            "Uninstall puts back the stock CUs after a restart.\n"
            "You'll be asked for your password, unless sudo still has it.")
        if answer == QMessageBox.StandardButton.Yes:
            self._run_unlock(["--install", mask], "install")

    def _uninstall(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            "Turn the boot unlock off?\n\n"
            "The board goes back to the stock CUs from the next restart.\n"
            "You'll be asked for your password, unless sudo still has it.")
        if answer == QMessageBox.StandardButton.Yes:
            self._run_unlock(["--uninstall"], "uninstall")

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
        self.note = (f"{action.capitalize()} failed. Show details says why." if code else
                     {"install": "The unlock is installed. Restart the board to turn it on.",
                      "uninstall": "The boot unlock is off. Restart to go back to the stock CUs."}.get(action, ""))
        self.refresh()

    # -------------------------------------------------------------- session
    def _run(self, job: str, args: list[str]) -> None:
        if self.session.busy:
            return
        self.job = job
        self.errors = []
        self.note = ""
        self._log(f"$ ps5-cu-bisect.sh {' '.join(args)}")
        try:
            self.session.start(args, block_sleep=job == "test")    # a test keeps the board awake until it ends
            self._start_spin()
        except OSError as exc:
            self.job = ""
            self.note = f"Could not start ps5-cu-bisect.sh: {exc}"
        self._render()

    RUNNING = {"scan": "the scan", "test": "the test", "reset": "deleting the results", "report": "the report"}

    def _on_spin(self) -> None:
        """Turns the symbol and counts the seconds while a script runs."""
        busy = self.session.busy or self.unlock.busy
        self.running.setVisible(busy)
        if not busy:
            self._spin.stop()
            return
        self._spin_frame = (self._spin_frame + 1) % 4
        what = self.RUNNING.get(self.job, "the script") if self.session.busy else "ps5-cu-unlock.sh"
        if self.job == "test" and self.live.get("item"):
            what = f"round {self.live.get('round', '?')}, {self.live['item']}"
        secs = int(time.monotonic() - self._busy_since)
        self.running.setText(f"{'◐◓◑◒'[self._spin_frame]}  Running: {what} \u00b7 {secs} s")

    def _start_spin(self) -> None:
        self._busy_since = time.monotonic()
        self._spin.start()
        self._on_spin()

    def _log(self, text: str) -> None:
        self.output.appendPlainText(text)

    def _follow(self) -> None:
        """Reads the test's files again during a run, so the window shows the step that runs now, not the one it
        started from (owner, 24-11-2026: it stayed on Scan during the whole safety check)."""
        self.p = progress.load()
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
        elif name == "ask":
            self._answer(args[0] if args else "question")
            return
        self._render()

    def _answer(self, question: str) -> None:
        yes, no = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No
        if question == "restart":
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
        elif question == "idle":
            answer = QMessageBox.question(self, APP_NAME, "The GPU is still busy. Write the masks anyway?\n\n"
                                          "Close games and video first, for a clean result.", yes | no, no)
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
            self.note = ("ps5-cu-bisect.sh stopped: " + self.errors[-1]) if self.errors else (
                f"ps5-cu-bisect.sh stopped with exit code {code}. Show details says why.")
            if job == "scan":
                self.scan = None
            self._render()
            if job == "test" and code != 130:       # 130 is Stop, which you pressed yourself
                notify.notify("CU test stopped", self.note)
            return
        if job == "reset":
            after, self._after_reset = self._after_reset, None
            if after:
                self._run("test", after)
            else:
                self.view = -1
                self.refresh()
            return
        if job == "report":
            report = next((line for line in reversed(self.output.toPlainText().splitlines())
                           if line.startswith("Report written to")), "")
            self.note = report.replace("Report written to", "The report is in", 1) if report else ""
            self._render()
            return
        if job == "test":
            self.live = {}
            needs_restart = self.restart_first or (self.p.this_boot_used and not self.same_boot_pill.isChecked())
            if needs_restart and resume.armed() and not self.paused:
                self._start_countdown("restart", RESTART_SECS)
                return
            if (self.same_boot_pill.isChecked() and not self.paused and self._phase() == ""
                    and self.p.control == "passed" and self.p.next_attempt()):
                self._run_test()                    # one boot: the safety check passed, so the WGPs follow at once
                return
            self._render()
            self._notify_end()
            return
        self._render()

    def _notify_end(self) -> None:
        """The desktop notification when a test has ended: done, stopped by the safety check, or the combined test's
        result. Nothing while attempts are left, so a pause or an attempt in between stays quiet."""
        p = self.p
        if not p.started:
            return
        if self._phase() == "combined":
            level = self.wizard.get("level", "")
            if p.control == "failed":
                notify.notify("Combined test failed",
                              f"{level} CUs failed as a whole. Pick a lower level in step 4 of CU Unlock.")
            elif not p.next_attempt():
                notify.notify("Combined test passed", f"{level} CUs passed. Install it in step 4 of CU Unlock.")
            return
        if p.control == "failed":
            bad = next(a for a in p.attempts if a.item == "control" and progress.FAIL_RE.match(a.outcome))
            notify.notify("CU test stopped", f"The safety check failed with {bad.outcome}: "
                          f"{OUTCOMES.get(bad.outcome, 'it failed')}. Your CUs were not tested.")
        elif p.control == "passed" and not p.next_attempt():
            fails = sum(1 for it, _ in p.items if it != "control" and p.verdict(it) == "bad")
            random = sum(1 for it, _ in p.items if it != "control" and p.verdict(it) == "random")
            wgps = "1 WGP" if fails == 1 else f"{fails} WGPs"
            notify.notify("CU test done", f"{p.total()} attempts. Fails every time: {wgps}. Random: {random}. "
                          f"Highest even level: {max(p.levels(), default=24)} CUs. Choose in step 4 of CU Unlock.")
