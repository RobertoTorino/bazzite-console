# SPDX-License-Identifier: GPL-3.0-or-later
"""The compatibility core from run.sh and the app's package."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# No Claude Code for the windows the tests open: the Claude pill reads nothing of this machine.
os.environ["CLAUDE_CONFIG_DIR"] = str(Path(__file__).resolve().parent / "no-claude")
APP = Path(__file__).resolve().parents[1]
CORE = APP.parents[1] / "core"
for path in (APP.parents[1] / "dev" / "core_compat", CORE, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(scope="session", autouse=True)
def nexus_theme():
    """The widgets draw with Nexus's theme, as create_app() sets it for this app (style.py)."""
    from nexus_core import widgets
    from nexus_release_tool.style import NEXUS
    widgets.set_theme(NEXUS)


@pytest.fixture(autouse=True)
def settings_in_a_temp_folder(tmp_path):
    """The .ini settings in a temp folder: no test reads or moves the user's own (those of the earlier name too)."""
    from PyQt6.QtCore import QSettings
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "config"))


@pytest.fixture(autouse=True)
def plain_tags_for_the_fixture_suites(monkeypatch):
    """The tests' suites without a TAG_PREFIX tag <app>-v<x.y.z>, and the tool reads them with this checkout's
    manifest tools (plan.check_manifest), which ask for this suite's ps5-: here they take a tag with or without."""
    import re

    from nexus_release_tool import plan
    monkeypatch.setattr(plan.check_manifest.manifest, "_TAG",
                        re.compile(r"^(?:ps5-)?(?P<app>[a-z0-9-]+)-v(?P<version>\d+\.\d+\.\d+)$"))
    monkeypatch.setattr(plan.check_manifest, "_PORTAL_TAG", re.compile(r"^(?:ps5-)?portal-v(\d+\.\d+\.\d+)$"))
