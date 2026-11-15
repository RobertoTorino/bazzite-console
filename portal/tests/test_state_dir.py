# SPDX-License-Identifier: GPL-3.0-or-later
"""What the portal remembers is kept apart from the installed portal's folder, which install.sh replaces."""

from __future__ import annotations

import bazzite_console_portal as portal


def test_the_state_folder_is_not_the_installed_portals_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    state = portal.state_dir()
    program = tmp_path / portal.APP_ID / "portal"          # install.sh's PORTAL_DIR
    assert state == tmp_path / portal.APP_ID / "state"
    assert program not in (state, *state.parents)


def test_the_installed_copy_is_the_portal_folder_in_the_suites_folder(monkeypatch, tmp_path):
    """install.sh's copy, ~/.local/share/<suite>/portal: the portal compares its build and offers a restart there;
    a checkout's portal/ is no installed copy."""
    installed = tmp_path / portal.APP_ID / "portal"
    monkeypatch.setattr(portal, "ROOT", installed)
    assert portal.installed_copy() == installed
    monkeypatch.setattr(portal, "ROOT", tmp_path / "checkout" / "portal")
    assert portal.installed_copy() is None
