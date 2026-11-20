# SPDX-License-Identifier: GPL-3.0-or-later

"""The unlock part of the window (owner, 20-11-2026: Cores Bisect and Cores Unlock are one app, CPU Tools, on one page,
as CU Tools): whether ps5-cores-bisect.sh's results accept the unlock (gate.py), and ps5-cores-unlock.sh's
Install, Uninstall and --status (runner.py). A row of the verdict (Accepted or Not accepted, its reasons in the tooltip
and the log) and the pills Install, Uninstall, Refresh, Root status and Re-check; the 8 physical cores, large, with an i
that explains their marks; then the log of ps5-cores-unlock.sh, behind a Show logs / Hide logs button, hidden at the
start. When an action fails, a red ! with "Check logs" shows beside the button, no message box; opening the log takes
it away."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from . import APP_NAME
from .gate import GateResult, check
from .runner import UnlockRunner
from .theme import GREEN, RED, header_font
from .widgets import InfoButton, MetricBox, Pill, SudoDialog, same_width

# Stock PS5 layout (mask 0x77): core 3 of each 4-core CCX is fused off.
DEFAULT_BASE = [0, 1, 2, 4, 5, 6]
DEFAULT_NEW = [3, 7]

_COLORS = {
    "stock": "#1565c0",
    "good": "#2e7d32",
    "bad": "#c62828",
    "random": "#ef6c00",
    "none": "#424242",
}
_MARKS = {"stock": "stock", "good": "ok", "bad": "xx", "random": "??", "none": ".."}

LEGEND = ("The 8 physical cores, in the order of the script's map: the stock cores first, the ones the unlock adds "
          "last.<br><b>stock</b>: always enabled (6C/12T). <b>ok</b>: passed every round. <b>xx</b>: fails every "
          "time, likely a bad core. <b>??</b>: random failures, more likely power or heat. <b>..</b>: not tested "
          "yet.<br>The unlock enables all cores or none, so one bad core means: don't install it.")


class CoreMapWidget(QWidget):
    """The 8 physical cores in the same order as the script's map: stock first, unlocked last. Large cells that share
    the window's width, as CU Tools' WGP rows (owner, 20-11-2026)."""

    CELL_HEIGHT = 48

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)   # the rows never spread
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(8)
        self._grid.setVerticalSpacing(4)
        self._cells: list[tuple[QLabel, QLabel]] = []
        for i in range(8):
            name = QLabel()
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet(header_font() + "font-size:16px; font-weight:700;")
            cell = QLabel()
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setMinimumSize(80, self.CELL_HEIGHT)
            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._grid.addWidget(name, 0, i)
            self._grid.addWidget(cell, 1, i)
            self._grid.setColumnStretch(i, 1)
            self._cells.append((name, cell))
        self.set_cores(DEFAULT_BASE, DEFAULT_NEW, {})

    def set_cores(self, base: list[int], new: list[int], verdicts: dict[int, str]) -> None:
        cores = [(c, "stock") for c in base] + [(c, verdicts.get(c, "none")) for c in new]
        for i, (name, cell) in enumerate(self._cells):
            if i < len(cores):
                core, state = cores[i]
                name.setText(f"core{core}")
                cell.setText(_MARKS[state])
                cell.setStyleSheet(f"background:{_COLORS[state]}; color:white; border-radius:6px; font-size:16px; "
                                   "font-weight:700;")
                name.show()
                cell.show()
            else:
                name.hide()
                cell.hide()


class UnlockPanel(QWidget):
    LOG_HEIGHT = 220

    def __init__(self, script: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.runner = UnlockRunner(script, self)
        self.runner.line.connect(self._append_line)
        self.runner.auth_failed.connect(self._on_auth_failed)
        self.runner.finished.connect(self._on_finished)
        self._gate_result: GateResult | None = None
        self._pending_action = ""  # what the running process is, for the right message when it ends
        self._pending_args: list[str] = []  # so a wrong password can be retried without re-clicking
        self._auth_failed_this_run = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addLayout(self._build_actions())
        map_row = QHBoxLayout()
        map_row.setSpacing(8)
        self.core_map = CoreMapWidget()
        map_row.addWidget(self.core_map, 1)
        self.legend_info = InfoButton(LEGEND, "What the marks mean")
        map_row.addWidget(self.legend_info, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(map_row)

        self.logs_button = QPushButton("Show logs")
        self.logs_button.setToolTip("Shows or hides what ps5-cores-unlock.sh prints.")
        self.logs_button.clicked.connect(lambda: self.show_logs(self.output.isHidden()))
        self.failed_label = QLabel(f"<span style='color:{RED}; font-size:18px; font-weight:900;'>!</span>"
                                   "&nbsp; Check logs")
        self.failed_label.setStyleSheet("font-weight:600;")
        self.failed_label.hide()
        logs_row = QHBoxLayout()
        logs_row.addWidget(self.logs_button)
        logs_row.addWidget(self.failed_label)
        logs_row.addStretch(1)
        root.addLayout(logs_row)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(2000)
        self.output.setMinimumHeight(self.LOG_HEIGHT)
        self.output.setPlaceholderText("Output of ps5-cores-unlock.sh appears here.")
        self.output.hide()
        root.addWidget(self.output, stretch=1)
        root.addStretch(0)                      # with the log hidden, room to spare goes under the button, not the rows

        self._refresh_gate()

    def start(self) -> None:
        """Reads the service's state once the window is up (--status, no root)."""
        self._refresh_status()

    def show_logs(self, shown: bool) -> None:
        self.output.setVisible(shown)
        if shown:
            self.failed_label.hide()            # the log is open: what failed is in it
        self.logs_button.setText("Hide logs" if shown else "Show logs")
        window = self.window()
        if not shown and window is not None:
            # The window gives back the room of the log, at its width. The layouts take the hidden log out first:
            # resized before that, the window kept the log's height and the rows above spread over it.
            for widget in (self, window):
                if widget.layout() is not None:
                    widget.layout().activate()
            window.resize(window.width(), window.sizeHint().height())

    def _build_actions(self) -> QHBoxLayout:
        """The verdict, then Install, Uninstall, Refresh, Root status and Re-check."""
        self.gate_box = MetricBox("Bisect results")
        self.install_pill = Pill("Install", "Keep 8 cores", "Enables the root service that applies the unlock again "
                                 "after a cold boot and warm-reboots once, so the 8 cores (16 threads) stay at every "
                                 "boot. Needs the results to accept the unlock.")
        self.install_pill.clicked.connect(self._on_install)
        self.uninstall_pill = Pill("Uninstall", "Stock after power off", "Removes the service. The unlock stays "
                                   "active until the next full power off (cold boot); then the board is back to the "
                                   "stock 6C/12T.", RED)
        self.uninstall_pill.clicked.connect(self._on_uninstall)
        self.status_pill = Pill("Refresh", "Service and cores", "Shows the threads, the service's and the guard's "
                                "state (--status, no root needed), in the log.")
        self.status_pill.clicked.connect(self._refresh_status)
        self.sudo_status_pill = Pill("Root status", "With sudo", "The status as root (asks for the sudo password), so "
                                     "it also shows the core presence mask, in the log.")
        self.sudo_status_pill.clicked.connect(self._on_sudo_status)
        self.recheck_pill = Pill("Re-check", "Bisect results", "Reads ps5-cores-bisect.sh's recorded results again, "
                                 "for example after more rounds finished, and writes the verdict in the log.")
        self.recheck_pill.clicked.connect(lambda: self._refresh_gate(log=True))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.boxes = [self.gate_box, self.install_pill, self.uninstall_pill, self.status_pill, self.sudo_status_pill,
                      self.recheck_pill]
        for box in self.boxes:
            row.addWidget(box)
        same_width(self.boxes)
        row.addStretch(1)
        return row

    @property
    def pills(self) -> list[Pill]:
        return [self.install_pill, self.uninstall_pill, self.status_pill, self.sudo_status_pill, self.recheck_pill]

    # ------------------------------------------------------------------ gate
    def _refresh_gate(self, log: bool = False) -> None:
        """The verdict in the first box, its reasons in the box's tooltip; Re-check also writes them in the log."""
        result = check()
        self._gate_result = result
        reasons = "\n".join(result.reasons)
        if result.accepted:
            self.gate_box.set_value("Accepted", reasons)
            self.gate_box.set_colour(GREEN)
        else:
            self.gate_box.set_value("Not accepted", reasons)
            self.gate_box.set_colour(RED)
        if log:
            self._append_line(f"Bisect results: {'accepted' if result.accepted else 'not accepted'}.")
            for reason in result.reasons:
                self._append_line(f"  {reason}")
        base = result.base_cores or DEFAULT_BASE
        new = result.new_cores or [c for c in range(8) if c not in base] or DEFAULT_NEW
        self.core_map.set_cores(base, new, result.core_verdicts)
        self.install_pill.setEnabled(result.accepted and not self.runner.busy)

    # ---------------------------------------------------------------- output
    def _append_line(self, text: str) -> None:
        self.output.appendPlainText(text)

    def _set_busy(self, busy: bool) -> None:
        for pill in self.pills:
            pill.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            label = {
                "install": "Working — installing…",
                "uninstall": "Working — uninstalling…",
            }.get(self._pending_action)
            if label:
                self._append_line(label)
        else:
            QApplication.restoreOverrideCursor()
            self.install_pill.setEnabled(self._gate_result is not None and self._gate_result.accepted)

    def _on_auth_failed(self) -> None:
        self._auth_failed_this_run = True
        self._append_line("sudo: authentication failed.")

    def _on_finished(self, code: int) -> None:
        self._set_busy(False)
        action = self._pending_action
        auth_failed = self._auth_failed_this_run
        self._auth_failed_this_run = False
        if auth_failed and code != 0 and action:
            # Wrong password: let the user retry right away instead of clicking again.
            entered = SudoDialog.ask(self, "Incorrect password, try again.")
            if entered is None:
                self._pending_action = ""
                self._pending_args = []
                return
            self._pending_action = action
            self._set_busy(True)
            self.runner.run(self._pending_args, pw=entered)
            return
        self._pending_action = ""
        self._pending_args = []
        if action in ("install", "uninstall"):
            self._append_line("({0} finished, exit code {1})".format(action, code))
            self._refresh_status()
        if code != 0 and action:
            self.failed_label.setToolTip("{0} failed (exit code {1}): the log says why.".format(action.capitalize(),
                                                                                              code))
            self.failed_label.setVisible(self.output.isHidden())

    # --------------------------------------------------------------- actions
    def _run_privileged(self, args: list[str], action: str) -> None:
        if self.runner.busy:
            return
        self._pending_action = action
        self._pending_args = args
        self._set_busy(True)
        if self.runner.sudo_ready():
            self.runner.run(args)
            return
        entered = SudoDialog.ask(self)
        if entered is None:
            self._pending_action = ""
            self._pending_args = []
            self._set_busy(False)
            return
        self.runner.run(args, pw=entered)

    def _on_install(self) -> None:
        if not self.install_pill.isEnabled():
            return
        self._refresh_gate()  # results may have changed since the window opened
        if self._gate_result is None or not self._gate_result.accepted:
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            ("Keep all 8 cores (16 threads) enabled on every boot?\n\n"
             "A root service checks the core mask at every boot. After a cold boot it re-applies "
             "the unlock and warm-reboots once. If the unlock isn't active right now, reboot (warm) "
             "after installing to bring the cores up."),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run_privileged(["--install"], "install")

    def _on_uninstall(self) -> None:
        if not self.uninstall_pill.isEnabled():
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            ("Remove the unlock service? The 8 cores stay enabled until the next full power off "
             "(cold boot); after that the board is back to the stock 6C/12T."),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run_privileged(["--uninstall"], "uninstall")

    def _on_sudo_status(self) -> None:
        if not self.sudo_status_pill.isEnabled():
            return
        self._run_privileged(["--status"], "status")

    def _refresh_status(self) -> None:
        if self.runner.busy:
            return
        self._pending_action = ""
        self.runner.run_unprivileged(["--status"])
