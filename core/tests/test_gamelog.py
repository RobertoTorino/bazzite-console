# SPDX-License-Identifier: GPL-3.0-or-later
"""gamelog.sh, the emulator log of the game managers' run wrappers: a stand-in wrapper sources it and runs a stand-in
emulator. Every line in the app's form (the time and a level); the game by its path, or by its title alone (Vita3K
starts one by its title ID); an option as the last argument is not a game. The managers' own wrapper tests (KytyPS5
Manager's in full) cover the rest."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

GAMELOG = Path(__file__).resolve().parents[1] / "bazzite_console_core" / "gamelog.sh"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="a bash script for Linux")


def _run(tmp_path: Path, *args: str, title: str = "", script: str = "echo playing\n") -> list[str]:
    """The stand-in wrapper's log, each line without its time; it asserts every line has one and a level."""
    build = tmp_path / "emulator" / "current"
    build.mkdir(parents=True, exist_ok=True)
    (build / "emu").write_text("#!/bin/bash\n" + script)
    (build / "emu").chmod(0o755)
    (tmp_path / "devices").write_text("")
    wrapper = tmp_path / "wrapper"
    wrapper.write_text(f'''#!/usr/bin/env bash
set -euo pipefail
. "{GAMELOG}"
GAMELOG_NAME="Emu"
GAMELOG_BUILD="{build}"
GAMELOG_TITLE="{title}"
INPUT_DEVICES="{tmp_path / "devices"}"
EMULATOR_LOG="{tmp_path / "emulator.log"}"
game=""
for arg in "$@"; do game=$arg; done
gamelog_run "{build / "emu"}" "$@"
''')
    environ = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "SteamGameId")}
    environ.update(GAMELOG_WAIT="0", GAMELOG_SYS=str(tmp_path / "sys"), HOME=str(tmp_path))
    subprocess.run(["/bin/bash", str(wrapper), *args], capture_output=True, env=environ, check=False)
    lines = (tmp_path / "emulator.log").read_text().splitlines()
    assert all(re.match(r"\d\d-\d\d-\d{4} \d\d:\d\d:\d\d (INFO|WARNING|ERROR) ", line) for line in lines)
    (tmp_path / "emulator.log").unlink()
    return [line[20:] for line in lines]


def test_the_game_by_its_path_or_by_its_title(tmp_path):
    game = tmp_path / "Games" / "My Game.iso"
    game.parent.mkdir()
    game.write_text("")
    assert "INFO Game: My Game.iso, from ~/Games/My Game.iso." in _run(tmp_path, "--fullscreen", str(game))
    assert "INFO Game: title ID PCSB00245." in _run(tmp_path, "-r", "PCSB00245", title="title ID PCSB00245")
    assert not any(line.startswith("INFO Game:") for line in _run(tmp_path, "--fullscreen"))   # an option


def test_what_the_emulator_prints_gets_a_level(tmp_path):
    lines = _run(tmp_path, script='echo "Initialized: Config"\necho "WARNING: GPU not fully supported"\n'
                                  'echo "ERROR: ld.so: cannot preload"\necho "GEM_CREATE failed: no memory"\n'
                                  'echo "Fatal error in the renderer"\nexit 2\n')
    assert ["INFO Initialized: Config", "WARNING GPU not fully supported", "ERROR ld.so: cannot preload",
            "WARNING GEM_CREATE failed: no memory", "ERROR Fatal error in the renderer"] == [
        line for line in lines if not line.split(" ", 1)[1].startswith(("Emu ", "Build", "Board", "Processor",
                                                                          "Controller", "Session", "Memory",
                                                                          "System log", "Display", "Desktop"))]
    assert "WARNING Controller: none connected." in lines
    assert re.fullmatch(r"WARNING Emu ended \(exit code 2\) after \d+ s\.", next(l for l in lines if "ended" in l))
