#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stills of the portal for Nexus Marketing's article (dev/marketing): the real portal view from this checkout, one
still per category tab and one of the Settings page, as WebP.

    python3 tools/portal_shots.py OUT_DIR [--size 1080p|1440p|2160p]

It writes <category>.webp for each tab (sustainable.webp, graphics.webp, ...), settings.webp, and portal.stamp: the
fingerprint of what the stills show (tools/portal_tour.py's fingerprint(), the portal's code, pictures and tiles).
Nexus Marketing compares that stamp with the portal as it is now and says when the stills are out of date.

It sets the portal up as the Portal Tour does (tools/portal_tour.py's Tour): offscreen, in a temporary home folder,
with a few apps "installed", the example wallpaper, no network, no sound and nothing from the machine it runs on. It
is a script of its own, so the tour's script and its stamp stay as they are."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "tools"))            # portal_tour.py and tour_frames.py

import portal_tour  # noqa: E402
import tour_frames  # noqa: E402

QUALITY = 88                                        # lossy WebP: pictures on a web page


def shoot(out: Path) -> list[Path]:
    """The stills in *out*: one per category tab, then the Settings page. Returns the files written."""
    out.mkdir(parents=True, exist_ok=True)
    written = []
    with tempfile.TemporaryDirectory(prefix="portal-shots-") as folder:
        home = Path(folder)
        portal_tour.prepare_home(home)
        tour = portal_tour.Tour(Path(os.devnull), 1, home)
        tour.ffmpeg.kill()                          # no video: only frames
        window = tour.window
        window.example_wallpaper()
        tour.pointer = (-100, -100)                 # no pointer in a still
        tour.say("")
        for index, category in enumerate(window.big.categories):
            window.big.bar.setCurrentIndex(index)
            tour.pump()
            path = out / f"{category}.webp"
            tour.frame().save(str(path), "WEBP", QUALITY)
            written.append(path)
        window.big.bar.setCurrentIndex(0)
        window.toggle_settings()
        tour.pump()
        path = out / "settings.webp"
        tour.frame().save(str(path), "WEBP", QUALITY)
        written.append(path)
    stamp = out / "portal.stamp"
    stamp.write_text(portal_tour.fingerprint() + "\n", encoding="utf-8", newline="\n")
    return [*written, stamp]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, help="the folder for the stills")
    parser.add_argument("--size", choices=tuple(tour_frames.SIZES), default="1080p",
                        help="the stills' size: 1080p (the default), 1440p or 2160p")
    args = parser.parse_args()
    tour_frames.set_size(args.size)
    for path in shoot(args.out.resolve()):
        print(path)
    return 0


if __name__ == "__main__":
    # As tools/portal_tour.py: os._exit skips the interpreter's shutdown, where Qt's objects are destroyed in no
    # fixed order.
    try:
        status = main()
    except SystemExit as exc:
        status = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except BaseException:
        import traceback
        traceback.print_exc()
        status = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(status)
