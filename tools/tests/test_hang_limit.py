# SPDX-License-Identifier: GPL-3.0-or-later
"""Every pytest run of test.sh and CI ends a hanging test after 2 minutes, saying where it is stuck (owner,
20-11-2026: a test that waited for a dialog ran 15 minutes without a word)."""

from __future__ import annotations

from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]
LIMIT = ("faulthandler_timeout=120", "faulthandler_exit_on_timeout=true")


def test_test_sh_limits_every_run():
    script = (SUITE / "test.sh").read_text(encoding="utf-8")
    assert all(f"-o {option}" in script for option in LIMIT)
    runs = [line for line in script.splitlines() if "-m pytest" in line]
    assert runs and all('"${HANG_LIMIT[@]}"' in line for line in runs)


def test_ci_limits_every_pytest_step():
    workflow = (SUITE / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    runs = [line for line in workflow.splitlines() if "-m pytest" in line and not line.lstrip().startswith("#")]
    assert runs and all(all(f"-o {option}" in line for option in LIMIT) for line in runs)
