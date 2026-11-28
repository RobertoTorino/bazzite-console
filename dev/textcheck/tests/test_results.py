# SPDX-License-Identifier: GPL-3.0-or-later
"""What a run of the text check found, read from its --json file and its table, in the tool's order."""

from __future__ import annotations

import json

from nexus_text_check import TEXT_CHECK, results
from nexus_text_check.results import FileResult, Problem

# The tool's output, as text_check.py prints it: its first line, the table, the summary
OUTPUT = """Checking 40 files, 9000 words...
  to fix per 1000  advice   words  file
       2     20.0       1     100  docs/apps/fan.md
       1      2.0       0     500  README.md

3 to fix and 1 pieces of advice (Vale's style hints).
4 problems in 2 of 40 files, 9000 words (0.4 per 1000 words).
rules long sentence 1, LanguageTool spelling 1, Vale readability 1, Vale advice 1
"""
PROBLEMS = [
    {"path": "README.md", "line": 3, "check": "LanguageTool", "kind": "spelling", "message": "Possible spelling "
     "mistake found.", "text": "the [colr] of it", "suggestion": "color / cold"},
    {"path": "docs/apps/fan.md", "line": 9, "check": "Vale", "kind": "advice", "message": "'is shown' may be "
     "passive voice. (write-good.Passive)", "text": "is shown", "suggestion": ""},
    {"path": "docs/apps/fan.md", "line": 4, "check": "rules", "kind": "long sentence", "message": "31 words. "
     "Split it.", "text": "A very long sentence", "suggestion": ""},
    {"path": "docs/apps/fan.md", "line": 4, "check": "Vale", "kind": "readability", "message": "Try to keep "
     "the Flesch-Kincaid grade level below 8. (Readability.FleschKincaid)", "text": "", "suggestion": ""},
]


def test_the_files_come_in_the_tools_order_with_their_counts():
    found = results.results(OUTPUT, results.read_problems(json.dumps(PROBLEMS)))
    assert [r.path for r in found] == ["docs/apps/fan.md", "README.md"]       # worst first, as the table says
    fan = found[0]
    assert (fan.words, fan.to_fix, fan.advice) == (100, 2, 1)
    assert [fan.count(check) for check in results.CHECKS] == [1, 0, 2]
    assert fan.per_1000 == 20.0
    assert [(p.line, p.check) for p in fan.problems] == [(4, "Vale"), (4, "rules"), (9, "Vale")]


def test_a_file_the_table_left_out_comes_last_by_its_count():
    extra = [*PROBLEMS, {"path": "docs/x.md", "line": 1, "check": "rules", "kind": "semicolon", "message": "m",
                         "text": "t", "suggestion": ""}]
    found = results.results(OUTPUT, results.read_problems(json.dumps(extra)))
    assert found[-1].path == "docs/x.md" and found[-1].per_1000 is None


def test_the_first_line_and_the_summary():
    assert results.checked(OUTPUT) == (40, 9000)
    assert results.summary(OUTPUT) == "4 problems in 2 of 40 files, 9000 words (0.4 per 1000 words)."
    assert results.checked("This tool needs podman.") is None and results.summary("") == ""


def test_the_end_of_the_output_says_why_it_stopped():
    output = "Checking 3 files, 50 words...\n\nThis tool needs Vale: brew install vale\n"
    assert results.last_lines(output, 1) == "This tool needs Vale: brew install vale"
    assert results.last_lines(output) == "Checking 3 files, 50 words...\nThis tool needs Vale: brew install vale"


def test_a_problem_has_the_fields_of_the_tools_json():
    """The tool's Problem and this one stay alike: the --json file fills every field."""
    tool = results.load_tool(TEXT_CHECK)
    assert list(tool.Problem.__dataclass_fields__) == list(Problem.__dataclass_fields__)
    assert FileResult("a").per_1000 is None


def test_without_podman_nothing_else_is_asked(monkeypatch):
    monkeypatch.setattr(results.shutil, "which", lambda name: None)
    assert results.probe(TEXT_CHECK) == results.Server(False, False, None)


def test_the_server_as_the_tool_sees_it(monkeypatch):
    """The tool's own podman call and shared_server(), with podman replaced: no test runs podman."""
    calls = []

    class Done:
        def __init__(self, code, out=""):
            self.returncode, self.stdout = code, out

    def fake_run(command, **_kwargs):
        calls.append(command[1:3])
        return Done(0, "127.0.0.1:41234\n") if command[1] == "port" else Done(1)

    monkeypatch.setattr(results.shutil, "which", lambda name: "/usr/bin/podman")
    monkeypatch.setattr("subprocess.run", fake_run)
    server = results.probe(TEXT_CHECK)
    assert server == results.Server(True, False, "http://127.0.0.1:41234")
    assert calls == [["image", "exists"], ["port", f"{TEXT_CHECK.parents[1].name}-languagetool"]]
