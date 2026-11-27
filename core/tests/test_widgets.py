# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton, QTabBar, QTableWidget, QTableWidgetItem,
                             QWidget)

from bazzite_console_core import theme
from bazzite_console_core.widgets import (
    ActionPill, AppHeader, InfoButton, MetricBox, Pill, RefreshButton, RoundedToolTip, StatusPill, StatusText, Terminal,
    TextDialog, accent_button, hide_tooltip, same_width, set_button_active, show_tooltip,
)


def test_status_pill_colours(qapp):
    """The theme's surface; the state a colored left edge, the edge's color for neutral."""
    pill = StatusPill()
    assert pill.text() == "Unknown"
    assert f"border-left:4px solid {theme.THEME.edge}" in pill.styleSheet()
    pill.set_status("Active", "ok", "tip")
    assert (pill.text(), pill.toolTip()) == ("Active", "tip")
    assert f"border-left:4px solid {theme.GREEN}" in pill.styleSheet()
    assert "white" not in pill.styleSheet()                                     # the theme's text color
    pill.set_status("?", "no-such-kind")
    assert f"border-left:4px solid {theme.THEME.edge}" in pill.styleSheet()


def test_status_text_colours(qapp):
    status = StatusText()
    assert status.text() == "Unknown" and "palette(window-text)" in status.label.styleSheet()
    status.set_status("Test failed", "bad", "tip")
    assert (status.text(), status.toolTip(), status.kind) == ("Test failed", "tip", "bad")
    assert theme.RED in status.label.styleSheet() and theme.RED in status.dot.styleSheet()
    assert "font-weight:700" in status.label.styleSheet()
    status.set_status("Not installed", "warn")
    assert theme.ORANGE in status.label.styleSheet()
    status.set_status("?", "no-such-kind")
    assert "palette(window-text)" in status.label.styleSheet()


def test_status_text_with_a_name_shows_the_name_alone(qapp):
    """The dot shows the state (owner, 22-11-2026): the name stays, the state opens the tooltip."""
    status = StatusText(name="shadNet")
    status.set_status("shadNet Offline", "bad", "The server does not answer.")
    assert status.shown() == "shadNet" and status.text() == "shadNet Offline" and status.kind == "bad"
    assert status.toolTip() == "shadNet Offline\nThe server does not answer."
    assert theme.RED in status.dot.styleSheet()
    status.set_status("shadNet Off", "neutral")
    assert status.shown() == "shadNet" and status.toolTip() == "shadNet Off"
    assert theme.RED in status.dot.styleSheet() and status.kind == "neutral"      # two colors: anything not ok is red
    status.set_status("Not installed", "warn")
    assert theme.RED in status.dot.styleSheet() and theme.ORANGE not in status.label.styleSheet()
    status.set_status("shadNet Online", "ok")
    assert theme.GREEN in status.dot.styleSheet()
    assert StatusText("Ready").shown() == "Ready"                     # without a name: the state, as before


def test_metric_box(qapp):
    box = MetricBox("GPU clock", theme.PURPLE)
    box.set_value("1800 MHz", "now")
    assert (box.value.text(), box.caption.text(), box.toolTip()) == ("1800 MHz", "GPU clock", "now")
    centre = Qt.AlignmentFlag.AlignHCenter
    assert box.value.alignment() & centre and box.caption.alignment() & centre        # centered by default
    left = MetricBox("GPU clock", theme.PURPLE, centred=False)
    assert not left.value.alignment() & centre
    assert f"border-left:4px solid {theme.PURPLE}" in box.styleSheet()
    box.set_colour(theme.RED)
    assert f"border-left:4px solid {theme.RED}" in box.styleSheet() and theme.PURPLE not in box.styleSheet()
    assert f"border-left:4px solid {theme.BLUE}" in MetricBox("Neutral").styleSheet()   # GRAY: the suite's blue
    assert theme.THEME.edge not in MetricBox("Neutral").styleSheet().split("border-left")[1].split(";")[0]


def test_pill_is_a_metric_box_that_clicks(qapp):
    """A click, Enter or Space emits clicked; the silver outline under the mouse or the keyboard focus."""
    from PyQt6.QtCore import QEvent
    from PyQt6.QtGui import QKeyEvent
    pill = Pill("Refresh", "Click to refresh", "tip")
    assert (pill.value.text(), pill.caption.text(), pill.toolTip()) == ("Refresh", "Click to refresh", "tip")
    assert f"#pill:hover, #pill:focus {{ border-color:{theme.OUTLINE}; }}" in pill.styleSheet()
    clicks = []
    pill.clicked.connect(lambda: clicks.append(1))
    pill.click()
    for key in (Qt.Key.Key_Space, Qt.Key.Key_Return):
        pill.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
    assert clicks == [1, 1, 1]
    pill.set_colour(theme.RED)                                  # the edge color and the hover both stay
    assert theme.RED in pill.styleSheet() and "#pill:hover" in pill.styleSheet()


def _text_lightness(pill: Pill) -> int:
    """The bright end of the pill's text on its dark surface (inside the border; the 20th brightest pixel)."""
    image = pill.grab().toImage()
    return sorted(image.pixelColor(x, y).lightness() for x in range(10, image.width() - 10)
                  for y in range(6, image.height() - 6))[-20]


def test_a_pill_that_cannot_be_clicked_looks_muted(qapp):
    """Only a disabled pill's text is muted (a rule on the pill's own state would mute every pill: Qt ignores an
    ancestor's pseudo-state); enabled again, it is bright again."""
    row = QWidget()
    layout = QHBoxLayout(row)
    enabled, disabled = Pill("Update", "Firmware"), Pill("Update", "Firmware")
    disabled.setEnabled(False)
    for pill in (enabled, disabled):
        layout.addWidget(pill)
    row.show()
    qapp.processEvents()
    assert _text_lightness(disabled) < _text_lightness(enabled)
    disabled.setEnabled(True)
    disabled.set_colour(theme.RED)                              # the rule survives a new color
    qapp.processEvents()
    assert _text_lightness(disabled) == _text_lightness(enabled)
    disabled.setEnabled(False)
    qapp.processEvents()
    assert _text_lightness(disabled) < _text_lightness(enabled)
    row.close()


def test_same_width_follows_the_widest(qapp):
    boxes = [Pill("A", "a"), MetricBox("Caption"), Pill("No", "Icons on Desktop")]
    same_width(boxes)
    widths = {b.minimumWidth() for b in boxes}
    assert len(widths) == 1 and widths.pop() >= max(b.sizeHint().width() for b in boxes)
    boxes[1].set_value("A much longer value than any other")    # a value grows: every box with it
    wide = boxes[1].sizeHint().width()
    assert {b.minimumWidth() for b in boxes} == {wide} and wide > MetricBox.MIN_WIDTH
    boxes[1].set_value("—")                                    # and shrinks back
    assert {b.minimumWidth() for b in boxes} == {max(MetricBox.MIN_WIDTH, *(b.sizeHint().width() for b in boxes))}
    boxes[0].floor = 400                                       # a card's row that must fill a wider page
    same_width(boxes)
    assert {b.minimumWidth() for b in boxes} == {400}


def test_set_button_active_keeps_height(qapp):
    button = QPushButton("Stress test")
    height = button.sizeHint().height()
    set_button_active(button, True)
    assert theme.ACTIVE_RED in button.styleSheet()
    assert button.height() == height and button.minimumHeight() == button.maximumHeight() == height
    set_button_active(button, False)
    assert button.styleSheet() == ""


def test_accent_button(qapp):
    assert theme.ACCENT in accent_button("Apply").styleSheet()


def test_terminal_follows_end_only_when_at_end(qapp):
    term = Terminal()
    term.resize(300, 100)
    term.show()
    term.set_text("\n".join(map(str, range(200))))
    bar = term.verticalScrollBar()
    bar.setValue(bar.maximum())
    term.set_text("\n".join(map(str, range(400))))
    assert bar.value() == bar.maximum()
    bar.setValue(0)
    term.set_text("\n".join(map(str, range(600))))
    assert bar.value() == 0


def test_text_dialog(qapp):
    dialog = TextDialog("journal", "line 1\nline 2")
    assert dialog.terminal.toPlainText() == "line 1\nline 2"
    assert dialog.terminal.isReadOnly()


def test_tooltip_follows_window_and_survives_its_deletion(qapp):
    tip = RoundedToolTip(qapp)
    first = QWidget()
    first.show()
    tip.show_text(QPoint(10, 10), "hello", first)
    assert tip.popup.parentWidget() is first.window()     # Wayland: parented to the hovered window
    assert tip.popup.isVisible() and tip.label.text() == "hello"
    tip.hide()
    assert not tip.popup.isVisible()
    first.deleteLater()
    qapp.processEvents()
    qapp.sendPostedEvents(None, 0)
    second = QWidget()
    second.show()
    tip.show_text(QPoint(10, 10), "again", second)        # rebuilt when it died with the first window
    assert not sip.isdeleted(tip.popup)
    assert tip.popup.parentWidget() is second
    tip.show_text(QPoint(10, 10), "", second)
    assert not tip.popup.isVisible()


def test_long_tooltip_wraps(qapp):
    tip = RoundedToolTip(qapp)
    owner = QWidget()
    owner.show()
    tip.show_text(QPoint(0, 0), "word " * 200, owner)
    assert tip.label.wordWrap() and tip.label.width() == RoundedToolTip.MAX_WIDTH


def test_tooltip_border_is_the_outline(qapp):
    """Framed in the theme's outline, silver in the suite's themes, not the accent (owner, 07-11-2026); a theme
    without an outline of its own (Nexus's) keeps its accent."""
    from bazzite_console_core.nexus import NEXUS
    from bazzite_console_core.widgets import current_theme, set_theme
    before = current_theme()
    try:
        for name, look in theme.THEMES.items():
            set_theme(look)
            sheet = RoundedToolTip(qapp).label.styleSheet()
            assert f"border:1px solid {look.outline};" in sheet and look.accent not in sheet, name
        set_theme(NEXUS)
        assert f"border:1px solid {NEXUS.accent};" in RoundedToolTip(qapp).label.styleSheet()
    finally:
        set_theme(before)


def test_tooltip_never_covers_the_cursor(qapp):
    geo = QApplication.primaryScreen().availableGeometry()
    size = QSize(300, 200)
    below = RoundedToolTip._place(geo.topLeft() + QPoint(50, 50), size)
    assert below == geo.topLeft() + QPoint(62, 66)                # room below: below and right, as before
    corner = geo.bottomRight() - QPoint(10, 10)                   # a button low in the window, by the screen's edge
    above = RoundedToolTip._place(corner, size)
    assert not QRect(above, size).contains(corner)
    assert above.y() + size.height() < corner.y() and above.x() + size.width() < corner.x()


def test_tooltip_lets_clicks_through(qapp):
    tip = RoundedToolTip(qapp)
    assert tip.popup.windowFlags() & Qt.WindowType.WindowTransparentForInput
    owner = QWidget()
    owner.show()
    tip.show_text(QPoint(10, 10), "hello", owner)                 # also after it moved to another window
    assert tip.popup.windowFlags() & Qt.WindowType.WindowTransparentForInput


def test_item_view_tooltip_text(qapp):
    table = QTableWidget(1, 1)
    item = QTableWidgetItem("x")
    item.setToolTip("cell tip")
    table.setItem(0, 0, item)
    table.resize(200, 100)
    table.show()
    rect = table.visualItemRect(item)
    text, area = RoundedToolTip._text_at(table.viewport(), rect.center())
    assert text == "cell tip" and area == rect


def test_tab_tooltip_text(qapp):
    """A tab's tooltip (setTabToolTip) in the rounded style too (owner, 26-10-2026: the portal's tabs showed Qt's
    plain one); between the tabs the bar's own, or nothing."""
    bar = QTabBar()
    bar.addTab("One")
    bar.addTab("Two")
    bar.setTabToolTip(1, "second tip")
    bar.setExpanding(False)                                  # room beside the tabs
    bar.resize(400, 40)
    bar.show()
    rect = bar.tabRect(1)
    assert RoundedToolTip._text_at(bar, rect.center()) == ("second tip", rect)
    assert RoundedToolTip._text_at(bar, bar.tabRect(0).center()) == ("", bar.tabRect(0))
    assert RoundedToolTip._text_at(bar, QPoint(390, 20)) == (None, bar.rect())
    bar.setToolTip("the bar")
    assert RoundedToolTip._text_at(bar, QPoint(390, 20)) == ("the bar", bar.rect())


def test_tooltip_filter_is_removed_when_the_app_quits(qapp, monkeypatch):
    from PyQt6.QtCore import QObject, pyqtSignal

    class App(QObject):                     # stands in for the QApplication, so the real one keeps running
        aboutToQuit = pyqtSignal()

        def __init__(self):
            super().__init__()
            self.filters: list[QObject] = []

        def installEventFilter(self, obj):  # noqa: N802
            self.filters.append(obj)

        def removeEventFilter(self, obj):   # noqa: N802
            self.filters.remove(obj)

    monkeypatch.setattr(RoundedToolTip, "_instance", None)
    app = App()
    tip = RoundedToolTip.install(app)
    assert app.filters == [tip] and RoundedToolTip._instance is tip
    app.aboutToQuit.emit()
    assert app.filters == []


def test_tooltip_filter_is_removed_by_uninstall(qapp, monkeypatch):
    """The test sessions' teardown (conftest.py): the app's filter off, so it sees no more events."""
    seen: list[QEvent.Type] = []

    class Tip(RoundedToolTip):
        def eventFilter(self, obj, event):  # noqa: N802
            seen.append(event.type())
            return False

    tip = Tip.install(qapp)
    monkeypatch.setattr(RoundedToolTip, "_instance", tip)  # install() set it on the subclass
    widget = QWidget()
    QApplication.sendEvent(widget, QEvent(QEvent.Type.User))
    assert QEvent.Type.User in seen
    RoundedToolTip.uninstall()
    seen.clear()
    QApplication.sendEvent(widget, QEvent(QEvent.Type.User))
    assert seen == [] and RoundedToolTip._instance is None


def test_manual_tooltip_uses_installed_instance(qapp, monkeypatch):
    tip = RoundedToolTip(qapp)
    monkeypatch.setattr(RoundedToolTip, "_instance", tip)
    owner = QWidget()
    owner.show()
    show_tooltip(QPoint(5, 5), "chart value", owner)
    assert tip.popup.isVisible() and tip.label.text() == "chart value"
    hide_tooltip()
    assert not tip.popup.isVisible()


def test_app_header_layout(qapp, tmp_path):
    """Icon at 96 px spanning the title row (name, version, states, actions) and the second row."""
    header = AppHeader(tmp_path / "missing.png", "PS5 Test", "1.2.3")
    state, action, box = StatusText("Ready"), QPushButton("Refresh"), MetricBox("Load", theme.BLUE)
    header.add_state(state)
    header.add_action(action)
    second = QHBoxLayout()
    header.add_second(box, 1)
    header.add_second(second)
    window = QWidget()
    window.setLayout(header)
    assert header.logo.width() == header.logo.height() == AppHeader.LOGO_PX == 96
    assert header.logo.cursor().shape() == Qt.CursorShape.ArrowCursor
    assert "PS5 Test" in header.title.text() and "v1.2.3" in header.title.text()
    row = [header.title_row.itemAt(i).widget() for i in range(header.title_row.count())]
    assert row[0] is header.title and row[1] is state and row[2] is None and row[3] is action   # None: stretch
    second_state = StatusText("Two")
    header.add_state(second_state)
    assert header.title_row.itemAt(2).widget() is second_state
    assert header.second_row.itemAt(0).widget() is box and header.second_row.itemAt(1).layout() is second
    assert "v" not in AppHeader(tmp_path / "x.png", "Name").title.text().replace("Name", "")
    assert isinstance(header.title, QLabel)
    third, pill = header.add_row(), MetricBox("More")                    # under the second row, the icon at the top
    third.addWidget(pill)
    assert header.right.itemAt(2).layout() is third and third.spacing() == header.second_row.spacing()
    assert header.itemAt(0).alignment() == Qt.AlignmentFlag.AlignTop


def test_app_header_title_lines_up_with_the_second_row(qapp, tmp_path):
    """The title's text starts where the second row's does: no padding pushes it to the right."""
    from PyQt6.QtGui import QColor
    header = AppHeader(tmp_path / "missing.png", "Bazzite Console Suite Releases", "0.1.0")
    second = QLabel("working tree clean")
    header.add_second(second)
    window = QWidget()
    window.setStyleSheet("background:black; color:white;")
    window.setLayout(header)
    window.resize(800, 130)
    window.show()
    qapp.processEvents()
    image = window.grab().toImage()

    def first_ink(label: QLabel) -> int:
        box = label.geometry()
        return next(x for x in range(box.left(), box.right())
                    if any(QColor(image.pixel(x, y)).lightness() > 128 for y in range(box.top(), box.bottom())))

    assert header.title.x() == second.x()
    assert abs(first_ink(header.title) - first_ink(second)) <= 3     # the glyphs' own side bearing only
    window.close()


def test_a_wrapped_labels_minimum_height_follows_its_width(qapp):
    """A plain wrapped QLabel reports one line as its minimum, whatever it wraps to; a WrappedLabel reports the
    lines it needs at its width (owner, 24-10-2026: the Settings tab squeezed under a three-line introduction)."""
    from bazzite_console_core.widgets import WrappedLabel, hint_label
    text = "A long explanation " * 30
    plain, wrapped = hint_label(text), hint_label(text, follow_height=True)
    assert isinstance(wrapped, WrappedLabel) and not isinstance(plain, WrappedLabel)
    for label in (plain, wrapped):
        label.resize(300, 10)
        label.show()
    qapp.processEvents()
    one_line = plain.fontMetrics().height()
    assert plain.minimumSizeHint().height() <= one_line + 4
    assert wrapped.minimumHeight() == wrapped.heightForWidth(300) > 3 * one_line
    wrapped.setText("Short.")
    assert wrapped.minimumHeight() <= one_line + 4
    plain.close()
    wrapped.close()


def test_an_apps_own_theme(qapp):
    """An app that is not a suite's (Nexus Releases) draws the widgets with its own theme: the surfaces, the muted
    text and the accent follow set_theme(), and create_app(theme=) sets it (owner, 26-10-2026: a Nexus app takes
    Nexus's design)."""
    from PyQt6.QtGui import QPalette
    from bazzite_console_core import widgets
    from bazzite_console_core.app import create_app
    from bazzite_console_core.appinfo import AppInfo
    own = theme.Theme("Own", True, "#010101", "#0f0f0f", "#010101", "#c0c0c0", "#0f0f0f", "#010101", "#66808080",
                      "#17b6a7", "#010101")
    assert widgets.current_theme() is theme.THEME and widgets.accent() == theme.ACCENT
    try:
        app = create_app(AppInfo("x-own", "Own", "0.1.0"), theme=own)
        assert widgets.current_theme() is own and widgets.accent() == "#17b6a7"
        assert app.palette().color(QPalette.ColorRole.Window).name() == "#010101"
        box = MetricBox("Box", theme.GREEN)
        assert "stop:0 #0f0f0f, stop:1 #010101" in box.styleSheet() and "color:#c0c0c0" in box.styleSheet()
        assert f"border-left:4px solid {theme.GREEN}" in box.styleSheet()
        assert "border-color:#17b6a7" in Pill("1", "c").styleSheet()
        assert "border:2px solid #17b6a7" in accent_button("Go").styleSheet()
        assert "border-left:4px solid #66808080" in StatusPill().styleSheet()      # the own theme's edge
    finally:
        widgets.set_theme(theme.THEME)
        theme.apply_theme(qapp)
    assert f"border-left:4px solid {theme.THEME.edge}" in StatusPill().styleSheet()


def test_info_button_opens_its_text_below_it(qapp):
    """The info symbol (owner, 01-11-2026): a click opens the text in a popup that stays; links work in it."""
    owner = QWidget()
    button = InfoButton("The split is the part of the 16 GB the GPU keeps. <a href='https://example.org/'>Manual</a>",
                        parent=owner)
    owner.show()
    assert button.text() == "i" and button.toolTip() == "What this does"
    assert button.width() == button.height() == InfoButton.SIZE
    assert f"background:{theme.ACCENT}" in button.styleSheet() and "color:white" in button.styleSheet()  # filled
    refresh = RefreshButton()                                           # the same family, beside it
    assert refresh.size() == button.size() and f"background:{theme.ACCENT}" in refresh.styleSheet()
    assert refresh.text() == "↻" and refresh.toolTip() == "Read again"
    button.click()
    assert button.popup is not None and button.popup.isVisible()
    assert button.popup.windowFlags() & Qt.WindowType.Popup
    label = button.popup.findChild(QLabel)
    assert "the GPU keeps" in label.text() and label.wordWrap() and label.openExternalLinks()
    assert label.width() <= InfoButton.MAX_WIDTH
    first = button.popup
    button.set_text("Shorter.")
    button.click()                                                 # a second click replaces the popup
    qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert sip.isdeleted(first) and button.popup.findChild(QLabel).text() == "Shorter."
    button.popup.close()
    taken = []
    button.opens = taken.append                                    # the app opens a link itself
    button.set_text("Start it from <a href='steam://open/games'>Steam</a>.")
    button.click()
    label = button.popup.findChild(QLabel)
    assert not label.openExternalLinks()
    label.linkActivated.emit("steam://open/games")
    assert taken == ["steam://open/games"] and not button.popup.isVisible()
    qapp.processEvents()
    owner.close()


def test_action_pill_stands_in_for_a_button(qapp):
    from PyQt6.QtWidgets import QMenu
    pill = ActionPill("Turn on", "Click to apply", "tip")
    clicks = []
    pill.clicked.connect(lambda: clicks.append(1))
    assert pill.text() == "Turn on" and pill.caption.text() == "Click to apply"
    pill.setText("Apply")
    assert pill.text() == "Apply" and pill.toolTip() == "tip"
    pill.click()
    pill.setEnabled(False)
    pill.click()                                    # off: as a button, nothing happens
    assert clicks == [1]
    pill.setEnabled(True)
    menu = QMenu()
    menu.addAction("One")
    pill.setMenu(menu)
    pill.click()
    assert menu.isVisible() and clicks == [1, 1]
    menu.close()


def test_wheel_guard_leaves_a_value_until_a_click(qapp):
    """Over a list, a number field or a slider without the focus, the wheel changes nothing and the turn is left
    ignored, which QApplication::notify then hands to the parent (the page scrolls). After a click it changes it. A
    sent event is never spontaneous, so the parent's part needs a real wheel and is not tested here."""
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QWheelEvent
    from PyQt6.QtWidgets import QComboBox, QScrollBar, QSlider, QSpinBox, QVBoxLayout
    from bazzite_console_core.widgets import WheelGuard
    guard = WheelGuard.install(qapp)
    try:
        page = QWidget()
        lay = QVBoxLayout(page)
        combo, spin, slider = QComboBox(), QSpinBox(), QSlider(Qt.Orientation.Horizontal)
        bar = QScrollBar()
        combo.addItems(["one", "two", "three"])
        combo.setCurrentIndex(1)
        for w in (spin, slider, bar):
            w.setValue(50)
        button = QPushButton("Has the focus")
        for w in (button, combo, spin, slider, bar):
            lay.addWidget(w)
        page.show()
        button.setFocus()
        qapp.processEvents()

        def turn(widget: QWidget) -> bool:
            event = QWheelEvent(QPointF(5, 5), QPointF(widget.mapToGlobal(QPoint(5, 5))), QPoint(), QPoint(0, -120),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(widget, event)
            return event.isAccepted()

        for widget in (combo, spin, slider):
            assert widget.focusPolicy() == Qt.FocusPolicy.StrongFocus     # a turn does not give it the focus
            assert not turn(widget)
        assert (combo.currentIndex(), spin.value(), slider.value()) == (1, 50, 50)
        turn(bar)
        assert bar.value() != 50                                # a scroll bar scrolls as before
        for widget in (combo, spin, slider):
            widget.setFocus()
            qapp.processEvents()
            turn(widget)
        assert combo.currentIndex() != 1 and spin.value() != 50 and slider.value() != 50
        page.close()
    finally:
        qapp.removeEventFilter(guard)
        WheelGuard._instance = None
