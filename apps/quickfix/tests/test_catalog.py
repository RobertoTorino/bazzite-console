# SPDX-License-Identifier: GPL-3.0-or-later
"""The quickfixes as the portal lists them (portal/apps.toml) and as the app has them, and Quickfix's groups as Board
Test's installer has them, stay the same."""

from __future__ import annotations

import re
import tomllib

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
    assert "--mprime)    install_mprime ;;" in script and "install_speedtest; install_mprime ;;" in script   # in --all


def test_mprime_goes_where_cpu_tools_looks_and_is_checked_first():
    """Prime95's mprime: unpacked into ~/mprime, the first place Core Unlock's bisect looks in, with a link in
    ~/.local/bin, where this window looks; the download is compared with a pinned SHA-256 before it is unpacked."""
    script = (SUITE / "apps" / "board" / state.INSTALLER).read_text(encoding="utf-8")
    bisect = (SUITE / "apps" / "cores" / "ps5-cores-bisect.sh").read_text(encoding="utf-8")
    assert 'MPRIME_DIR="${MPRIME_DIR:-$HOME/mprime}"' in script and 'for p in "$HOME/mprime/mprime"' in bisect
    assert 'ln -sfn "$MPRIME_DIR/mprime" "$BIN_DIR/mprime"' in script
    assert re.search(r'^MPRIME_SHA256="[0-9a-f]{64}"$', script, re.M)                 # the release it falls back to
    assert "if mprime_latest; then" in script and 'MPRIME_PAGE="${MPRIME_PAGE:-https://www.mersenne.org/download/}"' in script
    assert 'echo "$MPRIME_FILE" >"$MPRIME_DIR/.release"' in script                    # what Nexus Deps compares
    assert re.search(r'^MPRIME_URL="https://download\.mersenne\.ca/gimps/', script, re.M)
    body = script[script.index("install_mprime() {"):]
    assert body.index("sha256sum -c") < body.index("tar -xzf")
    group = next(g for g in state.GROUPS if g.option == "--mprime")
    assert [(t.command, t.package) for t in group.tools] == [("mprime", "mprime")]


def test_how_follows_ostree(tmp_path):
    rpms, bins = state.GROUPS[0], state.GROUPS[1]
    assert state.how(rpms, tmp_path) == state.WITH_DNF                    # flattened: no /run/ostree-booted
    assert state.how(bins, tmp_path) == bins.what
    (tmp_path / "run").mkdir()
    (tmp_path / state.OSTREE_BOOTED).touch()
    assert state.how(rpms, tmp_path) == state.LAYERED
