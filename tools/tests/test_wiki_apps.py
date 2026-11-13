# SPDX-License-Identifier: GPL-3.0-or-later
"""The wiki and the README list the apps the portal lists: every app of portal/apps.toml has its chapter, its line
in the overviews and its place in the navigation, and nothing lists an app that is gone."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]
APPS = tomllib.loads((SUITE / "portal" / "apps.toml").read_text(encoding="utf-8"))["apps"]
_LINK = re.compile(r"\]\((?:apps/)?([a-z0-9]+)\.md\)")


def test_every_app_has_a_chapter_and_no_chapter_is_left_over():
    chapters = {p.stem for p in (SUITE / "docs" / "apps").glob("*.md")} - {"index", "categories"}
    assert chapters == set(APPS)


def test_the_overviews_list_exactly_the_apps():
    for page in ("docs/apps/index.md", "docs/apps/categories.md", "docs/index.md"):
        text = (SUITE / page).read_text(encoding="utf-8")
        assert set(_LINK.findall(text)) - {"index", "install", "portal"} == set(APPS), page
        for app in APPS.values():
            assert app["name"] in text, f"{page}: {app['name']}"


def test_the_navigation_and_the_readme_name_every_app():
    nav = (SUITE / "mkdocs.yml").read_text(encoding="utf-8")
    assert set(re.findall(r"apps/([a-z0-9]+)\.md", nav)) - {"index", "categories"} == set(APPS)
    readme = (SUITE / "README.md").read_text(encoding="utf-8")
    assert set(re.findall(r"\]\(apps/([a-z0-9]+)\)", readme)) == set(APPS)


def test_the_install_page_names_a_portal_release():
    """The hook writes the newest published portal's tag where the page says {{ portal_tag }}."""
    import sys

    import pytest
    pytest.importorskip("mkdocs.structure.files")   # the hook imports it; CI's tools job has none (tools/mkdocs is no package of it)
    sys.path.insert(0, str(SUITE / "tools" / "mkdocs"))
    try:
        import hooks
    finally:
        sys.path.pop(0)
    assert re.fullmatch(r"ps5-portal-v\d+\.\d+\.\d+", hooks.portal_tag())
    assert hooks.PORTAL_TAG in (SUITE / "docs" / "install.md").read_text(encoding="utf-8")
