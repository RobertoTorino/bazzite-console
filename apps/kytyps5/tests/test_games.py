# SPDX-License-Identifier: GPL-3.0-or-later
"""The game scan (games.py) on folders made in a temp folder: the title, ID and version from param.json, the
folder's name without one, depth, doubles and a folder that cannot be read."""

from __future__ import annotations

import json

from conftest import make_game

from kytyps5_manager import games
from kytyps5_manager.games import Game, scan


def test_a_game_is_read_from_its_param_json(tmp_path):
    eboot = make_game(tmp_path / "PPSA21567-app0", "ASTRO BOT", "PPSA21567", "01.019.000", pictures=False)
    assert scan([tmp_path]) == [Game(eboot, "ASTRO BOT", "PPSA21567", "01.019.000")]
    assert scan([tmp_path])[0].folder == tmp_path / "PPSA21567-app0"


def test_the_title_in_the_default_language_else_any(tmp_path):
    assert games.title_of({"localizedParameters": {"defaultLanguage": "ja-JP", "en-US": {"titleName": "English"},
                                                   "ja-JP": {"titleName": "Japanese"}}}) == "Japanese"
    assert games.title_of({"localizedParameters": {"defaultLanguage": "fr-FR",
                                                   "en-US": {"titleName": " English "}}}) == "English"
    assert games.title_of({"localizedParameters": {"defaultLanguage": "en-US", "en-US": {}}}) == ""
    assert games.title_of({"localizedParameters": "x"}) == "" and games.title_of({}) == ""


def test_without_or_with_a_broken_param_json_the_folder_names_the_game(tmp_path):
    plain = make_game(tmp_path / "Plain Game")
    broken = make_game(tmp_path / "Broken")
    (broken.parent / "sce_sys" / "param.json").write_text("{not json")
    listed = make_game(tmp_path / "A list")
    (listed.parent / "sce_sys" / "param.json").write_text(json.dumps([1, 2]))
    assert [(g.title, g.title_id, g.version) for g in scan([tmp_path])] == [
        ("A list", "", ""), ("Broken", "", ""), ("Plain Game", "", "")]
    assert plain.parent.name == "Plain Game"


def test_depth_doubles_and_what_is_skipped(tmp_path):
    deep = tmp_path
    for n in range(games.MAX_DEPTH + 1):
        deep = deep / f"d{n}"
    make_game(deep, "Too deep")
    make_game(tmp_path / "a" / "b" / "game", "Found")
    make_game(tmp_path / ".hidden" / "game", "Hidden")
    (tmp_path / "a" / "b" / "game" / "sce_sys" / "eboot.bin").write_text("")     # never looked in
    assert [g.title for g in scan([tmp_path, tmp_path / "a", tmp_path / "missing"])] == ["Found"]


def test_a_games_pictures(tmp_path, qapp):
    with_art = scan([make_game(tmp_path / "one", "One", pictures=True).parent])[0]
    assert with_art.picture("icon0.png") == tmp_path / "one" / "sce_sys" / "icon0.png"
    assert scan([make_game(tmp_path / "two", "Two").parent])[0].picture("icon0.png") is None
