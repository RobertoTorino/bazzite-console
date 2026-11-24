# SPDX-License-Identifier: GPL-3.0-or-later
"""Every app has the same layout: its Python package(s) and images/ directly in apps/<name>/, no wrapper folder; the
development apps in dev/<name>/ (Nexus Dashboard for PS5, Nexus Release Tool, Nexus Demo Recorder, Nexus
Installer Tests, Nexus Sound Lab, Nexus Deps, Nexus TTS, Nexus Remix Studio) the same."""

from __future__ import annotations

import re
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]         # the checkout
SKIP = {"tests", "__pycache__", ".pytest_cache"}


def _apps() -> list[Path]:
    """The apps (apps/<name>, each with its VERSION) and the development apps (dev/<name>, which have none)."""
    return sorted([*(path for path in (SUITE / "apps").iterdir() if (path / "VERSION").is_file()),
                   *(path for path in (SUITE / "dev").iterdir() if (path / "CHANGELOG").is_file())])


def _visible(path: Path, app: Path) -> bool:
    parts = path.relative_to(app).parts
    return not (set(parts) & SKIP) and not any(part.startswith(".venv") for part in parts)


def test_packages_sit_at_the_app_root():
    """apps/<name>/<package>/__main__.py, never apps/<name>/<folder>/<package>/__main__.py."""
    nested = [str(main.relative_to(SUITE)) for app in _apps() for main in app.rglob("__main__.py")
              if _visible(main, app) and main.parent.parent != app]
    assert not nested, f"packages in a wrapper folder: {', '.join(nested)}"


def test_every_app_has_a_package_and_images_at_its_root():
    for app in _apps():
        if not any(app.glob("*/__main__.py")) and not any(app.glob("*.sh")):
            raise AssertionError(f"{app.name}: no package or script at the app root")
        assert (app / "images").is_dir(), f"{app.name}: no images/ at the app root"


def _installer(app: Path) -> Path:
    """An app's installer: install.sh."""
    return app / "install.sh"


def _installers() -> list[Path]:
    """Every installer: the apps', the development apps' and the portal's."""
    return [*(_installer(app) for app in _apps()), SUITE / "portal" / "install.sh"]


def test_every_app_has_an_installer_at_its_root():
    missing = [f"{app.name} ({_installer(app).name})" for app in _apps() if not _installer(app).is_file()]
    assert not missing, f"no installer at the app root: {', '.join(missing)}"


def test_installers_take_the_standard_options_and_refuse_root():
    """--no-desktop-shortcut, --uninstall, --uninstall --purge, --help; run as your own user, not with sudo."""
    for installer in _installers():
        text = installer.read_text(encoding="utf-8")
        for option in ("--no-desktop-shortcut", "--uninstall", "--purge", "--help"):
            assert f"{option})" in text, f"{installer.relative_to(SUITE)} does not handle {option}"
        assert "only goes with --uninstall" in text, f"{installer.relative_to(SUITE)} accepts --purge alone"
        assert "not with sudo" in text, f"{installer.relative_to(SUITE)} does not refuse to run as root"


def test_installers_upgrade_the_python_packages():
    """pip install -r with --upgrade: installing again brings each package to the newest version its requirements
    allow, a security fix within the range included (owner's decision, 13-10-2026)."""
    installers = sorted([*SUITE.glob("apps/*/install.sh"), *SUITE.glob("apps/*/packaging/*/*.sh"),
                         *SUITE.glob("portal/install.sh")])
    calls = [(path, line) for path in installers for line in path.read_text(encoding="utf-8").splitlines()
             if re.search(r"\bpip\"? install\b.* -r ", line) and not line.lstrip().startswith("#")]
    assert len(calls) >= 18
    assert [(path.relative_to(SUITE), line) for path, line in calls if "--upgrade -r" not in line] == []


def test_the_suite_names_its_system():
    import importlib.util
    spec = importlib.util.spec_from_file_location("nexus_suites", SUITE / "tools" / "suites.py")
    suites = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suites)
    assert suites.system() in suites.SYSTEMS, f"SYSTEM: one of {', '.join(suites.SYSTEMS)}"


def test_the_tags_start_with_the_suites_prefix():
    """The suite's release tags are ps5-<app>-v<x.y.z> and ps5-portal-v<x.y.z> (owner, 15-11-2026): TAG_PREFIX
    says ps5-, every pin in apps.toml has it, and no app's key starts with it, so a tag names one app."""
    import tomllib
    assert (SUITE / "TAG_PREFIX").read_text(encoding="utf-8").strip() == "ps5-"
    apps = tomllib.loads((SUITE / "portal" / "apps.toml").read_text(encoding="utf-8"))["apps"]
    assert all(entry["tag"] == f"ps5-{key}-v{entry['tag'].rsplit('-v', 1)[1]}" for key, entry in apps.items())
    assert not [p.name for p in (SUITE / "apps").iterdir() if p.name.startswith("ps5")]


def test_every_app_has_tests_and_ci_runs_them():
    import re
    for app in _apps():
        assert (app / "tests").is_dir(), f"{app.name}: no tests/"
        assert (app / "requirements-dev.txt").is_file(), f"{app.name}: no requirements-dev.txt (CI installs it)"
    # ci.yml reads its matrix from the repository's folders in a plan job (tools/ci_matrix.py)
    import importlib.util
    spec = importlib.util.spec_from_file_location("ci_matrix", SUITE / "tools" / "ci_matrix.py")
    ci_matrix = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci_matrix)
    listed = set()
    for workflow in sorted((SUITE / ".github" / "workflows").glob("ci*.yml")):
        text = workflow.read_text(encoding="utf-8")
        if static := re.search(r"dir: \[([^\]]*)\]", text):
            listed |= {entry.strip() for entry in static.group(1).replace("\n", " ").split(",")}
        if "tools/ci_matrix.py plan" in text:
            assert "dir: ${{ fromJSON(needs.plan.outputs.dirs) }}" in text, workflow.name
            listed |= set(ci_matrix.pytest_dirs(SUITE))
    folders = {path.parent.relative_to(SUITE).as_posix() for path in SUITE.glob("**/tests")
               if path.is_dir() and not (set(path.relative_to(SUITE).parts) & {".git", "site", "node_modules"})
               and not any(part.startswith(".venv") for part in path.relative_to(SUITE).parts)}
    assert folders <= listed, f"CI's pytest matrix misses {sorted(folders - listed)}"


def test_the_dev_venv_installs_every_test_folders_requirements():
    """requirements-dev.txt at the root, the one venv of ./test.sh and the wiki, takes in the requirements-dev.txt of
    every folder with tests/."""
    included = set(re.findall(r"^-r (\S+)/requirements-dev\.txt", (SUITE / "requirements-dev.txt").read_text(
        encoding="utf-8"), re.M))
    folders = {path.parent.relative_to(SUITE).as_posix() for path in SUITE.glob("*/tests")} | \
              {path.parent.relative_to(SUITE).as_posix() for path in SUITE.glob("*/*/tests")
               if path.parts[-3] in ("apps", "dev")}
    assert folders == included
    assert all((SUITE / folder / "requirements-dev.txt").is_file() for folder in included)
