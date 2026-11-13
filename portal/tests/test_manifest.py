# SPDX-License-Identifier: GPL-3.0-or-later
"""The portal reads its required app first from apps.toml."""

from __future__ import annotations

import pytest

from bazzite_console_portal import CARDS, ROOT
from bazzite_console_portal.manifest import ManifestError, load, load_cards, parse, parse_cards


def test_required_app_is_first_and_only_required():
    entries = load(ROOT / "apps.toml")
    assert len(entries) == 17
    assert entries[0].key == "bazzite"
    assert entries[0].name == "Bazzite Test"
    assert entries[0].required
    assert [entry.key for entry in entries if entry.required] == ["bazzite"]
    assert entries[0].tag.startswith("ps5-bazzite-v")


def test_invalid_tag_and_missing_required_app_are_rejected():
    text = (ROOT / "apps.toml").read_text(encoding="utf-8")
    tag = load(ROOT / "apps.toml")[0].tag
    with pytest.raises(ManifestError, match="tag must be"):
        parse(text.replace(tag, tag.removeprefix("ps5-")))
    with pytest.raises(ManifestError, match="exactly one required"):
        parse(text.replace("required = true", "required = false"))


def test_media_services_are_cards_not_apps():
    cards = load_cards(CARDS)
    assert cards == []


def test_card_icon_must_be_a_webp_filename():
    with pytest.raises(ManifestError, match="WebP filename"):
        parse_cards('[cards.test]\nname = "Test"\nsummary = "Test card."\ncategory = "gaming"\n'
                    'icon = "../test.png"\nflatpak_id = "com.test.App"\nflatpak_name = "Test App"\n'
                    'launch = ["flatpak", "run", "com.test.App"]\n')


def test_card_must_launch_its_required_flatpak():
    with pytest.raises(ManifestError, match="required Flatpak"):
        parse_cards('[cards.test]\nname = "Test"\nsummary = "Test card."\ncategory = "gaming"\n'
                    'icon = "test.webp"\nflatpak_id = "com.test.App"\nflatpak_name = "Test App"\n'
                    'launch = ["flatpak", "run", "com.example.Other"]\n')
