# SPDX-License-Identifier: GPL-3.0-or-later
"""The changelog check scopes Git history to bazzite-console, including in a parent checkout."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t")

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")

spec = importlib.util.spec_from_file_location("check_changelogs", TOOLS / "check_changelogs.py")
check_changelogs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = check_changelogs
spec.loader.exec_module(check_changelogs)

OLD = "Changelog: 02-10-2026 10:00:00\n\nFixed.\n\nChangelog: 01-10-2026 10:00:00\n\nAdded.\n"
NEW = "Changelog: 03-10-2026 10:00:00\n\nUpdated.\n\n"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True, env=ENV).stdout


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "bazzite-console"
    for path in ("CHANGELOG", "apps/alpha/CHANGELOG"):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(OLD, encoding="utf-8")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "tag", "base")
    return root


def test_new_entries_keep_history_in_nested_project(project: Path):
    (project / "CHANGELOG").write_text(NEW + OLD, encoding="utf-8")
    assert check_changelogs.check(project, "base") == []


def test_lost_entries_are_reported_with_project_relative_paths(project: Path):
    (project / "apps/alpha/CHANGELOG").write_text(NEW, encoding="utf-8")
    assert check_changelogs.check(project, "base") == [
        "apps/alpha/CHANGELOG: 2 of the 2 entries it had at base are gone "
        "(the newest: 'Changelog: 02-10-2026 10:00:00')"
    ]


def test_a_staged_rename_keeps_the_changelog(project: Path, tmp_path: Path):
    (project / "dev").mkdir()
    git(tmp_path, "mv", "bazzite-console/apps/alpha", "bazzite-console/dev/alpha")
    (project / "dev/alpha/CHANGELOG").write_text(NEW + OLD, encoding="utf-8")
    assert check_changelogs.renamed(project, "base") == {
        "apps/alpha/CHANGELOG": "dev/alpha/CHANGELOG"
    }
    assert check_changelogs.check(project, "base") == []
