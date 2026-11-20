# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/ci_matrix.py: the CI matrix read from the suite's folders (stage 2 of the release redesign), as the plan
job of ci.yml and tools/ci_local.py read it."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ci_matrix", ROOT / "tools" / "ci_matrix.py")
cm = importlib.util.module_from_spec(spec)
sys.modules["ci_matrix"] = cm
spec.loader.exec_module(cm)


def suite(folder: Path, system: str, apps: dict[str, bool]) -> Path:
    """A suite with *apps* (name: whether it has tests/), its portal and tools with tests, and some folders that
    never count."""
    (folder / "portal" / "tests").mkdir(parents=True)
    (folder / "portal" / "apps.toml").write_text("", encoding="utf-8")
    (folder / "tools" / "tests").mkdir(parents=True)
    (folder / "SYSTEM").write_text(f"{system}\n", encoding="utf-8")
    for app, tested in apps.items():
        (folder / "apps" / app).mkdir(parents=True)
        (folder / "apps" / app / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        if tested:
            (folder / "apps" / app / "tests").mkdir()
    (folder / "apps" / "zed" / "node_modules" / "tests").mkdir(parents=True)        # no VERSION, and never listed
    (folder / "site" / "tests").mkdir(parents=True)
    (folder / ".venv-linux" / "lib" / "tests").mkdir(parents=True)
    return folder


def test_the_pytest_matrix_is_every_folder_with_tests(tmp_path):
    bazzite = suite(tmp_path, "bazzite", {"gpu": True, "fan": True, "noui": False})
    assert cm.pytest_dirs(bazzite) == ["apps/fan", "apps/gpu", "portal", "tools"]


def test_the_suite_matches_its_workflow_and_the_layout_rule():
    """ci.yml reads its matrix from this tool, and the list is what tools/tests/test_layout.py wants: every folder
    with tests/, core, tools and dev/ among them."""
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tools/ci_matrix.py plan" in text and "dir: ${{ fromJSON(needs.plan.outputs.dirs) }}" in text
    dirs = cm.pytest_dirs(ROOT)
    assert {"core", "tools", "portal", "dev/nrt", "apps/fan"} <= set(dirs)
    assert all((ROOT / d / "tests").is_dir() for d in dirs)


def test_the_command_line(capsys):
    assert cm.main(["pytest"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("dirs=[") and "portal" in json.loads(out.removeprefix("dirs="))


def changed_suite(tmp_path: Path) -> Path:
    """A suite whose installer tests name their app, one of them every app, and whose dash tests read apps.toml."""
    folder = suite(tmp_path, "bazzite", {"gpu": True, "fan": True, "consoles": True})
    for name in ("core", "dev/dash"):
        (folder / name / "tests").mkdir(parents=True)
    (folder / "dev" / "dash" / "tests" / "test_local.py").write_text('MANIFEST = "apps.toml"\n', encoding="utf-8")
    (folder / "apps" / "consoles" / "native").mkdir()
    (folder / "apps" / "consoles" / "native" / "Cargo.toml").write_text("", encoding="utf-8")
    tests = folder / "tools" / "installer-tests"
    tests.mkdir()
    for name, text in {"gpu.sh": "bash apps/gpu/install.sh", "fan.sh": "bash apps/fan/install.sh",
                       "portal.sh": "bash portal/install.sh; tools/stage_app.py gpu",
                       "not-installed.sh": "for app in apps/*; do :; done", "release.sh": "apps/gpu portal/apps.toml",
                       "shims.sh": "# no test"}.items():
        (tests / name).write_text(text + "\n", encoding="utf-8")
    return folder


def test_a_push_runs_the_jobs_of_what_it_changed(tmp_path):
    """One app: its tests and tools' (the repository's rules), and the installer tests that name it."""
    folder = changed_suite(tmp_path)
    plan = cm.plan(["apps/gpu/gpu_governor/stress.py"], folder)
    assert plan == {"dirs": ["apps/gpu", "tools"], "installers": "gpu.sh not-installed.sh release.sh",
                    "native": False, "docs": False, "full": False}
    wiki = cm.plan(["docs/portal.md"], folder)
    assert (wiki["dirs"], wiki["installers"], wiki["docs"]) == (["tools"], "", True)
    assert cm.plan(["apps/consoles/native/src/lib.rs"], folder)["native"]
    assert cm.plan(["apps/fan/install.sh"], folder)["installers"] == "fan.sh not-installed.sh"
    assert cm.plan(["tools/stage_app.py"], folder)["installers"] == "portal.sh"         # the test that runs the tool
    assert cm.plan(["tools/installer-tests/fan.sh"], folder)["installers"] == "fan.sh"


def test_a_shared_file_is_the_change_of_every_folder_whose_tests_read_it(tmp_path):
    """The release commit pins apps.toml: the portal's tests, and those of the folders that read the manifest."""
    plan = cm.plan(["portal/apps.toml", "apps/fan/VERSION"], changed_suite(tmp_path))
    assert plan["dirs"] == ["apps/fan", "dev/dash", "portal", "tools"]
    assert plan["installers"] == "fan.sh not-installed.sh portal.sh release.sh"


def test_everything_when_the_change_is_not_known_or_every_job_stands_on_it(tmp_path):
    folder = changed_suite(tmp_path)
    everything = cm.plan(None, folder)
    assert everything["full"] and everything["dirs"] == cm.pytest_dirs(folder) and everything["native"]
    assert everything["installers"] == "fan.sh gpu.sh not-installed.sh portal.sh release.sh"   # the tarballs last
    for path in ("core/bazzite_console_core/theme.py", ".github/workflows/ci.yml", "tools/ci_matrix.py",
                 "requirements-dev.txt", "tools/installer-tests/shims.sh"):
        assert cm.plan([path], folder) == everything, path
    for path in ("tools/ci-apt.sh", "tools/ci-qt-libs.sh", "tools/ci-font.sh",        # the jobs on GitHub run these
                 ".github/actions/runner-packages/action.yml"):
        assert cm.plan([path], folder)["full"], path
    for path in ("tools/ci_local.py", "tools/ci-local.sh", "tools/ci-local/Containerfile"):
        local = cm.plan([path], folder)                                 # no job on GitHub runs the local CI
        assert not local["full"] and local["dirs"] == ["tools"] and not local["native"], path
    assert cm.changed_files("no-such-commit", folder) is None          # a new branch, a forced push


def test_the_plan_on_the_command_line(capsys):
    assert cm.main(["plan"]) == 0
    lines = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert lines["full"] == "true" and "portal" in json.loads(lines["dirs"])
    assert lines["installers"].endswith("release.sh") and "shims.sh" not in lines["installers"]
