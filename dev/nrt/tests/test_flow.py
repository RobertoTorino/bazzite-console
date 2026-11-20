# SPDX-License-Identifier: GPL-3.0-or-later
"""flow.py, the release: what it holds, what Start writes (as steps 1 and 2 would, with the portal's version worked
out), when Start can go, its one command, and the commands that follow the run."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from nexus_release_tool import flow
from nexus_release_tool import plan as rp

APPS_TOML = ('[apps.test]\nname = "T"\nsummary = "s"\ntag = "ps5-test-v0.1.0"\nsha256 = "' + "ab" * 32 + '"\n'
             'required = true\ncategory = "sustainable"\ninstall = ["i"]\nuninstall = ["u"]\ndetect = ["d"]\n')


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def sh(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def suite(tmp_path) -> Path:
    """A suite with its own tag prefix (ps5-), its release on GitHub (release.yml), released once, then a change
    in its test app."""
    root = tmp_path / "suite"
    write(root / ".gitignore", "__pycache__/\n")
    write(root / "TAG_PREFIX", "ps5-\n")
    write(root / "core/VERSION", "0.1.0\n")
    write(root / "core/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nVersion 0.1.0.\n")
    write(root / "core/bazzite_console_core/__init__.py", '__version__ = "0.1.0"\n')
    write(root / "portal/VERSION", "1.0.0\n")
    write(root / "portal/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nRelease 1.0.0.\n")
    write(root / "apps/test/VERSION", "0.1.0\n")
    write(root / "apps/test/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nRelease 0.1.0.\n")
    write(root / "apps/test/app.py", "print('hi')\n")
    write(root / "portal/apps.toml", APPS_TOML)
    write(root / ".github/workflows/release.yml", "on:\n  workflow_dispatch:\n")
    sh(root, "init", "-q", "-b", "main")
    sh(root, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    sh(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "start")
    for tag in ("ps5-test-v0.1.0", "ps5-portal-v1.0.0"):
        sh(root, "tag", tag)
    write(root / "apps/test/app.py", "print('hello')\n")
    write(root / "apps/test/CHANGELOG", "Changelog: 02-01-2026 00:00:00\n\nAdded. A greeting.\n\n"
                                        "Changelog: 01-01-2026 00:00:00\n\nRelease 0.1.0.\n")
    sh(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "greeting")
    return root


def test_the_release_runs_on_github_through_release_yml(suite):
    assert flow.releases_on_github(suite)
    (suite / ".github/workflows/release.yml").write_text("on:\n  push:\n", encoding="utf-8")
    assert not flow.releases_on_github(suite) and flow.waiting_portals(suite) == []
    (suite / ".github/workflows/release.yml").write_text("on:\n  workflow_call:\n", encoding="utf-8")
    assert flow.releases_on_github(suite)


def test_the_release_holds_the_changed_app_and_its_portal(suite):
    found = {p.unit.key: p for p in flow.picks(suite)}
    assert set(found) == {"test", "portal"}                         # core did not change
    assert found["test"].choices[0] == "0.2.0"                      # Added. -> minor
    assert found["portal"].version == flow.AUTO
    assert found["test"].label == "test" and found["test"].unit.last_tag == "ps5-test-v0.1.0"   # the suite's prefix


def test_nothing_changed_nothing_to_release(suite):
    sh(suite, "tag", "-f", "ps5-test-v0.1.0")                        # the change is in the tag now
    assert flow.picks(suite) == []


def test_a_portal_bump_with_nothing_else_is_nothing_to_release(suite):
    """Only the version and its Release entry moved since the tags (owner, 15-11-2026: Bump wrote portal 21.0.2 while
    21.0.1 waited for its device test, and Start released it, a second portal of the same apps)."""
    sh(suite, "tag", "-f", "ps5-test-v0.1.0")
    write(suite / "portal/VERSION", "1.0.1\n")
    write(suite / "portal/CHANGELOG", "Changelog: 03-01-2026 00:00:00\n\nRelease 1.0.1.\n\n"
                                        "Changelog: 01-01-2026 00:00:00\n\nRelease 1.0.0.\n")
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "bump")
    portal = next(u for u in rp.load_units(suite) if u.kind == "portal")
    assert portal.changed == [] and not portal.needs_release
    assert flow.picks(suite) == []
    write(suite / "portal/CHANGELOG", "Changelog: 04-01-2026 00:00:00\n\nFixed. A tile.\n\n"
                                        + (suite / "portal/CHANGELOG").read_text())
    assert [p.unit.key for p in flow.picks(suite)] == ["portal"]    # a change of its own: released


def test_a_version_copy_that_moved_with_something_else_still_counts(suite):
    sh(suite, "tag", "-f", "ps5-test-v0.1.0")
    write(suite / "apps/test/VERSION", "0.1.1\n")
    write(suite / "apps/test/app.py", "__version__ = \"0.1.1\"\nprint('hello')\n")
    unit = next(u for u in rp.load_units(suite) if u.key == "test")
    assert unit.changed == ["apps/test/app.py"]                  # VERSION is only the bump; app.py is more
    write(suite / "apps/test/app.py", "print('hello')\n")
    unit = next(u for u in rp.load_units(suite) if u.key == "test")
    assert unit.changed == [] and not unit.needs_release


def test_a_withdrawal_entry_is_no_release_of_the_app(suite):
    """Retract writes a Withdrawn: entry in the app's CHANGELOG: the app ships nothing new, its portal does."""
    sh(suite, "tag", "-f", "ps5-test-v0.1.0")
    write(suite / "apps/test/CHANGELOG", "Changelog: 05-01-2026 00:00:00\n\nWithdrawn: ps5-test-v0.1.0. Broken.\n\n"
                                            + (suite / "apps/test/CHANGELOG").read_text())
    unit = next(u for u in rp.load_units(suite) if u.key == "test")
    assert not unit.needs_release


def test_start_writes_the_release_as_steps_one_and_two_would(suite):
    log, tags = flow.write(suite, flow.picks(suite), base="HEAD")
    assert tags == ["ps5-test-v0.2.0", "ps5-portal-v1.1.0"]
    assert (suite / "apps/test/VERSION").read_text() == "0.2.0\n"
    manifest = (suite / "portal/apps.toml").read_text()
    assert 'tag = "ps5-test-v0.2.0"\nsha256 = ""\n' in manifest          # the sha256 is the workflow's
    assert (suite / "portal/VERSION").read_text() == "1.1.0\n"       # an app minor: a portal minor
    assert "Release 1.1.0. Pins ps5-test-v0.2.0." in (suite / "portal/CHANGELOG").read_text()
    assert "Release 0.2.0." in (suite / "apps/test/CHANGELOG").read_text()
    assert len(log) == 2


def test_a_typed_version_overrides_the_suggestion(suite):
    chosen = flow.picks(suite)
    for pick in chosen:
        pick.version = {"test": "1.0.0", "portal": "2.0.0"}[pick.unit.key]
        pick.notes = "notes" if pick.unit.key == "test" else ""
    _log, tags = flow.write(suite, chosen, base="HEAD")
    assert tags == ["ps5-test-v1.0.0", "ps5-portal-v2.0.0"]
    assert "Release 1.0.0. notes" in (suite / "apps/test/CHANGELOG").read_text()


def test_a_portal_typed_too_low_gets_what_ci_asks(suite):
    chosen = flow.picks(suite)
    for pick in chosen:
        if pick.unit.key == "test":
            pick.version = "1.0.0"                                  # a major app release
        if pick.unit.key == "portal":
            pick.version = "1.0.1"
    log, tags = flow.write(suite, chosen, base="HEAD")
    assert "ps5-portal-v2.0.0" in tags and any("less than CI asks" in line for line in log)


def test_wrong_versions_are_refused_before_anything_is_written(suite):
    chosen = flow.picks(suite)
    chosen[0].version = "0.0.9"
    assert flow.problems(chosen) == ["test: 0.0.9 is not higher than 0.1.0, which is already tagged"]
    chosen[0].version = "abc"
    assert "is not x.y.z" in flow.problems(chosen)[0]


def test_start_needs_a_clean_tree_at_the_last_push(suite):
    assert flow.ready(suite, base="HEAD") == []
    (suite / "apps/test/app.py").write_text("changed\n")
    assert flow.ready(suite, base="HEAD")[0].startswith("The working tree has changes")
    sh(suite, "checkout", "-q", "--", ".")
    assert "not pushed" in flow.ready(suite, base="HEAD~1")[0]
    assert "git fetch" in flow.ready(suite, base="origin/main")[0]


def test_the_one_command_commits_pushes_and_starts_the_workflow():
    command = flow.start_command(flow.commit_message(["ps5-test-v0.2.0", "ps5-portal-v1.1.0"]))
    assert command.startswith("git commit -a -q -m 'Release ps5-test-v0.2.0, ps5-portal-v1.1.0' && ")
    assert "git push origin HEAD:main && gh workflow run release.yml --ref main" in command
    assert '-f commit="$(git rev-parse HEAD)"' in command


def test_the_run_is_followed_stopped_and_resumed():
    other = rp.BuildRun("CI Nexus", "main", "completed", "success", "https://github.com/o/r/actions/runs/1", "abc", "t",
                        file="ci-nexus.yml")
    run = rp.BuildRun("Release", "main", "in_progress", "", "https://github.com/o/r/actions/runs/42", "abc", "t",
                      file="release.yml")
    assert flow.release_run([other, run]) is run and flow.release_run([other, run], "def") is None
    tagged = rp.BuildRun("Release", "ps5-portal-v1.1.0", "completed", "success",
                         "https://github.com/o/r/actions/runs/43", "pin", "Pin ps5-test-v0.2.0", file="release.yml")
    assert flow.release_run([tagged, other, run]) is run           # Publish's tag started it: not the release
    assert flow.stop_command(run) == "gh run cancel 42"
    assert flow.resume_command(run) == "gh run rerun 42 --failed"


def test_the_device_test_and_publish_work_on_the_portals_draft(suite):
    assert flow.waiting_portals(suite) == ["ps5-portal-v1.0.0"]
    assert flow.publish_command("ps5-portal-v1.1.0") == ("gh release edit ps5-portal-v1.1.0 --draft=false --latest"
                                                        " && git fetch origin main tag ps5-portal-v1.1.0")   # seen at once
    line = flow.device_test_line(suite, "ps5-portal-v1.1.0")
    assert line.endswith("tools/check-release.sh draft ps5-portal-v1.1.0")


def test_a_release_commit_whose_push_stopped_is_pushed_and_started(suite):
    assert flow.unpushed_release(suite, base="HEAD") == ""
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m",
       "Release ps5-test-v0.2.0, ps5-portal-v1.1.0")
    assert flow.unpushed_release(suite, base="HEAD~1") == "Release ps5-test-v0.2.0, ps5-portal-v1.1.0"
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "other")
    assert flow.unpushed_release(suite, base="HEAD~2") == ""             # not right on top of the last push
    assert flow.push_and_start_command().startswith("git push origin HEAD:main && gh workflow run release.yml")


@pytest.fixture
def release_window(suite, tmp_path):
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    launched: list[str] = []
    w = main_window.ReleaseWindow(suite, launch=launched.append, runs_source=None, status_source=None,
                                  claude_source=None)
    w.base_ref = "HEAD"
    w.reload()
    w.launched = launched
    yield w
    w.close()


def test_the_window_opens_on_the_nexus_release(release_window):
    w = release_window
    page = w.release_page
    assert w.tabs.widget(0) is page and w.tabs.tabText(0) == "Nexus release"
    assert [pick.label for pick, _combo, _notes in page.rows] == ["test", "portal"]
    assert page.rows[0][1].currentText() == "0.2.0" and page.rows[1][1].currentText() == flow.AUTO
    assert page.start_button.isEnabled() and page.portal_choice.currentText() == "ps5-portal-v1.0.0"
    assert not page.stop_button.isEnabled() and not page.resume_button.isEnabled()


def test_the_suite_field_has_room_before_its_text_and_only_it(release_window):
    page = release_window.release_page
    assert "padding-left: 8px" in page.portal_choice.styleSheet()
    assert all(not combo.styleSheet() for _pick, combo, _notes in page.rows)


def test_start_writes_the_release_and_runs_the_one_command(release_window, monkeypatch):
    w = release_window
    page = w.release_page
    ran = []
    monkeypatch.setattr(w, "confirm_git", lambda *a: True)
    monkeypatch.setattr(w, "run_git", ran.append)
    page.rows[0][2].setText("A greeting")
    page.start()
    assert ran == [flow.start_command("Release ps5-test-v0.2.0, ps5-portal-v1.1.0")]
    assert "Release 0.2.0. A greeting" in (w.root / "apps/test/CHANGELOG").read_text()
    assert "test: 0.2.0" in page.output.toPlainText()


def identity(monkeypatch) -> None:
    """A committer for git rebase, which CI's runner has none of."""
    for name in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(name, "t@t" if "EMAIL" in name else "t")


def test_start_fetches_the_tags_and_main_first_and_goes_on(release_window, monkeypatch, tmp_path):
    """A portal is tagged on GitHub when it is published, and a release pins on main after it: neither is here until
    fetched (owner, 31-10-2026: Release 6.2.0 again after 6.2.0 was out; the Pin ... commit refused the push). Start
    fetches the tags and brings in main's commits under this checkout, reads the versions again and goes on to its
    question, with nothing to do by hand."""
    identity(monkeypatch)
    w = release_window
    page = w.release_page
    origin = tmp_path / "origin.git"
    sh(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    sh(w.root, "remote", "add", "origin", str(origin))
    sh(w.root, "push", "-q", "origin", "main")
    sh(w.root, "push", "-q", "origin", "HEAD:refs/tags/ps5-portal-v1.1.0")    # published on GitHub, not fetched
    other = tmp_path / "other"                                       # the release's Pin ... commit, on GitHub only
    sh(tmp_path, "clone", "-q", "-b", "main", str(origin), str(other))
    write(other / "portal/apps.toml", (other / "portal/apps.toml").read_text() + "\n")
    sh(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Pin ps5-test-v0.1.0")
    sh(other, "push", "-q", "origin", "HEAD:main")
    w.base_ref = "origin/main"
    ran, asked = [], []
    monkeypatch.setattr(w, "confirm_git", lambda *a: asked.append(a[1]) or True)
    monkeypatch.setattr(w, "run_git", ran.append)
    page.start()
    assert sh(w.root, "tag", "--list", "ps5-portal-v1.1.0").strip() == "ps5-portal-v1.1.0"
    assert "Pin ps5-test-v0.1.0" in sh(w.root, "log", "--format=%s")       # brought in, under the release
    assert len(ran) == 1 and "ps5-portal-v1.2.0" in ran[0] and "portal: 1.0.0 -> auto" in asked[0]
    assert flow.fetch_tags(w.root) == []                            # nothing new the second time


def test_fetch_tags_names_a_tag_here_that_git_will_not_move(suite, tmp_path, monkeypatch):
    """A tag here on another commit than GitHub's: git refuses to move it ("would clobber existing tag"), and the
    message says which tag and what to do (owner, 03-11-2026: Start only said the fetch failed)."""
    identity(monkeypatch)
    origin = tmp_path / "origin.git"
    sh(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    sh(suite, "remote", "add", "origin", str(origin))
    sh(suite, "push", "-q", "origin", "main", "--tags")
    assert flow.fetch_tags(suite) == []
    sh(suite, "push", "-q", "-f", "origin", "HEAD:refs/tags/ps5-test-v0.1.0")   # GitHub's tag moved on; this one stays
    failed = flow.fetch_tags(suite)
    assert isinstance(failed, flow.FetchFailed) and failed.clobbered == ("ps5-test-v0.1.0",)
    text = failed.explain()
    assert "would clobber existing tag" in text and "The tag ps5-test-v0.1.0 here points to another commit" in text
    assert "git tag -d ps5-test-v0.1.0\ngit fetch --tags" in text and text.endswith(flow.WAITS)
    sh(suite, "tag", "-d", "ps5-test-v0.1.0")
    assert flow.fetch_tags(suite) == ["ps5-test-v0.1.0"]                # dropped here, GitHub's comes in
    assert flow.FetchFailed("fatal: unable to access").explain().startswith(
        "git fetch --tags failed:\n\nfatal: unable to access\n\nThe release reads")        # offline: no tag to drop
    two = flow.FetchFailed("", ("a-v1.0.0", "b-v2.0.0")).explain()
    assert "The tags a-v1.0.0, b-v2.0.0 here point to another commit" in two and "git tag -d b-v2.0.0" in two


def test_start_shows_why_the_fetch_failed(release_window, monkeypatch, tmp_path):
    identity(monkeypatch)
    w = release_window
    origin = tmp_path / "origin.git"
    sh(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    sh(w.root, "remote", "add", "origin", str(origin))
    sh(w.root, "push", "-q", "origin", "main", "--tags")
    sh(w.root, "push", "-q", "-f", "origin", "HEAD:refs/tags/ps5-test-v0.1.0")
    from PyQt6.QtWidgets import QMessageBox
    shown, ran = [], []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    monkeypatch.setattr(w, "run_git", ran.append)
    w.release_page.start()
    assert ran == [] and len(shown) == 1 and "git tag -d ps5-test-v0.1.0" in shown[0]


def test_catch_up_brings_in_mains_commits_under_this_checkouts(suite, tmp_path, monkeypatch):
    identity(monkeypatch)
    origin = tmp_path / "origin.git"
    sh(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    sh(suite, "remote", "add", "origin", str(origin))
    sh(suite, "push", "-q", "origin", "main")
    sh(suite, "fetch", "-q", "origin")
    assert flow.catch_up(suite) == 0                                # nothing to bring in
    other = tmp_path / "other"
    sh(tmp_path, "clone", "-q", "-b", "main", str(origin), str(other))
    write(other / "portal/apps.toml", (other / "portal/apps.toml").read_text() + "\n")
    sh(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Pin ps5-test-v0.1.0")
    sh(other, "push", "-q", "origin", "HEAD:main")
    write(suite / "apps/test/app.py", "print('hello again')\n")   # this checkout's own commit, not pushed
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "mine")
    sh(suite, "fetch", "-q", "origin")
    write(suite / "apps/test/app.py", "not committed\n")
    assert flow.catch_up(suite) is None                             # changes not committed: nothing is done
    sh(suite, "checkout", "-q", "--", ".")
    assert flow.catch_up(suite) == 1
    assert sh(suite, "log", "--format=%s", "-2").split("\n")[:2] == ["mine", "Pin ps5-test-v0.1.0"]


def test_a_version_only_offered_follows_the_next_offer(release_window):
    """After the tags are read again the table offers anew; what the owner typed stays (owner, 31-10-2026: the old
    offer 5.3.0 stayed as if typed, and Start refused it)."""
    page = release_window.release_page
    pick, combo, _notes = page.rows[0]
    pick.choices[0] = "0.1.5"                                       # what it offered before the tags were read
    combo.setEditText("0.1.5")
    page.fill()
    assert page.rows[0][1].currentText() == "0.2.0"
    page.rows[0][1].setEditText("0.4.0")                            # typed: stays
    page.fill()
    assert page.rows[0][1].currentText() == "0.4.0"


def test_changes_not_committed_make_commit_the_step_to_do(release_window, monkeypatch):
    """The steps in their order (owner, 30-10-2026: "exactly what has to be done in their logical sequence"): with
    changes in the tree, step 2 Commit is the one lit, and Start waits."""
    w = release_window
    page = w.release_page
    (w.root / "apps/test/app.py").write_text("changed\n")
    w.reload()
    states = flow.step_states(page.facts)
    assert states["pull"] == "done" and states["commit"] == "now" and states["start"] == "later"
    assert page.marks["commit"].text() == "▶" and "1 file changed" in page.details["commit"].text()
    assert not page.start_button.isEnabled() and not page.push_button.isEnabled()
    assert page.commit_message.text() == "see changelog" and page.commit_button.isEnabled()
    page.commit_message.clear()
    assert not page.commit_button.isEnabled()                   # a message first
    page.commit_message.setText("A greeting")
    assert page.commit_button.isEnabled()
    ran = []
    monkeypatch.setattr(w, "run_git", ran.append)
    page.commit()
    assert ran[0].startswith("python3 tools/all_tests.py && git add -A && tools/fix-modes.sh")
    assert "git commit" in ran[0] and "A greeting" in ran[0]
    assert "check_manifest.py" in ran[0]
    warned = []
    monkeypatch.setattr("nexus_release_tool.release_page.QMessageBox.warning", lambda *a: warned.append(a[2]))
    page.start()
    assert warned and "working tree has changes" in warned[0]


def _run(sha="abc1234", file="release.yml", workflow="Release", status="completed",
         conclusion="success", ref="main", title="title"):
    return rp.BuildRun(workflow, ref, status, conclusion, f"https://github.com/o/r/actions/runs/{abs(hash(sha+file))}",
                       sha, title, file=file)


def test_the_step_to_do_follows_the_release():
    """Every step in turn: pull, commit, push, CI, Start, the run, the device test and Publish, the pin commit."""
    assert flow.current_step(flow.Facts(behind=2, dirty=True)) == "pull"
    assert flow.current_step(flow.Facts(dirty=True, ahead=1)) == "commit"
    assert flow.current_step(flow.Facts(ahead=1)) == "push"
    assert flow.current_step(flow.Facts(ci="building", something=True)) == "ci"
    states = flow.step_states(flow.Facts(ci="failed", something=True))
    assert states["ci"] == "failed" and states["commit"] == "done" and states["start"] == "later"
    assert flow.current_step(flow.Facts(ci="passed", something=True)) == "start"
    assert flow.current_step(flow.Facts(ci="unknown", something=True)) == "start"      # no GitHub here: not held
    assert flow.current_step(flow.Facts(ci="passed")) == ""                             # nothing to release
    assert set(flow.step_states(flow.Facts(ci="passed")).values()) == {"done"}
    assert flow.current_step(flow.Facts(ahead=1, unpushed="Release x")) == "start"     # Push and start
    running = _run(status="in_progress", conclusion="")
    assert flow.current_step(flow.Facts(run=running)) == "run"
    failed = flow.step_states(flow.Facts(run=_run(conclusion="failure")))
    assert failed["run"] == "failed" and failed["start"] == "done" and failed["test"] == "later"
    states = flow.step_states(flow.Facts(run=_run(), drafts=["ps5-portal-v2.0.0"]))
    assert states["test"] == states["publish"] == "now" and states["run"] == "done"
    assert flow.current_step(flow.Facts(run=_run(), behind=1)) == "finish"
    assert flow.current_step(flow.Facts(run=_run())) == ""                               # out and pulled
    waiting = flow.Facts(run=_run(), building=("Wiki on main",))                         # GitHub still runs
    assert flow.current_step(waiting) == "ready" and flow.step_states(waiting)["finish"] == "done"
    assert flow.current_step(flow.Facts(run=_run(), behind=1, building=("Wiki on main",))) == "finish"
    assert flow.KEYS[-1] == "ready" and len(flow.KEYS) == 10
    assert flow.current_step(flow.Facts(run=_run(), drafts=["x"], dirty=True)) == "commit"  # a fix after Not OK


def test_a_failed_release_gets_its_fix_then_starts_again_on_it():
    """CI failed on the release commit (30-10-2026): the release is written and pushed, so its fix goes through Commit,
    Push and CI, then the run starts again on it; Start never writes it a second time."""
    failed = _run(conclusion="failure")
    states = flow.step_states(flow.Facts(run=failed, dirty=True, restart=True))
    assert flow.current_step(flow.Facts(run=failed, dirty=True, restart=True)) == "commit"
    assert states["start"] == "done" and states["run"] == "failed" and states["commit"] == "now"
    assert flow.current_step(flow.Facts(run=failed, ahead=1, restart=True)) == "push"
    assert flow.current_step(flow.Facts(run=failed, restart=True, ci="building")) == "ci"
    assert flow.current_step(flow.Facts(run=failed, restart=True, ci="passed", something=True)) == "run"
    assert flow.current_step(flow.Facts(run=failed, ci="passed")) == "run"             # no fix: Resume run
    assert flow.restart_command().startswith('gh workflow run release.yml --ref main -f commit="$(git rev-parse '
                                             'HEAD)"')


def test_a_failed_release_run_lasts_with_fixes_on_top(suite):
    head = sh(suite, "rev-parse", "HEAD").strip()
    failed = _run(head, conclusion="failure")
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Fix CI")
    assert flow.cycle_run(suite, [failed]) is failed               # still that release: its fix is on top
    assert flow.cycle_run(suite, [_run(head)]) is None              # one that passed: other work ends it


def test_failed_ci_runs_again(release_window, monkeypatch):
    """CI failed for GitHub's own trouble (30-10-2026, Actions degraded): step 4 lights Run CI again, which starts
    the failed CI runs of HEAD again; a passed one and another commit's are left alone."""
    runs = [_run("aaa", "ci.yml", "CI", conclusion="failure"), _run("aaa", "ci-nexus.yml", "CI Nexus"),
            _run("bbb", "ci.yml", "CI", conclusion="failure")]
    assert flow.failed_ci(runs, "aaa") == [runs[0]]
    assert flow.rerun_ci_command(flow.failed_ci(runs, "aaa")) == f"gh run rerun {flow.run_id(runs[0])} --failed"
    w = release_window
    page = w.release_page
    head = sh(w.root, "rev-parse", "HEAD").strip()
    monkeypatch.setattr(w.build, "runs", [_run(head, "ci.yml", "CI", conclusion="failure")])
    monkeypatch.setattr(w.build, "source", object())
    page.show_state()
    assert page.facts.ci == "failed" and page.rerun_ci_button.isEnabled()
    assert "Run CI again" in page.details["ci"].text()
    ran = []
    monkeypatch.setattr(w, "run_git", ran.append)
    page.rerun_ci()
    assert ran and ran[0].startswith("gh run rerun ") and ran[0].endswith(" --failed")
    # Pressed: until GitHub shows the next attempt, the run still reads as failed, and the button stays off
    # (owner, 15-11-2026: a second press failed with "This workflow is already running")
    page.show_state()
    assert not page.rerun_ci_button.isEnabled() and "asked GitHub to start" in page.details["ci"].text()
    page.rerun_ci()
    assert len(ran) == 1
    w.ticker.show_runs(w.build.runs, signed_in=False)
    assert w.ticker.rerun_button.isHidden()                         # the ticker's Run again: the same memory
    again = rp.BuildRun(**{**w.build.runs[0].__dict__, "attempt": 2})   # it ran again and failed again
    monkeypatch.setattr(w.build, "runs", [again])
    page.show_state()
    assert page.rerun_ci_button.isEnabled()


def test_ci_state_reads_the_ci_runs_of_the_commit():
    runs = [_run("aaa", "ci.yml", "CI"), _run("aaa", "ci-nexus.yml", "CI Nexus", "in_progress", ""),
            _run("aaa", "release.yml"), _run("bbb", "ci.yml", "CI", conclusion="failure")]
    assert flow.ci_state(runs, "aaa") == "building" and flow.ci_state(runs, "bbb") == "failed"
    assert flow.ci_state(runs[:1], "aaa") == "passed" and flow.ci_state(runs, "ccc") == "none"
    failed = _run("aaa", "ci.yml", "CI", conclusion="failure")
    assert flow.ci_state([runs[0], failed], "aaa") == "failed" and flow.failed_ci([runs[0], failed], "aaa") == [failed]


def test_the_release_run_lasts_until_other_work_is_committed(suite):
    head = sh(suite, "rev-parse", "HEAD").strip()
    run = _run(head)
    assert flow.cycle_run(suite, [run]) is run
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Pin ps5-test-v0.2.0")
    assert flow.cycle_run(suite, [run]) is run                    # the pin commit pulled: still this release
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Other work")
    assert flow.cycle_run(suite, [run]) is None
    assert flow.cycle_run(suite, []) is None
    assert flow.published(suite, [_run(ref="ps5-portal-v9.9.9")], "ps5-portal-v9.9.9")
    assert not flow.published(suite, [], "ps5-portal-v9.9.9")


def test_a_release_with_a_draft_to_test_lasts_with_other_work_on_top(suite):
    """Other work pushed before a portal draft's device test (owner, 04-11-2026): the release lasts until the draft is published or Not OK, so Start never replaces it."""
    write(suite / "portal/VERSION", "1.1.0\n")                  # what the release wrote: ps5-portal-v1.1.0, a draft
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Release ps5-portal-v1.1.0")
    head = sh(suite, "rev-parse", "HEAD").strip()
    run = _run(head)
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Other work")
    assert flow.cycle_run(suite, [run]) is run
    assert flow.cycle_run(suite, [run], ["ps5-portal-v1.1.0"]) is None      # Not OK: a new release may replace it
    assert flow.cycle_run(suite, [_run(head, conclusion="failure")]) is not None   # a failed run lasted already
    sh(suite, "tag", "ps5-portal-v1.1.0")                             # published: its tag fetched
    assert flow.cycle_run(suite, [run]) is None


def test_a_portal_version_raised_after_a_published_release_is_the_next_release(suite):
    """The portal's version raised in a commit after its release was published (owner, 07-11-2026: NRT showed the
    release on GitHub done and offered the device test of ps5-portal-v10.1.0, a draft no run had built): the run's
    own portal is out, so that release is over and Start new release is next; the draft is read at the run's commit."""
    head = sh(suite, "rev-parse", "HEAD").strip()
    run = _run(head)
    assert flow.published(suite, [], "ps5-portal-v1.0.0")              # the run's portal, published (the fixture's tag)
    write(suite / "portal/VERSION", "1.1.0\n")
    sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Other work")
    assert flow.waiting_portals(suite) == ["ps5-portal-v1.1.0"]          # the checkout's: the next release
    assert flow.waiting_portals(suite, head) == ["ps5-portal-v1.0.0"]    # the run's own
    assert flow.cycle_run(suite, [run]) is None


def test_a_push_git_has_not_fetched_lights_the_pull(release_window, monkeypatch):
    """The release's Pin ... commit is on GitHub, not fetched (owner, 30-10-2026: step 9 stayed dark while git pull
    (new) was lit): GitHub's newest run on main names a commit this checkout lacks, so step 9 is the one to do."""
    w = release_window
    page = w.release_page
    head = sh(w.root, "rev-parse", "HEAD").strip()
    release = _run(head)
    assert flow.pushed_elsewhere(w.root, [_run(head, "ci.yml", "CI"), release]) is None
    pin = _run("f" * 40, "ci.yml", "CI")
    assert flow.pushed_elsewhere(w.root, [pin, release]) is pin
    monkeypatch.setattr(w.build, "runs", [pin, release])
    monkeypatch.setattr(flow, "waiting_portals", lambda root, at="": [])
    page.show_state()
    assert page.facts.behind == 1 and flow.current_step(page.facts) == "finish"
    assert page.finish_button.isEnabled()


def test_the_device_test_and_publish(release_window, monkeypatch):
    w = release_window
    page = w.release_page
    w.build.runs = [_run(sh(w.root, "rev-parse", "HEAD").strip())]   # the release run passed on HEAD: its draft
    monkeypatch.setattr(flow, "published", lambda *a: False)          # ps5-portal-v1.0.0 a draft still
    page.show_state()
    page.device_test()
    assert w.launched and w.launched[-1].endswith("draft ps5-portal-v1.0.0")
    ran = []
    monkeypatch.setattr(w, "confirm_git", lambda *a: True)
    monkeypatch.setattr(w, "run_git", ran.append)
    page.publish()
    assert ran == [flow.publish_command("ps5-portal-v1.0.0")]
    page.show_state()
    assert flow.step_states(page.facts)["test"] == "now"
    page.reject()
    assert "stays a draft" in page.output.toPlainText()
    # Not OK shows on the step (owner, 30-10-2026: it seemed to do nothing): red, with what comes next
    assert flow.step_states(page.facts)["test"] == "failed" and page.facts.rejected == ["ps5-portal-v1.0.0"]
    assert page.details["test"].text().startswith("Not OK: ps5-portal-v1.0.0 stays a draft")
    assert page.marks["test"].text() == "!" and page.test_button.isEnabled() and page.publish_button.isEnabled()


def test_the_portal_choice_holds_only_the_drafts(release_window, monkeypatch):
    """A tag published since the choice was filled leaves it (owner, 05-11-2026: the choice stayed on
    portal-v15.2.0, so Publish published it again): only the draft is left."""
    w = release_window
    page = w.release_page
    monkeypatch.setattr(flow, "waiting_portals", lambda root, at="": ["ps5-portal-v1.0.0"])
    monkeypatch.setattr(flow, "published", lambda root, runs, tag: False)
    w.build.runs = [_run(sh(w.root, "rev-parse", "HEAD").strip())]
    page.portal_choice.clear()
    page.portal_choice.addItems(["portal-v2.0.0", "ps5-portal-v1.0.0"])
    page.show_state()
    assert page.facts.drafts == ["ps5-portal-v1.0.0"]
    assert [page.portal_choice.itemText(i) for i in range(page.portal_choice.count())] == ["ps5-portal-v1.0.0"]
    assert page.details["test"].text() == ("ps5-portal-v1.0.0 is a draft: Device test, then Publish when it works "
                                           "or Not OK.")
    ran = []
    monkeypatch.setattr(w, "confirm_git", lambda *a: True)
    monkeypatch.setattr(w, "run_git", ran.append)
    page.publish()
    assert ran == [flow.publish_command("ps5-portal-v1.0.0")]


def test_not_ok_is_the_runs_and_a_fix_goes_on_from_commit():
    run = _run()
    facts = flow.Facts(run=run, drafts=["ps5-portal-v6.0.0"], rejected=["ps5-portal-v6.0.0"])
    states = flow.step_states(facts)
    assert flow.current_step(facts) == "test" and states["test"] == "failed" and states["publish"] == "later"
    assert flow.step_states(flow.Facts(run=run, drafts=["ps5-portal-v6.0.0"]))["test"] == "now"   # a run made anew
    assert flow.current_step(flow.Facts(run=run, drafts=["ps5-portal-v6.0.0"], rejected=["ps5-portal-v6.0.0"],
                                        dirty=True)) == "commit"


def test_commit_offers_the_portal_bump_when_apps_toml_changed(release_window, monkeypatch):
    """apps.toml changed since the last portal release (an app added): the commit's manifest check would refuse
    the commit, so Commit offers the portal bump (owner, 02-11-2026) and writes it with its CHANGELOG entry on a
    yes; on a no nothing is committed and the output says why."""
    w = release_window
    page = w.release_page
    extra = APPS_TOML.replace("apps.test", "apps.extra").replace('"T"', '"E"').replace("ps5-test-v0.1.0", "ps5-extra-v0.1.0") \
        .replace("required = true", "required = false")
    (w.root / "portal/apps.toml").write_text(APPS_TOML + "\n" + extra, encoding="utf-8")
    w.reload()
    assert rp.portal_offer(w.root, "HEAD") == ("1.1.0", "the least the manifest check accepts",
                                                      "extra was added")
    page.commit_message.setText("An app")
    ran, asked = [], []
    monkeypatch.setattr(w, "run_git", ran.append)
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr("nexus_release_tool.release_page.QMessageBox.question",
                        lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No)
    page.commit()
    assert ran == [] and "extra was added" in asked[0] and "1.1.0" in asked[0]
    assert "Not committed" in page.output.toPlainText()
    assert (w.root / "portal/VERSION").read_text() == "1.0.0\n"

    monkeypatch.setattr("nexus_release_tool.release_page.QMessageBox.question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    page.commit()
    assert len(ran) == 1 and "git commit" in ran[0] and "An app" in ran[0]
    assert (w.root / "portal/VERSION").read_text() == "1.1.0\n"
    assert "Release 1.1.0." in (w.root / "portal/CHANGELOG").read_text()
    assert "portal 1.1.0" in page.output.toPlainText()
    assert rp.portal_offer(w.root, "HEAD") is None            # the bump is there: nothing to offer

    # A Breaking entry in the portal's CHANGELOG: the offer is step 2's major, above the least the check accepts.
    (w.root / "portal/VERSION").write_text("1.0.0\n")
    (w.root / "portal/CHANGELOG").write_text("Changelog: 03-01-2026 00:00:00\n\nBreaking. Gone.\n\n"
                                                "Changelog: 01-01-2026 00:00:00\n\nRelease 1.0.0.\n")
    w.reload()
    assert rp.portal_offer(w.root, "HEAD")[0] == "2.0.0"


def test_the_step_being_done_says_a_command_runs(release_window, monkeypatch):
    """While its command runs (owner, 05-11-2026: Push stayed lit for its two minutes of CI's jobs, which read as
    "push again"), the step to do has a teal ⋯ and says what runs, and its pill rests."""
    from nexus_release_tool import release_page
    w = release_window
    page = w.release_page
    page.show_state()
    now = flow.current_step(page.facts)
    assert now and page.marks[now].text() == "▶"
    monkeypatch.setattr(w.commands, "is_running", lambda: True)
    page.show_state()
    assert page.marks[now].text() == "⋯"
    assert page.details[now].text() == release_page.RUNNING.get(now, release_page.RUNNING_ELSE)
    assert not any(b.isEnabled() for b in (page.pull_button, page.commit_button, page.push_button, page.start_button))
    monkeypatch.setattr(w.commands, "is_running", lambda: False)
    page.show_state()
    assert page.marks[now].text() == "▶"
    assert "Pushing: CI's jobs run here first" in release_page.RUNNING["push"]


CI_OUTPUT = ("Current branch main is up to date.\n46 jobs from ci.yml, 6 at a time, on Python 3.12.16\n"
             "  ok   versions                                         0.3 s\n"
             "  FAIL pytest/apps/pcsx2                                2.3 s\n"
             "  ok   pytest/apps/ppsspp                               7.0 s\n")


def test_ci_here_is_read_from_its_output():
    """The Push step's tools/ci-local.sh (owner, 15-11-2026: the push seemed to hang, a failed job went unseen)."""
    assert not flow.local_ci("Current branch main is up to date.\n").started
    progress = flow.local_ci(CI_OUTPUT)
    assert (progress.total, progress.done, progress.failed) == (46, 3, ("pytest/apps/pcsx2",))
    assert progress.line() == "CI's jobs here, before the push: 3 of 46 done; failed: pytest/apps/pcsx2."
    waiting = flow.local_ci("==> Another ci-local.sh run is going on this computer: waiting until it ends\n")
    assert waiting.started and "the push waits until it ends" in waiting.line()


def test_a_run_asked_to_run_again_is_not_asked_twice():
    failed = _run(conclusion="failure")
    assert flow.not_asked([failed], set()) == [failed]
    assert flow.not_asked([failed], {(failed.url, 1)}) == []
    assert flow.not_asked([rp.BuildRun(**{**failed.__dict__, "attempt": 2})], {(failed.url, 1)})
    assert rp.parse_runs({"workflow_runs": [{"html_url": "u", "run_attempt": 3}]})[0].attempt == 3


def test_why_a_push_ended_badly():
    assert flow.push_failure(CI_OUTPUT, 0) == ""
    assert flow.push_failure(CI_OUTPUT + "44 of 45 jobs passed\n", 1).startswith(
        "CI failed here on pytest/apps/pcsx2, so nothing was pushed.")
    assert flow.push_failure("", None).startswith("The push was stopped")
    assert "exit code 1" in flow.push_failure("! [rejected] main -> main (fetch first)\n", 1)
    assert flow.step_states(flow.Facts(ahead=1, push_failed="x"))["push"] == "failed"
    assert flow.step_states(flow.Facts(ahead=1))["push"] == "now"


def test_the_push_shows_ci_here_and_a_failure_stays_on_its_step(release_window):
    w = release_window
    page = w.release_page
    w.base_ref = "HEAD~1"                                           # one commit to push
    w.reload()
    commands = w.commands
    commands.running = rp.push_command()                            # as while Push runs
    commands.output_of_run = CI_OUTPUT
    monkey_running = commands.is_running
    commands.is_running = lambda: True
    page.command_output("x")
    assert w.ticker.isVisibleTo(w) and w.ticker.local.startswith("CI's jobs here, before the push: 3 of 46 done")
    assert w.ticker.target() == ""                                  # nothing on GitHub to open yet
    assert page.details["push"].text().startswith("CI's jobs here, before the push: 3 of 46 done; failed: ")
    commands.is_running = monkey_running
    commands.last_command, commands.running, commands.last_code = rp.push_command(), "", 1
    w.command_finished()
    assert w.ticker.local == ""                                     # back to GitHub's runs
    assert flow.step_states(page.facts)["push"] == "failed" and page.marks["push"].text() == "!"
    assert page.details["push"].text().startswith("CI failed here on pytest/apps/pcsx2")
    assert page.push_button.isEnabled()                             # Push again, or a fix first
    commands.last_command, commands.last_code = "git status", 0     # another command: the failure stays
    w.command_finished()
    assert page.details["push"].text().startswith("CI failed here on pytest/apps/pcsx2")
    sh(w.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "fix")
    w.reload()                                                      # a new commit: its push is still to do
    assert flow.step_states(page.facts)["push"] == "now"


def test_a_push_github_has_no_runs_of_yet_shows_no_old_failure(release_window, monkeypatch):
    """Right after a push, GitHub's newest runs are the commit's before: one that failed showed this push as failed
    until GitHub had started its runs (owner, 15-11-2026). The pill and the line under it wait for GitHub instead."""
    w = release_window
    head = sh(w.root, "rev-parse", "HEAD").strip()
    old = _run("0" * 40, "ci.yml", "CI", conclusion="failure")
    w.build.head = head
    monkeypatch.setattr(w.build, "awaiting_head", lambda: True)
    monkeypatch.setattr(w.build, "source", object())
    w.build.checked(([old], "e1"))
    assert w.build.state == "running" and f"Pushed {head[:7]}: waiting for GitHub" in w.build.toolTip()
    assert w.ticker.local.startswith(f"Pushed {head[:7]}") and w.ticker.isVisibleTo(w)
    monkeypatch.setattr(w.build, "awaiting_head", lambda: False)
    w.build.checked(([_run(head, "ci.yml", "CI")], "e2"))
    assert w.build.state == "passed" and w.ticker.local == ""


def test_the_portal_video_check(tmp_path):
    """tools/portal_tour.py --check: "" when the video is current or the suite has none, else why it waits."""
    import sys
    from nexus_release_tool import flow
    assert flow.video_reason(tmp_path) == ""                                   # no tour in this suite
    script = tmp_path / "tools" / "portal_tour.py"
    script.parent.mkdir()
    script.write_text("import sys\nsys.exit(1)\n")
    assert flow.video_reason(tmp_path, sys.executable) == flow.VIDEO_STALE
    script.write_text("import sys\nsys.exit(0)\n")
    assert flow.video_reason(tmp_path, sys.executable) == ""
    assert "could not run" in flow.video_reason(tmp_path, str(tmp_path / "no-python"))


# --- how long a release takes ---------------------------------------------------------------------------------------

def _timed(sha, file, started, ended, conclusion="success", ref="main"):
    """A run of *file* on *sha* that ran from *started* to *ended* (0: it still runs)."""
    return rp.BuildRun("Release" if file == "release.yml" else "CI", ref, "completed" if ended else "in_progress",
                       conclusion if ended else "", f"https://github.com/o/r/actions/runs/{sha}-{file}", sha, "t",
                       started=started, file=file, ended=ended)


def test_a_release_takes_from_its_work_commit_to_ci_passed_and_from_its_commit_to_the_end_of_its_run(suite):
    """Two releases in the checkout, each a commit on top of the one CI passed on; a failed run and a run on a tag
    are no releases; what the owner waited between CI and Start is not counted. The time before Start runs from
    the work's commit, so the push with CI's jobs here is in it (owner, 20-11-2026), not GitHub's CI alone."""
    shas = [sh(suite, "rev-parse", "HEAD").strip()]
    for n in (1, 2, 3):
        write(suite / "apps/test/app.py", f"print({n})\n")
        sh(suite, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", f"change {n}")
        shas.append(sh(suite, "rev-parse", "HEAD").strip())
    before_old, old, before_new, new = shas
    at = {sha: float(sh(suite, "log", "-1", "--format=%ct", sha)) for sha in shas}
    asked = []

    def read(url):
        asked.append(url)
        if "workflows/release.yml" in url:
            return [_timed("zzz", "release.yml", at[new] + 500, at[new] + 600, ref="ps5-portal-v1.1.0"),
                    _timed("yyy", "release.yml", at[new] + 300, at[new] + 400, conclusion="failure"),
                    _timed(new, "release.yml", at[new] + 4, at[new] + 200),
                    _timed(old, "release.yml", at[old] + 4, at[old] + 90)]
        sha = url.split("head_sha=")[1].split("&")[0]
        return {before_new: [_timed(before_new, "docs.yml", 10, 5000),
                             _timed(before_new, "ci.yml", at[before_new] + 900, at[before_new] + 1050)],
                before_old: [_timed(before_old, "ci.yml", at[before_old] + 20, at[before_old] + 80)]}[sha]
    times = flow.release_times(suite, read=read)
    assert [(t.sha, t.before, t.release, t.running) for t in times] == [(new, 1050, 200, False), (old, 80, 90, False)]
    assert times[0].total == 1250 and flow.deviation(times) == 1080
    assert len(asked) == 3                                  # the release runs, and CI on each release's parent


def test_a_release_that_still_runs_counts_the_time_so_far_and_a_first_release_has_no_deviation(suite):
    head = sh(suite, "rev-parse", "HEAD").strip()
    committed = float(sh(suite, "log", "-1", "--format=%ct", head))

    def read(url):
        return [_timed(head, "release.yml", committed + 3, 0)] if "workflows/release.yml" in url else []
    times = flow.release_times(suite, now=lambda: committed + 75, read=read)
    assert [(t.before, t.release, t.running) for t in times] == [(0, 75, True)]      # the CI run is no longer listed
    assert flow.deviation(times) is None and flow.release_times(suite, read=lambda url: []) == []


def test_times_and_deviations_in_words():
    assert [flow.duration_text(s) for s in (0, 42, 60, 185, 3725)] == ["0 s", "42 s", "1 min 00 s", "3 min 05 s",
                                                                       "1 h 02 min"]
    assert [flow.deviation_text(s) for s in (185, -42, 0, 0.2)] == ["+3 min 05 s", "−42 s", "0 s", "0 s"]


def test_the_page_shows_both_times_and_the_deviation_and_a_banner_over_the_limit(release_window):
    """Over the limit the deviation is orange and in the banner; 0 or less and under the limit it is in its box
    only; while the release runs a deviation under the limit says nothing yet."""
    page = release_window.release_page
    assert page.times_row.isHidden() and page.slow_banner.isHidden()            # nothing read yet
    page.times_checked([flow.ReleaseTime("a" * 40, 100, 400), flow.ReleaseTime("b" * 40, 100, 200)])
    assert not page.times_row.isHidden() and not page.slow_banner.isHidden()
    assert "3 min 20 s longer" in page.slow_note.text() and "8 min 20 s against 5 min 00 s" in page.slow_note.text()
    # No release is being made: the first box is the latest one GitHub has, not "this" one (owner, 20-11-2026)
    assert page.time_now.caption.text() == "Latest release" and page.time_before.caption.text() == "Release before it"
    assert page.slow_note.text().startswith("The latest release took")
    page.times_checked([flow.ReleaseTime("a" * 40, 100, 250), flow.ReleaseTime("b" * 40, 100, 200)])
    assert page.slow_banner.isHidden()                                          # 50 s longer: under the limit
    page.times_checked([flow.ReleaseTime("a" * 40, 50, 100), flow.ReleaseTime("b" * 40, 100, 200)])
    assert page.slow_banner.isHidden() and flow.deviation(page.times) == -150
    page.times_checked([flow.ReleaseTime("a" * 40, 100, 30, running=True), flow.ReleaseTime("b" * 40, 100, 200)])
    assert page.slow_banner.isHidden()
    page.times_checked([flow.ReleaseTime("a" * 40, 100, 900, running=True), flow.ReleaseTime("b" * 40, 100, 200)])
    assert "is taking 11 min 40 s longer" in page.slow_note.text() and not page.slow_banner.isHidden()
    assert page.time_now.caption.text() == "This release"                       # its run goes on
    page.times_checked(OSError("offline"))                                      # GitHub not reached: as it was
    assert len(page.times) == 2 and not page.slow_banner.isHidden()
    page.times_checked([flow.ReleaseTime("a" * 40, 100, 400)])                  # the first release ever
    assert page.slow_banner.isHidden() and not page.times_row.isHidden()
    assert page.deviation_limit() == flow.DEVIATION_LIMIT and release_window.times_source is None


def test_the_times_are_read_through_the_windows_source(release_window):
    """The build indicator asks with each look (check_times): the source runs off the GUI thread and its answer
    fills the boxes; a source that cannot reach GitHub leaves them as they were."""
    from PyQt6.QtWidgets import QApplication
    page = release_window.release_page
    page.check_times()                                                          # no source: nothing to ask
    assert page.times == [] and not page.time_checker.running
    asked = []

    def answered() -> None:
        deadline = time.monotonic() + 5
        while page.time_checker.running and time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(0.01)
    release_window.times_source = lambda root: (asked.append(root),
                                                [flow.ReleaseTime("a" * 40, 60, 120)])[1]
    page.check_times()
    answered()
    assert asked == [release_window.root] and [t.total for t in page.times] == [180]
    assert not page.times_row.isHidden()

    def offline(root):
        raise OSError("no network")
    release_window.times_source = offline
    page.check_times()
    answered()
    assert [t.total for t in page.times] == [180] and not page.time_checker.running


def test_the_time_boxes_are_wide(release_window):
    """Owner, 20-11-2026: wider; "9 min 39 s so far" filled its box."""
    from nexus_release_tool import release_page
    page = release_window.release_page
    assert release_page.TIME_BOX_PX >= 240
    assert all(box.minimumWidth() == release_page.TIME_BOX_PX
               for box in (page.time_now, page.time_before, page.time_deviation))


def test_start_follows_by_itself_when_this_window_saw_ci_pass(release_window, monkeypatch):
    """Owner, 20-11-2026: "If CI passes in NRT we autostart". Only after CI passes was the step to do on this
    commit in this window; a window opened on a commit whose CI passed already starts nothing; without the question."""
    from PyQt6.QtWidgets import QApplication
    w = release_window
    page = w.release_page
    head = sh(w.root, "rev-parse", "HEAD").strip()
    started = []
    monkeypatch.setattr(w, "confirm_git", lambda *a: started.append("asked") or False)
    monkeypatch.setattr(w, "run_git", started.append)
    monkeypatch.setattr(w.build, "source", object())
    passed = [_run(head, "ci.yml", "CI")]
    monkeypatch.setattr(w.build, "runs", passed)
    page.show_state()                                           # opened on a commit that passed: the pill, as before
    QApplication.processEvents()
    assert started == [] and page.start_button.isEnabled()
    monkeypatch.setattr(w.build, "runs", [_run(head, "ci.yml", "CI", status="in_progress", conclusion="")])
    page.show_state()
    assert page.ci_waited == head and "follows by itself" in page.details["ci"].text()
    QApplication.processEvents()
    assert started == []
    monkeypatch.setattr(w.build, "runs", passed)
    page.show_state()
    page.show_state()                                           # a second look starts no second release
    QApplication.processEvents()
    assert started == [flow.start_command("Release ps5-test-v0.2.0, ps5-portal-v1.1.0")]
    assert "starts by itself" in page.output.toPlainText()


def test_start_does_not_follow_by_itself_when_the_settings_say_so_or_another_commit_waited(release_window, monkeypatch):
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    w = release_window
    page = w.release_page
    head = sh(w.root, "rev-parse", "HEAD").strip()
    started = []
    monkeypatch.setattr(page, "start", lambda asked=True: started.append(asked))
    monkeypatch.setattr(w.build, "source", object())
    facts = flow.Facts(ci="passed", something=True)
    assert flow.autostart(facts, head, head) and not flow.autostart(facts, "other", head)
    assert not flow.autostart(facts, "", "") and not flow.autostart(flow.Facts(ci="building", something=True), head, head)
    assert not flow.autostart(flow.Facts(ahead=1, unpushed="Release x"), head, head)
    w.settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "nexus", "nrt-test")
    w.settings.setValue(flow.AUTOSTART_KEY, "false")
    monkeypatch.setattr(w.build, "runs", [_run(head, "ci.yml", "CI", status="in_progress", conclusion="")])
    page.show_state()
    assert "follows by itself" not in page.details["ci"].text()
    monkeypatch.setattr(w.build, "runs", [_run(head, "ci.yml", "CI")])
    page.show_state()
    QApplication.processEvents()
    assert started == [] and page.start_button.isEnabled()


def test_the_last_step_waits_until_github_runs_nothing_more(release_window, monkeypatch):
    """Owner, 20-11-2026: step 9 had its check while the wiki still ran on GitHub. The tenth step is the one to do
    until every run finished, then says All runs finished, ready."""
    w = release_window
    page = w.release_page
    head = sh(w.root, "rev-parse", "HEAD").strip()
    monkeypatch.setattr(w.build, "source", object())
    monkeypatch.setattr(flow, "waiting_portals", lambda root, at="": [])
    release = _run(head)
    wiki = _run(head, "docs.yml", "Wiki", status="in_progress", conclusion="")
    monkeypatch.setattr(w.build, "runs", [wiki, release])
    page.show_state()
    assert flow.current_step(page.facts) == "ready" and page.marks["ready"].text() == "▶"
    assert page.marks["finish"].text() == "✓" and page.titles["ready"].text() == "10. All runs finished"
    assert "GitHub still runs Wiki on main: wait until it finished" in page.details["ready"].text()
    monkeypatch.setattr(w.build, "runs", [_run(head, "docs.yml", "Wiki"), release])
    page.show_state()
    assert page.marks["ready"].text() == "✓" and page.details["ready"].text() == flow.READY == \
        "All runs finished, ready."
    assert flow.still_running([wiki, wiki, release]) == ("Wiki on main",)
