# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from bazzite_console_core import appinfo, theme
from bazzite_console_core.app import create_app
from bazzite_console_core.appinfo import AppInfo
from bazzite_console_core.help import HelpView
from bazzite_console_core.text import fill


def test_create_app_sets_names_and_current(qapp, info):
    app = create_app(info)
    assert app is qapp
    assert app.applicationName() == info.app_id
    assert app.applicationDisplayName() == "PS5 Test App 1.2.3"
    assert app.applicationVersion() == "1.2.3"
    assert app.desktopFileName() == info.app_id
    assert app.palette().window().color().name() == theme.THEME.window      # the suite's theme
    assert app.styleSheet().startswith(theme.stylesheet())
    app.setStyleSheet("")                       # a style sheet wraps the style; without it, Fusion shows
    assert app.style().name().lower() == "fusion"
    assert appinfo.current() is info


def test_org_only_when_declared(qapp):
    qapp.setOrganizationName("")
    create_app(AppInfo("ps5-governor-manager", "Gov", "0.1.0"))
    assert qapp.organizationName() == ""
    create_app(AppInfo("ps5-cu-unlock", "Unlock", "0.1.0", settings_org="ps5-cu-bisect"))
    assert (qapp.organizationName(), qapp.applicationName()) == ("ps5-cu-bisect", "ps5-cu-unlock")
    qapp.setOrganizationName("")


def test_help_view(qapp):
    html = fill("<p>See {repo}</p>", {"repo": "https://example.org"})
    assert "https://example.org" in HelpView(html).toPlainText()
