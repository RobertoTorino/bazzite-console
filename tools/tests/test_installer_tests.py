# SPDX-License-Identifier: GPL-3.0-or-later
"""Every installable part of the suite has an installer test, and CI runs every installer test. Nexus Installer
Tests finds the scripts by itself (tools/installer-tests/*.sh), so a new script appears there without a change."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]
TESTS = SUITE / "tools" / "installer-tests"
HELPERS = {"shims.sh"}
NOT_INSTALLERS = {"release.sh",         # the release tarballs end to end, not one app's installer
                  "not-installed.sh",   # every installer's uninstall where nothing is installed
                  "release-check.sh"}   # tools/check-release.sh status and remove


def _scripts() -> set[str]:
    return {path.name for path in TESTS.glob("*.sh")} - HELPERS


def test_every_app_has_an_installer_test():
    apps = {path.name for path in (SUITE / "apps").iterdir() if (path / "VERSION").is_file()}
    missing = sorted(app for app in apps | {"portal"} if not (TESTS / f"{app}.sh").is_file())
    assert not missing, f"no tools/installer-tests/<name>.sh for: {', '.join(missing)}"


def _from_the_checkout() -> set[str]:
    """The tools that run from the checkout, outside the portal: the Nexus apps in dev/ (Nexus Dashboard, Nexus
    Release Tool, Nexus Demo Recorder, Nexus Installer Tests, Nexus Sound Lab, Text to Speech, Nexus Remix Studio), each
    with an install.sh."""
    return {path.parent.name for path in (SUITE / "dev").glob("*/install.sh")}


def test_every_portal_entry_and_checkout_tool_has_an_installer_test():
    manifest = tomllib.loads((SUITE / "portal" / "apps.toml").read_text(encoding="utf-8"))
    names = set(manifest.get("apps", {})) | _from_the_checkout()
    missing = sorted(name for name in names if not (TESTS / f"{name}.sh").is_file())
    assert not missing, f"no tools/installer-tests/<name>.sh for: {', '.join(missing)}"
    assert {"dash", "demo", "itests", "nrt", "sounds", "studio", "text"} <= _from_the_checkout()


def test_every_installer_test_is_for_something_that_exists():
    known = {path.name for path in (SUITE / "apps").iterdir()} | {"portal"} | _from_the_checkout()
    stale = sorted(name for name in _scripts() - NOT_INSTALLERS if name.removesuffix(".sh") not in known)
    assert not stale, f"installer tests for nothing in the suite: {', '.join(stale)}"


def test_ci_runs_every_installer_test():
    """CI's installers job runs the tools/installer-tests/*.sh its plan job names (tools/ci_matrix.py plan): every
    one it finds on a full run (stage 2, 04-11-2026: a new app's test runs without an edit to the workflow), the
    helper left out and the release tarballs last; no script is named in the workflow."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ci_matrix", SUITE / "tools" / "ci_matrix.py")
    ci_matrix = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci_matrix)
    listed = ci_matrix.plan(None, SUITE)["installers"].split()
    assert set(listed) == _scripts() and listed[-1] == "release.sh"
    ci = (SUITE / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "TESTS: ${{ needs.plan.outputs.installers }}" in ci and 'bash "tools/installer-tests/$1"' in ci
    assert not re.findall(r"bash tools/installer-tests/[\w.-]+\.sh", ci)     # no step by name
