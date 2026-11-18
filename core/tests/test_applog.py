# SPDX-License-Identifier: GPL-3.0-or-later
"""An app's log file (applog.py): where it is, what a line looks like, an uncaught error in it, the tail, and a
folder that cannot be made."""

from __future__ import annotations

import logging
import sys

from bazzite_console_core import applog


def test_the_file_and_its_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert applog.log_file("ps5-x") == tmp_path / "data" / "ps5-x" / "ps5-x.log"
    path = applog.setup("ps5-test-app", tmp_path / "logs" / "app.log")
    assert path == tmp_path / "logs" / "app.log"
    assert applog.setup("ps5-test-app", tmp_path / "other.log") == tmp_path / "other.log"     # second: no change
    log = applog.logger("ps5-test-app")
    log.info("PCSX2 2.8.2 is installed.")
    log.error("Steam was not changed: no Steam")
    lines = path.read_text().splitlines()
    assert len(lines) == 2 and len(log.handlers) == 1
    assert lines[0].endswith(" INFO PCSX2 2.8.2 is installed.") and lines[1].split()[2] == "ERROR"
    assert lines[0][2] == "-" and lines[0][10] == " "                           # DD-MM-YYYY HH:MM:SS
    assert applog.tail(path) == "\n".join(lines) and applog.tail(path, 1) == lines[1]
    assert applog.tail(tmp_path / "none.log") == ""
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


def test_an_uncaught_error_is_logged(tmp_path, monkeypatch):
    reported = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: reported.append(args[1]))
    path = applog.setup("ps5-test-crash", tmp_path / "crash.log")
    try:
        raise ValueError("boom")
    except ValueError as error:
        sys.excepthook(type(error), error, error.__traceback__)
    text = path.read_text()
    assert "CRITICAL Uncaught error" in text and "ValueError: boom" in text
    assert [str(e) for e in reported] == ["boom"]                                 # Python's own report still comes
    log = applog.logger("ps5-test-crash")
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


def test_without_a_folder_the_log_goes_to_stderr(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("")
    path = applog.setup("ps5-test-noroom", blocker / "app.log")              # a file where the folder would be
    log = applog.logger("ps5-test-noroom")
    assert isinstance(log.handlers[0], logging.StreamHandler) and not isinstance(log.handlers[0],
                                                                                 logging.FileHandler)
    log.info("still said")
    assert "still said" in capsys.readouterr().err and path == blocker / "app.log"
    log.handlers.clear()


def test_a_private_log_masks_the_users_folders(tmp_path, monkeypatch):
    """private=True (owner, 29-10-2026): no user name in a line."""
    from pathlib import Path
    home = Path("/home/someone")
    monkeypatch.setattr(Path, "home", lambda: home)
    path = applog.setup("ps5-private-app", tmp_path / "app.log", private=True)
    log = applog.logger("ps5-private-app")
    log.info(f"Game folder added: {home / 'Games'} (2 game(s)).")
    line = path.read_text(encoding="utf-8").splitlines()[0]
    assert str(home) not in line and "~" in line
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


def test_clear_empties_the_log_and_the_older_ones(tmp_path):
    """Clear logs (owner, 18-11-2026): the file emptied while it stays the app's log, the older ones removed."""
    path = applog.setup("ps5-test-clear", tmp_path / "app.log")
    log = applog.logger("ps5-test-clear")
    log.info("before")
    older = [tmp_path / f"app.log.{number}" for number in range(1, applog.KEPT + 1)]
    for file in older:
        file.write_text("older\n")
    assert applog.clear("ps5-test-clear", path)
    assert path.read_text() == "" and not any(file.exists() for file in older)
    log.info("after")                                   # still the app's log: its first line now
    lines = path.read_text().splitlines()
    assert len(lines) == 1 and lines[0].endswith(" INFO after")
    assert applog.clear("ps5-test-none", tmp_path / "none.log") and not (tmp_path / "none.log").exists()
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)
