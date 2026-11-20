# SPDX-License-Identifier: GPL-3.0-or-later

"""The one window of CPU Tools (owner, 20-11-2026: Cores Bisect and Cores Unlock are one app, CPU Tools, on one page,
as CU Tools). Its top half starts ps5-cores-bisect.sh: pick the options, hit Start, and the GUI hands off to a
terminal running the real script. Its bottom half is the unlock (unlock_panel.py): the verdict on the results, Install
and Uninstall of the persistence service, the 8 cores and the log of ps5-cores-unlock.sh.

The layout, as CU Tools' (owner, 19-11-2026): the suite's header, the icon spanning the title with the version and a
row of pills: Help (the script's --help as a styled page), Start, Show status and Reset; no About. Under it one line
with the run's numbers (load per attempt, rounds per item, the load tool) and the run's rough length, then the run's
switches as on/off pills: Rasdaemon, Same boot, Unattended and Auto resume. What a control does is in its tooltip, and
what the window does is the first paragraph of Help; the window carries no long text."""

from __future__ import annotations

import shlex

from PyQt6.QtCore import QByteArray, QSettings, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QSpinBox, QVBoxLayout, QWidget

from . import APP_NAME, LOGO_PATH, __version__
from .options import (
    DEFAULT_LOAD_TOOL, DEFAULT_ROUNDS, DEFAULT_TIME_SECS, LOAD_TIPS, LOAD_TOOLS, MAX_ROUNDS, MIN_ROUNDS,
    MIN_TIME_SECS, BisectOptions,
)
from .terminal import launch_in_terminal
from .theme import ACCENT, RED, header_font, muted
from .unlock_panel import UnlockPanel
from .widgets import HelpDialog, Pill, TogglePill, same_width

# control + post-control + one item per new core + combined, on a standard 0x77 board.
_TYPICAL_ITEMS = 5
# Rough warm-reboot + desktop-settle cost of one attempt when not running --same-boot.
_REBOOT_OVERHEAD_SECS = 120
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
        self._update_hint()
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
        # The window's actions as pills under the title, as CU Tools': Help, Start, Show status, Reset.
        self.help_pill = Pill("Help", "How it works", "The script's help, as a page: what it does and every option.")
        self.help_pill.clicked.connect(lambda: HelpDialog(self.script, self).exec())
        self.start_pill = Pill("Start", "Run in a terminal", "Starts ps5-cores-bisect.sh with these options in a "
                               "terminal, after a summary; this window closes.", ACCENT)
        self.start_pill.clicked.connect(self._on_start)
        self.status_pill = Pill("Show status", "Results so far", "Shows the results so far and writes the report "
                                "(--status), in a terminal. Starts nothing.")
        self.status_pill.clicked.connect(self._on_status)
        self.reset_pill = Pill("Reset", "Delete results", "Deletes every saved result and log in "
                               "~/.local/share/ps5-cores-bisect (--reset), after a question; the next run starts "
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
        """Load per attempt, Rounds per item and Load tool on one line, then the run's rough length; each label has
        its field's tooltip."""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.time_spin = QSpinBox()
        self.time_spin.setRange(MIN_TIME_SECS, 36000)
        self.time_spin.setSingleStep(60)
        self.time_spin.setValue(DEFAULT_TIME_SECS)
        self.time_spin.setSuffix(" s")
        self.time_spin.setToolTip("How long the CPU is loaded in each attempt (-t): at least {0} s, {1} s by default."
                                  .format(MIN_TIME_SECS, DEFAULT_TIME_SECS))
        self.time_spin.valueChanged.connect(self._update_hint)
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(MIN_ROUNDS, MAX_ROUNDS)
        self.rounds_spin.setValue(DEFAULT_ROUNDS)
        self.rounds_spin.setToolTip("Attempts per item (-r), interleaved so heat and the time of day favor none. A "
                                    "single round cannot tell a genuinely bad core from a random failure.")
        self.rounds_spin.valueChanged.connect(self._update_hint)
        self.load_combo = QComboBox()
        for index, tool in enumerate(LOAD_TOOLS):
            self.load_combo.addItem(tool, tool)                     # the data is the literal --load value
            self.load_combo.setItemData(index, LOAD_TIPS[tool], Qt.ItemDataRole.ToolTipRole)
        self.load_combo.setCurrentIndex(LOAD_TOOLS.index(DEFAULT_LOAD_TOOL))
        self.load_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.load_combo.setToolTip("The load of every attempt (--load). stress-ng verifies its own results and is "
                                   "always there. mprime's torture test is a much heavier AVX/FMA load that checks "
                                   "every result, so it catches silent miscalculation stress-ng misses; it has to be "
                                   "installed separately. both: one after the other, twice the load time.")
        self.load_combo.currentIndexChanged.connect(self._update_hint)
        for caption, field in (("Load per attempt", self.time_spin), ("Rounds per item", self.rounds_spin),
                               ("Load tool", self.load_combo)):
            label = QLabel(caption)
            label.setStyleSheet("font-weight:600;")
            label.setBuddy(field)
            label.setToolTip(field.toolTip())
            row.addWidget(label)
            row.addWidget(field)
            row.addSpacing(10)
        self.hint_label = QLabel()
        self.hint_label.setStyleSheet(f"color:{muted()}; font-style:italic;")
        row.addWidget(self.hint_label)
        row.addStretch(1)
        return row

    def _build_switches(self) -> QHBoxLayout:
        """The run's switches as on/off pills; each one's tooltip says what it does."""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.ras_pill = TogglePill("Rasdaemon", "--rasdaemon: reads ras-mc-ctl's error database before and after "
                                   "every attempt. rasdaemon keeps its errors, so they are still counted when the "
                                   "journal is volatile or the attempt ends in a crash. Needs the rasdaemon service.")
        self.same_boot_pill = TogglePill("Same boot", "--same-boot: no reboot between attempts. Much faster, but every "
                                         "attempt inherits the one before, so a failure is harder to pin on one core.")
        self.same_boot_pill.toggled.connect(self._update_hint)
        self.auto_pill = TogglePill("Unattended", "--auto: no questions, reboots by itself and goes on after every "
                                    "login until every item is done. Needs passwordless sudo for setpci and "
                                    "journalctl.")
        self.auto_pill.toggled.connect(self._on_auto_toggled)
        self.autostart_pill = TogglePill("Auto resume", "Installs and enables "
                                         "~/.config/systemd/user/ps5-cores-bisect-auto.service, which starts the "
                                         "run again after every reboot and login; the script removes it once every "
                                         "item is done. Only with Unattended.")
        self.autostart_pill.setEnabled(False)
        switches = [self.ras_pill, self.same_boot_pill, self.auto_pill, self.autostart_pill]
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
    def _on_auto_toggled(self, checked: bool) -> None:
        self.autostart_pill.setEnabled(checked)
        self.autostart_pill.setChecked(checked)

    def _update_hint(self) -> None:
        """The run's rough length beside the numbers, short; how it is reckoned is in its tooltip."""
        per_attempt = self.time_spin.value()
        if self._load_tool() == "both":
            per_attempt *= 2  # stress-ng and mprime each get the full load time, back to back
        if not self.same_boot_pill.isChecked():
            per_attempt += _REBOOT_OVERHEAD_SECS
        total_hours = _TYPICAL_ITEMS * self.rounds_spin.value() * per_attempt / 3600
        self.hint_label.setText("About {0:.1f} h".format(total_hours))
        self.hint_label.setToolTip(("A rough estimate for a typical board: {0} items x {1} rounds{2}. The run can be "
                                    "resumed: the results are saved after every attempt.").format(
            _TYPICAL_ITEMS, self.rounds_spin.value(),
            "" if self.same_boot_pill.isChecked() else ", reboots included"))

    def _load_tool(self) -> str:
        return self.load_combo.currentData() or DEFAULT_LOAD_TOOL

    def _collect_options(self) -> BisectOptions:
        return BisectOptions(
            time_secs=self.time_spin.value(),
            rounds=self.rounds_spin.value(),
            same_boot=self.same_boot_pill.isChecked(),
            unattended=self.auto_pill.isChecked(),
            load_tool=self._load_tool(),
            rasdaemon=self.ras_pill.isChecked(),
        )

    def _run_script(self, *args: str) -> bool:
        try:
            launch_in_terminal(shlex.join(["bash", self.script, *args]))
        except RuntimeError as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return False
        return True

    def _on_status(self) -> None:
        self._run_script("--status")

    def _on_reset(self) -> None:
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setWindowTitle(APP_NAME)
        confirm.setText("Delete all ps5-cores-bisect results?")
        confirm.setInformativeText(
            "This permanently deletes every saved result and log in "
            "~/.local/share/ps5-cores-bisect (--reset). This cannot be undone and there is no "
            "backup. The script will still ask you to confirm once more in the terminal.")
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return
        self._run_script("--reset")

    def _on_start(self) -> None:
        opts = self._collect_options()
        errors = opts.validate()
        if errors:
            QMessageBox.warning(self, APP_NAME, "\n".join(errors))
            return

        summary = (
            "Start ps5-cores-bisect.sh with:\n\n"
            "  load time: {t}s\n  rounds: {r}\n  load tool: {lt}\n  rasdaemon: {ras}\n"
            "  same-boot: {sb}\n  unattended: {au}\n\n"
            "This window will close and the run continues in a terminal."
        ).format(t=opts.time_secs, r=opts.rounds, lt=opts.load_tool, ras=opts.rasdaemon,
                 sb=opts.same_boot, au=opts.unattended)
        if QMessageBox.question(self, APP_NAME, summary) != QMessageBox.StandardButton.Yes:
            return

        if opts.unattended and self.autostart_pill.isChecked():
            from . import service
            try:
                service.install(self.script, opts)
            except Exception as exc:  # noqa: BLE001 - surfaced to the user, not fatal to starting
                QMessageBox.warning(self, APP_NAME, (
                    "Could not install the auto-resume login service:\n{0}\n\n"
                    "The run will still start now; see the manual's --auto checklist to set it up "
                    "by hand.").format(exc))

        if not self._run_script(*opts.to_args()):
            return
        self.close()
