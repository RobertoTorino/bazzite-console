# SPDX-License-Identifier: GPL-3.0-or-later

"""The GPU's 4 shader-array rows of 5 WGPs, large, each cell with its state in color and in words: on now, locked
and not tested, testing, healthy, fails every time, fails at random, or not read yet. At the right end of each row,
the Mask column shows the row's mask (owner, 23-11-2026: see the values, not only the cells): the hex value of the
WGPs that are on, and the same bits under it, WGP4 first, so 0x07,0x07,0x07,0x0b reads off the map."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QSizePolicy, QWidget

from .progress import ROWS
from .theme import header_font, muted

# state -> (background, word)
CELLS = {
    "on": ("#2e7d32", "On"),
    "wait": ("#424242", "Not tested"),
    "now": ("#f9a825", "Testing"),
    "ok": ("#1565c0", "Healthy"),
    "bad": ("#c62828", "Fails"),
    "random": ("#ef6c00", "Random"),
    "unknown": ("#303030", "Not read"),
}
LEGEND = ("<span style='color:#2e7d32'>■</span> on now &nbsp; <span style='color:#757575'>■</span> locked, not "
          "tested &nbsp; <span style='color:#f9a825'>■</span> testing &nbsp; <span style='color:#1565c0'>■</span> "
          "healthy &nbsp; <span style='color:#c62828'>■</span> fails every time &nbsp; "
          "<span style='color:#ef6c00'>■</span> fails at random")


class CuMap(QWidget):
    CELL_HEIGHT = 40

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.cells: list[list[QLabel]] = []
        for r, row in enumerate(ROWS):
            name = QLabel(row)
            name.setStyleSheet(header_font() + "font-size:15px; font-weight:700;")
            grid.addWidget(name, r, 0)
            cells = []
            for b in range(5):
                cell = QLabel()
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setMinimumSize(110, self.CELL_HEIGHT)
                cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                grid.addWidget(cell, r, b + 1)
                cells.append(cell)
            self.cells.append(cells)
        self.masks: list[QLabel] = []
        for r in range(len(ROWS)):
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumWidth(90)
            grid.addWidget(label, r, 6)
            self.masks.append(label)
        for b in range(5):
            grid.setColumnStretch(b + 1, 1)
        self.states: list[list[str]] = []
        self.set_states([["unknown"] * 5 for _ in ROWS])

    def set_states(self, states: list[list[str]]) -> None:
        self.states = [list(row) for row in states]
        for r, row in enumerate(states):
            for b, state in enumerate(row):
                colour, word = CELLS[state]
                cell = self.cells[r][b]
                cell.setText(f"WGP{b}\n{word}")
                cell.setStyleSheet(f"background:{colour}; color:white; border-radius:6px; font-size:13px; "
                                   "font-weight:700;")
            if "unknown" in row:
                self.masks[r].setText("<span style='font-size:17px; font-weight:800;'>\u2014</span>")
                self.masks[r].setToolTip("Not read yet.")
                continue
            value = sum(1 << b for b, state in enumerate(row) if state == "on")
            bits = "".join("1" if value >> b & 1 else "0" for b in range(4, -1, -1))
            self.masks[r].setText(f"<span style='font-size:17px; font-weight:800;'>0x{value:02x}</span><br><span "
                                  f"style='color:{muted()}; font-size:12px; font-family:monospace;'>{bits}</span>")
            self.masks[r].setToolTip(f"{ROWS[r]}: 0x{value:02x}, the green WGPs of this row. The bits read WGP4 "
                                     "first, WGP0 last.")
