# SPDX-License-Identifier: GPL-3.0-or-later
"""The quickfixes as the portal lists them (portal/apps.toml) and as the app has them, and Quickfix's groups as Board
Test's installer has them, stay the same."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from quickfix import ROOT, state
from quickfix.catalog import QUICKFIXES
from quickfix.windows import WINDOWS

SUITE = ROOT.parents[1]


def test_the_portal_lists_every_quickfix():
    app = tomllib.loads((SUITE / "portal" / "apps.toml").read_text(encoding="utf-8"))["apps"]["quickfix"]
    listed = [(h["key"], h["name"], h["summary"], h.get("changes_board", False), h["launch"]) for h in app["quickfixes"]]
    assert listed == [(h.key, h.name, h.summary, h.changes_board, f"~/.local/bin/ps5-quickfix {h.key}")
                      for h in QUICKFIXES]
    assert app["required"] is True and not app.get("changes_board", False)
    assert list(WINDOWS) == [h.key for h in QUICKFIXES]


def test_the_groups_are_board_tests_installers():
    script = (SUITE / "apps" / "board" / state.INSTALLER).read_text(encoding="utf-8")
    rpms = re.search(r"^RPMS=\(([^)]*)\)", script, re.M)[1].split()
    assert [t.package for t in state.GROUPS[0].tools] == rpms
    options = re.findall(r"^\s+(--[a-z]+)\)", script, re.M)
    assert [g.option for g in state.GROUPS] + ["--all"] == options
    assert "install_vkpeak; install_memtest_vulkan" in script and "install_speedtest" in script
    assert 'sudo rpm-ostree install "$@"' in script and 'sudo dnf install -y "$@"' in script
    assert "install_packages sqlite" in script


def test_how_follows_ostree(tmp_path):
    rpms, bins = state.GROUPS[0], state.GROUPS[1]
    assert state.how(rpms, tmp_path) == state.WITH_DNF                    # flattened: no /run/ostree-booted
    assert state.how(bins, tmp_path) == bins.what
    (tmp_path / "run").mkdir()
    (tmp_path / state.OSTREE_BOOTED).touch()
    assert state.how(rpms, tmp_path) == state.LAYERED
