# SPDX-License-Identifier: GPL-3.0-or-later
"""The app's own game folders (library.py) and what Games Uninstall offers to delete."""

from __future__ import annotations

from conftest import make_game

from kytyps5_manager import library
from kytyps5_manager.games import scan


def test_the_own_folder_is_made_and_a_drives_is_added(tmp_path):
    drive = tmp_path / "media" / "USB"
    (drive / "Games" / "PS5").mkdir(parents=True)
    other = tmp_path / "media" / "empty"
    other.mkdir()
    folders = library.fixed(tmp_path / "home", lambda: [drive, other])
    assert folders == [tmp_path / "home" / "Games" / "PS5", drive / "Games" / "PS5"]
    assert folders[0].is_dir()


def test_what_games_uninstall_offers(tmp_path):
    root = tmp_path / "Games" / "PS5"
    make_game(root / "one", "One")
    make_game(root / "nest" / "two", "Two", "PPSA00002")
    make_game(root / "nest", "Outer", "PPSA00003")
    found = scan([root])
    one, outer = (next(g for g in found if g.title == t) for t in ("One", "Outer"))
    items, why = library.removal_items(one, [root], found, in_steam=True)
    assert [(i.label, i.paths) for i in items] == [("one (the game's folder)", (root / "one",)),
                                                   ("Its shortcut in Steam", ())] and why == ""
    assert [i.key for i in library.removal_items(one, [root], found, in_steam=False)[0]] == [str(root / "one")]
    items, why = library.removal_items(outer, [root], found, in_steam=False)
    assert items == [] and why == "nest holds another game too (Two): delete Outer's files by hand."


def test_a_game_folder_itself_is_never_offered(tmp_path):
    root = tmp_path / "Games" / "PS5"
    make_game(root, "Loose")
    game = scan([root])[0]
    items, why = library.removal_items(game, [root], [game], in_steam=False)
    assert items == [] and why == "Loose is in PS5, one of the app's game folders itself: delete its files by hand."
