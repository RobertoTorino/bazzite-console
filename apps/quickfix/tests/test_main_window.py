# SPDX-License-Identifier: GPL-3.0-or-later
"""The window opens offscreen with the suite's header and every quickfix; the version and the icons are where the
checks expect them."""

from __future__ import annotations

from quickfix import APP_ID, APP_NAME, INFO, LOGO_PATH, ROOT, __version__
from quickfix.catalog import QUICKFIXES
from quickfix.main_window import MainWindow


def test_version_is_the_single_source():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == __version__ == INFO.version


def test_icons_are_beside_the_package():
    assert LOGO_PATH.is_file() and LOGO_PATH.name == f"{APP_ID}.webp"
    assert (ROOT / "images" / f"{APP_ID}-128.png").is_file()


def test_window_lists_every_quickfix_and_opens_one(qapp):
    window = MainWindow()
    window.show()
    assert window.windowTitle() == APP_NAME
    assert list(window.buttons) == [h.key for h in QUICKFIXES]
    opened = window.open_quickfix("mangohud")
    assert opened.isVisible() and opened.windowTitle() == "MangoHud Config"
    assert window.open_quickfix("mangohud") is opened                    # one window per quickfix
    opened.close()
    window.close()
