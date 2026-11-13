#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy the category icons in icons/<category>/ to every app and to the portal, as icons/categories.toml assigns
them:

    python3 tools/sync_icons.py                              # write the copies that differ
    python3 tools/sync_icons.py --check                      # only list them; exit 1 when there are any
    python3 tools/sync_icons.py --category C --from IMAGE    # the category's four icons from one square image first

An app's icon is its category's: <icon>.webp (512 px) in its window and <icon>-128.png for its menu entry and
Desktop icon. The portal gets the 256 px icon as the app's tile picture (portal/images/apps/<key>.webp, which the
wiki shows too) and the 512 px one per category (portal/images/categories/<category>.webp). The copies stay in git
where they are, so the installers, the portal, the wiki and a release find them; icons/ is the one place to change
them. They are WebP, which Qt and the wiki read, except the 128 px one: menu entries and Desktop icons get that
PNG, which every desktop shows."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
SIZES = (1024, 512, 256, 128)
WEBP_QUALITY = 90


def icon_path(category_dir: Path, size: int) -> Path:
    """A category's icon at one size: WebP, the 128 px one PNG."""
    return category_dir / f"{category_dir.name}-{size}.{'png' if size == 128 else 'webp'}"


def copies(root: Path = SUITE) -> dict[Path, Path]:
    """Each copy with the category icon it is a copy of."""
    table = tomllib.loads((root / "icons" / "categories.toml").read_text(encoding="utf-8"))
    found = {}
    for key, entry in table.items():
        category_dir = root / "icons" / entry["category"]
        if not category_dir.is_dir():
            raise SystemExit(f"[{key}]: no icons/{entry['category']}/")
        for icon in entry["icons"]:
            found[root / f"{icon}.webp"] = icon_path(category_dir, 512)
            found[root / f"{icon}-128.png"] = icon_path(category_dir, 128)
        if "tile" in entry:                     # an app the portal lists
            found[root / entry["tile"]] = icon_path(category_dir, 256)
            found[root / "portal" / "images" / "categories" / f"{category_dir.name}.webp"] = icon_path(
                category_dir, 512)
    return found


def stale(root: Path = SUITE) -> list[Path]:
    """The copies that are missing or differ from their category icon."""
    return [copy for copy, source in copies(root).items()
            if not copy.is_file() or copy.read_bytes() != source.read_bytes()]


def convert(source: Path, category_dir: Path) -> list[Path]:
    """Write the category's four icons from one square image; the paths written."""
    from PIL import Image   # imported here: the copies alone need no Pillow

    try:
        with Image.open(source) as image:
            image = image.convert("RGBA")
    except OSError as error:
        raise SystemExit(f"{source}: not an image Pillow reads ({error})") from None
    if image.width != image.height:
        raise SystemExit(f"{source}: {image.width} x {image.height} px, an icon must be square")
    written = []
    for size in SIZES:
        target = icon_path(category_dir, size)
        scaled = image if image.size == (size, size) else image.resize((size, size), Image.Resampling.LANCZOS)
        if size == 128:
            scaled.save(target, "PNG", optimize=True)
        else:
            scaled.save(target, "WEBP", quality=WEBP_QUALITY, method=6)
        written.append(target)
    return written


def main(argv: list[str], root: Path = SUITE) -> int:
    parser = argparse.ArgumentParser(description="Copy the category icons to the apps and the portal.")
    parser.add_argument("--check", action="store_true", help="only list what is out of date; exit 1 when any is")
    parser.add_argument("--category", help="the category (a folder of icons/) --from writes")
    parser.add_argument("--from", dest="source", type=Path, help="a square image to make the category's icons from")
    args = parser.parse_args(argv)
    if (args.category is None) != (args.source is None):
        parser.error("--category and --from go together")
    if args.check and args.source is not None:
        parser.error("--check does not convert: leave out --category and --from")
    if args.source is not None:
        category_dir = root / "icons" / args.category
        if not category_dir.is_dir():
            parser.error(f"no icons/{args.category}/")
        if not args.source.is_file():
            parser.error(f"no such image: {args.source}")
        for target in convert(args.source, category_dir):
            print(f"converted: {args.source} -> {target.relative_to(root).as_posix()}")
    sources, out = copies(root), stale(root)
    for copy in out:
        print(("out of date: " if args.check else "updated: ") + copy.relative_to(root).as_posix())
        if not args.check:
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(sources[copy].read_bytes())
    if args.check and out:
        print("run python3 tools/sync_icons.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
