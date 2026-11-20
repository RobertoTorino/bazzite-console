# SPDX-License-Identifier: GPL-3.0-or-later

"""The Help dialog, the masked sudo password prompt (returned once, never stored), the status box and pill (copies of
core's MetricBox and Pill: this app is not on core), the on/off pills of the run's switches and the info symbol (a
copy of core's InfoButton)."""

from __future__ import annotations

import subprocess

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QLabel, QLineEdit, QSizePolicy, QTextBrowser, QToolButton, QVBoxLayout,
    QWidget,
)

from . import window_title
from .help_page import WINDOW, help_html, page_style
from .theme import ACCENT, BLUE, GREY, OUTLINE, header_font, muted, surface_style


class HelpDialog(QDialog):
    """ps5-cores-bisect.sh's own ``--help`` (the single source of what the options do, so the help never drifts
    from the script) as a styled page (help_page.py): a title, what the window does, How it works, the options in a
    table, the link."""

    def __init__(self, script: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(window_title("help"))
        self.setModal(True)
        self.resize(820, 640)
        layout = QVBoxLayout(self)

        self.page = QTextBrowser()
        self.page.setOpenExternalLinks(True)
        self.page.document().setDefaultStyleSheet(page_style(ACCENT, muted(), GREY))
        self.page.document().setDocumentMargin(14)
        self.page.setHtml(help_html(self._help_text(script), WINDOW))
        layout.addWidget(self.page)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _help_text(script: str) -> str:
        try:
            result = subprocess.run(
                ["bash", script, "--help"], capture_output=True, text=True, timeout=10, check=False)
            if result.stdout.strip():
                return result.stdout
        except (OSError, subprocess.SubprocessError):
            pass
        return (
            "Could not read ps5-cores-bisect.sh --help.\n\n"
            "Run it from a terminal instead:\n"
            f"  bash {script} --help"
        )


class SudoDialog(QDialog):
    def __init__(self, message: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(window_title("administrator password"))
        self.setModal(True)
        layout = QVBoxLayout(self)
        text = QLabel(("Writing the SMU mailbox and installing the systemd service need root, so this runs "
                       "ps5-cores-unlock.sh through sudo.\nYour password is passed to sudo only and is never stored."))
        text.setWordWrap(True)
        layout.addWidget(text)
        if message:
            err = QLabel(message)
            err.setStyleSheet("color:#e57373; font-weight:600;")
            err.setWordWrap(True)
            layout.addWidget(err)
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText("sudo password")
        layout.addWidget(self.edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setEnabled(False)
        self.edit.textChanged.connect(lambda text: self._ok_btn.setEnabled(bool(text)))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.edit.setFocus()

    @classmethod
    def ask(cls, parent: QWidget | None, message: str = "") -> str | None:
        dlg = cls(message, parent)
        ok = dlg.exec() == QDialog.DialogCode.Accepted
        password = dlg.edit.text()
        dlg.edit.clear()
        dlg.deleteLater()
        return password if ok else None


class MetricBox(QFrame):
    """One box of the header's second row: a big value with a caption, centered, on the theme's surface with
    *colour* as its left edge. A copy of core's MetricBox with the same sizes (and same_width): this app is not on
    core."""

    MIN_WIDTH = 120

    def __init__(self, caption: str, colour: str = BLUE, parent: QWidget | None = None):
        super().__init__(parent)
        self.peers: list[MetricBox] = []        # same_width(): the boxes this one keeps its width with
        self.set_colour(colour)
        self.setMinimumWidth(self.MIN_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 7, 11, 7)         # 12, 8, 12, 8 inside the border
        layout.setSpacing(0)
        self.value = QLabel("—")
        self.value.setStyleSheet(header_font() + "font-size:22px; font-weight:800;")
        self.caption = QLabel(caption)
        self.caption.setStyleSheet("font-size:12px; font-weight:600;")
        for label in (self.value, self.caption):
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(label)

    def set_value(self, text: str, tooltip: str = "") -> None:
        self.value.setText(text)
        self.setToolTip(tooltip)
        if self.peers:
            _even(self.peers)

    def set_colour(self, colour: str) -> None:
        """The box's state or category color, its left edge."""
        self.setStyleSheet(surface_style(colour) + "QLabel { background:transparent; border:none; }")


class Pill(MetricBox):
    """A header pill that is a button, as the status boxes look: the value in large type, what it is under it; the
    accent edge under the mouse or the keyboard focus. A click, Enter or Space emits clicked. A copy of core's Pill."""

    clicked = pyqtSignal()

    def __init__(self, value: str, caption: str, tooltip: str = "", colour: str = BLUE):
        super().__init__(caption, colour)
        self.setObjectName("pill")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)      # never cut off
        self.set_value(value, tooltip)

    def set_colour(self, colour: str) -> None:
        super().set_colour(colour)
        # A pill that cannot be clicked (setEnabled(False)) shows its text muted, as a disabled button does.
        # The rule is on the labels' own state: Qt ignores an ancestor's pseudo-state in a selector, so
        # "#pill:disabled QLabel" would mute every pill.
        self.setStyleSheet(self.styleSheet() + f"#pill:hover, #pill:focus {{ border-color:{OUTLINE}; }}"
                           f"#pill QLabel:disabled {{ color:{muted()}; }}")

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            return
        super().keyPressEvent(event)

    def click(self) -> None:
        self.clicked.emit()


def same_width(boxes: list[MetricBox]) -> None:
    """A row of boxes all as wide as the widest, and again whenever a value changes; never narrower than their
    text (the minimum width alone would let a narrow window cut it off)."""
    for box in boxes:
        box.peers = boxes
        box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    _even(boxes)


def _even(boxes: list[MetricBox]) -> None:
    width = max([MetricBox.MIN_WIDTH, *(box.sizeHint().width() for box in boxes)])
    for box in boxes:
        box.setMinimumWidth(width)



class TogglePill(Pill):
    """A switch of the run as a pill (owner, 19-11-2026: the switches are pills, not check boxes): its name in large
    type, On or Off under it, the accent edge while it is on. A click, Enter or Space turns it over while it is
    enabled. It stands in for a QCheckBox: isChecked(), setChecked() and toggled."""

    toggled = pyqtSignal(bool)

    def __init__(self, name: str, tooltip: str = "", checked: bool = False):
        super().__init__(name, "Off", tooltip, GREY)
        self.checked = False
        self.clicked.connect(self._flip)
        self.setChecked(checked)

    def isChecked(self) -> bool:  # noqa: N802 (as QCheckBox's)
        return self.checked

    def setChecked(self, checked: bool) -> None:  # noqa: N802 (as QCheckBox's)
        changed = checked != self.checked
        self.checked = checked
        self.caption.setText("On" if checked else "Off")
        self.set_colour(ACCENT if checked else GREY)
        if changed:
            self.toggled.emit(checked)

    def _flip(self) -> None:
        if self.isEnabled():
            self.setChecked(not self.checked)


class InfoButton(QToolButton):
    """A small round "i" that opens an explanation below it on a click, where a line of text would take the room
    (owner, 01-11-2026); its tooltip says what it explains. A copy of core's InfoButton: this app is not on core.
    The text is rich text with its links clickable; a click outside it or Escape closes it."""

    SIZE = 22
    MAX_WIDTH = 380

    def __init__(self, text: str, tooltip: str = "What this does", parent: QWidget | None = None):
        super().__init__(parent)
        self.text_ = text
        self.popup: QWidget | None = None
        self.setText("i")
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setStyleSheet(
            f"QToolButton {{ border:1px solid {ACCENT}; border-radius:{self.SIZE // 2}px; color:{ACCENT}; "
            "background:transparent; font-weight:800; font-family:Georgia, serif; font-style:italic; padding:0; }"
            f"QToolButton:hover, QToolButton:focus {{ background:{ACCENT}; color:white; }}")
        self.clicked.connect(self.show_text)

    def show_text(self) -> None:
        if self.popup is not None:
            self.popup.close()
        # Wayland maps a popup relative to a parent surface, so it is a child of the button's window.
        self.popup = QWidget(self.window(), Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        box = QVBoxLayout(self.popup)
        box.setContentsMargins(0, 0, 0, 0)
        label = QLabel(self.text_)
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setStyleSheet(
            f"QLabel {{ background:palette(window); color:palette(window-text); border:1px solid {ACCENT}; "
            "border-radius:6px; padding:8px 10px; }")
        label.setFixedWidth(min(self.MAX_WIDTH, max(label.sizeHint().width(), 200)))
        box.addWidget(label)
        self.popup.adjustSize()
        self.popup.move(self.mapToGlobal(QPoint(-12, self.height() + 4)))
        self.popup.show()
