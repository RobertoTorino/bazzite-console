# SPDX-License-Identifier: GPL-3.0-or-later
"""The category icons' copies: every app of the portal has its entry, and no copy differs from its category's."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
SUITE = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import sync_icons  # noqa: E402


def test_every_app_has_its_category_and_icons():
    apps = tomllib.loads((SUITE / "portal" / "apps.toml").read_text(encoding="utf-8"))["apps"]
    table = tomllib.loads((SUITE / "icons" / "categories.toml").read_text(encoding="utf-8"))
    assert set(table) == set(apps)
    for key, entry in table.items():
        assert entry["category"] == apps[key]["category"], key
        assert entry["tile"] == f"portal/images/apps/{key}.webp", key
        assert all(icon.startswith(f"apps/{key}/images/") for icon in entry["icons"]), key


def test_no_copy_is_out_of_date():
    assert [path.relative_to(SUITE).as_posix() for path in sync_icons.stale()] == []


def _suite(root: Path) -> Path:
    icons = root / "icons" / "gaming"
    icons.mkdir(parents=True)
    for size in sync_icons.SIZES:
        sync_icons.icon_path(icons, size).write_bytes(f"gaming {size}".encode())
    (root / "icons" / "categories.toml").write_text(
        '[game]\ncategory = "gaming"\nicons = ["apps/game/images/ps5-game"]\ntile = "portal/images/apps/game.webp"\n',
        encoding="utf-8")
    return root


def test_check_lists_and_sync_writes(tmp_path, capsys):
    root = _suite(tmp_path)
    assert sync_icons.main(["--check"], root) == 1
    assert "out of date: apps/game/images/ps5-game.webp" in capsys.readouterr().out
    assert sync_icons.main([], root) == 0
    assert (root / "apps/game/images/ps5-game.webp").read_bytes() == b"gaming 512"
    assert (root / "apps/game/images/ps5-game-128.png").read_bytes() == b"gaming 128"
    assert (root / "portal/images/apps/game.webp").read_bytes() == b"gaming 256"
    assert (root / "portal/images/categories/gaming.webp").read_bytes() == b"gaming 512"
    assert sync_icons.main(["--check"], root) == 0


def test_convert_writes_the_four_sizes(tmp_path):
    from PIL import Image

    root = _suite(tmp_path)
    source = tmp_path / "new.png"
    Image.new("RGBA", (1024, 1024), (10, 20, 30, 255)).save(source)
    assert sync_icons.main(["--category", "gaming", "--from", str(source)], root) == 0
    for size in sync_icons.SIZES:
        with Image.open(sync_icons.icon_path(root / "icons" / "gaming", size)) as image:
            assert image.size == (size, size) and image.format == ("PNG" if size == 128 else "WEBP")
    assert (root / "apps/game/images/ps5-game-128.png").read_bytes() == \
        (root / "icons/gaming/gaming-128.png").read_bytes()
