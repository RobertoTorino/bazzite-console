# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/suites.py: the suite of the repository, its system and tag prefix, and the app and version a release tag
names."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("nexus_suites", TOOLS / "suites.py")
suites = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suites)


def make(root: Path, system: str = "", prefix: str = "") -> Path:
    (root / "portal").mkdir(parents=True)
    (root / "portal" / "apps.toml").write_text("")
    if system:
        (root / "SYSTEM").write_text(system + "\n")
    if prefix:
        (root / "TAG_PREFIX").write_text(prefix + "\n")
    return root


def test_the_system_and_the_prefix(tmp_path):
    suite = make(tmp_path / "suite", "bazzite", "ps5-")
    assert suites.system(suite) == "bazzite" and suites.tag_prefix(suite) == "ps5-"
    bare = make(tmp_path / "bare")
    assert suites.system(bare) == suites.tag_prefix(bare) == ""


def test_a_tag_names_its_app_and_version(tmp_path):
    suite = make(tmp_path, "bazzite", "ps5-")
    assert suites.of_tag("ps5-portal-v10.1.0", suite) == ("portal", "10.1.0")
    assert suites.of_tag("ps5-cu-unlock-v0.2.0", suite) == ("cu-unlock", "0.2.0")
    for bad in ("portal-v1.0.0", "ps5-portal", "ps5-portal-v1.0", "ps5-Portal-v1.0.0", "wp-portal-v1.0.0"):
        with pytest.raises(LookupError, match="is not ps5-<app>-v<x.y.z>"):
            suites.of_tag(bad, suite)


def test_the_command_line():
    """This repository is the suite."""
    run = lambda *args: subprocess.run([sys.executable, str(TOOLS / "suites.py"), *args], capture_output=True,
                                       text=True)
    assert run().stdout.split() == ["bazzite", "ps5-"]
    assert run("--tag", "ps5-portal-v1.0.0").stdout.split() == ["portal", "1.0.0"]
    result = run("--tag", "nothing")
    assert result.returncode == 1 and "is not ps5-<app>-v<x.y.z>" in result.stderr
