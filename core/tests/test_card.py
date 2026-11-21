# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from PyQt6.QtWidgets import QComboBox

from bazzite_console_core.card import CardWindow
from bazzite_console_core.widgets import ActionPill, InfoButton, MetricBox, RefreshButton


class Card(CardWindow):
    def __init__(self, tmp_path, info="What it does"):
        super().__init__(tmp_path / "missing.png", "Example", "1.2.3", info)
        self.reads = 0

    def refresh(self):
        self.reads += 1


def test_card_has_the_symbols_in_the_title_row_and_no_pill_there(qapp, tmp_path):
    card = Card(tmp_path)
    row = [card.header.title_row.itemAt(i).widget() for i in range(card.header.title_row.count())]
    assert row == [card.header.title, card.state, card.info, None, card.refresh_button]      # None: the stretch
    assert isinstance(card.refresh_button, RefreshButton) and card.refresh_button.width() == InfoButton.SIZE
    assert card.windowTitle() == "Example" and not card.info.isHidden()
    card.refresh_button.click()
    assert card.reads == 1
    assert Card(tmp_path, info="").info.isHidden()                       # no text: no symbol


def test_card_rows_hold_five_even_places_and_give_the_width(qapp, tmp_path):
    card = Card(tmp_path)
    boxes = [MetricBox("One"), MetricBox("Two"), ActionPill("A much longer action", "Click"), ActionPill("On", "x"),
             ActionPill("Off", "y")]
    pick = QComboBox()
    card.set_rows(boxes, [ActionPill("More", "z"), pick])
    assert card.header.right.count() == 3                                # the title row and two rows of places
    widths = {box.minimumWidth() for box in boxes}
    assert len(widths) == 1 and widths.pop() >= boxes[2].sizeHint().width()
    assert card.width() == card.card_width(boxes[0].minimumWidth())      # the fifth place ends at the border
    assert pick.minimumWidth() != boxes[0].minimumWidth()                # not a box: its own width
    with pytest.raises(AssertionError):
        Card(tmp_path).set_rows([MetricBox(str(i)) for i in range(6)])
    with pytest.raises(NotImplementedError):
        CardWindow(tmp_path / "x.png", "Bare").refresh()
