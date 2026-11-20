# SPDX-License-Identifier: GPL-3.0-or-later

"""The one window of CU Tools (owner, 19-11-2026: CU Bisect and CU Unlock are one app, CU Tools, on one page). Its top half
starts ps5-cu-bisect.sh: pick the options, hit Start, and the GUI hands off to a terminal running the real script.
Its bottom half is the unlock (unlock_panel.py): the verdict on the results, Install and Uninstall of a tested mask,
the WGP rows and the log of ps5-cu-unlock.sh.

The layout (owner, 19-11-2026): the suite's header, the icon spanning the title with the version and a row of
pills: Help (the script's --help as a styled page), Start, Show status and Reset. Under it one line with
the run's numbers (load per attempt, rounds per item, the baseline), then the run's switches as on/off pills:
Control only, Same boot, Unattended, Auto resume and No watch. What a control does is in its tooltip, and what the
window does is the first paragraph of Help (owner, 19-11-2026: no info symbols here); the window carries no long
text."""

from __future__ import annotations

import shlex

from PyQt6.QtCore import QByteArray, QSettings, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout, QWidget,
)

from . import APP_NAME, LOGO_PATH, __version__
from .options import BASELINE_PRESETS, BASELINE_TIPS, MASK_RE, BisectOptions
from .terminal import launch_in_terminal
from .theme import ACCENT, RED, header_font, muted
from .unlock_panel import UnlockPanel
from .widgets import HelpDialog, Pill, TogglePill, same_width

_CUSTOM_LABEL = "Custom..."
WIDTH = 900                             # as the suite's other apps (shadPS4 Manager): never narrower

class MainWindow(QWidget):
    def __init__(self, script: str, unlock_script: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.script = script
        self.setWindowTitle(f"{APP_NAME} {__version__}")

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.addLayout(self._build_header())
        root.addLayout(self._build_numbers())
        root.addLayout(self._build_switches())
        root.addSpacing(6)
        self.unlock = UnlockPanel(unlock_script, self)
        root.addWidget(self.unlock, 1)

        # 900 wide, or wider when the pills need it ("Not accepted" the widest verdict): never cut off
        verdict = self.unlock.gate_box.value.text(), self.unlock.gate_box.toolTip()
        self.unlock.gate_box.set_value("Not accepted", verdict[1])
        self.setMinimumWidth(max(WIDTH, self.minimumSizeHint().width()))
        self.unlock.gate_box.set_value(*verdict)
        self._restore_geometry()
        self._on_baseline_changed(self.baseline_combo.currentText())
        self.unlock.start()

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
        header_right = QVBoxLayout()
        header_right.setSpacing(6)
        title_row = QHBoxLayout()
        title = QLabel(f"{APP_NAME}  <span style='color:{muted()}; font-size:14px;'>v{__version__}</span>")
        title.setStyleSheet(header_font() + "font-size:24px; font-weight:800;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        header_right.addLayout(title_row)
        # The window's actions as pills under the title (owner, 19-11-2026): Help, Start, Show status, Reset.
        self.help_pill = Pill("Help", "How it works", "The script's help, as a page: what it does and every option.")
        self.help_pill.clicked.connect(lambda: HelpDialog(self.script, self).exec())
        self.start_pill = Pill("Start", "Run in a terminal", "Starts ps5-cu-bisect.sh with these options in a "
                               "terminal, after a summary; this window closes.", ACCENT)
        self.start_pill.clicked.connect(self._on_start)
        self.status_pill = Pill("Show status", "Results so far", "Shows the results so far and writes the report "
                                "(--status), in a terminal. Starts nothing.")
        self.status_pill.clicked.connect(self._on_status)
        self.reset_pill = Pill("Reset", "Delete results", "Deletes every saved result and log in "
                               "~/.local/share/ps5-cu-bisect (--reset), after a question; the next run starts "
                               "from scratch.", RED)
        self.reset_pill.clicked.connect(self._on_reset)
        pills = QHBoxLayout()
        pills.setSpacing(8)
        actions = [self.help_pill, self.start_pill, self.status_pill, self.reset_pill]
        for pill in actions:
            pills.addWidget(pill)
        same_width(actions)
        pills.addStretch(1)
        header_right.addLayout(pills)
        header.addLayout(header_right, 1)
        return header

    def _build_numbers(self) -> QHBoxLayout:
        """Load per attempt, Rounds per item and Baseline on one line; each label has its field's tooltip."""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.time_spin = QSpinBox()
        self.time_spin.setRange(60, 36000)
        self.time_spin.setSingleStep(30)
        self.time_spin.setValue(180)
        self.time_spin.setSuffix(" s")
        self.time_spin.setToolTip("How long the GPU is loaded in each attempt (-t): at least 60 s, 180 s by default.")
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(2, 9)
        self.rounds_spin.setValue(3)
        self.rounds_spin.setToolTip("Attempts per item (-r), interleaved so heat and the time of day favor none. "
                                    "At least 2; 1 with Control only.")
        self.baseline_combo = QComboBox()
        for index, label in enumerate(BASELINE_PRESETS):
            self.baseline_combo.addItem(label)
            self.baseline_combo.setItemData(index, BASELINE_TIPS[label], Qt.ItemDataRole.ToolTipRole)
        self.baseline_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.baseline_combo.setToolTip("The masks every attempt starts from (--baseline). Auto-detect: this boot's "
                                       "own clean masks, the safest choice. Stock: 0x07,0x07,0x07,0x07 (24 CUs). "
                                       "Unlocked: 0x1f,0x1f,0x1f,0x1f (40 CUs). Custom: any other mask.")
        self.baseline_combo.currentTextChanged.connect(self._on_baseline_changed)
        self.baseline_custom = QLineEdit()
        self.baseline_custom.setPlaceholderText("0x0f,0x0f,0x0f,0x0f")
        self.baseline_custom.setToolTip("Four masks, one per shader array, as --baseline takes them.")
        self.baseline_custom.textChanged.connect(self._validate_custom_baseline)
        for caption, field in (("Load per attempt", self.time_spin), ("Rounds per item", self.rounds_spin),
                               ("Baseline", self.baseline_combo)):
            label = QLabel(caption)
            label.setStyleSheet("font-weight:600;")
            label.setBuddy(field)
            label.setToolTip(field.toolTip())
            row.addWidget(label)
            row.addWidget(field)
            row.addSpacing(10)
        self.baseline_custom.setMinimumWidth(180)                  # a whole mask: 0x0f,0x0f,0x0f,0x0f
        row.addWidget(self.baseline_custom)
        row.addStretch(1)
        return row

    def _build_switches(self) -> QHBoxLayout:
        """The run's switches as on/off pills; each one's tooltip says what it does."""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.control_only_pill = TogglePill("Control only", "--control-only: only the control item, to re-check a "
                                            "combined mask you already bisected. Allows a single round.")
        self.control_only_pill.toggled.connect(self._on_control_only_toggled)
        self.same_boot_pill = TogglePill("Same boot", "--same-boot: no reboot between attempts. Faster, but every "
                                         "attempt inherits the one before.")
        self.auto_pill = TogglePill("Unattended", "--auto: no questions, reboots by itself and goes on after every "
                                    "login until every item is done. Needs passwordless sudo for umr and the "
                                    "kernel log.")
        self.auto_pill.toggled.connect(self._on_auto_toggled)
        self.autostart_pill = TogglePill("Auto resume", "Installs and enables "
                                         "~/.config/systemd/user/ps5-cu-bisect-auto.service, which starts the run "
                                         "again after every reboot and login. Only with Unattended.")
        self.autostart_pill.setEnabled(False)
        self.no_watch_pill = TogglePill("No watch", "--no-watch: the registers are not read back during the load.")
        switches = [self.control_only_pill, self.same_boot_pill, self.auto_pill, self.autostart_pill,
                    self.no_watch_pill]
        for pill in switches:
            row.addWidget(pill)
        same_width(switches)
        row.addStretch(1)
        return row

    # --------------------------------------------------------------- window
    def _restore_geometry(self) -> None:
        settings = QSettings()
        geometry = settings.value("main_window/geometry")
        if isinstance(geometry, QByteArray) and self.restoreGeometry(geometry):
            return
        self.resize(self.minimumWidth(), self.sizeHint().height())

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        QSettings().setValue("main_window/geometry", self.saveGeometry())
        super().closeEvent(event)

    # ------------------------------------------------------------- behavior
    def _on_baseline_changed(self, label: str) -> None:
        is_custom = label == _CUSTOM_LABEL
        self.baseline_custom.setVisible(is_custom)
        if not is_custom:
            self.baseline_custom.clear()
            self.baseline_custom.setStyleSheet("")

    def _validate_custom_baseline(self, text: str) -> None:
        text = text.strip()
        ok = not text or bool(MASK_RE.match(text))
        self.baseline_custom.setStyleSheet("" if ok else "border:1px solid #c62828;")

    def _on_auto_toggled(self, checked: bool) -> None:
        self.autostart_pill.setEnabled(checked)
        self.autostart_pill.setChecked(checked)

    def _on_control_only_toggled(self, checked: bool) -> None:
        # Rounds must be >=2 normally; a single confirmation round is only allowed for
        # control-only re-validation runs.
        self.rounds_spin.setMinimum(1 if checked else 2)

    def _resolved_baseline(self) -> str:
        label = self.baseline_combo.currentText()
        if label == _CUSTOM_LABEL:
            return self.baseline_custom.text().strip()
        return BASELINE_PRESETS.get(label) or ""

    def _collect_options(self) -> BisectOptions:
        return BisectOptions(
            time_secs=self.time_spin.value(),
            rounds=self.rounds_spin.value(),
            baseline=self._resolved_baseline(),
            control_only=self.control_only_pill.isChecked(),
            same_boot=self.same_boot_pill.isChecked(),
            unattended=self.auto_pill.isChecked(),
            no_watch=self.no_watch_pill.isChecked(),
        )

    def _on_status(self) -> None:
        try:
            launch_in_terminal(shlex.join(["bash", self.script, "--status"]))
        except RuntimeError as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def _on_reset(self) -> None:
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setWindowTitle(APP_NAME)
        confirm.setText("Delete all ps5-cu-bisect results?")
        confirm.setInformativeText(("This permanently deletes every saved result and log in "
                                    "~/.local/share/ps5-cu-bisect (--reset). This cannot be undone and there is no "
                                    "backup. The script will still ask you to confirm once more in the terminal."))
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return
        try:
            launch_in_terminal(shlex.join(["bash", self.script, "--reset"]))
        except RuntimeError as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def _on_start(self) -> None:
        opts = self._collect_options()
        errors = opts.validate()
        if errors:
            QMessageBox.warning(self, APP_NAME, "\n".join(errors))
            return

        summary = (
            "Start ps5-cu-bisect.sh with:\n\n"
            "  load time: {t}s\n  rounds: {r}\n  baseline: {b}\n"
            "  control-only: {co}\n  same-boot: {sb}\n  unattended: {au}\n  no-watch: {nw}\n\n"
            "This window will close and the run continues in a terminal."
        ).format(t=opts.time_secs, r=opts.rounds, b=opts.baseline or "auto-detect",
                  co=opts.control_only, sb=opts.same_boot, au=opts.unattended, nw=opts.no_watch)
        if QMessageBox.question(self, APP_NAME, summary) != QMessageBox.StandardButton.Yes:
            return

        if opts.unattended and self.autostart_pill.isChecked():
            from . import service
            try:
                service.install(self.script, opts.time_secs, opts.rounds)
            except Exception as exc:  # noqa: BLE001 - surfaced to the user, not fatal to starting
                QMessageBox.warning(self, APP_NAME, (
                    "Could not install the auto-resume login service:\n{0}\n\n"
                    "The run will still start now; see the manual's --auto checklist to set it up "
                    "by hand.").format(exc))

        try:
            launch_in_terminal(opts.to_command(self.script))
        except RuntimeError as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return

        self.close()
