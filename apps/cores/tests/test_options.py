# SPDX-License-Identifier: GPL-3.0-or-later
"""The window's advanced choices as a ps5-cores-bisect.sh command line."""

from __future__ import annotations

import shlex

import pytest

from cores_bisect.options import LOAD_TOOLS, BisectOptions


def test_defaults_are_the_scripts_own():
    assert BisectOptions().to_args() == ["-t", "600", "-r", "3"]
    assert BisectOptions().validate() == []


def test_every_switch_reaches_the_command_line():
    opts = BisectOptions(time_secs=900, rounds=5, same_boot=True, unattended=True, load_tool="both", rasdaemon=True)
    assert opts.to_args() == ["-t", "900", "-r", "5", "--load", "both", "--rasdaemon", "--same-boot", "--auto"]
    assert shlex.split(opts.to_command("/opt/ps5-cores-bisect/ps5-cores-bisect.sh"))[:2] == [
        "bash", "/opt/ps5-cores-bisect/ps5-cores-bisect.sh"]


@pytest.mark.parametrize(("opts", "message"), [
    (BisectOptions(time_secs=30), "at least 60 seconds"),
    (BisectOptions(rounds=0), "between 1 and 9"),
    (BisectOptions(rounds=10), "between 1 and 9"),
    (BisectOptions(load_tool="prime95"), "Load tool must be one of"),
])
def test_validation(opts, message):
    assert any(message in error for error in opts.validate())


def test_load_tools():
    assert LOAD_TOOLS == ("stress-ng", "mprime", "both")

