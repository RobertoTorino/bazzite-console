# SPDX-License-Identifier: GPL-3.0-or-later
"""The helpers as the portal lists them (portal/apps.toml) and as the app has them, and Test Extras' groups as Board
Test's installer has them, stay the same."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from helpers import ROOT, state
from helpers.catalog import HELPERS
from helpers.windows import WINDOWS

SUITE = ROOT.parents[1]


def test_the_portal_lists_every_helper():
    app = tomllib.loads((SUITE / "portal" / "apps.toml").read_text(encoding="utf-8"))["apps"]["helpers"]
    listed = [(h["key"], h["name"], h["summary"], h.get("changes_board", False), h["launch"]) for h in app["helpers"]]
    assert listed == [(h.key, h.name, h.summary, h.changes_board, f"~/.local/bin/ps5-helpers {h.key}")
                      for h in HELPERS]
    assert app["required"] is True and not app.get("changes_board", False)
    assert list(WINDOWS) == [h.key for h in HELPERS]


def test_the_groups_are_board_tests_installers():
    script = (SUITE / "apps" / "board" / state.INSTALLER).read_text(encoding="utf-8")
    rpms = re.search(r"^RPMS=\(([^)]*)\)", script, re.M)[1].split()
    assert [t.package for t in state.GROUPS[0].tools] == rpms
    options = re.findall(r"^\s+(--[a-z]+)\)", script, re.M)
    assert [g.option for g in state.GROUPS] + ["--all"] == options
    assert "install_vkpeak; install_memtest_vulkan" in script and "install_speedtest" in script
    assert "sudo rpm-ostree install sqlite" in script
