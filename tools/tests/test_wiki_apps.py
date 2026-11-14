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
CATEGORIES = ("sustainable", "graphics", "gaming", "utilities")     # the navigation's headers, in the portal's order
# The pages of docs/apps/ that are no app's chapter: the overviews, and a category without an app ("Coming soon.").
OTHER = {"index", "categories", "covers"} | {c for c in CATEGORIES if all(app["category"] != c for app in APPS.values())}


def test_every_app_has_a_chapter_and_no_chapter_is_left_over():
    chapters = {p.stem for p in (SUITE / "docs" / "apps").glob("*.md")} - OTHER
    assert chapters == set(APPS)


def test_the_overviews_list_exactly_the_apps():
    for page in ("docs/apps/index.md", "docs/apps/categories.md", "docs/index.md"):
        text = (SUITE / page).read_text(encoding="utf-8")
        assert set(_LINK.findall(text)) - {"install", "portal", "privacy"} - OTHER == set(APPS), page
        for app in APPS.values():
            assert app["name"] in text, f"{page}: {app['name']}"


def test_the_navigation_and_the_readme_name_every_app():
    nav = (SUITE / "mkdocs.yml").read_text(encoding="utf-8")
    assert set(re.findall(r"apps/([a-z0-9]+)\.md", nav)) - OTHER == set(APPS)
    readme = (SUITE / "README.md").read_text(encoding="utf-8")
    assert set(re.findall(r"\]\(apps/([a-z0-9]+)\)", readme)) == set(APPS)


def test_the_navigation_lists_the_apps_by_category_in_alphabetical_order():
    """A header per category under Apps, each with its apps by name; a category without an app says Coming soon."""
    nav = (SUITE / "mkdocs.yml").read_text(encoding="utf-8")
    found: dict[str, list[str]] = {}
    for line in nav.splitlines():
        if header := re.fullmatch(r" {6}- (\w+):", line):
            found[header[1].lower()] = []
        elif entry := re.fullmatch(r" {10}- (.+): apps/([a-z0-9]+)\.md", line):
            found[list(found)[-1]].append(entry[2])
            assert entry[1].strip('"') == (APPS[entry[2]]["name"] if entry[2] in APPS else "Coming soon."), line
    assert tuple(found) == CATEGORIES
    for category, listed in found.items():
        apps = [key for key, app in APPS.items() if app["category"] == category]
        assert listed == (sorted(apps, key=lambda key: APPS[key]["name"].casefold()) or [category]), category


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
