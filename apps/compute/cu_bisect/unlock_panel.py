# SPDX-License-Identifier: GPL-3.0-or-later

"""The unlock part of the window (owner, 19-11-2026: CU Bisect and CU Unlock are one app, on one page): whether
ps5-cu-bisect.sh's results accept a mask (gate.py), and ps5-cu-unlock.sh's Install, Uninstall and --status
(runner.py). A row of the verdict (Accepted or Not accepted, its reasons in the tooltip and the log) and the pills
Install, Uninstall, Refresh and Re-check; the four shader-array rows with their WGPs, large; Preview a mask with an i
that explains the masks; then the log of ps5-cu-unlock.sh, behind a Show logs / Hide logs button (owner,
19-11-2026: a button, not a pill), hidden at the start. When Install or Uninstall fails, a red ! with "Check logs"
shows beside the button, no message box (owner, 19-11-2026); opening the log takes it away."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from . import APP_NAME
from .gate import GateResult, MASK_RE, check, cu_count, even_level
from .runner import UnlockRunner
from .theme import GREEN, ORANGE, RED, header_font
from .widgets import InfoButton, MetricBox, Pill, SudoDialog, same_width

ROWS = ("SE0.SH0", "SE0.SH1", "SE1.SH0", "SE1.SH1")

PREVIEW = ("A mask is four numbers, one per shader-array row (SE0.SH0, SE0.SH1, SE1.SH0, SE1.SH1), as "
           "<code>--baseline</code> and the README write them: <code>0x0f,0x0f,0x0f,0x0f</code>. Each bit is one "
           "WGP (2 CUs): bit 0 is WGP0, bit 4 is WGP4. Type one to see it on the rows above; it does not have to be "
           "an accepted result, and nothing is written. Only even masks can be installed: 3 WGPs on every row "
           "(<code>0x07</code>, 24 CUs, stock), 4 (<code>0x0f</code>, 32 CUs) or 5 (<code>0x1f</code>, 40 CUs). "
           "Clear the field to see the accepted mask again.")


class CuMapWidget(QWidget):
    """The 4 shader-array rows of 5 WGPs for the accepted or previewed mask: a WGP that is on is green. Large cells
    that share the window's width (owner, 19-11-2026)."""

    CELL_HEIGHT = 48

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)   # the rows never spread
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(8)
        self._grid.setVerticalSpacing(8)
        self._cells: list[list[QLabel]] = []
        for r, row in enumerate(ROWS):
            name = QLabel(row)
            name.setStyleSheet(header_font() + "font-size:16px; font-weight:700;")
            self._grid.addWidget(name, r, 0)
            cells = []
            for b in range(5):
                cell = QLabel("WGP%d" % b)
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setMinimumSize(110, self.CELL_HEIGHT)
                cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                cell.setStyleSheet(self._style(False))
                self._grid.addWidget(cell, r, b + 1)
                cells.append(cell)
            self._cells.append(cells)
        for b in range(5):
            self._grid.setColumnStretch(b + 1, 1)
        self.clear()

    @staticmethod
    def _style(unlocked: bool) -> str:
        bg = "#2e7d32" if unlocked else "#424242"
        return f"background:{bg}; color:white; border-radius:6px; font-size:16px; font-weight:700;"

    def clear(self) -> None:
        for cells in self._cells:
            for cell in cells:
                cell.setStyleSheet(self._style(False))

    def set_masks(self, masks: str) -> None:
        values = [int(m, 16) for m in masks.split(",")]
        for r, v in enumerate(values):
            for b in range(5):
                self._cells[r][b].setStyleSheet(self._style(bool(v >> b & 1)))


class UnlockPanel(QWidget):
    LOG_HEIGHT = 220

    def __init__(self, script: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.runner = UnlockRunner(script, self)
        self.runner.line.connect(self._append_line)
        self.runner.auth_failed.connect(self._on_auth_failed)
        self.runner.finished.connect(self._on_finished)
        self._pending_action = ""  # what the running process is, for the right message when it ends
        self._pending_args: list[str] = []  # so a wrong password can be retried without re-clicking
        self._auth_failed_this_run = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addLayout(self._build_actions())
        self.cu_map = CuMapWidget()
        root.addWidget(self.cu_map)
        root.addLayout(self._build_preview())

        self.logs_button = QPushButton("Show logs")
        self.logs_button.setToolTip("Shows or hides what ps5-cu-unlock.sh prints.")
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
        self.output.setPlaceholderText("Output of ps5-cu-unlock.sh appears here.")
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
        """The verdict, then Install, Uninstall, Refresh and Re-check (owner, 19-11-2026)."""
        self.gate_box = MetricBox("Bisect results")
        self.install_pill = Pill("Install", "Apply and keep", "Applies the accepted mask now and again at every "
                                 "boot (the unlock service). Needs the results to accept a mask.")
        self.install_pill.clicked.connect(self._on_install)
        self.uninstall_pill = Pill("Uninstall", "Stock next boot", "Disables the unlock service and removes its "
                                   "files; the board is back to the stock 24 CUs from the next reboot.", RED)
        self.uninstall_pill.clicked.connect(self._on_uninstall)
        self.status_pill = Pill("Refresh", "Service and masks", "Shows the installed masks, the service's state and "
                                "the live masks (--status, no root needed), in the log.")
        self.status_pill.clicked.connect(self._refresh_status)
        self.recheck_pill = Pill("Re-check", "Bisect results", "Reads ps5-cu-bisect.sh's recorded results again, "
                                 "for example after another retest, and writes the verdict in the log.")
        self.recheck_pill.clicked.connect(lambda: self._refresh_gate(log=True))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.boxes = [self.gate_box, self.install_pill, self.uninstall_pill, self.status_pill, self.recheck_pill]
        for box in self.boxes:
            row.addWidget(box)
        same_width(self.boxes)
        row.addStretch(1)
        return row

    def _build_preview(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel("Preview a mask")
        label.setStyleSheet("font-weight:600;")
        row.addWidget(label)
        self.mask_preview_input = QLineEdit()
        self.mask_preview_input.setPlaceholderText("0x0f,0x0f,0x0f,0x0f")
        self.mask_preview_input.setMinimumWidth(240)
        self.mask_preview_input.setToolTip("Four masks, one per row, to see on the rows above. Nothing is written.")
        self.mask_preview_input.textChanged.connect(self._on_mask_preview_changed)
        label.setBuddy(self.mask_preview_input)
        label.setToolTip(self.mask_preview_input.toolTip())
        row.addWidget(self.mask_preview_input)
        self.mask_preview_label = QLabel()
        row.addWidget(self.mask_preview_label, 1)
        self.preview_info = InfoButton(PREVIEW, "How a mask works")
        row.addWidget(self.preview_info)
        return row

    # ------------------------------------------------------------------ gate
    def _refresh_gate(self, log: bool = False) -> None:
        """The verdict in the first box, its reasons in the box's tooltip; Re-check also writes them in the log."""
        result: GateResult = check()
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
        self.install_pill.setEnabled(result.accepted and not self.runner.busy)
        # Don't stomp on a mask the user is currently previewing (see _on_mask_preview_changed).
        if not self.mask_preview_input.text().strip():
            self._apply_gate_map()

    def _apply_gate_map(self) -> None:
        result = getattr(self, "_gate_result", None)
        if result is not None and result.accepted:
            self.cu_map.set_masks(result.masks or "")
        else:
            self.cu_map.clear()

    # --------------------------------------------------------------- preview
    def _on_mask_preview_changed(self, text: str) -> None:
        text = text.strip()
        if not text:
            self.mask_preview_input.setStyleSheet("")
            self.mask_preview_label.setText("")
            self._apply_gate_map()
            return
        if not MASK_RE.match(text):
            self.mask_preview_input.setStyleSheet(f"border:1px solid {RED};")
            self.mask_preview_label.setText("invalid mask")
            return
        self.cu_map.set_masks(text)
        if even_level(text) is None:
            self.mask_preview_input.setStyleSheet(f"border:1px solid {ORANGE};")
            self.mask_preview_label.setText(
                "{0} CUs \u2014 not installable (needs 3, 4 or 5 WGPs on every row = 24/32/40 CUs)"
                .format(cu_count(text)))
            return
        self.mask_preview_input.setStyleSheet(f"border:1px solid {GREEN};")
        self.mask_preview_label.setText("{0} CUs (preview)".format(cu_count(text)))

    # ---------------------------------------------------------------- output
    def _append_line(self, text: str) -> None:
        self.output.appendPlainText(text)

    def _set_busy(self, busy: bool) -> None:
        for pill in (self.install_pill, self.uninstall_pill, self.status_pill, self.recheck_pill):
            pill.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            label = {
                "install": "Working \u2014 installing\u2026",
                "uninstall": "Working \u2014 uninstalling\u2026",
            }.get(self._pending_action)
            if label:
                self._append_line(label)
        else:
            QApplication.restoreOverrideCursor()
            self.install_pill.setEnabled(getattr(self, "_gate_result", None) is not None
                                         and self._gate_result.accepted)

    def _on_auth_failed(self) -> None:
        self._auth_failed_this_run = True
        self._append_line("sudo: authentication failed.")

    def _on_finished(self, code: int) -> None:
        self._set_busy(False)
        action = self._pending_action
        auth_failed = self._auth_failed_this_run
        self._auth_failed_this_run = False
        if auth_failed and code != 0 and action:
            # Wrong password: let the user retry right away instead of re-clicking Install/Uninstall.
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
        result = getattr(self, "_gate_result", None)
        if result is None or not result.accepted or not result.masks:
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            "Apply {0} ({1} CUs) now and keep it enabled on every boot?"
            .format(result.masks, result.cu_total),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run_privileged(["--install", result.masks], "install")

    def _on_uninstall(self) -> None:
        if not self.uninstall_pill.isEnabled():
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            ("Disable the unlock service? The board goes back to the stock 24 CUs from the "
             "next reboot."),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run_privileged(["--uninstall"], "uninstall")

    def _refresh_status(self) -> None:
        if self.runner.busy:
            return
        self._pending_action = ""
        self.runner.run_unprivileged(["--status"])
