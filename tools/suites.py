#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The suite of the repository: the repository itself, with its portal's manifest at portal/apps.toml (the Bazzite
Console Suite). The suite names the system it is made for in its SYSTEM file (bazzite). Its release tags are
<prefix><app>-v<x.y.z>, the prefix in its TAG_PREFIX file (ps5-, so ps5-portal-v2.0.0).

    python3 tools/suites.py                             # the suite's system and tag prefix: bazzite ps5-
    python3 tools/suites.py --tag ps5-portal-v2.0.0    # the tag's app and version: portal 2.0.0"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path("portal") / "apps.toml"
SYSTEMS = ("bazzite",)                    # what SYSTEM may say
TAG = re.compile(r"^(?P<app>[a-z0-9-]+)-v(?P<version>\d+\.\d+\.\d+)$")      # a tag without the suite's prefix


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def system(root: Path = ROOT) -> str:
    """The system the suite in *root* is made for, from its SYSTEM file ("" without one)."""
    return _read(root / "SYSTEM")


def tag_prefix(root: Path = ROOT) -> str:
    """What the release tags of the suite in *root* start with, from its TAG_PREFIX file ("" without one)."""
    return _read(root / "TAG_PREFIX")


def of_tag(tag: str, root: Path = ROOT) -> tuple[str, str]:
    """The app key and version of the release tag *tag* (<prefix><app>-v<x.y.z>). Raises LookupError for a tag
    that is not the suite's."""
    prefix = tag_prefix(root)
    match = TAG.match(tag.removeprefix(prefix)) if tag.startswith(prefix) else None
    if not match:
        raise LookupError(f"{tag} is not {prefix}<app>-v<x.y.z>")
    return match["app"], match["version"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", help="the app and version of this release tag, on one line")
    args = parser.parse_args(argv)
    if args.tag:
        try:
            print(*of_tag(args.tag))
        except LookupError as exc:
            print(exc, file=sys.stderr)
            return 1
        return 0
    print(system(), tag_prefix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
