# SPDX-License-Identifier: GPL-3.0-or-later
"""The portal's example wallpaper: shipped, within the rules, and chosen only by the user."""

from __future__ import annotations

from bazzite_console_portal import wallpaper


def test_the_example_is_shipped_and_meets_the_rules(qapp):
    assert wallpaper.EXAMPLE.is_file() and wallpaper.problem(wallpaper.EXAMPLE) == ""


def test_the_example_shows_once_chosen(qapp, tmp_path):
    assert wallpaper.shown(tmp_path) is None
    wallpaper.use_example(tmp_path)
    assert wallpaper.is_example(tmp_path) and wallpaper.shown(tmp_path) == wallpaper.EXAMPLE
    wallpaper.remove(tmp_path)
    assert wallpaper.shown(tmp_path) is None
