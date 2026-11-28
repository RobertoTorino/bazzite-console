# SPDX-License-Identifier: GPL-3.0-or-later
"""The window opens offscreen with Nexus's header, runs a fake of the text check as a process of its own, fills the
tables from what it wrote, and keeps its pills in step with the LanguageTool server. No test runs podman or the
real tool."""

from __future__ import annotations

import textwrap

from PyQt6.QtWidgets import QApplication

from nexus_text_check import APP_NAME, CHECKOUT, LOGO_PATH
from nexus_text_check.main_window import MainWindow
from nexus_text_check.results import Server

from test_results import OUTPUT, PROBLEMS

READY = Server(True, True, None)


def fake_tool(tmp_path, output=OUTPUT, problems=PROBLEMS, code=0):
    """A stand-in for tools/text_check.py: it writes down its arguments, writes *problems* to its --json file and
    prints *output*."""
    script = tmp_path / "text_check.py"
    script.write_text(textwrap.dedent(f"""\
        import json, sys
        args = sys.argv[1:]
        with open({str(tmp_path / 'args.log')!r}, "a") as log:
            log.write(" ".join(args) + "\\n")
        if "--json" in args and {code} == 0:
            with open(args[args.index("--json") + 1], "w") as out:
                json.dump({problems!r}, out)
        print({output!r}, end="")
        sys.exit({code})
        """))
    return script


def calls(tmp_path) -> list[str]:
    return (tmp_path / "args.log").read_text().splitlines()


def settle(window) -> None:
    """Lets the running tool and the look at the server finish."""
    if window.process is not None:
        assert window.process.waitForFinished(20000)
    while window.worker.running:
        QApplication.processEvents()
    QApplication.processEvents()


def open_window(tmp_path, servers=(READY,), **tool):
    """A window on a fake tool, its looks at the server answered from *servers* in turn (the last one stays)."""
    answers = list(servers)
    looks = []

    def prober(path):
        looks.append(path)
        return answers.pop(0) if len(answers) > 1 else answers[0]

    window = MainWindow(tool=fake_tool(tmp_path, **tool), prober=prober)
    window.looks = looks
    settle(window)
    return window


def test_the_header_is_nexus_with_the_pills(tmp_path):
    window = open_window(tmp_path)
    assert window.windowTitle() == APP_NAME and LOGO_PATH.is_file()
    assert [p.text() for p in (window.all_pill, window.check_pill, window.start_pill, window.stop_pill)] == \
        ["Check all", "Check…", "Start", "Stop"]
    assert window.state.text() == "Ready"
    window.close()


def test_the_pills_follow_the_server(tmp_path):
    window = open_window(tmp_path)
    assert window.server_box.value.text() == "Off"
    assert window.all_pill.isEnabled() and window.check_pill.isEnabled()
    assert window.start_pill.isEnabled() and not window.stop_pill.isEnabled()
    window.close()
    window = open_window(tmp_path, servers=(Server(True, True, "http://127.0.0.1:41234"),))
    assert window.server_box.value.text() == "Running"
    assert not window.start_pill.isEnabled() and window.stop_pill.isEnabled()  # what runs cannot start again
    window.close()


def test_without_podman_nothing_runs(tmp_path):
    window = open_window(tmp_path, servers=(Server(False, False, None),))
    assert window.server_box.value.text() == "No podman" and window.state.text() == "No podman"
    assert not any(p.isEnabled() for p in (window.all_pill, window.check_pill, window.start_pill, window.stop_pill))
    assert "needs podman" in window.line.text()
    window.close()


def test_before_the_download_the_window_says_its_size(tmp_path):
    window = open_window(tmp_path, servers=(Server(True, False, None),))
    assert window.server_box.value.text() == "Not downloaded"
    assert "about 250 MB" in window.line.text() and window.start_pill.isEnabled()
    window.close()


def test_check_all_fills_the_files_worst_first_and_a_file_shows_its_problems(tmp_path):
    window = open_window(tmp_path)
    window.all_pill.click()
    assert not window.all_pill.isEnabled() and not window.start_pill.isEnabled()   # one run at a time
    assert window.state.text() == "Checking the whole suite"
    settle(window)

    assert calls(tmp_path)[0].startswith("--json ")                 # no paths: the whole suite
    assert window.json_path is None
    rows = [[window.files.item(r, c).text() for c in range(window.files.columnCount())]
            for r in range(window.files.rowCount())]
    assert rows == [["docs/apps/fan.md", "2", "20.0", "1", "1", "0", "2"],
                    ["README.md", "1", "2.0", "0", "0", "1", "0"]]
    assert window.state.text() == "3 to fix"
    assert window.line.text() == "4 problems in 2 of 40 files, 9000 words (0.4 per 1000 words)."
    assert window.problems.rowCount() == 3                           # the first file is selected
    window.files.selectRow(1)
    problem = [window.problems.item(0, c).text() for c in range(window.problems.columnCount())]
    assert problem == ["3", "LanguageTool", "spelling", "Possible spelling mistake found.", "the [colr] of it",
                       "color / cold"]
    assert window.all_pill.isEnabled() and len(window.looks) == 2    # it looks at the server again after a run
    window.close()


def test_nothing_to_fix(tmp_path):
    window = open_window(tmp_path, output="Checking 1 files, 20 words...\n0 problems in 0 of 1 files, 20 words.\n",
                         problems=[])
    window.check_path(CHECKOUT / "README.md")
    settle(window)
    assert calls(tmp_path)[0].startswith("README.md --json ")        # from the repository's root
    assert window.state.text() == "Nothing to fix" and window.files.rowCount() == 0
    window.close()


def test_only_a_path_in_the_checkout(tmp_path):
    window = open_window(tmp_path)
    window.check_path(tmp_path)
    assert window.process is None and not (tmp_path / "args.log").exists()
    assert "is not in this checkout" in window.line.text()
    window.check_path(CHECKOUT)                                       # the root itself: the whole suite
    settle(window)
    assert calls(tmp_path)[0].startswith("--json ")
    window.close()


def test_a_failing_tool_says_why(tmp_path):
    window = open_window(tmp_path, output="Checking 3 files, 50 words...\nThis tool needs Vale: brew install vale\n",
                         code=1)
    window.check([])
    settle(window)
    assert window.state.text() == "Failed"
    assert "The text check failed." in window.line.text() and "brew install vale" in window.line.text()
    assert window.files.rowCount() == 0 and window.all_pill.isEnabled()
    window.close()


def test_a_broken_json_file_is_a_failure(tmp_path):
    window = open_window(tmp_path, problems="not a list")
    window.check([])
    settle(window)
    assert window.state.text() == "Failed"
    window.close()


def test_start_and_stop_run_the_tools_server_and_look_again(tmp_path):
    running = Server(True, True, "http://127.0.0.1:41234")
    window = open_window(tmp_path, servers=(READY, running, READY), output="LanguageTool runs at "
                         "http://127.0.0.1:41234. Stop it with: python3 tools/text_check.py --server stop\n")
    window.start_pill.click()
    assert window.state.text() == "Starting the server"
    settle(window)
    assert calls(tmp_path) == ["--server start"]
    assert window.server_box.value.text() == "Running" and window.stop_pill.isEnabled()
    assert "runs" in window.line.text()
    window.stop_pill.click()
    settle(window)
    assert calls(tmp_path)[-1] == "--server stop"
    assert window.server_box.value.text() == "Off" and window.start_pill.isEnabled()
    window.close()


def test_a_server_that_does_not_start(tmp_path):
    window = open_window(tmp_path, output="LanguageTool's container did not start. Error: no image\n", code=1)
    window.start_pill.click()
    settle(window)
    assert window.state.text() == "Failed" and "did not start" in window.line.text()
    window.close()


def test_closing_during_a_check_ends_the_tool(tmp_path):
    window = open_window(tmp_path)
    window.tool.write_text("import time\ntime.sleep(30)\n")
    window.check([])
    json_path = window.json_path
    window.close()
    assert window.process is None and not json_path.exists()

