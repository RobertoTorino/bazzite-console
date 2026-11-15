# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from bazzite_console_core.appinfo import SUITE_REPO_URL, AppInfo


def test_defaults(info):
    assert info.display_name == "PS5 Test App 1.2.3"
    assert info.org == info.settings_name == info.app_id
    assert info.repo_url == SUITE_REPO_URL
    assert info.releases_url == SUITE_REPO_URL + "/releases"
    assert info.user_agent == f"{info.app_id}/1.2.3"


def test_existing_settings_names_are_kept():
    cu = AppInfo("ps5-cu-bisect-gui", "PS5 CU Bisect", "0.1.0",
                 settings_org="ps5-cu-bisect", settings_app="ps5-cu-bisect-gui")
    assert (cu.org, cu.settings_name) == ("ps5-cu-bisect", "ps5-cu-bisect-gui")
