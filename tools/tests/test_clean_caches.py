# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/clean_caches.py: which venvs, pytest folders and scratch folders it removes, and what it leaves."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import clean_caches as cc  # noqa: E402

NOW = time.time()


def aged(path: Path, days: float, text: str = "x") -> Path:
    """*path* written *days* ago."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    when = NOW - days * cc.DAY
    os.utime(path, (when, when))
    return path


def test_a_venv_goes_a_week_after_its_last_run(tmp_path):
    venvs = tmp_path / "venvs"
    aged(venvs / "old" / cc.USED, 8)
    aged(venvs / "old" / "lib" / "big.so", 30, "x" * 5000)
    aged(venvs / "used" / cc.USED, 2)
    aged(venvs / "used" / "lib" / "big.so", 30)
    found = cc.stale_venvs(venvs, NOW)
    assert [f.path.name for f in found] == ["old"] and found[0].size >= 5000


def test_a_venv_from_before_the_marks_is_marked_and_stays(tmp_path):
    """The first run removes nothing: a venv without a mark may be one a job uses."""
    venvs = tmp_path / "venvs"
    aged(venvs / "unknown" / "pyvenv.cfg", 40)
    assert cc.stale_venvs(venvs, NOW, write=False) == [] and not (venvs / "unknown" / cc.USED).exists()   # a dry run
    assert cc.stale_venvs(venvs, NOW) == [] and (venvs / "unknown" / cc.USED).exists()
    assert cc.stale_venvs(tmp_path / "no-such-folder", NOW) == []


def test_pytests_folders_go_after_a_day(tmp_path):
    base = tmp_path / "pytest-of-me"
    aged(base / "pytest-7" / "test_a0" / "card.ps2", 3)
    aged(base / "pytest-8" / "test_a0" / "card.ps2", 0.2)
    aged(base / "notes.txt", 9)                                            # not a run of pytest's
    assert [f.path.name for f in cc.old_pytest_runs(tmp_path, "me", NOW)] == ["pytest-7"]
    assert cc.old_pytest_runs(tmp_path, "someone-else", NOW) == []


def test_a_scratch_folder_goes_when_nothing_in_it_changed_for_six_hours(tmp_path):
    """A session that still runs wrote to its folder lately: one new file keeps the whole folder."""
    base = tmp_path / f"claude-{os.getuid()}" / "project"
    aged(base / "ended" / "scratchpad" / "a.bin", 0.3)                    # seven hours ago
    aged(base / "idle" / "scratchpad" / "a.bin", 0.2)                     # under five: it may still be in use
    aged(base / "running" / "scratchpad" / "old.bin", 5)
    aged(base / "running" / "tasks" / "now.output", 0.01)
    found = cc.old_scratch(tmp_path, os.getuid(), NOW)
    assert [f.path.name for f in found] == ["ended"]


def test_a_link_is_never_followed_or_removed(tmp_path):
    outside = aged(tmp_path / "outside" / "keep.txt", 30).parent
    base = tmp_path / "pytest-of-me"
    base.mkdir()
    (base / "pytest-3").symlink_to(outside)
    assert cc.old_pytest_runs(tmp_path, "me", NOW) == []


def test_the_run_removes_what_it_found_and_a_dry_run_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setattr(cc.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    monkeypatch.setattr(cc.getpass, "getuser", lambda: "me")
    monkeypatch.setattr(cc, "prune_images", lambda dry_run: 0)
    monkeypatch.setattr(cc, "crash_dumps", lambda: 2 * cc.DUMPS_LIMIT)
    venv = aged(tmp_path / "cache" / cc.CI_CACHE / "venvs" / "old" / cc.USED, 9).parent
    run = aged(tmp_path / "tmp" / "pytest-of-me" / "pytest-1" / "f", 2).parent
    assert cc.main(["--dry-run"]) == 0 and venv.exists() and run.exists()
    said = capsys.readouterr().out
    assert said.count("would go: ") == 2 and "2 folders under 1 MB" in said and cc.DUMPS_COMMAND in said
    assert cc.main([]) == 0 and not venv.exists() and not run.exists()
    assert "removed: " in capsys.readouterr().out
    assert cc.main(["--quiet"]) == 0
    assert capsys.readouterr().out.strip().endswith(cc.DUMPS_COMMAND)      # nothing went: only the dumps' line
    assert cc.size_text(3 << 30) == "3.0 GB" and cc.size_text(5 << 20) == "5.0 MB" and cc.size_text(2048) == "2 kB"
