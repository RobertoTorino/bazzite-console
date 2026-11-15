# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/ci_matrix.py: the CI matrix read from the suite's folders (stage 2 of the release redesign), as the plan
job of ci.yml and tools/ci_local.py read it."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ci_matrix", ROOT / "tools" / "ci_matrix.py")
cm = importlib.util.module_from_spec(spec)
sys.modules["ci_matrix"] = cm
spec.loader.exec_module(cm)


def suite(folder: Path, system: str, apps: dict[str, bool]) -> Path:
    """A suite with *apps* (name: whether it has tests/), its portal and tools with tests, and some folders that
    never count."""
    (folder / "portal" / "tests").mkdir(parents=True)
    (folder / "portal" / "apps.toml").write_text("", encoding="utf-8")
    (folder / "tools" / "tests").mkdir(parents=True)
    (folder / "SYSTEM").write_text(f"{system}\n", encoding="utf-8")
    for app, tested in apps.items():
        (folder / "apps" / app).mkdir(parents=True)
        (folder / "apps" / app / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        if tested:
            (folder / "apps" / app / "tests").mkdir()
    (folder / "apps" / "zed" / "node_modules" / "tests").mkdir(parents=True)        # no VERSION, and never listed
    (folder / "site" / "tests").mkdir(parents=True)
    (folder / ".venv-linux" / "lib" / "tests").mkdir(parents=True)
    return folder


def test_the_pytest_matrix_is_every_folder_with_tests(tmp_path):
    bazzite = suite(tmp_path, "bazzite", {"gpu": True, "fan": True, "noui": False})
    assert cm.pytest_dirs(bazzite) == ["apps/fan", "apps/gpu", "portal", "tools"]


def test_the_suite_matches_its_workflow_and_the_layout_rule():
    """ci.yml reads its matrix from this tool, and the list is what tools/tests/test_layout.py wants: every folder
    with tests/, core, tools and dev/ among them."""
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tools/ci_matrix.py pytest" in text and "dir: ${{ fromJSON(needs.plan.outputs.dirs) }}" in text
    dirs = cm.pytest_dirs(ROOT)
    assert {"core", "tools", "portal", "dev/nrt", "apps/fan"} <= set(dirs)
    assert all((ROOT / d / "tests").is_dir() for d in dirs)


def test_the_command_line(capsys):
    assert cm.main(["pytest"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("dirs=[") and "portal" in json.loads(out.removeprefix("dirs="))
