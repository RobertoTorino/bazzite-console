# SPDX-License-Identifier: GPL-3.0-or-later
"""flow.py, the Nexus release: what it holds, what Start writes (as steps 1 and 2 would, with the portal's and
Nexus's versions worked out), when Start can go, its one command, and the commands that follow the run."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from nexus_release_tool import flow
from nexus_release_tool import plan as rp

APPS_TOML = ('[apps.test]\nname = "T"\nsummary = "s"\ntag = "ws-test-v0.1.0"\nsha256 = "' + "ab" * 32 + '"\n'
             'required = true\ncategory = "sustainable"\ninstall = ["i"]\nuninstall = ["u"]\ndetect = ["d"]\n')


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def sh(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def nexus(tmp_path) -> Path:
    """Nexus with a suite of its own tags on the Nexus release (ws), released once, then a change in its
    test app."""
    root = tmp_path / "nexus"
    write(root / ".gitignore", "__pycache__/\n")                    # as the repository's: the manifest tools' caches
    write(root / "VERSION", "0.5.0\n")
    write(root / "CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nRelease 0.5.0.\n")
    write(root / "core/VERSION", "0.1.0\n")
    write(root / "core/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nVersion 0.1.0.\n")
    write(root / "core/bazzite_console_core/__init__.py", '__version__ = "0.1.0"\n')
    ws = root / "ws"
    write(ws / "SYSTEM", "bazzite\n")
    write(ws / "TAG_PREFIX", "ws-\n")
    write(ws / "portal/VERSION", "1.0.0\n")
    write(ws / "portal/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nRelease 1.0.0.\n")
    write(ws / "apps/test/VERSION", "0.1.0\n")
    write(ws / "apps/test/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nRelease 0.1.0.\n")
    write(ws / "apps/test/app.py", "print('hi')\n")
    real = Path(__file__).resolve().parents[3]                  # a suite's own manifest tools: this checkout's
    for path in ("tools/check_manifest.py", "portal/bazzite_console_portal/manifest.py"):
        write(ws / path, (real / path).read_text(encoding="utf-8").replace("ps5-", "ws-"))
    write(ws / "portal/apps.toml", APPS_TOML)
    write(root / ".github/workflows/release-ws.yml", "on:\n  workflow_call:\n")
    sh(root, "init", "-q", "-b", "main")
    sh(root, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    sh(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "start")
    for tag in ("ws-test-v0.1.0", "ws-portal-v1.0.0"):
        sh(root, "tag", tag)
    write(ws / "apps/test/app.py", "print('hello')\n")
    write(ws / "apps/test/CHANGELOG", "Changelog: 02-01-2026 00:00:00\n\nAdded. A greeting.\n\n"
                                      "Changelog: 01-01-2026 00:00:00\n\nRelease 0.1.0.\n")
    sh(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "greeting")
    return root


def test_only_the_suites_on_the_nexus_release(nexus):
    assert flow.release_suites(nexus) == ["ws"]
    (nexus / ".github/workflows/release-ws.yml").write_text("on:\n  push:\n", encoding="utf-8")
    assert flow.release_suites(nexus) == []


def test_the_release_holds_the_changed_app_its_portal_and_nexus(nexus):
    found = {p.unit.key: p for p in flow.picks(nexus)}
    assert set(found) == {"test", "portal", rp.NEXUS}               # core did not change
    assert found["test"].choices[0] == "0.2.0" and found["test"].suite == "ws"     # Added. -> minor
    assert found["portal"].version == flow.AUTO and found[rp.NEXUS].version == flow.AUTO
    assert found["test"].label == "ws · test" and found[rp.NEXUS].label == "nexus"


def test_nothing_changed_nothing_to_release(nexus):
    sh(nexus, "tag", "-f", "ws-test-v0.1.0")                        # the change is in the tag now
    assert flow.picks(nexus) == []


def test_start_writes_the_release_as_steps_one_and_two_would(nexus):
    log, tags = flow.write(nexus, flow.picks(nexus), base="HEAD")
    assert tags == ["ws-test-v0.2.0", "ws-portal-v1.1.0", "nexus-v0.6.0"]
    assert (nexus / "ws/apps/test/VERSION").read_text() == "0.2.0\n"
    manifest = (nexus / "ws/portal/apps.toml").read_text()
    assert 'tag = "ws-test-v0.2.0"\nsha256 = ""\n' in manifest          # the sha256 is the workflow's
    assert (nexus / "ws/portal/VERSION").read_text() == "1.1.0\n"       # an app minor: a portal minor
    assert "Release 1.1.0. Pins ws-test-v0.2.0." in (nexus / "ws/portal/CHANGELOG").read_text()
    assert "Release 0.2.0." in (nexus / "ws/apps/test/CHANGELOG").read_text()
    assert (nexus / "VERSION").read_text() == "0.6.0\n"                 # a suite's release: Nexus minor
    assert "Release 0.6.0. Brings ws-portal-v1.1.0, ws-test-v0.2.0." in (nexus / "CHANGELOG").read_text()
    assert len(log) == 3


def test_a_typed_version_overrides_the_suggestion(nexus):
    chosen = flow.picks(nexus)
    for pick in chosen:
        pick.version = {"test": "1.0.0", "portal": "2.0.0", rp.NEXUS: "1.0.0"}[pick.unit.key]
        pick.notes = "notes" if pick.unit.key == "test" else ""
    _log, tags = flow.write(nexus, chosen, base="HEAD")
    assert tags == ["ws-test-v1.0.0", "ws-portal-v2.0.0", "nexus-v1.0.0"]
    assert "Release 1.0.0. notes" in (nexus / "ws/apps/test/CHANGELOG").read_text()


def test_a_portal_typed_too_low_gets_what_ci_asks(nexus):
    chosen = flow.picks(nexus)
    for pick in chosen:
        if pick.unit.key == "test":
            pick.version = "1.0.0"                                  # a major app release
        if pick.unit.key == "portal":
            pick.version = "1.0.1"
    log, tags = flow.write(nexus, chosen, base="HEAD")
    assert "ws-portal-v2.0.0" in tags and any("less than CI asks" in line for line in log)


def test_wrong_versions_are_refused_before_anything_is_written(nexus):
    chosen = flow.picks(nexus)
    chosen[0].version = "0.0.9"
    assert flow.problems(chosen) == ["ws · test: 0.0.9 is not higher than 0.1.0, which is already tagged"]
    chosen[0].version = "abc"
    assert "is not x.y.z" in flow.problems(chosen)[0]


def test_start_needs_a_clean_tree_at_the_last_push(nexus):
    assert flow.ready(nexus, base="HEAD") == []
    (nexus / "ws/apps/test/app.py").write_text("changed\n")
    assert flow.ready(nexus, base="HEAD")[0].startswith("The working tree has changes")
    sh(nexus, "checkout", "-q", "--", ".")
    assert "not pushed" in flow.ready(nexus, base="HEAD~1")[0]
    assert "git fetch" in flow.ready(nexus, base="origin/main")[0]


def test_the_one_command_commits_pushes_and_starts_the_workflow():
    command = flow.start_command(flow.commit_message(["ws-test-v0.2.0", "ws-portal-v1.1.0", "nexus-v0.6.0"]))
    assert command.startswith("git commit -a -q -m 'Release ws-test-v0.2.0, ws-portal-v1.1.0, nexus-v0.6.0' && ")
    assert "git push origin HEAD:main && gh workflow run release.yml --ref main" in command
    assert '-f commit="$(git rev-parse HEAD)"' in command


def test_the_run_is_followed_stopped_and_resumed():
    other = rp.BuildRun("CI Nexus", "main", "completed", "success", "https://github.com/o/r/actions/runs/1", "abc", "t",
                        file="ci-nexus.yml")
    run = rp.BuildRun("Release", "main", "in_progress", "", "https://github.com/o/r/actions/runs/42", "abc", "t",
                      file="release.yml")
    assert flow.release_run([other, run]) is run and flow.release_run([other, run], "def") is None
    assert flow.stop_command(run) == "gh run cancel 42"
    assert flow.resume_command(run) == "gh run rerun 42 --failed"


def test_the_device_test_and_publish_work_on_the_portals_draft(nexus):
    assert flow.waiting_portals(nexus) == ["ws-portal-v1.0.0"]
    assert flow.publish_command("ws-portal-v1.1.0") == ("gh release edit ws-portal-v1.1.0 --draft=false --latest"
                                                        " && git fetch origin tag ws-portal-v1.1.0")   # seen at once
    line = flow.device_test_line(nexus, "ws", "ws-portal-v1.1.0")
    assert line.endswith("ws/tools/check-release.sh draft ws-portal-v1.1.0")


def test_a_release_commit_whose_push_stopped_is_pushed_and_started(nexus):
    assert flow.unpushed_release(nexus, base="HEAD") == ""
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m",
       "Release ws-test-v0.2.0, ws-portal-v1.1.0")
    assert flow.unpushed_release(nexus, base="HEAD~1") == "Release ws-test-v0.2.0, ws-portal-v1.1.0"
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "other")
    assert flow.unpushed_release(nexus, base="HEAD~2") == ""             # not right on top of the last push
    assert flow.push_and_start_command().startswith("git push origin HEAD:main && gh workflow run release.yml")


@pytest.fixture
def release_window(nexus, tmp_path):
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    launched: list[str] = []
    w = main_window.ReleaseWindow(nexus, launch=launched.append, runs_source=None, status_source=None,
                                  claude_source=None, suite="ws")
    w.portal_page.base_edit.setText("HEAD")
    w.reload()
    w.launched = launched
    yield w
    w.close()


def test_the_window_opens_on_the_nexus_release(release_window):
    w = release_window
    page = w.release_page
    assert w.tabs.widget(0) is page and w.tabs.tabText(0) == "Nexus release"
    assert [pick.label for pick, _combo, _notes in page.rows] == ["ws · test", "ws · portal", "nexus"]
    assert page.rows[0][1].currentText() == "0.2.0" and page.rows[1][1].currentText() == flow.AUTO
    assert page.start_button.isEnabled() and page.portal_choice.currentText() == "ws-portal-v1.0.0"
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
    assert ran == [flow.start_command("Release ws-test-v0.2.0, ws-portal-v1.1.0, nexus-v0.6.0", ["ws"])]
    assert "suites" not in ran[0]                # release.yml releases the repository's one suite: no such input
    assert "Release 0.2.0. A greeting" in (w.root / "ws/apps/test/CHANGELOG").read_text()
    assert "ws · test: 0.2.0" in page.output.toPlainText()


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
    sh(w.root, "push", "-q", "origin", "HEAD:refs/tags/ws-portal-v1.1.0")    # published on GitHub, not fetched
    other = tmp_path / "other"                                       # the release's Pin ... commit, on GitHub only
    sh(tmp_path, "clone", "-q", "-b", "main", str(origin), str(other))
    write(other / "ws/portal/apps.toml", (other / "ws/portal/apps.toml").read_text() + "\n")
    sh(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Pin ws-test-v0.1.0")
    sh(other, "push", "-q", "origin", "HEAD:main")
    w.portal_page.base_edit.setText("origin/main")
    ran, asked = [], []
    monkeypatch.setattr(w, "confirm_git", lambda *a: asked.append(a[1]) or True)
    monkeypatch.setattr(w, "run_git", ran.append)
    page.start()
    assert sh(w.root, "tag", "--list", "ws-portal-v1.1.0").strip() == "ws-portal-v1.1.0"
    assert "Pin ws-test-v0.1.0" in sh(w.root, "log", "--format=%s")       # brought in, under the release
    assert len(ran) == 1 and "ws-portal-v1.2.0" in ran[0] and "ws · portal: 1.0.0 -> auto" in asked[0]
    assert flow.fetch_tags(w.root) == []                            # nothing new the second time


def test_fetch_tags_names_a_tag_here_that_git_will_not_move(nexus, tmp_path, monkeypatch):
    """A tag here on another commit than GitHub's: git refuses to move it ("would clobber existing tag"), and the
    message says which tag and what to do (owner, 03-11-2026: nexus-v1.33.0, and Start only said the fetch failed)."""
    identity(monkeypatch)
    origin = tmp_path / "origin.git"
    sh(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    sh(nexus, "remote", "add", "origin", str(origin))
    sh(nexus, "push", "-q", "origin", "main", "--tags")
    assert flow.fetch_tags(nexus) == []
    sh(nexus, "push", "-q", "-f", "origin", "HEAD:refs/tags/ws-test-v0.1.0")   # GitHub's tag moved on; this one stays
    failed = flow.fetch_tags(nexus)
    assert isinstance(failed, flow.FetchFailed) and failed.clobbered == ("ws-test-v0.1.0",)
    text = failed.explain()
    assert "would clobber existing tag" in text and "The tag ws-test-v0.1.0 here points to another commit" in text
    assert "git tag -d ws-test-v0.1.0\ngit fetch --tags" in text and text.endswith(flow.WAITS)
    sh(nexus, "tag", "nexus-v0.5.0")                                 # the Nexus index, fetched once
    sh(nexus, "push", "-q", "origin", "nexus-v0.5.0")
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Later")
    sh(nexus, "push", "-q", "-f", "origin", "HEAD:refs/tags/nexus-v0.5.0")    # made anew on main's newest commit
    sh(nexus, "tag", "-d", "ws-test-v0.1.0")
    assert flow.fetch_tags(nexus) == ["ws-test-v0.1.0"]                # the index tag follows GitHub's, no refusal
    assert sh(nexus, "rev-parse", "nexus-v0.5.0^{commit}") == sh(nexus, "rev-parse", "HEAD")
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
    sh(w.root, "push", "-q", "-f", "origin", "HEAD:refs/tags/ws-test-v0.1.0")
    from PyQt6.QtWidgets import QMessageBox
    shown, ran = [], []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    monkeypatch.setattr(w, "run_git", ran.append)
    w.release_page.start()
    assert ran == [] and len(shown) == 1 and "git tag -d ws-test-v0.1.0" in shown[0]
    w.portal_page.fetch_tags()                                       # the Fetch tags pill says the same
    assert "git tag -d ws-test-v0.1.0" in w.portal_page.output.toPlainText()


def test_catch_up_brings_in_mains_commits_under_this_checkouts(nexus, tmp_path, monkeypatch):
    identity(monkeypatch)
    origin = tmp_path / "origin.git"
    sh(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    sh(nexus, "remote", "add", "origin", str(origin))
    sh(nexus, "push", "-q", "origin", "main")
    sh(nexus, "fetch", "-q", "origin")
    assert flow.catch_up(nexus) == 0                                # nothing to bring in
    other = tmp_path / "other"
    sh(tmp_path, "clone", "-q", "-b", "main", str(origin), str(other))
    write(other / "ws/portal/apps.toml", (other / "ws/portal/apps.toml").read_text() + "\n")
    sh(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Pin ws-test-v0.1.0")
    sh(other, "push", "-q", "origin", "HEAD:main")
    write(nexus / "ws/apps/test/app.py", "print('hello again')\n")   # this checkout's own commit, not pushed
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "mine")
    sh(nexus, "fetch", "-q", "origin")
    write(nexus / "ws/apps/test/app.py", "not committed\n")
    assert flow.catch_up(nexus) is None                             # changes not committed: nothing is done
    sh(nexus, "checkout", "-q", "--", ".")
    assert flow.catch_up(nexus) == 1
    assert sh(nexus, "log", "--format=%s", "-2").split("\n")[:2] == ["mine", "Pin ws-test-v0.1.0"]


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
    (w.root / "ws/apps/test/app.py").write_text("changed\n")
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
    assert ran[0].startswith("git add -A && tools/fix-modes.sh") and "git commit" in ran[0] and "A greeting" in ran[0]
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
    # No release workflow on GitHub (a standalone suite): the steps of a release it would run get no ✓
    manual = flow.step_states(flow.Facts(ci="passed", manual=True))
    assert [key for key, state in manual.items() if state == "done"] == ["pull", "commit", "push", "ci"]
    assert {manual[key] for key in ("start", "run", "test", "publish", "finish")} == {"later"}
    assert flow.step_states(flow.Facts(dirty=True, manual=True))["commit"] == "now"
    assert flow.current_step(flow.Facts(ahead=1, unpushed="Release x")) == "start"     # Push and start
    running = _run(status="in_progress", conclusion="")
    assert flow.current_step(flow.Facts(run=running)) == "run"
    failed = flow.step_states(flow.Facts(run=_run(conclusion="failure")))
    assert failed["run"] == "failed" and failed["start"] == "done" and failed["test"] == "later"
    states = flow.step_states(flow.Facts(run=_run(), drafts=["ws-portal-v2.0.0"]))
    assert states["test"] == states["publish"] == "now" and states["run"] == "done"
    assert flow.current_step(flow.Facts(run=_run(), behind=1)) == "finish"
    assert flow.current_step(flow.Facts(run=_run())) == ""                               # out and pulled
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


def test_a_failed_release_run_lasts_with_fixes_on_top(nexus):
    head = sh(nexus, "rev-parse", "HEAD").strip()
    failed = _run(head, conclusion="failure")
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Fix CI")
    assert flow.cycle_run(nexus, [failed]) is failed               # still that release: its fix is on top
    assert flow.cycle_run(nexus, [_run(head)]) is None              # one that passed: other work ends it


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


def test_a_suite_is_on_the_nexus_release_through_its_own_workflow(tmp_path):
    """release-<suite>.yml for a suite with a tag prefix, release.yml for the one without."""
    for name, prefix in (("bc", ""), ("ws", "ws-")):
        (tmp_path / name / "portal").mkdir(parents=True)
        (tmp_path / name / "portal" / "apps.toml").write_text("", encoding="utf-8")
        if prefix:
            (tmp_path / name / "TAG_PREFIX").write_text(prefix, encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    assert flow.release_suites(tmp_path) == []
    (workflows / "release.yml").write_text("on:\n  push:\n", encoding="utf-8")
    (workflows / "release-ws.yml").write_text("on:\n  push:\n  workflow_call:\n", encoding="utf-8")
    assert flow.release_suites(tmp_path) == ["ws"]
    (workflows / "release.yml").write_text("on:\n  push:\n  workflow_call:\n", encoding="utf-8")
    (workflows / "release-bc.yml").write_text("on:\n  push:\n", encoding="utf-8")     # not the plain suite's
    assert flow.release_suites(tmp_path) == ["bc", "ws"]


def test_ci_state_reads_the_ci_runs_of_the_commit():
    runs = [_run("aaa", "ci.yml", "CI"), _run("aaa", "ci-nexus.yml", "CI Nexus", "in_progress", ""),
            _run("aaa", "release.yml"), _run("bbb", "ci.yml", "CI", conclusion="failure")]
    assert flow.ci_state(runs, "aaa") == "building" and flow.ci_state(runs, "bbb") == "failed"
    assert flow.ci_state(runs[:1], "aaa") == "passed" and flow.ci_state(runs, "ccc") == "none"
    # Another suite's CI, which every push starts too, never holds the step or Run CI again (owner, 27-10-2026).
    other = _run("aaa", "ci-ws.yml", "CI WS", conclusion="failure")
    assert flow.ci_state([runs[0], other], "aaa") == "failed" and flow.failed_ci([runs[0], other], "aaa") == [other]
    hidden = {"ci-ws.yml", "release-ws.yml"}
    assert flow.ci_state([runs[0], other], "aaa", hidden) == "passed"
    assert flow.failed_ci([runs[0], other], "aaa", hidden) == [] and flow.ci_state([other], "aaa", hidden) == "none"


def test_the_release_run_lasts_until_other_work_is_committed(nexus):
    head = sh(nexus, "rev-parse", "HEAD").strip()
    run = _run(head)
    assert flow.cycle_run(nexus, [run]) is run
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Pin ws-test-v0.2.0")
    assert flow.cycle_run(nexus, [run]) is run                    # the pin commit pulled: still this release
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Other work")
    assert flow.cycle_run(nexus, [run]) is None
    assert flow.cycle_run(nexus, []) is None
    assert flow.published(nexus, [_run(ref="ws-portal-v9.9.9", file="nexus-index.yml")], "ws-portal-v9.9.9")
    assert not flow.published(nexus, [], "ws-portal-v9.9.9")


def test_a_release_with_a_draft_to_test_lasts_with_other_work_on_top(nexus):
    """Other work pushed before a portal draft's device test (owner, 04-11-2026: a suite's portal, after a fix
    to the board's): the release lasts until the draft is published or Not OK, so Start never replaces it."""
    write(nexus / "ws/portal/VERSION", "1.1.0\n")                  # what the release wrote: ws-portal-v1.1.0, a draft
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Release ws-portal-v1.1.0")
    head = sh(nexus, "rev-parse", "HEAD").strip()
    run = _run(head)
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Other work")
    assert flow.cycle_run(nexus, [run]) is run
    assert flow.cycle_run(nexus, [run], ["ws-portal-v1.1.0"]) is None      # Not OK: a new release may replace it
    assert flow.cycle_run(nexus, [_run(head, conclusion="failure")]) is not None   # a failed run lasted already
    sh(nexus, "tag", "ws-portal-v1.1.0")                             # published: its tag fetched
    assert flow.cycle_run(nexus, [run]) is None


def test_a_portal_version_raised_after_a_published_release_is_the_next_release(nexus):
    """The portal's version raised in a commit after its release was published (owner, 07-11-2026: NRT showed the
    release on GitHub done and offered the device test of ws-portal-v10.1.0, a draft no run had built): the run's
    own portal is out, so that release is over and Start new release is next; the draft is read at the run's commit."""
    head = sh(nexus, "rev-parse", "HEAD").strip()
    run = _run(head)
    assert flow.published(nexus, [], "ws-portal-v1.0.0")              # the run's portal, published (the fixture's tag)
    write(nexus / "ws/portal/VERSION", "1.1.0\n")
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "Other work")
    assert flow.waiting_portals(nexus, "ws") == ["ws-portal-v1.1.0"]          # the checkout's: the next release
    assert flow.waiting_portals(nexus, "ws", head) == ["ws-portal-v1.0.0"]    # the run's own
    assert flow.cycle_run(nexus, [run], suite="ws") is None


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
    monkeypatch.setattr(flow, "waiting_portals", lambda root, only=None, at="": [])
    page.show_state()
    assert page.facts.behind == 1 and flow.current_step(page.facts) == "finish"
    assert page.finish_button.isEnabled()


def test_the_device_test_and_publish(release_window, monkeypatch):
    w = release_window
    page = w.release_page
    w.build.runs = [_run(sh(w.root, "rev-parse", "HEAD").strip())]   # the release run passed on HEAD: its draft
    monkeypatch.setattr(flow, "published", lambda *a: False)          # ws-portal-v1.0.0 a draft still
    page.show_state()
    page.device_test()
    assert w.launched and w.launched[-1].endswith("draft ws-portal-v1.0.0")
    ran = []
    monkeypatch.setattr(w, "confirm_git", lambda *a: True)
    monkeypatch.setattr(w, "run_git", ran.append)
    page.publish()
    assert ran == [flow.publish_command("ws-portal-v1.0.0")]
    page.show_state()
    assert flow.step_states(page.facts)["test"] == "now"
    page.reject()
    assert "stays a draft" in page.output.toPlainText()
    # Not OK shows on the step (owner, 30-10-2026: it seemed to do nothing): red, with what comes next
    assert flow.step_states(page.facts)["test"] == "failed" and page.facts.rejected == ["ws-portal-v1.0.0"]
    assert page.details["test"].text().startswith("Not OK: ws-portal-v1.0.0 stays a draft")
    assert page.marks["test"].text() == "!" and page.test_button.isEnabled() and page.publish_button.isEnabled()


def test_the_portal_choice_holds_only_the_drafts(release_window, monkeypatch):
    """A tag published since the choice was filled leaves it (owner, 05-11-2026: the choice stayed on
    portal-v15.2.0, so Publish published it again): only the draft is left."""
    w = release_window
    page = w.release_page
    monkeypatch.setattr(flow, "waiting_portals", lambda root, only=None, at="": ["ws-portal-v1.0.0"])
    monkeypatch.setattr(flow, "published", lambda root, runs, tag: False)
    w.build.runs = [_run(sh(w.root, "rev-parse", "HEAD").strip())]
    page.portal_choice.clear()
    page.portal_choice.addItems(["portal-v2.0.0", "ws-portal-v1.0.0"])
    page.show_state()
    assert page.facts.drafts == ["ws-portal-v1.0.0"]
    assert [page.portal_choice.itemText(i) for i in range(page.portal_choice.count())] == ["ws-portal-v1.0.0"]
    assert page.details["test"].text() == ("ws-portal-v1.0.0 is a draft: Device test, then Publish when it works "
                                           "or Not OK.")
    ran = []
    monkeypatch.setattr(w, "confirm_git", lambda *a: True)
    monkeypatch.setattr(w, "run_git", ran.append)
    page.publish()
    assert ran == [flow.publish_command("ws-portal-v1.0.0")]


def test_each_suite_stands_apart(nexus):
    """Two suites on the Nexus release (owner, 05-11-2026: one suite's draft, waiting for its device, held up the
    board's next release): each release is of one suite, its run says which, and only its own draft keeps it."""
    bc = nexus / "bc"
    write(bc / "SYSTEM", "bazzite\n")
    write(bc / "portal/VERSION", "2.0.0\n")
    write(bc / "portal/apps.toml", "")
    write(nexus / ".github/workflows/release.yml", "on:\n  workflow_call:\n")
    write(nexus / "ws/portal/VERSION", "1.1.0\n")                 # the ws release wrote ws-portal-v1.1.0: a draft
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "Release ws-portal-v1.1.0")
    head = sh(nexus, "rev-parse", "HEAD").strip()
    sh(nexus, "tag", "portal-v2.0.0")                                # the board's portal is out
    sh(nexus, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Other work")
    assert flow.release_suites(nexus) == ["bc", "ws"]
    assert flow.waiting_portals(nexus) == ["portal-v2.0.0", "ws-portal-v1.1.0"]
    assert flow.waiting_portals(nexus, "bc") == ["portal-v2.0.0"]
    assert {p.suite for p in flow.picks(nexus, "ws")} == {"ws", ""}           # its apps and portal, core and Nexus
    # A run of before 05-11-2026 carried every suite: the ws draft keeps the ws release, not the board's
    old = _run(head)
    assert flow.run_suites(old) is None
    assert flow.cycle_run(nexus, [old], suite="ws") is old
    assert flow.cycle_run(nexus, [old], suite="bc") is None          # Start new release for the board
    # A run started for the board says so in its title, and is not the ws release's
    board = _run("f" * 40, title="Release: bc")
    assert flow.run_suites(board) == ["bc"]
    assert flow.release_run([board, old], suite="bc") is board
    assert flow.release_run([board, old], suite="ws") is old
    assert flow.tag_suites(nexus, ["test-v1.0.0", "portal-v2.1.0", "nexus-v0.6.0"]) == ["bc"]
    assert flow.tag_suites(nexus, ["ws-portal-v1.1.0"]) == ["ws"] and flow.tag_suites(nexus, ["nexus-v0.6.0"]) == []
    assert "suites" not in flow.start_command("Release portal-v2.1.0", ["bc"])       # release.yml takes none
    assert "suites" not in flow.restart_command(["bc"]) and "suites" not in flow.restart_command()


def test_not_ok_is_the_runs_and_a_fix_goes_on_from_commit():
    run = _run()
    facts = flow.Facts(run=run, drafts=["ws-portal-v6.0.0"], rejected=["ws-portal-v6.0.0"])
    states = flow.step_states(facts)
    assert flow.current_step(facts) == "test" and states["test"] == "failed" and states["publish"] == "later"
    assert flow.step_states(flow.Facts(run=run, drafts=["ws-portal-v6.0.0"]))["test"] == "now"   # a run made anew
    assert flow.current_step(flow.Facts(run=run, drafts=["ws-portal-v6.0.0"], rejected=["ws-portal-v6.0.0"],
                                        dirty=True)) == "commit"


def test_commit_offers_the_portal_bump_when_apps_toml_changed(release_window, monkeypatch):
    """apps.toml changed since the last portal release (an app added): the commit's manifest check would refuse
    the commit, so Commit offers the portal bump (owner, 02-11-2026) and writes it with its CHANGELOG entry on a
    yes; on a no nothing is committed and the output says why."""
    w = release_window
    page = w.release_page
    extra = APPS_TOML.replace("apps.test", "apps.extra").replace('"T"', '"E"').replace("ws-test-v0.1.0", "ws-extra-v0.1.0") \
        .replace("required = true", "required = false")
    (w.root / "ws/portal/apps.toml").write_text(APPS_TOML + "\n" + extra, encoding="utf-8")
    w.reload()
    assert rp.portal_offer(w.root, "HEAD", "ws") == ("1.1.0", "the least the manifest check accepts",
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
    assert (w.root / "ws/portal/VERSION").read_text() == "1.0.0\n"

    monkeypatch.setattr("nexus_release_tool.release_page.QMessageBox.question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    page.commit()
    assert len(ran) == 1 and "git commit" in ran[0] and "An app" in ran[0]
    assert (w.root / "ws/portal/VERSION").read_text() == "1.1.0\n"
    assert "Release 1.1.0." in (w.root / "ws/portal/CHANGELOG").read_text()
    assert "portal 1.1.0" in page.output.toPlainText()
    assert rp.portal_offer(w.root, "HEAD", "ws") is None            # the bump is there: nothing to offer

    # A Breaking entry in the portal's CHANGELOG: the offer is step 2's major, above the least the check accepts.
    (w.root / "ws/portal/VERSION").write_text("1.0.0\n")
    (w.root / "ws/portal/CHANGELOG").write_text("Changelog: 03-01-2026 00:00:00\n\nBreaking. Gone.\n\n"
                                                "Changelog: 01-01-2026 00:00:00\n\nRelease 1.0.0.\n")
    w.reload()
    assert rp.portal_offer(w.root, "HEAD", "ws")[0] == "2.0.0"


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
