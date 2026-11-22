# SPDX-License-Identifier: GPL-3.0-or-later
"""The wiki names only what is there (tools/wiki_names.py; owner, 22-11-2026): its paths, the constants and functions
it names in code style, the options of our scripts and the window labels it tells you to use."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wiki_names  # noqa: E402


def test_everything_the_wiki_names_is_there():
    assert wiki_names.problems() == []


def test_a_gone_name_is_found(tmp_path):
    (tmp_path / "docs" / "apps").mkdir(parents=True)
    (tmp_path / "apps" / "demo" / "demo").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    (tmp_path / "apps" / "demo" / "demo" / "window.py").write_text(
        'PIN = "1.0"\ndef start():\n    pill("Demo", "Install")\n    button("Delete")\n'
        '    box("Use a {0} from this PC:".format(NAME))\n', encoding="utf-8")
    (tmp_path / "tools" / "run.sh").write_text('case "$1" in --check) ;; esac\n', encoding="utf-8")
    (tmp_path / "docs" / "apps" / "demo.md").write_text(
        "`apps/demo/demo/window.py` `apps/demo/gone.py` `PIN` `OLD_PIN` `start()` `stop()`\n"
        "`tools/run.sh --check` `tools/run.sh --fix`\n"
        "Click **Delete**, then **Demo Install** and the **Remove** button. Press **Shift+Tab**.\n"
        "Check **Use a demo.dll from this PC**.\n", encoding="utf-8")
    assert wiki_names.problems(tmp_path) == [
        "docs/apps/demo.md: apps/demo/gone.py (no such path)",
        "docs/apps/demo.md: OLD_PIN (no such name in the code)",
        "docs/apps/demo.md: stop() (no such function in the code)",
        "docs/apps/demo.md: tools/run.sh --fix (--fix is not an option of tools/run.sh)",
        "docs/apps/demo.md: **Remove** (no such label in the app)"]
