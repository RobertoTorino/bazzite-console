# SPDX-License-Identifier: GPL-3.0-or-later
"""The card: the template of a small window (owner, 21-11-2026), first used by the quickfixes.

    ┌────────┐  Name  v1.2.3   ● State  (i)                               (↻)
    │  icon  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │ 96 px  │  │  box   │ │  box   │ │  pill  │ │  pill  │ │  pill  │
    └────────┘  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
    the page: whatever the card holds, which gives it its height

The title row has the name with the version, the state, the info symbol with what the app does, and the refresh
symbol at the right end. No pill stands in that row. Under it are the rows of boxes and pills, five on a row at
most, all as wide as the widest. The card is as wide as a full row, so the fifth place ends at the right border.
A place takes its hover text when it is filled (MetricBox.set_value(), Pill's tooltip). A card that needs another
width sets it after set_rows(): an exception, which is the owner's decision."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from .widgets import AppHeader, InfoButton, MetricBox, RefreshButton, StatusText, same_width


class CardWindow(QMainWindow):
    """A card: the header, then the page the app fills (self.page). A subclass gives its rows to set_rows() and
    reads its state in refresh()."""

    ROW_MAX = 5                         # boxes and pills on one row under the title
    HEIGHT = 420                        # to start with; a card resizes to what it holds

    def __init__(self, logo: str | Path, name: str, version: str = "", info: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(name)
        self.header = AppHeader(logo, name, version)
        self.state = StatusText()
        self.header.add_state(self.state)
        self.info = InfoButton(info)
        self.info.setVisible(bool(info))
        self.header.add_state(self.info)
        self.refresh_button = RefreshButton()
        self.refresh_button.clicked.connect(lambda: self.refresh())
        self.header.add_action(self.refresh_button)
        contents = QWidget()
        self.page = QVBoxLayout(contents)
        self.page.addLayout(self.header)
        self.setCentralWidget(contents)
        self.resize(self.card_width(MetricBox.MIN_WIDTH), self.HEIGHT)

    def set_rows(self, *rows: list[QWidget]) -> None:
        """The boxes and pills under the title, left to right: the first row beside the icon, each further one under
        it."""
        for number, widgets in enumerate(rows):
            assert len(widgets) <= self.ROW_MAX, f"{len(widgets)} on one row"
            row = self.header.second_row if number == 0 else self.header.add_row()
            for widget in widgets:
                row.addWidget(widget)
            row.addStretch(1)
        self.even([widget for widgets in rows for widget in widgets])

    def even(self, widgets: list[QWidget]) -> None:
        """Every box and pill as wide as the widest, and the card as wide as a full row of them. Another widget on
        a row (a list to pick from) keeps its own width."""
        boxes = [widget for widget in widgets if isinstance(widget, MetricBox)]
        if boxes:
            same_width(boxes)
            self.resize(self.card_width(boxes[0].minimumWidth()), self.height())

    def card_width(self, place: int) -> int:
        """The card's width with places of *place* pixels."""
        margins, gap = self.page.contentsMargins(), self.header.second_row.spacing()
        return (margins.left() + margins.right() + AppHeader.LOGO_PX + self.header.spacing()
                + self.ROW_MAX * place + (self.ROW_MAX - 1) * gap)

    def refresh(self) -> None:
        raise NotImplementedError
