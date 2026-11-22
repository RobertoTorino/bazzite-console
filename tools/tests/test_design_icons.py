# SPDX-License-Identifier: GPL-3.0-or-later
"""DESIGN.md's Icons (tools/design_icons.py; owner, 22-11-2026): read from the repository, every file it names there."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import design_icons  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_every_file_the_listing_names_is_there():
    assert design_icons.missing(ROOT) == []


def test_the_parts_come_from_the_repository():
    text = design_icons.section(ROOT)
    for heading in ("## Icons", "### The suite's icon", "### The category icons", "### The portal's symbols",
                    "### The desktop style's icons", "### Material Design icons in the wiki", "### Characters as icons"):
        assert f"\n{heading}\n" in f"\n{text}\n"
    assert ("install", "An arrow down into a tray.") in design_icons.glyphs(ROOT)
    assert "code-braces" in design_icons.material(ROOT)               # the Development page's icon


def test_a_symbol_and_a_style_icon_are_found_in_the_code(tmp_path):
    for folder in ("apps/demo/demo", "core", "dev", "portal"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "apps/demo/demo/window.py").write_text(
        'label = "✓ done"\nicon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)\n', encoding="utf-8")
    (tmp_path / "portal/apps.toml").write_text('[apps.demo]\nname = "Demo"\n', encoding="utf-8")
    assert design_icons.symbols(tmp_path) == {"Demo": ["✓"]}
    assert design_icons.style_icons(tmp_path) == {"SP_MessageBoxWarning": ["Demo"]}
