# SPDX-License-Identifier: GPL-3.0-or-later

"""The SoC's 8 physical cores of 2 threads each, large, each cell with its state in color and in words: on now,
not tested yet, testing, healthy, fails every time, fails at random, or not read yet."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QSizePolicy, QWidget

from .progress import CORES

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
LEGEND = ("<span style='color:#2e7d32'>■</span> on now &nbsp; <span style='color:#757575'>■</span> not "
          "tested yet &nbsp; <span style='color:#f9a825'>■</span> testing &nbsp; <span style='color:#1565c0'>■</span> "
          "healthy &nbsp; <span style='color:#c62828'>■</span> fails every time &nbsp; "
          "<span style='color:#ef6c00'>■</span> fails at random")


class CoreMap(QWidget):
    CELL_HEIGHT = 56

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.cells: list[QLabel] = []
        for core in CORES:
            cell = QLabel()
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setMinimumSize(96, self.CELL_HEIGHT)
            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            grid.addWidget(cell, core // 4, core % 4)
            self.cells.append(cell)
        for column in range(4):
            grid.setColumnStretch(column, 1)
        self.states: list[str] = []
        self.set_states(["unknown"] * len(CORES))

    def set_states(self, states: list[str]) -> None:
        self.states = list(states)
        for core, state in enumerate(states):
            colour, word = CELLS[state]
            cell = self.cells[core]
            cell.setText(f"core{core}\n{word}")
            cell.setStyleSheet(f"background:{colour}; color:white; border-radius:6px; font-size:14px; "
                               "font-weight:700;")
