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
