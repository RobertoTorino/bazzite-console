# SPDX-License-Identifier: GPL-3.0-or-later
"""The app's own game folders, as PS5 shadPS4 Manager's (fixed folders, no folder choosing): Games/PS5 in the user's
home folder, made when the app opens, and Games/PS5 on each removable drive that has one (a USB drive or an SD card;
core's drives). The games are dropped there, each in a folder of its own."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bazzite_console_core import keep
from bazzite_console_core.drives import game_folders, removable_drives

from .games import Game

GAMES_HOME = Path("Games") / "PS5"      # the app's own game folder, in the home folder and on a removable drive


def fixed(home: Path, drives: Callable[[], list[Path]] = removable_drives) -> list[Path]:
    """The app's own game folders: Games/PS5 in the home folder, made when it is missing, then Games/PS5 on each
    removable drive that has one."""
    return game_folders(home, GAMES_HOME, drives)


# --- Games Uninstall (before deleting anything, the user decides what to keep; core's keep) ----------------------

STEAM_ITEM = "steam"


def removal_items(game: Game, chosen: list[Path], found: list[Game], in_steam: bool) -> tuple[list[keep.Item], str]:
    """The keep page's rows for Games Uninstall: the game's folder, then its shortcut in Steam when it is in Steam.
    With no rows, why not: a drive, a game folder of the list (or one holding one) or a folder holding another game
    is never offered. The saves stay."""
    folder = game.folder
    if folder.parent == folder:
        return [], f"{game.title} is at the top of {folder}: delete its files by hand."
    for place in chosen:
        if place == folder or folder in place.parents:
            return [], f"{game.title} is in {folder.name}, one of the app's game folders itself: delete its files by hand."
    for other in found:
        if other.eboot != game.eboot and folder in other.eboot.parents:
            return [], f"{folder.name} holds another game too ({other.title}): delete {game.title}'s files by hand."
    items = [keep.Item(str(folder), f"{folder.name} (the game's folder)", (folder,))]
    if in_steam:
        items.append(keep.Item(STEAM_ITEM, "Its shortcut in Steam"))
    return items, ""
