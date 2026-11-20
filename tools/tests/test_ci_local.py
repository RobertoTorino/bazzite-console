# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/ci_local.py: the jobs it reads from the CI workflow (a matrix job once per entry), the ${{ }} expressions it
fills in, which jobs a name selects, and the requirement files that key a job's venv."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

pytest.importorskip("yaml")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ci_local  # noqa: E402

SUITE = Path(__file__).resolve().parents[2]
CI = SUITE / ".github" / "workflows" / "ci.yml"


def test_every_job_of_ci_yml_and_every_matrix_entry():
    jobs = {j.name: j for j in ci_local.load_jobs(CI)}
    assert {"versions", "native", "shell", "installers", "docs"} <= set(jobs)
    assert "pytest/apps/fan" in jobs and "pytest" not in jobs
    assert jobs["pytest/apps/fan"].matrix == {"dir": "apps/fan"}
    assert jobs["shell"].runs_here
    assert not ci_local.Job("windows", {"runs-on": "windows-latest"}).runs_here     # GitHub's only, not here


def test_the_free_memory_limits_the_jobs_at_a_time():
    """Half the cores, fewer when the memory is short, never under two; a system that names no memory gets half."""
    assert ci_local.default_workers(12, 32000) == 6
    assert ci_local.default_workers(12, 5000) == 3
    assert ci_local.default_workers(12, 900) == 2
    assert ci_local.default_workers(2, 32000) == 2
    assert ci_local.default_workers(12, 0) == 6
    assert ci_local.free_memory() > 0


def test_a_job_that_compiles_runs_alone():
    """The native job starts a compiler per core; beside five other jobs one of them crashed for lack of memory."""
    jobs = {j.name: j for j in ci_local.load_jobs(CI)}
    assert [name for name, job in jobs.items() if job.compiles] == ["native"]
    assert ci_local.Job("wheel", {"steps": [{"run": "pip install maturin\nmaturin build --release"}]}).compiles
    assert not ci_local.Job("docs", {"steps": [{"uses": "actions/checkout@v7"}, {"run": "mkdocs build"}]}).compiles


def test_a_matrix_from_a_plan_job_is_read_by_running_it(tmp_path):
    """ci.yml's pytest matrix is the plan job's output (tools/ci_matrix.py, fromJSON): the plan job's steps run
    here and their $GITHUB_OUTPUT lines give the entries; the plan job itself is a job too."""
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text('''jobs:
  plan:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.plan.outputs.dirs }}
    steps:
      - uses: actions/checkout@v7
      - id: plan
        run: echo 'dirs=["a/one", "a/two"]' | tee -a "$GITHUB_OUTPUT"
      - run: echo 'word=plain' >> "$GITHUB_OUTPUT"
  pytest:
    needs: plan
    runs-on: ubuntu-latest
    strategy:
      matrix:
        dir: ${{ fromJSON(needs.plan.outputs.dirs) }}
    steps:
      - run: echo ${{ matrix.dir }}
''', encoding="utf-8")
    jobs = {j.name: j for j in ci_local.load_jobs(workflows / "ci.yml")}
    assert set(jobs) == {"plan", "pytest/a/one", "pytest/a/two"}
    assert jobs["pytest/a/two"].matrix == {"dir": "a/two"}
    assert ci_local.job_outputs(yaml.safe_load((workflows / "ci.yml").read_text())["jobs"], "plan", tmp_path) == {
        "dirs": ["a/one", "a/two"], "word": "plain"}
    assert not list(tmp_path.glob(".ci-local*"))                   # nothing written into the checkout


def test_a_job_the_plan_leaves_out_is_not_run_and_its_outputs_reach_the_steps(tmp_path):
    """ci.yml's plan job names what a push runs (tools/ci_matrix.py plan): a job whose if compares one of its
    outputs is skipped when it is false, as on GitHub, and a step reads an output as its text."""
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text('''jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - env:
          BASE: ${{ github.event.pull_request.base.sha || github.event.before }}
        run: |
          echo "docs=false" >> "$GITHUB_OUTPUT"
          echo "native=true" >> "$GITHUB_OUTPUT"
          echo "installers=$BASE.sh fan.sh" >> "$GITHUB_OUTPUT"
  docs:
    needs: plan
    if: needs.plan.outputs.docs == 'true'
    runs-on: ubuntu-latest
  native:
    needs: plan
    if: needs.plan.outputs.native == 'true'
    runs-on: ubuntu-latest
  installers:
    needs: plan
    if: needs.plan.outputs.installers != ''
    runs-on: ubuntu-latest
    steps:
      - env:
          TESTS: ${{ needs.plan.outputs.installers }}
        run: echo $TESTS
''', encoding="utf-8")
    jobs = {j.name: j for j in ci_local.load_jobs(workflows / "ci.yml", base="abc")}
    assert set(jobs) == {"plan", "native", "installers"}
    step = jobs["installers"].spec["steps"][0]
    assert ci_local.expand(step["env"]["TESTS"], jobs["installers"], "abc") == "abc.sh fan.sh"


def test_expressions_and_selection():
    jobs = ci_local.all_jobs(SUITE)
    fan = next(j for j in jobs if j.name == "pytest/apps/fan")
    assert ci_local.expand("cd ${{ matrix.dir }}", fan, "abc") == "cd apps/fan"
    assert ci_local.expand("${{ github.event.pull_request.base.sha || github.event.before }}", fan, "abc") == "abc"
    assert [j.name for j in ci_local.selected(jobs, ["pytest/tools"])] == ["pytest/tools"]
    assert [j.name for j in ci_local.selected(jobs, ["shell"])] == ["shell"]
    assert all(j.name.startswith("pytest/") for j in ci_local.selected(jobs, ["pytest"]))
    assert {"pytest/core", "pytest/tools", "pytest/dev/nrt", "pytest/portal"} <= {
        j.name for j in ci_local.selected(jobs, ["pytest"])}
    assert ci_local.selected(jobs, []) == jobs


def test_requirement_files_follow_includes(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "requirements.txt").write_text("PyQt6\n")
    (tmp_path / "app" / "requirements-dev.txt").write_text("-r ../requirements.txt\npytest\n")
    found = ci_local.requirement_files("python -m pip install -q -r requirements-dev.txt", tmp_path / "app")
    assert [p.resolve() for p in found] == [(tmp_path / "app" / "requirements-dev.txt").resolve(),
                                            (tmp_path / "requirements.txt").resolve()]


def test_ci_runs_for_every_branch_push_and_no_tag():
    """A push to a branch runs CI, a tag does not (tag-release.sh tags only a commit CI passed). GitHub reads a push
    filter with only tags or tags-ignore as "no branch at all", which ran CI for no push."""
    import yaml
    for workflow in (CI,):
        spec = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        push = spec.get("on", spec.get(True))["push"]                     # PyYAML reads the key on as True
        assert push.get("branches") == ["**"] and not {"branches-ignore", "tags", "tags-ignore"} & set(push)
        assert all("timeout-minutes" in job for job in spec["jobs"].values()), workflow.name


def test_only_the_workflows_a_push_starts():
    """Without job names, the workflows GitHub starts for the push: ci.yml has no paths filter, so every push."""
    names = lambda changed: [name for name, _ in ci_local.workflows(SUITE, changed)]   # noqa: E731
    assert names(None) == [name for name, _ in ci_local.WORKFLOWS] == ["ci.yml"]
    assert names(["portal/apps.toml"]) == names(["core/bazzite_console_core/app.py"]) == names([]) == ["ci.yml"]
    assert ci_local.glob_match("apps/**", "apps/a/b.py")
    assert not ci_local.glob_match("apps/**", "apps-x/a.py")
    assert ci_local.glob_match("test.sh", "test.sh") and not ci_local.glob_match("test.sh", "tools/test.sh")


def test_a_cache_is_a_hit_only_under_its_key(tmp_path, monkeypatch):
    """A step that fills a cache (if: cache-hit != 'true') is skipped only when the folder was filled under the
    same key: when a file its hashFiles names changes, the step runs again, as on GitHub (owner, 20-11-2026: the
    native job found the FFmpeg of the build.sh before its version changed, and failed)."""
    work, cache, folder = tmp_path / "work", tmp_path / "cache", tmp_path / "kept"
    work.mkdir()
    (work / "build.sh").write_text("one", encoding="utf-8")
    monkeypatch.setattr(ci_local, "WORK", work)
    monkeypatch.setattr(ci_local, "CACHE", cache)
    spec = {"runs-on": "ubuntu-latest", "steps": [
        {"id": "kept", "uses": "actions/cache@v6",
         "with": {"path": str(folder), "key": "kept-${{ runner.os }}-${{ hashFiles('build.sh') }}"}},
        {"if": "steps.kept.outputs.cache-hit != 'true'", "run": f"mkdir -p {folder} && echo run >> {folder}/runs"}]}

    def runs() -> int:
        assert ci_local.run_job(ci_local.Job("native", spec), "").ok
        return len((folder / "runs").read_text(encoding="utf-8").split())

    assert runs() == 1
    assert runs() == 1                                             # the same key: a hit
    (work / "build.sh").write_text("two", encoding="utf-8")
    assert runs() == 2                                             # another key: a miss
    assert runs() == 2
    (folder / ci_local.CACHE_KEY).unlink()
    assert runs() == 3                                             # a folder without a key: a miss

    spec["steps"][1]["run"] = "false"
    (work / "build.sh").write_text("three", encoding="utf-8")
    assert not ci_local.run_job(ci_local.Job("native", spec), "").ok
    assert not ci_local.cache_hit(*ci_local.cache_of("kept", spec["steps"], ci_local.Job("native", spec), ""))
