# SPDX-License-Identifier: GPL-3.0-or-later
"""The bug report's App dropdown lists the portal and exactly the apps of portal/apps.toml, in its order, so a new
app is there and a removed or renamed one is gone."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]


def test_the_bug_reports_apps_are_the_manifests():
    apps = list(tomllib.loads((SUITE / "portal" / "apps.toml").read_text(encoding="utf-8"))["apps"])
    text = (SUITE / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text(encoding="utf-8")
    dropdown = text[text.index("id: app"):]
    options = dropdown[dropdown.index("options:"):dropdown.index("validations:")]
    assert re.findall(r"^ {8}- (\S+)$", options, re.M) == ["portal", *apps]
