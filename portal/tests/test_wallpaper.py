# SPDX-License-Identifier: GPL-3.0-or-later
"""The portal's example wallpaper: shipped, within the rules, and the wallpaper until the user chooses another or
none."""

from __future__ import annotations

from bazzite_console_portal import wallpaper


def test_the_example_is_shipped_and_meets_the_rules(qapp):
    assert wallpaper.EXAMPLE.is_file() and wallpaper.problem(wallpaper.EXAMPLE) == ""


def test_the_portal_starts_with_the_example(qapp, tmp_path):
    assert wallpaper.is_example(tmp_path) and wallpaper.shown(tmp_path) == wallpaper.EXAMPLE


def test_no_wallpaper_is_remembered_until_the_example_is_chosen_again(qapp, tmp_path):
    wallpaper.remove(tmp_path)
    assert not wallpaper.is_example(tmp_path) and wallpaper.shown(tmp_path) is None
    wallpaper.use_example(tmp_path)
    assert wallpaper.shown(tmp_path) == wallpaper.EXAMPLE


def test_a_picture_of_the_users_own_goes_before_the_example_and_ends_no_wallpaper(qapp, tmp_path):
    wallpaper.remove(tmp_path / "state")
    own = wallpaper.choose(wallpaper.EXAMPLE, tmp_path / "state")
    assert wallpaper.shown(tmp_path / "state") == own
    assert not (tmp_path / "state" / wallpaper.NONE).exists()
