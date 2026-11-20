# SPDX-License-Identifier: AGPL-3.0-or-later
"""The FFmpeg the native core's decoder links: build.rs looks for it in the folder named after the version that
ffmpeg/build.sh pins, so the two name the same version; the pins are a version and a SHA-256 each."""

from __future__ import annotations

import re
from pathlib import Path

NATIVE = Path(__file__).resolve().parents[1] / "native"


def _pins() -> dict[str, str]:
    return dict(re.findall(r"^([A-Z0-9_]+)=(\S+)", (NATIVE / "ffmpeg" / "build.sh").read_text(), re.M))


def test_build_rs_names_the_pinned_ffmpeg():
    found = re.search(r'const FFMPEG_VERSION: &str = "([^"]+)";', (NATIVE / "build.rs").read_text())
    assert found and found.group(1) == _pins()["FFMPEG_VERSION"]


def test_the_pins():
    pins = _pins()
    for name in ("FFMPEG", "LIBVA"):
        assert re.fullmatch(r"\d+\.\d+\.\d+", pins[f"{name}_VERSION"])
        assert re.fullmatch(r"[0-9a-f]{64}", pins[f"{name}_SHA256"])
    # libva x.y.z carries VA-API 1.y.0
    assert pins["LIBVA_API"] == f"1.{pins['LIBVA_VERSION'].split('.')[1]}.0"
