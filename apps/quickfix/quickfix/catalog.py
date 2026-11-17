# SPDX-License-Identifier: GPL-3.0-or-later
"""The quickfixes: one small window each, for one job. The portal shows each as a tile of its own in Utilities, from
the [[apps.quickfix.quickfixes]] tables of its apps.toml, which name the same keys, names and summaries
(tests/test_catalog.py keeps the two the same)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quickfix:
    key: str                    # "tools": ps5-quickfix tools opens it
    name: str                   # "Quickfix"
    summary: str                # one line, on its tile and in the list
    changes_board: bool = False


QUICKFIXES: tuple[Quickfix, ...] = (
    Quickfix("tools", "Quickfix",
           "The optional tools Board Test's tests use: which are there, and their installer."),
    Quickfix("mangohud", "MangoHud Config",
           "Open or create MangoHud's config, edit and save it; turn on the FPS log Board Test reads."),
    Quickfix("mapcount", "Game Memory Map",
           "Raise vm.max_map_count, the number of memory areas a game may map.", changes_board=True),
    Quickfix("journal", "Persistent Journal",
           "Keep the system journal on the disk, so the logs of a boot that crashed can be read after it.",
           changes_board=True),
    Quickfix("cmdline", "Boot Command Line",
           "Edit cmdline.txt, the kernel command line the PS5 loader starts Linux with.", changes_board=True),
)

BY_KEY = {quickfix.key: quickfix for quickfix in QUICKFIXES}
