# SPDX-License-Identifier: GPL-3.0-or-later
"""The wiki's sections to read again after a change (tools/check_wiki.py; owner, 22-11-2026): a section that names a
changed file and did not change itself, as the Development chapter's part about pins on 20-11-2026."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_wiki  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="needs git")


def commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                    "commit", "-qm", message], check=True)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "apps" / "demo" / "demo").mkdir(parents=True)
    (tmp_path / "core" / "demo_core").mkdir(parents=True)
    (tmp_path / "docs" / "development").mkdir(parents=True)
    (tmp_path / "apps" / "demo" / "demo" / "emulator.py").write_text('PINNED_BUILD = "1"\n', encoding="utf-8")
    (tmp_path / "core" / "demo_core" / "builds.py").write_text("def use(build):\n    pass\n", encoding="utf-8")
    (tmp_path / "docs" / "development" / "index.md").write_text(
        "# Development\n\n## Pins\n\nThe manager installs `PINNED_BUILD` from `emulator.py`.\n\n"
        "## Builds\n\nCore's `builds` keeps them, `builds.use()` picks one.\n\n## Other\n\nNothing named.\n",
        encoding="utf-8")
    monkeypatch.setattr(check_wiki, "ROOT", tmp_path)
    return tmp_path, commit(tmp_path, "first")


def test_a_section_that_names_a_changed_file_is_listed(repo):
    root, base = repo
    (root / "apps" / "demo" / "demo" / "emulator.py").write_text('PINNED_BUILD = "2"\n', encoding="utf-8")
    (root / "core" / "demo_core" / "builds.py").write_text("def use(build):\n    return build\n", encoding="utf-8")
    found = check_wiki.review(base, root=root)
    assert [line.split(":")[0] for line in found] == ["docs/development/index.md#pins", "docs/development/index.md#builds"]
    assert "core/demo_core/builds.py (core's module)" in found[1]


def test_a_section_that_changed_with_the_code_is_left_out(repo):
    root, base = repo
    (root / "apps" / "demo" / "demo" / "emulator.py").write_text('PINNED_BUILD = "2"\n', encoding="utf-8")
    page = root / "docs" / "development" / "index.md"
    page.write_text(page.read_text(encoding="utf-8").replace("installs `PINNED_BUILD`", "was tried with `PINNED_BUILD`"),
                    encoding="utf-8")
    head = commit(root, "second")
    assert check_wiki.review(base, head, root=root) == []


def test_a_test_or_a_changelog_is_no_reason():
    assert not check_wiki.counts("apps/demo/tests/test_emulator.py")
    assert not check_wiki.counts("apps/demo/CHANGELOG") and check_wiki.counts("apps/demo/demo/emulator.py")
    assert not check_wiki.counts("apps/demo/.gitignore")


def test_a_comment_in_a_code_block_is_no_heading():
    page = "## Usage\n\n```bash\n# run it\ntools/x.sh\n```\n\nMore.\n"
    assert [title for title, _ in check_wiki.sections(page)] == ["Usage"]
