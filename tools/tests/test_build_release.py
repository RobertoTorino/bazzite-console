# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/build_release.py: what a release's tarball holds."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
import tarfile
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_release_tested", SUITE / "tools" / "build_release.py")
build_release = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = build_release
spec.loader.exec_module(build_release)


def test_bazzite_tests_release_records_its_engines_checksum(tmp_path, monkeypatch):
    """A release of Bazzite Test is a release build: bazzite_test/_build_info.py names the SHA-256 of the
    test-bazzite.sh in the same tarball, so the app refuses an engine that was changed. The checkout gets no such
    file."""
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    version = (SUITE / "apps" / "bazzite" / "VERSION").read_text(encoding="utf-8").strip()
    tag = f"ps5-bazzite-v{version}"
    build_release.build(tag, tmp_path)
    with tarfile.open(tmp_path / f"{tag}.tar.gz") as archive:
        info = archive.extractfile(f"{tag}/bazzite_test/_build_info.py").read().decode("utf-8")
        engine = archive.extractfile(f"{tag}/test-bazzite.sh").read()
    recorded = re.search(r'SCRIPT_SHA256 = "([0-9a-f]{64})"', info)
    assert recorded and recorded[1] == hashlib.sha256(engine).hexdigest()
    assert 'BUILD_DATE = "2023-11-14 22:13 UTC"' in info
    assert not (SUITE / "apps" / "bazzite" / "bazzite_test" / "_build_info.py").exists()
