# SPDX-License-Identifier: GPL-3.0-or-later
"""The main window: the PS5's CEC adapter (the kernel's ps5-cec) and the TV behind it, buttons for the TV and what it
tells about itself (tvinfo.py), the PS5's name on the TV, pausing media while the TV is off (media.py, through the
watcher service), the automatic behavior of Valve's CEC daemon (cecd) with the remote's buttons (keys.py), and a
tester for the remote's keys.

The buttons send their messages with cec-ctl, so they work whichever CEC mode Bazzite is in. The automatic part
(wake and standby with the PS5, the remote as key presses) is cecd's: the app only writes its settings.

There are no DP-to-HDMI picture workarounds and no boot service: the PS5 has its own HDMI port, and its kernel already turns the TV on
and switches it at boot (hdmi.one_touch_play)."""

from __future__ import annotations

import sys
import time
from html import escape
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow,
                             QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from bazzite_console_core import SUITE_MANUAL_URL, window_title
from bazzite_console_core import __version__ as CORE_VERSION
from bazzite_console_core.platform import config_home, launch_in_terminal
from bazzite_console_core.settings import SettingsStore
from bazzite_console_core.theme import ORANGE, PURPLE
from bazzite_console_core.widgets import AppHeader, MetricBox, StatusText, TextDialog, hint_label

from . import APP_NAME, INFO, LOGO_PATH, ROOT, __version__
from . import bazzite, cec, keys, runner, service, tvinfo
from .remote import RemoteListener

MANUAL_URL = f"{SUITE_MANUAL_URL}apps/cec/"
KEYS_SHOWN = 12                         # the key tester's list
NO_ANSWER = ("No device answered. Check that CEC is switched on in the TV's settings (it has a brand name there: "
             "Anynet+, SimpLink, Bravia Sync, HDMI control, …), that the TV is on, and that the HDMI cable is "
             "plugged straight into the TV (some AV receivers and switches do not pass CEC).")
AUTOMATIC = (
    ("wake_tv", "Turn the TV on when the PS5 wakes from sleep"),
    ("suspend_tv", "Put the TV in standby when the PS5 goes to sleep"),
    ("uinput", "Use the TV remote as a keyboard (arrows, OK, back, play/pause)"),
    ("allow_standby", "Put the PS5 to sleep when the TV goes to standby"),
)
# The four boxes at the top, left to right, each its own color: the info blue, orange, black, purple.
DARK_BLUE = "#1565c0"


class CecSettings(SettingsStore):
    DEFAULTS = {}


class TableDialog(QDialog):
    """A title, a two-column table and a Close button: the TV Info window."""

    def __init__(self, title: str, headers: tuple[str, str], rows: list[tuple[str, str]], note: str,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(window_title(title))
        self.resize(620, 420)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(rows), 2)
        self.table.setHorizontalHeaderLabels(list(headers))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, (question, answer) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(question))
            self.table.setItem(row, 1, QTableWidgetItem(answer))
        layout.addWidget(self.table, 1)
        layout.addWidget(hint_label(note))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class RemoteDialog(QDialog):
    """What each button of the TV remote does: one key for each, or cecd's default, or nothing."""

    def __init__(self, choices: dict[str, str | None], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(window_title("Remote buttons"))
        self.resize(480, 640)
        layout = QVBoxLayout(self)
        layout.addWidget(hint_label("What each button of the TV remote does on the PS5. Valve's CEC daemon turns "
                                    "the buttons into key presses; Default is its own choice. A button gives one "
                                    "key, not a combination. The buttons most TVs pass on come first; which of the "
                                    "others arrive depends on the TV and its remote."))
        self.table = QTableWidget(len(keys.BUTTONS), 2)
        self.table.setHorizontalHeaderLabels(["Button", "Key"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.combos: dict[str, QComboBox] = {}
        for row, (button, label) in enumerate(keys.BUTTONS):
            item = QTableWidgetItem(label)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, item)
            combo = QComboBox()
            for key, text in keys.KEYS:
                combo.addItem(text if key != "" else f"Default ({keys.label(keys.DEFAULTS[button])})", key)
            current = choices.get(button, "")
            index = combo.findData(current)
            if index < 0:                                   # a key the list does not offer, set in the file
                combo.addItem(current, current)
                index = combo.count() - 1
            combo.setCurrentIndex(index)
            self.combos[button] = combo
            self.table.setCellWidget(row, 1, combo)
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choices(self) -> dict[str, str | None]:
        return {button: combo.currentData() for button, combo in self.combos.items()}


class MainWindow(QMainWindow):
    def __init__(self, dev_root: Path = Path("/dev"), sys_root: Path = Path("/sys"),
                 config_dir: Path | None = None, etc_root: Path = Path("/etc"), usr_root: Path = Path("/usr"),
                 run: Callable[[list[str]], runner.Result] = runner.run,
                 terminal: Callable[[str], None] = launch_in_terminal, listen: bool = True):
        super().__init__()
        self.resize(880, 860)
        self.dev_root, self.sys_root, self.etc_root, self.usr_root = dev_root, sys_root, etc_root, usr_root
        self.config_dir = config_dir or config_home()
        self.run, self.terminal = run, terminal
        self.settings = CecSettings(INFO, self)
        self.adapter: cec.Adapter | None = None
        self.audio_target = cec.TV                  # the audio system (5) once it answered a poll, else the TV

        header = AppHeader(LOGO_PATH, APP_NAME, __version__)
        self.badge = StatusText()
        header.add_state(self.badge)

        self.adapter_box = MetricBox("CEC adapter", DARK_BLUE)
        self.address_box = MetricBox("Physical address", ORANGE)
        self.display_box = MetricBox("Display", DARK_BLUE)      # the suite's blue (owner, 26-10-2026)
        self.power_box = MetricBox("TV power", PURPLE)
        for box in (self.adapter_box, self.address_box, self.display_box, self.power_box):
            header.add_second(box)
        self.adapter_note = hint_label("")

        tv = QGroupBox("TV")
        self.on_button = QPushButton("Turn TV on")
        self.on_button.setToolTip("Wake the TV and switch it to the PS5")
        self.on_button.clicked.connect(self.tv_on)
        self.source_button = QPushButton("Switch to PS5")
        self.source_button.setToolTip("Make the TV show the PS5's input")
        self.source_button.clicked.connect(self.switch_source)
        self.standby_button = QPushButton("TV standby")
        self.standby_button.clicked.connect(self.tv_standby)
        self.check_button = QPushButton("Check TV")
        self.check_button.setToolTip("Ask the TV whether it is there and on (a poll and its power status)")
        self.check_button.clicked.connect(self.check_tv)
        self.volume_buttons = []
        for text, ui_cmd in (("Volume −", "volume-down"), ("Volume +", "volume-up"), ("Mute", "mute")):
            button = QPushButton(text)
            button.setToolTip("To the AV receiver when one answers, else to the TV")
            button.clicked.connect(lambda _c=False, cmd=ui_cmd: self.press(cmd))
            self.volume_buttons.append(button)
        self.topology_button = QPushButton("Devices on the bus…")
        self.topology_button.setToolTip("Ask every device on the HDMI bus who it is (read-only)")
        self.topology_button.clicked.connect(self.show_topology)
        self.info_button = QPushButton("TV info…")
        self.info_button.setToolTip("What the TV tells about itself over CEC (only questions)")
        self.info_button.clicked.connect(self.show_tv_info)
        grid = QGridLayout()
        for col, w in enumerate((self.on_button, self.source_button, self.standby_button, self.check_button)):
            grid.addWidget(w, 0, col)
        for col, w in enumerate((*self.volume_buttons, self.topology_button)):
            grid.addWidget(w, 1, col)
        grid.addWidget(self.info_button, 2, 3)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(bazzite.OSD_NAME_BYTES)
        self.name_edit.setToolTip("The name the TV shows for the PS5, in its list of inputs and devices")
        self.name_button = QPushButton("Set name")
        self.name_button.clicked.connect(self.save_name)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name on the TV:"))
        name_row.addWidget(self.name_edit)
        name_row.addWidget(self.name_button)
        name_row.addStretch(1)
        grid.addLayout(name_row, 2, 0, 1, 3)
        self.result = hint_label("")
        lay_tv = QVBoxLayout(tv)
        lay_tv.addLayout(grid)
        lay_tv.addWidget(self.result)

        media_group = QGroupBox("When the TV turns off and on")
        self.pause_box = QCheckBox("Pause videos and music while the TV is off, and continue them when it is on again")
        self.pause_box.setToolTip("Media players (browsers, mpv, VLC, Spotify, …), through a small background "
                                  "service that asks the TV every 5 seconds whether it is on; games keep running")
        self.pause_box.toggled.connect(self.choose_pause)
        lay_media = QVBoxLayout(media_group)
        lay_media.addWidget(self.pause_box)
        lay_media.addWidget(hint_label("At boot the PS5's kernel turns the TV on and switches it to the PS5 by "
                                       "itself (hdmi.one_touch_play)."))

        automatic = QGroupBox("Automatic (Valve's CEC daemon)")
        self.mode_label = QLabel()
        self.mode_label.setWordWrap(True)
        self.native_button = QPushButton("Use Valve's CEC daemon…")
        self.native_button.setToolTip(f"Runs `{bazzite.NATIVE_COMMAND}` in a terminal; it asks for your password")
        self.native_button.clicked.connect(self.use_native)
        self.recheck_button = QPushButton("Check again")
        self.recheck_button.clicked.connect(self.refresh)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.mode_label, 1)
        mode_row.addWidget(self.native_button)
        mode_row.addWidget(self.recheck_button)
        self.remote_button = QPushButton("Remote buttons…")
        self.remote_button.setToolTip("Choose the key each button of the TV remote gives")
        self.remote_button.clicked.connect(self.edit_remote)
        mode_row.addWidget(self.remote_button)
        self.boxes: dict[str, QCheckBox] = {}
        lay_auto = QVBoxLayout(automatic)
        lay_auto.addLayout(mode_row)
        for key, text in AUTOMATIC:
            box = QCheckBox(text)
            box.toggled.connect(self.save_automatic)
            self.boxes[key] = box
            lay_auto.addWidget(box)
        self.automatic_note = hint_label("")
        lay_auto.addWidget(self.automatic_note)
        lay_auto.addWidget(hint_label(
            "Bazzite starts the daemon with your desktop session. These switches are its settings for your account, "
            f"in ~/.config/cecd/config.d/{bazzite.FRAGMENT}. <a href='{MANUAL_URL}'>Manual</a>"))

        keys = QGroupBox("Remote control keys")
        self.keys = QListWidget()
        self.keys.setMaximumHeight(110)
        self.keys_note = hint_label("")
        lay_keys = QVBoxLayout(keys)
        lay_keys.addWidget(self.keys_note)
        lay_keys.addWidget(self.keys)
        self.listener = RemoteListener(self)
        self.listener.pressed.connect(self.key_pressed)
        self.listening = listen and self.listener.start()

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addLayout(header)
        lay.addWidget(self.adapter_note)
        lay.addWidget(tv)
        lay.addWidget(media_group)
        lay.addWidget(automatic)
        lay.addWidget(keys)
        lay.addStretch(1)
        version = QLabel(f"{APP_NAME} {__version__} · core {CORE_VERSION}\nSends CEC messages when you press a button,"
                         "\nand asks the TV's power while Pause media is on.")
        version.setAlignment(Qt.AlignmentFlag.AlignRight)
        version.setStyleSheet("color:palette(placeholder-text);")
        lay.addWidget(version, 0, Qt.AlignmentFlag.AlignRight)
        scroll = QScrollArea()              # a smaller window scrolls instead of cutting off the wrapped texts
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        geometry = self.settings.window_state("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.refresh()

    # --- State ------------------------------------------------------------------------------------------------

    def cec_ctl(self, args: list[str]) -> runner.Result:
        return self.run([cec.CEC_CTL, *args])

    def refresh(self) -> None:
        """Reads the adapter and Bazzite's CEC mode again; sends nothing on the bus."""
        found = cec.devices(self.dev_root)
        read = [self.cec_ctl(cec.info(device)) for device in found]
        adapters = [cec.parse_info(device, r.out) for device, r in zip(found, read) if r.ok]
        self.adapter = cec.pick(adapters)
        a = self.adapter
        if a is None:
            self.badge.set_status("No CEC adapter", "warn")
            self.adapter_box.set_value("None")
            self.address_box.set_value("—")
            self.display_box.set_value("—")
            self.adapter_note.setText(
                "No /dev/cec* device. On the PS5 the CEC adapter is the kernel's ps5-cec; it is missing when the "
                "kernel is not a ps5-linux one or the module did not load (Bazzite Test shows the kernel)."
                if not found else
                f"cec-ctl could not read {found[0]}. Is v4l-utils installed?")
        else:
            self.adapter_box.set_value(a.name or Path(a.device).name, f"{a.device} · driver {a.driver}")
            self.address_box.set_value(a.physical_address if a.has_display else "None",
                                       "The display's HDMI address for this input, from its EDID")
            self.display_box.set_value(cec.display_name(a.name, self.sys_root) or "—")
            if not a.has_display:
                self.badge.set_status("No display seen", "warn")
                self.adapter_note.setText("The adapter sees no display: the TV is off or not connected, or its "
                                          "EDID was not read. CEC needs both.")
            else:
                self.badge.set_status("Not checked", "neutral", "Check TV asks the TV whether it is there")
                others = [b.device for b in adapters if b is not a]
                self.adapter_note.setText(f"{escape(a.device)} on {escape(a.name)} ({escape(a.driver)}), "
                                          f"{escape(', '.join(a.logical_addresses) or 'no logical address yet')}."
                                          + (f" Also here: {escape(', '.join(others))}; the app uses the one that "
                                             "sees a display." if others else ""))
        for w in (self.on_button, self.source_button, self.standby_button, self.check_button, self.topology_button,
                  self.info_button, self.name_button, *self.volume_buttons):
            w.setEnabled(a is not None)
        self.name_edit.setText(self.osd_name())
        self.power_box.set_value("—")
        self.refresh_picture()
        self.refresh_mode()

    def osd_name(self) -> str:
        return bazzite.read_fragment(self.config_dir).get("osd_name") or cec.OSD_NAME

    def refresh_picture(self) -> None:
        self.pause_box.blockSignals(True)
        self.pause_box.setChecked(service.PAUSE in service.jobs(self.run, self.config_dir))
        self.pause_box.blockSignals(False)
        self.pause_box.setEnabled(self.adapter is not None)

    def refresh_mode(self) -> None:
        mode = bazzite.read_mode(self.run, self.usr_root)
        self.mode = mode
        running = "running" if mode.cecd_running else "not running"
        if not mode.cecd_installed:
            text = "This Bazzite has no cecd (Valve's linux-cec package), so there is no automatic part."
        elif mode.name == "native":
            text = f"Bazzite CEC mode: <b>{mode.label}</b>, cecd is {running}."
        else:
            text = (f"Bazzite CEC mode: <b>{mode.label}</b>. The automatic part needs Valve's CEC daemon: "
                    "Bazzite's native mode, made for a machine with its own CEC adapter like the PS5's ps5-cec.")
        self.mode_label.setText(text)
        native = mode.name == "native"
        self.native_button.setVisible(mode.cecd_installed and not native)
        self.remote_button.setEnabled(mode.cecd_installed and keys.available())
        current = bazzite.read_settings(self.config_dir, self.etc_root, self.usr_root)
        for key, box in self.boxes.items():
            box.blockSignals(True)
            box.setChecked(current[key])
            box.blockSignals(False)
            box.setEnabled(native)
        self.automatic_note.setText("" if native else "The switches show cecd's settings; they take effect in native "
                                                      "mode.")
        self.automatic_note.setVisible(bool(self.automatic_note.text()))
        if not self.listening:
            self.keys_note.setText("No session bus: the key tester cannot listen.")
        elif mode.cecd_running:
            self.keys_note.setText("Press keys on the TV remote: each one the PS5 receives shows here. The TV "
                                   "sends them only while the PS5 is the input it shows.")
        else:
            self.keys_note.setText("The key tester listens to Valve's CEC daemon, which is not running.")

    # --- TV ---------------------------------------------------------------------------------------------------

    def ensure_configured(self) -> bool:
        """The adapter needs a logical address to send from, under the PS5's name. cecd claims one with its own
        name setting; without it the app configures the adapter when it has no address or another name, and tells
        the TV the name."""
        a = self.adapter
        if a is None:
            return False
        name = self.osd_name()
        if not a.configured or (cec.needs_name(a, name) and not self.mode.cecd_running):
            result = self.cec_ctl(cec.configure(a.device, name))
            if not result.ok:
                self.show_result(f"Could not configure {a.device}:\n{result.out.strip()}")
                return False
            renamed = a.configured
            self.adapter = cec.parse_info(a.device, result.out) if "Driver Info" in result.out else a
            if renamed:
                self.cec_ctl(cec.set_osd_name(a.device, name))
        return True

    def send(self, args: list[str], done: str) -> bool:
        result = self.cec_ctl(args)
        if cec.acked(result.out):
            self.show_result(done, ok=True)
            return True
        if "Not Acknowledged" in result.out:
            self.show_result(NO_ANSWER, ok=False)
        else:
            self.show_result(f"The message did not go out:\n{result.out.strip()}")
        return False

    def show_result(self, text: str, ok: bool | None = None) -> None:
        """The outcome under the buttons; *ok* also sets the badge: whether the TV answered (None: not asked)."""
        self.result.setText(f"{time.strftime('%H:%M:%S')}  {escape(text)}")
        if ok is not None:
            self.badge.set_status("TV answers" if ok else "TV does not answer", "ok" if ok else "warn")

    def tv_on(self) -> None:
        if self.ensure_configured() and self.send(cec.image_view_on(self.adapter.device), "The TV took Image View On."):
            self.switch_source()

    def switch_source(self) -> None:
        a = self.adapter
        if not self.ensure_configured() or a is None:
            return
        if not a.has_display:
            self.show_result("The PS5 has no physical address yet, so the TV cannot be switched to it.")
            return
        self.send(cec.active_source(a.device, a.physical_address),
                  f"Sent Active Source {a.physical_address}: the TV should show the PS5.")

    def tv_standby(self) -> None:
        if self.ensure_configured():
            self.send(cec.standby(self.adapter.device), "The TV took Standby.")

    def check_tv(self) -> None:
        if not self.ensure_configured():
            return
        device = self.adapter.device
        if not self.send(cec.poll(device), "The TV answered the poll."):
            self.power_box.set_value("No answer")
            return
        state = cec.power_status(self.cec_ctl(cec.give_power_status(device)).out)
        self.power_box.set_value(state[:1].upper() + state[1:] if state else "Unknown",   # "On", "Standby"
                                 "" if state else "The TV took the question but did not reply")
        audio = self.cec_ctl(cec.poll(device, cec.AUDIO_SYSTEM))
        self.audio_target = cec.AUDIO_SYSTEM if cec.acked(audio.out) else cec.TV
        receiver = (" An AV receiver answered too; the volume buttons go to it."
                    if self.audio_target == cec.AUDIO_SYSTEM else "")
        self.show_result(f"The TV answered: power {state or 'unknown'}.{receiver}", ok=True)

    def press(self, ui_cmd: str) -> None:
        if not self.ensure_configured():
            return
        device = self.adapter.device
        if self.send(cec.key_press(device, self.audio_target, ui_cmd), f"Sent {ui_cmd}."):
            self.cec_ctl(cec.key_release(device, self.audio_target))

    def show_tv_info(self) -> None:
        if not self.ensure_configured():
            return
        rows = tvinfo.rows(tvinfo.ask(self.run, self.adapter.device))
        TableDialog("TV Info", ("Question", "Answer"), rows, "Asked just now. These are only questions: nothing on "
                    "the TV changed.", self).exec()

    def save_name(self) -> None:
        name = self.name_edit.text().strip()
        problem = bazzite.osd_name_problem(name)
        if problem:
            self.show_result(problem)
            return
        bazzite.update_fragment(self.config_dir, osd_name=name)
        if self.mode.cecd_running:                          # cecd owns the adapter: it takes the name at a restart
            bazzite.restart_cecd(self.run)
            self.show_result(f"Valve's CEC daemon restarted with the name {name}.")
            return
        a = self.adapter
        if a is None:
            return
        result = self.cec_ctl(cec.configure(a.device, name))
        if not result.ok:
            self.show_result(f"Could not configure {a.device}:\n{result.out.strip()}")
            return
        self.adapter = cec.parse_info(a.device, result.out) if "Driver Info" in result.out else a
        self.send(cec.set_osd_name(a.device, name), f"The TV now knows the PS5 as {name}.")

    def show_topology(self) -> None:
        if not self.ensure_configured():
            return
        result = self.cec_ctl(cec.topology(self.adapter.device))
        found = cec.parse_topology(result.out)
        lines = [f"{address}  {name}" for address, name in found] or ["No devices found."]
        if len(found) <= 1:
            lines += ["", NO_ANSWER]
        TextDialog("Devices on the HDMI bus", "\n".join(lines) + f"\n\ncec-ctl said:\n{result.out}", self).exec()

    # --- Media while the TV is off ---------------------------------------------------------------------------

    def choose_pause(self, on: bool) -> None:
        jobs = service.jobs(self.run, self.config_dir) - {service.PAUSE}
        self.set_jobs(jobs | ({service.PAUSE} if on else set()))
        self.refresh_picture()

    def set_jobs(self, jobs: set[str]) -> None:
        result = service.set_jobs(self.run, self.config_dir, sys.executable, ROOT, jobs)
        if not result.ok:
            QMessageBox.warning(self, window_title("Background service"),
                                f"The background service did not start:\n{result.out.strip()}")

    # --- Automatic --------------------------------------------------------------------------------------------

    def save_automatic(self) -> None:
        settings = {key: box.isChecked() for key, box in self.boxes.items()}
        path = bazzite.write_settings(self.config_dir, settings)
        reloaded = bazzite.reload_cecd(self.run)
        self.automatic_note.setText(f"Saved in {path}." + ("" if reloaded.ok else
                                                           " cecd is not running; it reads them when it starts."))
        self.automatic_note.setVisible(True)

    def edit_remote(self) -> None:
        dialog = RemoteDialog(keys.choices_from(bazzite.read_fragment(self.config_dir).get("mappings")), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        bazzite.update_fragment(self.config_dir, mappings=keys.mappings_for(dialog.choices()))
        restarted = bazzite.restart_cecd(self.run)
        self.automatic_note.setText("Saved. " + ("Valve's CEC daemon restarted with the new buttons."
                                                 if self.mode.cecd_running and restarted.ok else
                                                 "Valve's CEC daemon uses them when it starts."))
        self.automatic_note.setVisible(True)

    def use_native(self) -> None:
        answer = QMessageBox.question(
            self, window_title("Valve's CEC daemon"),
            "Switch Bazzite's HDMI-CEC to native mode?\n\n"
            f"This runs `{bazzite.NATIVE_COMMAND}` in a terminal, Bazzite's own command. It turns off the older "
            "cec-control services and starts Valve's CEC daemon with your desktop session. It asks for your "
            "password.\n\nPress Check again when it is done.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.terminal(bazzite.NATIVE_COMMAND)
        except RuntimeError as exc:
            QMessageBox.warning(self, window_title("Valve's CEC daemon"), str(exc))

    # --- Remote -----------------------------------------------------------------------------------------------

    def key_pressed(self, command: int, initiator: int) -> None:
        source = "TV" if initiator == cec.TV else f"device {initiator}"
        self.keys.insertItem(0, f"{time.strftime('%H:%M:%S')}  {cec.ui_command_name(command)}  "
                                f"(0x{command:02x}, from the {source})")
        while self.keys.count() > KEYS_SHOWN:
            self.keys.takeItem(self.keys.count() - 1)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.set_window_state("geometry", self.saveGeometry())
        self.settings.sync()
        super().closeEvent(event)
