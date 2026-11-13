# SPDX-License-Identifier: GPL-3.0-or-later
"""The version check covers the suite's apps and portal, not sibling suites."""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import check_versions  # noqa: E402


def app(root: Path, folder: str, version: str = "1.2.3") -> Path:
    unit = root / folder
    package = unit / "package"
    package.mkdir(parents=True)
    (unit / "VERSION").write_text(version + "\n", encoding="utf-8")
    (package / "__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    (package / "install.sh").write_text(f'VERSION="{version}"\n', encoding="utf-8")
    return unit


def test_matching_app_and_portal_versions_pass(tmp_path: Path):
    app(tmp_path, "apps/player")
    app(tmp_path, "portal")
    assert check_versions.check(tmp_path) == []


def test_a_mismatched_copy_is_reported(tmp_path: Path):
    unit = app(tmp_path, "apps/player")
    (unit / "package" / "__init__.py").write_text('__version__ = "9.0.0"\n', encoding="utf-8")
    assert check_versions.check(tmp_path) == ["apps/player/package/__init__.py: 9.0.0 != VERSION 1.2.3"]


def test_a_missing_version_file_is_reported(tmp_path: Path):
    unit = tmp_path / "apps/player"
    unit.mkdir(parents=True)
    assert check_versions.check(tmp_path) == ["apps/player: no VERSION file"]
