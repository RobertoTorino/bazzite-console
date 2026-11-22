# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/all_tests.py: ALL-TESTS.md is the list of the tests as they are (owner, 17-11-2026), and the wiki shows it
under Development."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("all_tests", SUITE / "tools" / "all_tests.py")
at = importlib.util.module_from_spec(spec)
sys.modules["all_tests"] = at
spec.loader.exec_module(at)


def suite(folder: Path) -> Path:
    tests = folder / "apps" / "fan" / "tests"
    tests.mkdir(parents=True)
    (tests / "test_guard.py").write_text('''import pytest


def test_it_stops_at_the_limit():
    """The guard stops the board at the limit. Not before."""


@pytest.mark.parametrize("speed", [1, 2, 3])
def test_every_speed(speed):
    pass


class TestCurve:
    def test_a_point(self):
        pass
''', encoding="utf-8")
    scripts = folder / "tools" / "installer-tests"
    scripts.mkdir(parents=True)
    (scripts / "fan.sh").write_text("#!/usr/bin/env bash\n# SPDX-License-Identifier: GPL-3.0-or-later\n"
                                    "# Exercise apps/fan/install.sh (the guard too): install, then\n# uninstall. "
                                    "Runs with the shims.\nset -u\n", encoding="utf-8")
    (scripts / "shims.sh").write_text("# no test\n", encoding="utf-8")
    (folder / "mkdocs.yml").write_text("# license\n\nsite_name: Some Suite\nsite_url: https://example.org/\n",
                                       encoding="utf-8")
    return folder


def test_the_list_is_written_from_the_tests(tmp_path):
    text = at.write(suite(tmp_path))
    assert text.startswith("<!-- SPDX-License-Identifier: GPL-3.0-or-later -->\n\n# All tests (Some Suite)\n")
    assert "3 test functions (3 cases counting the parametrized ones) in 1 test folders, and 1 installer tests." in text
    assert "| `test_guard.py` | `test_it_stops_at_the_limit` |  |  | The guard stops the board at the limit. |" in text
    assert "| `test_guard.py` | `test_every_speed` |  |  | Every speed. |" in text
    assert "| `test_guard.py` | `TestCurve::test_a_point` |  |  | A point. |" in text
    assert "| `fan.sh` | Exercise apps/fan/install.sh (the guard too). |" in text and "shims.sh" not in text


def test_the_cases_and_times_of_a_run_stay_until_the_next_one(tmp_path):
    """Written again without a run, the file keeps what a run gave it: only the tests themselves change it."""
    folder = suite(tmp_path)
    values = {("apps/fan", "test_guard.py", "test_every_speed"): (3, 1.26, ""),
              ("apps/fan", "test_guard.py", "TestCurve::test_a_point"): (1, 0.01, at.SKIPPED)}
    ran = at.write(folder, values, {"apps/fan": 1.3}, ran=True)
    assert "| `test_guard.py` | `test_every_speed` | 3 | 1.3 s | Every speed. |" in ran
    assert "A point. (Skipped here.) |" in ran and "3 tests in 1 files, 1.3 s in a local run." in ran
    assert "limit. (Not run here: it needs the built native module" in ran          # in no report of the run
    (folder / at.NAME).write_text(ran, encoding="utf-8")
    assert at.current(folder) == ran
    test = folder / "apps" / "fan" / "tests" / "test_guard.py"
    test.write_text(test.read_text(encoding="utf-8") + "\n\ndef test_a_new_one():\n    pass\n", encoding="utf-8")
    assert "| `test_guard.py` | `test_a_new_one` |  |  | A new one. |" in at.current(folder) != ran


def test_the_suites_list_is_its_tests():
    """ALL-TESTS.md is what tools/all_tests.py writes from the tests now: run it after a test is added, renamed or
    removed (Nexus Release Tool's Commit does)."""
    assert (SUITE / at.NAME).read_text(encoding="utf-8") == at.current(SUITE), "run python3 tools/all_tests.py"


def test_the_wiki_shows_it_under_development():
    nav = (SUITE / "mkdocs.yml").read_text(encoding="utf-8")
    assert "      - All tests: development/all-tests.md" in nav
    assert "development/all-tests.md" in (SUITE / "tools" / "mkdocs" / "hooks.py").read_text(encoding="utf-8")
