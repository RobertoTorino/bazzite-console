# SPDX-License-Identifier: GPL-3.0-or-later
"""plan.py (and the window on top of it) in a small git repo of its own."""

from __future__ import annotations

import datetime
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from nexus_release_tool import flow
from nexus_release_tool import plan as rp

SHA = "cd" * 32


def card(key: str, required: bool = False) -> str:
    return (f'[apps.{key}]\nname = "{key}"\nsummary = "s"\ntag = "{key}-v0.1.0"\nsha256 = ""\n'
            f'required = {"true" if required else "false"}\nchanges_board = false\ninstall = ["bash install.sh"]\n'
            f'uninstall = ["bash install.sh --uninstall"]\ndetect = ["~/.local/bin/{key}"]\n\n')


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode())


def sh(root: Path, *args: str) -> None:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=env)


@pytest.fixture
def repo(tmp_path) -> Path:
    root = tmp_path / "suite"
    write(root / "core/VERSION", "0.1.0\n")
    write(root / "core/bazzite_console_core/__init__.py", '__version__ = "0.1.0"\n')
    write(root / "core/pyproject.toml", '[project]\nname = "c"\nversion = "0.1.0"\n')
    write(root / "core/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nCore.\n")
    write(root / "portal/VERSION", "0.1.0\n")
    write(root / "portal/bazzite_console_portal/__init__.py", '__version__ = "0.1.0"\n')
    write(root / "portal/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nPortal.\n")
    write(root / "portal/apps.toml", "# the pins\n\n" + card("alpha", required=True) + card("beta"))
    for key in ("alpha", "beta"):
        write(root / f"apps/{key}/VERSION", "0.1.0\n")
        write(root / f"apps/{key}/{key}/__init__.py", f'APP = "{key}"\n__version__ = "0.1.0"\n')
        write(root / f"apps/{key}/run.sh", 'VERSION="0.1.0"\necho "$VERSION"\n')
        write(root / f"apps/{key}/tests/test_x.py", '__version__ = "0.1.0"\n')
        write(root / f"apps/{key}/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nFirst.\n")
    write(root / "apps/standalone/VERSION", "0.1.0\n")
    write(root / "apps/standalone/.standalone", "Standalone app; do not add to portal/apps.toml.\n")
    write(root / "apps/releases/VERSION", "0.1.0\n")                  # like this app: never released
    write(root / "apps/releases/.standalone", "Not in the portal.\n")
    write(root / "apps/releases/.checkout-only", "No releases.\n")
    write(root / "apps/alpha/alpha/ui.py", "from bazzite_console_core import widgets\n")      # alpha bundles core, beta not
    # A Rust crate, as Console Link has: Cargo.lock repeats the crate's version, next to another crate's.
    write(root / "apps/alpha/native/Cargo.toml", '[package]\nname = "alpha-core"\nversion = "0.1.0"\n')
    write(root / "apps/alpha/native/Cargo.lock", 'version = 4\n\n[[package]]\nname = "aes"\nversion = "0.1.0"\n\n'
                                                '[[package]]\nname = "alpha-core"\nversion = "0.1.0"\n')
    write(root / "docs/apps/alpha.md", "# Alpha\n")
    sh(root, "init", "-q", "-b", "main")
    sh(root, "add", "-A")
    sh(root, "commit", "-q", "-m", "start")
    sh(root, "tag", "alpha-v0.1.0")
    sh(root, "tag", "standalone-v0.1.0")
    sh(root, "branch", "pushed")                # stands in for origin/main
    write(root / "apps/alpha/alpha/extra.py", "x = 1\n")
    sh(root, "add", "-A")
    sh(root, "commit", "-q", "-m", "work")
    return root


def unit(root: Path, key: str) -> rp.Unit:
    return next(u for u in rp.load_units(root) if u.key == key)


def test_a_suites_tags_carry_its_prefix(repo):
    """The suite's TAG_PREFIX starts its tags: the apps' and the portal's, never core's; a tag without it is not the
    suite's."""
    write(repo / "TAG_PREFIX", "ps5-\n")
    sh(repo, "tag", "ps5-beta-v0.1.0")
    assert rp.tag_prefix(repo) == "ps5-"
    units = {u.key: u for u in rp.load_units(repo)}
    assert units["beta"].last_tag == "ps5-beta-v0.1.0" and units["alpha"].last_tag is None     # alpha-v0.1.0: no
    assert units["portal"].tag == "ps5-portal-v0.1.0" and units["core"].prefix == ""
    beta = units["beta"]
    rp.set_version(repo, beta, "0.2.0")
    rp.pin(repo, beta, "AB" * 32)
    assert 'tag = "ps5-beta-v0.2.0"\nsha256 = "' + "ab" * 32 + '"' in (repo / "portal/apps.toml").read_text()
    assert rp.changed_pins(repo, "HEAD") == ["ps5-beta-v0.2.0"]


def test_units(repo):
    units = {u.key: u for u in rp.load_units(repo)}
    assert list(units) == ["core", "portal", "alpha", "beta", "standalone"]   # not the checkout-only app
    alpha = units["alpha"]
    assert (alpha.version, alpha.last_tag, alpha.commits, alpha.released) == ("0.1.0", "alpha-v0.1.0", 1, True)
    assert alpha.pinned_tag == "alpha-v0.1.0" and alpha.pinned_sha == ""
    assert units["beta"].last_tag is None and not units["beta"].released
    assert units["standalone"].standalone and units["standalone"].released
    assert units["core"].kind == "core" and units["core"].last_tag is None


def test_versions():
    assert rp.next_versions("1.2.3") == {"patch": "1.2.4", "minor": "1.3.0", "major": "2.0.0"}
    assert rp.check_new_version("0.1.0", "0.1.0", released=False) == ""        # a first release as it is
    assert "already tagged" in rp.check_new_version("0.1.0", "0.1.0", released=True)
    assert "not higher" in rp.check_new_version("0.2.0", "0.1.9", released=False)
    assert "not x.y.z" in rp.check_new_version("0.1.0", "0.2", released=False)


def test_set_version_changes_a_copy_with_a_comment(repo):
    init = repo / "apps/alpha/alpha/__init__.py"
    init.write_text('APP = "alpha"\n__version__ = "0.1.0"   # equal to VERSION\n')
    rp.set_version(repo, unit(repo, "alpha"), "0.2.0")
    assert init.read_text() == 'APP = "alpha"\n__version__ = "0.2.0"   # equal to VERSION\n'      # comment kept


def test_set_version_changes_every_copy_but_tests(repo):
    alpha = unit(repo, "alpha")
    changed = rp.set_version(repo, alpha, "0.2.0")
    assert {p.relative_to(repo).as_posix() for p in changed} == {
        "apps/alpha/VERSION", "apps/alpha/alpha/__init__.py", "apps/alpha/run.sh", "apps/alpha/native/Cargo.toml",
        "apps/alpha/native/Cargo.lock"}
    lock = (repo / "apps/alpha/native/Cargo.lock").read_text()
    assert 'name = "alpha-core"\nversion = "0.2.0"' in lock and 'name = "aes"\nversion = "0.1.0"' in lock
    assert (repo / "apps/alpha/VERSION").read_text() == "0.2.0\n"
    assert (repo / "apps/alpha/alpha/__init__.py").read_text() == 'APP = "alpha"\n__version__ = "0.2.0"\n'
    assert (repo / "apps/alpha/run.sh").read_text().startswith('VERSION="0.2.0"\n')
    assert '"0.1.0"' in (repo / "apps/alpha/tests/test_x.py").read_text()
    core = unit(repo, "core")
    rp.set_version(repo, core, "0.2.0")
    assert 'version = "0.2.0"' in (repo / "core/pyproject.toml").read_text()


@pytest.mark.parametrize("utc, local", [
    ((2026, 10, 10, 18, 0), "10-10-2026 20:00:00"),          # CEST
    ((2026, 10, 25, 0, 59), "25-10-2026 02:59:00"),          # the last minute of CEST
    ((2026, 10, 25, 1, 0), "25-10-2026 02:00:00"),           # CET
    ((2026, 3, 29, 1, 0), "29-03-2026 03:00:00"),            # CEST again
    ((2026, 1, 5, 12, 0), "05-01-2026 13:00:00"),
])
def test_amsterdam_time(utc, local):
    now = datetime.datetime(*utc, tzinfo=datetime.timezone.utc)
    assert rp.amsterdam_now(now).strftime("%d-%m-%Y %H:%M:%S") == local


def test_changelog_entry(repo):
    now = datetime.datetime(2026, 10, 10, 18, 0, tzinfo=datetime.timezone.utc)
    rp.add_changelog_entry(repo, unit(repo, "beta"), rp.release_text("0.1.0", "  The first one. "), now)
    assert (repo / "apps/beta/CHANGELOG").read_text() == (
        "Changelog: 10-10-2026 20:00:00\n\nRelease 0.1.0. The first one.\n\n"
        "Changelog: 01-01-2026 00:00:00\n\nFirst.\n")
    assert rp.portal_text("0.2.0", ["alpha-v0.2.0"], "") == "Release 0.2.0. Pins alpha-v0.2.0."


def test_applying_a_release_again_keeps_one_entry(repo):
    """Apply after a check stopped the commit wrote "Release 1.3.0." a second time (owner, 28-10-2026): the same
    release replaces the newest entry, with the latest notes; another release, or another kind of entry, is added."""
    beta = unit(repo, "beta")
    first = datetime.datetime(2026, 10, 10, 18, 0, tzinfo=datetime.timezone.utc)
    again = datetime.datetime(2026, 10, 10, 18, 5, tzinfo=datetime.timezone.utc)
    rp.add_changelog_entry(repo, beta, rp.release_text("0.1.0", ""), first)
    rp.add_changelog_entry(repo, beta, rp.release_text("0.1.0", "Pins alpha-v0.2.0."), again)
    text = (repo / "apps/beta/CHANGELOG").read_text()
    assert text == ("Changelog: 10-10-2026 20:05:00\n\nRelease 0.1.0. Pins alpha-v0.2.0.\n\n"
                    "Changelog: 01-01-2026 00:00:00\n\nFirst.\n")
    rp.add_changelog_entry(repo, beta, "Fixed. A typo.", again)
    rp.add_changelog_entry(repo, beta, rp.release_text("0.1.1", ""), again)
    rp.add_changelog_entry(repo, beta, rp.release_text("0.1.1", ""), again)
    assert [rp.entry_body(e) for e in rp.changelog_entries((repo / "apps/beta/CHANGELOG").read_text())] == [
        "Release 0.1.1.", "Fixed. A typo.", "Release 0.1.0. Pins alpha-v0.2.0.", "First."]


def test_a_pushed_release_entry_stays(repo):
    """The portal release replaced the "Release 3.2.0. Pins ..." entry its app release had pushed, and the push
    failed check_changelogs.py (owner, 29-10-2026): an entry the last push has is history, so the same release is
    added on top of it."""
    beta = unit(repo, "beta")
    first = datetime.datetime(2026, 10, 10, 18, 0, tzinfo=datetime.timezone.utc)
    again = datetime.datetime(2026, 10, 10, 18, 5, tzinfo=datetime.timezone.utc)
    rp.add_changelog_entry(repo, beta, rp.release_text("0.1.0", "Pins alpha-v0.2.0."), first, base="pushed")
    sh(repo, "commit", "-q", "-am", "release")
    sh(repo, "branch", "-f", "pushed")
    rp.add_changelog_entry(repo, beta, rp.release_text("0.1.0", ""), again, base="pushed")
    assert [rp.entry_body(e) for e in rp.changelog_entries((repo / "apps/beta/CHANGELOG").read_text())] == [
        "Release 0.1.0.", "Release 0.1.0. Pins alpha-v0.2.0.", "First."]


def test_pin_and_portal(repo):
    assert rp.portal_minimum(repo, "pushed", "0.1.0") == ("", "")
    alpha = unit(repo, "alpha")
    rp.set_version(repo, alpha, "0.1.1")
    sh(repo, "tag", "alpha-v0.1.1")
    alpha = unit(repo, "alpha")
    assert alpha.released
    rp.pin(repo, alpha, SHA.upper())
    text = (repo / "portal/apps.toml").read_text()
    assert f'tag = "alpha-v0.1.1"\nsha256 = "{SHA}"' in text and text.startswith("# the pins\n")
    assert rp.changed_pins(repo, "pushed") == ["alpha-v0.1.1"]
    assert rp.portal_minimum(repo, "pushed", "0.1.0") == ("0.1.1", "apps.toml changed")
    assert rp.portal_minimum(repo, "pushed", "0.2.0")[0] == "0.2.0"     # already bumped far enough


def test_ticker_shows_the_runs_of_the_push(repo, tmp_path):
    """The ticker shows every run of the newest push, the running ones first."""
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    w = main_window.ReleaseWindow(repo, status_source=None, runs_source=lambda etag, head="": (None, etag),
                                  notify=lambda *a: None, claude_source=None, jobs_source=None)
    runs = [run(n=2), run("Release", "portal-v3.0.1", status="in_progress", n=1)]
    for data, path in zip(runs, ("ci.yml", "release.yml")):
        data["path"] = f".github/workflows/{path}"
    w.build.checked((rp.parse_runs({"workflow_runs": runs}), "e1"))
    w.ticker.checker.stop(2000)
    assert w.ticker.line == "Release on portal-v3.0.1: in progress   |   CI on main: passed"
    w.close()


def test_a_pushed_head_without_a_run_is_looked_at_again_soon(repo, tmp_path):
    """GitHub starts the CI of a push seconds after it (owner, 05-11-2026: CI ran on GitHub while the CI passes step
    said it had none, for 5 minutes): while the pushed HEAD has no run, the next look is in 10 s, not 5 minutes."""
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    w = main_window.ReleaseWindow(repo, status_source=None, runs_source=lambda etag, head="": (None, etag),
                                  notify=lambda *a: None, claude_source=None, jobs_source=None)
    head = (rp.git(repo, "rev-parse", "HEAD") or "").strip()
    w.build.head = head
    w.base = lambda: "HEAD"                                         # HEAD is pushed: on the base
    older = rp.parse_runs({"workflow_runs": [run(n=1, sha="older")]})
    w.build.checked((older, "e1"))
    assert w.build.awaiting_head() and w.build.timer.interval() == main_window.BUILD_SOON_MS
    w.build.checked((rp.parse_runs({"workflow_runs": [run(n=2, sha=head, status="in_progress"), run(n=1, sha="older")]}),
                     "e2"))
    assert not w.build.awaiting_head() and w.build.timer.interval() == main_window.BUILD_BUSY_MS
    w.base = lambda: "HEAD~0^{tree}"                                # not pushed: no reason to hurry
    w.build.runs = older
    assert not w.build.awaiting_head()
    w.close()


def test_a_run_that_finishes_is_told_about(repo, tmp_path):
    """A run seen running that finishes gives a desktop notification, which names it."""
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    notes = []
    w = main_window.ReleaseWindow(repo, status_source=None, runs_source=lambda etag, head="": (None, etag),
                                  notify=lambda *a: notes.append(a), claude_source=None, jobs_source=None)

    def runs(status, conclusion="success"):
        found = [run(name, status=status, conclusion=conclusion, n=n) for n, name in ((2, "Release"), (1, "CI"))]
        for data, path in zip(found, ("release.yml", "ci.yml")):
            data["path"] = f".github/workflows/{path}"
        return rp.parse_runs({"workflow_runs": found})
    w.build.checked((runs("in_progress"), "e1"))
    w.build.checked((runs("completed", "failure"), "e2"))
    assert notes[-1][0] == "GitHub build failed"
    assert "Release on main" in notes[-1][1] and "CI on main" in notes[-1][1]
    w.close()


def test_git_button_commands():
    assert rp.add_command() == "python3 tools/all_tests.py && git add -A && tools/fix-modes.sh && git status --short"
    assert rp.commit_command("Release alpha-v0.2.0", "origin/main") == (
        "python3 tools/check_wiki.py --base origin/main && python3 tools/check_versions.py && "
        "python3 tools/check_manifest.py --base origin/main && "
        "git commit -m 'Release alpha-v0.2.0'")                       # the checks first, the commit only after
    assert rp.commit_command("it's", "pushed", python="/v/python").endswith("git commit -m 'it'\"'\"'s'")
    assert rp.commit_command("", "pushed", amend=True).endswith(" && git commit --amend --no-edit")


def test_git_state(repo):
    assert rp.git_state(repo, "pushed") == (False, False, 1)         # clean, one commit ("work") not pushed
    write(repo / "apps/alpha/alpha/extra.py", "x = 2\n")
    write(repo / "apps/alpha/new.py", "y = 1\n")
    assert rp.git_state(repo, "pushed") == (True, False, 1)
    sh(repo, "add", "apps/alpha/alpha/extra.py")
    assert rp.git_state(repo, "pushed") == (True, True, 1)           # the new file is not staged yet
    sh(repo, "add", "-A")
    assert rp.git_state(repo, "pushed") == (False, True, 1)
    assert rp.git_state(repo, "main")[2] == 0


def test_window_get_up_to_date_counts_what_the_remote_has(window, repo, monkeypatch):
    """Get up to date, the first step (owner, 28-10-2026: a push from the other machine only showed as a push that
    failed): its pill runs git pull, its line counts what the remote has that HEAD does not, and it is the step to
    do when GitHub's newest push on main is no commit here. The git row under the tabs is gone (owner, 01-11-2026)."""
    ran = []
    monkeypatch.setattr(window.commands, "run_now", lambda command: ran.append(command) or True)
    assert not hasattr(window, "pull_button") and not hasattr(window, "commit_message")
    page = window.release_page
    sh(repo, "checkout", "-q", "pushed")                                 # the other machine pushes two commits
    for name in ("a", "b"):
        write(repo / f"{name}.txt", name)
        sh(repo, "add", "-A")
        sh(repo, "commit", "-q", "-m", name)
    sh(repo, "checkout", "-q", "main")
    assert rp.behind(repo, "pushed") == 2
    window.reload()
    assert page.pull_button.isEnabled() and "2 commits on GitHub that this checkout lacks" in page.details["pull"].text()
    page.pull_button.click()
    assert ran[-1] == rp.pull_command() and window.tabs.currentIndex() == window.commands_tab
    sh(repo, "branch", "-f", "pushed", "main")
    window.reload()
    assert not page.pull_button.isEnabled()
    elsewhere = run(sha="f" * 40)                                         # GitHub saw a push this checkout lacks
    window.build.checked((rp.parse_runs({"workflow_runs": [elsewhere]}), "e1"))
    page.show_state()
    assert page.pull_button.isEnabled() and "1 commit on GitHub" in page.details["pull"].text()


def test_the_minimum_needs_no_second_bump_for_the_pins(repo):
    """The owner's case of 17-10-2026: the push with the apps' releases carried the portal bump; the next push, with
    their checksums pinned, was offered 1.13.1 (a patch over the last push). Against the last portal release the
    bump already made covers it, so the minimum stays the version in the tree and no second bump is made."""
    sh(repo, "tag", "portal-v0.1.0")
    rp.set_version(repo, unit(repo, "beta"), "0.2.0")
    rp.pin(repo, unit(repo, "beta"), "")                                      # the new tag, as Start writes it
    rp.set_version(repo, unit(repo, "portal"), "0.2.0")
    sh(repo, "commit", "-qam", "Release beta-v0.2.0")
    sh(repo, "branch", "-f", "pushed")                                        # pushed with the bump in it
    text = (repo / "portal/apps.toml").read_text()
    write(repo / "portal/apps.toml", text.replace('name = "beta"\nsummary = "s"', 'name = "beta"\nsummary = "pinned"'))
    assert rp.portal_minimum(repo, "pushed", "0.2.0") == ("0.2.0", "beta 0.1.0 -> 0.2.0")
    assert rp.portal_minimum(repo, "pushed", "0.3.0") == ("0.3.0", "beta 0.1.0 -> 0.2.0")   # bumped further: kept


def test_withdrawal(repo):
    now = datetime.datetime(2026, 10, 13, 12, 0, tzinfo=datetime.timezone.utc)
    units = rp.load_units(repo)
    assert [u.key for u in rp.withdrawable(repo, units)] == ["beta"]             # alpha is the required app
    beta = unit(repo, "beta")
    before = (repo / "portal/apps.toml").read_text()
    changed = rp.withdraw(repo, beta, 'Privacy: shows the "account ID".', now)
    text = (repo / "portal/apps.toml").read_text()
    assert text == before.replace('[apps.beta]\nname = "beta"\nsummary = "s"\n',
                                  '[apps.beta]\nname = "beta"\nsummary = "s"\n'
                                  'withdrawn = "Privacy: shows the \\"account ID\\"."\n')
    assert rp.withdrawn_reason(repo, "beta") == 'Privacy: shows the "account ID".'
    assert [p.relative_to(repo).as_posix() for p in changed] == ["portal/apps.toml", "apps/beta/CHANGELOG"]
    assert (repo / "apps/beta/CHANGELOG").read_text().startswith(
        'Changelog: 13-10-2026 14:00:00\n\nWithdrawn: beta-v0.1.0. Privacy: shows the "account ID".\n')
    # The portal release that follows: a minor bump, and its CHANGELOG entry names the withdrawal.
    assert rp.changed_withdrawals(repo, "pushed") == [("beta-v0.1.0", 'Privacy: shows the "account ID".')]
    assert rp.portal_minimum(repo, "pushed", "0.1.0") == ("0.2.0", "beta was withdrawn")
    assert rp.portal_text("0.2.0", [], "", rp.changed_withdrawals(repo, "pushed")) == (
        'Release 0.2.0. Withdraws beta-v0.1.0: Privacy: shows the "account ID".')
    commands = rp.withdraw_commands("beta-v0.1.0", "Privacy.", now)
    assert ("gh release edit beta-v0.1.0 --prerelease --title 'Withdrawn: beta-v0.1.0' --notes 'Withdrawn on "
            "13-10-2026: Privacy. Do not install this release.'") in commands
    # Taken back: apps.toml as it was, and a CHANGELOG entry that says so.
    rp.withdraw(repo, beta, "", now)
    assert (repo / "portal/apps.toml").read_text() == before
    assert "Withdrawal of beta-v0.1.0 taken back." in (repo / "apps/beta/CHANGELOG").read_text()
    with pytest.raises(ValueError, match="no \\[apps.gamma\\]"):
        rp.set_withdrawn(before, "gamma", "x")


# --- The window -------------------------------------------------------------------------------------------------

launched: list[str] = []


@pytest.fixture
def window(repo, tmp_path):
    pytest.importorskip("PyQt6.QtWidgets")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    w = main_window.ReleaseWindow(repo, launch=launched.append, runs_source=None, status_source=None)
    w.base_ref = "pushed"
    w.reload()
    yield w
    w.close()


def needs(root):
    return {u.key: (u.needs_release, u.release_reason, u.changed) for u in rp.load_units(root)}


def test_needs_release_follows_what_ships(repo):
    alpha = needs(repo)["alpha"]
    assert alpha == (True, "yes: 1 file", ["apps/alpha/alpha/extra.py"])          # committed after the tag
    assert needs(repo)["beta"][:2] == (True, "first release")
    assert needs(repo)["core"][0] is False
    sh(repo, "tag", "alpha-v0.1.1")                                               # released: nothing left
    assert needs(repo)["alpha"][:2] == (False, "no")
    write(repo / "apps/alpha/tests/test_y.py", "x = 2\n")                         # tests do not ship
    write(repo / "apps/alpha/requirements-dev.txt", "pytest\n")
    assert needs(repo)["alpha"][0] is False
    write(repo / "apps/alpha/alpha/__init__.py", 'APP = "alpha"\n__version__ = "0.1.0"\n# changed\n')
    assert needs(repo)["alpha"][2] == ["apps/alpha/alpha/__init__.py"]           # not committed yet
    write(repo / "apps/alpha/alpha/new.py", "y = 1\n")
    assert "apps/alpha/alpha/new.py" in needs(repo)["alpha"][2]                  # new, untracked


def test_core_and_manual_changes_count_for_the_apps_that_ship_them(repo):
    sh(repo, "tag", "alpha-v0.1.1")
    sh(repo, "tag", "beta-v0.1.0")
    write(repo / "core/bazzite_console_core/widgets.py", "class StatusText: pass\n")
    state = needs(repo)
    assert state["alpha"][:2] == (True, "yes: core") and state["beta"][0] is False   # beta does not import core
    core = next(u for u in rp.load_units(repo) if u.kind == "core")
    assert (core.in_apps, core.changed, core.release_reason) == (
        ["alpha"], ["core/bazzite_console_core/widgets.py"], "changed: goes into 1 app release")
    assert not core.needs_release                                                 # core itself is never tagged
    write(repo / "docs/apps/alpha.md", "# Alpha\n\nMore.\n")                      # shipped as MANUAL.md
    assert needs(repo)["alpha"][1] == "yes: 1 file + core"


def test_core_bumped_with_its_change_needs_no_new_version(repo):
    """Core went to a new version with its change (released with some apps), and another app's release still
    carries it: that version already holds the change, so core offers itself as it is, not a higher one."""
    sh(repo, "tag", "alpha-v0.1.1")
    write(repo / "core/bazzite_console_core/widgets.py", "class StatusText: pass\n")
    assert rp.core_is_current(repo) is False                                      # changed, not bumped
    core = unit(repo, "core")
    rp.set_version(repo, core, "0.1.1")
    assert rp.core_is_current(repo) is True                                       # the bump, not committed yet
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", "core 0.1.1")
    core = unit(repo, "core")
    assert core.current and core.in_apps == ["alpha"]                             # alpha-v0.1.1 has the old core
    assert core.release_reason == "0.1.1 has it: goes into 1 app release"
    write(repo / "core/bazzite_console_core/widgets.py", "class StatusText: pass\n# more\n")
    assert not unit(repo, "core").current                                         # a change after the bump


def test_a_tag_before_the_bump_is_reported(repo):
    rp.set_version(repo, unit(repo, "beta"), "0.2.0")
    sh(repo, "tag", "beta-v0.2.0")                            # tagged, but the bump is not committed
    assert rp.bad_tags(repo, rp.load_units(repo)) == ["beta-v0.2.0 points at a commit where apps/beta/VERSION is 0.1.0"]
    sh(repo, "tag", "-d", "beta-v0.2.0")
    sh(repo, "commit", "-qam", "bump")
    sh(repo, "tag", "beta-v0.2.0")
    assert rp.bad_tags(repo, rp.load_units(repo)) == []


def test_window_warns_about_a_bad_tag(window, repo):
    assert window.bad_tags.isHidden()
    rp.set_version(repo, unit(repo, "beta"), "0.2.0")
    sh(repo, "tag", "beta-v0.2.0")
    window.reload()
    text = window.bad_tags.text()
    assert not window.bad_tags.isHidden() and "git tag -d beta-v0.2.0" in text and "tag-release.sh beta-v0.2.0" in text


def mock_question(answer):
    from unittest import mock
    from PyQt6.QtWidgets import QMessageBox
    return mock.patch.object(QMessageBox, "question", return_value=answer)


# --- GitHub builds ----------------------------------------------------------------------------------------------

def run(workflow="CI", ref="main", status="completed", conclusion="success", n=1, sha="abc1234def"):
    return {"name": workflow, "head_branch": ref, "status": status, "conclusion": conclusion if status == "completed"
            else None, "html_url": f"https://github.invalid/runs/{n}", "head_sha": sha, "display_title": "Fix it"}


def test_build_state_of_the_latest_push():
    runs = rp.parse_runs({"workflow_runs": [run(n=3), run("Release", "governor-v0.1.1", "in_progress", n=2),
                                            run(n=1, sha="older", conclusion="failure")]})
    latest = rp.latest_push(runs)
    assert [r.url[-1] for r in latest] == ["3", "2"]                          # not the older commit
    assert rp.build_state(latest) == "running" and latest[1].outcome == "in progress"
    done = [replace(latest[1], status="completed", conclusion="failure")]
    assert rp.build_state([latest[0], *done]) == "failed" and done[0].outcome == "failure"
    assert rp.build_state([latest[0], replace(latest[1], status="completed", conclusion="skipped")]) == "passed"
    assert rp.build_state([]) == "" and rp.parse_runs({"message": "rate limit"}) == []
    # A run GitHub canceled for a later one of its workflow on the same commit (nexus-index.yml's concurrency) is no
    # failure (owner, 30-10-2026: the pill said Failed for 1759427); a canceled run nothing replaced still is
    index = rp.parse_runs({"workflow_runs": [run("Nexus index", n=6), run("Nexus index", conclusion="cancelled", n=5),
                                             run(n=4)]})
    assert rp.build_state(index) == "passed" and rp.superseded(index[1], index)
    assert not rp.superseded(index[1], [index[1], index[2]]) and rp.build_state([index[1], index[2]]) == "failed"
    before = {r.url: r for r in runs}
    assert rp.just_finished(before, [latest[0], *done]) == done              # only what was seen running
    assert rp.just_finished({}, done) == []                                   # finished before the first look


def job(name, status="completed", conclusion="success", steps=(), n=1):
    return {"name": name, "status": status, "conclusion": conclusion if status == "completed" else None,
            "html_url": f"https://github.invalid/jobs/{n}",
            "steps": [{"name": s, "status": st, "conclusion": c} for s, st, c in steps]}


def test_jobs_and_the_step_each_is_at():
    jobs = rp.parse_jobs({"jobs": [
        job("lint"),
        job("pytest (core)", "in_progress", steps=[("Set up", "completed", "success"),
                                                   ("Run tests", "in_progress", None), ("Post", "queued", None)], n=2),
        job("pytest (tools)", conclusion="failure", steps=[("Set up", "completed", "success"),
                                                           ("Run tests", "completed", "failure"),
                                                           ("Post", "completed", "skipped")], n=3),
        job("build", "in_progress", steps=[("Set up", "completed", "success"), ("Build", "queued", None)], n=4),
        "not a job"]})
    assert [(j.name, j.step, j.step_number, j.steps) for j in jobs] == [
        ("lint", "", 0, 0), ("pytest (core)", "Run tests", 2, 3), ("pytest (tools)", "Run tests", 2, 3),
        ("build", "Build", 2, 2)]                                             # between two steps: the next one
    assert jobs[2].outcome == "failure" and jobs[1].outcome == "in progress" and jobs[0].passed
    assert rp.parse_jobs({"message": "Not Found"}) == []
    data = run(status="in_progress", n=7)
    data.update(jobs_url="https://api.github.invalid/runs/7/jobs", run_started_at="2026-10-28T09:00:00Z")
    ci, nexus = rp.parse_runs({"workflow_runs": [data, run("Nexus CI", n=8)]})
    assert ci.jobs_url.endswith("/runs/7/jobs") and nexus.jobs_url == "" and nexus.started == 0.0
    now = ci.started + 134
    by_url = {ci.url: jobs}
    assert rp.run_line(ci, jobs, now) == ("CI on main: 2 of 4 jobs done · 1 failed · pytest (core): Run tests (2/3) "
                                          "· build: Build (2/2) · 2:14")
    assert rp.run_line(ci, None, now) == "CI on main: in progress · 2:14"     # its jobs not read: the run only
    assert rp.ticker_line([nexus, ci], by_url, now).startswith("CI on main")  # the running one first
    assert rp.ticker_line([nexus, ci], by_url, now).endswith("   |   Nexus CI on main: passed")
    failed = replace(ci, status="completed", conclusion="failure")
    assert rp.run_line(failed, jobs, now) == "CI on main: failure in pytest (tools), step Run tests"
    assert rp.run_line(failed, None, now) == "CI on main: failure"
    assert rp.ticker_target([nexus, ci], by_url) == "https://github.invalid/jobs/2"     # the job that runs
    assert rp.ticker_target([nexus, failed], {failed.url: jobs[:1] + jobs[2:3]}) == "https://github.invalid/jobs/3"
    assert rp.ticker_target([nexus, failed], {}) == failed.url and rp.ticker_target([nexus], {}) == nexus.url
    assert rp.ticker_target([], {}) == ""
    details = rp.ticker_details([nexus, ci], by_url, now)
    assert details.startswith("abc1234 Fix it\n\nCI on main: in progress, 2:14\n    lint: passed\n")
    assert "    pytest (core): in progress, step 2 of 3: Run tests" in details
    assert "    pytest (tools): failure, step 2 of 3: Run tests" in details and details.endswith("Nexus CI on main: passed")
    assert rp.elapsed(3723) == "1:02:03" and rp.elapsed(-5) == "0:00" and rp.epoch(None) == 0.0


def test_window_ticker_shows_the_jobs_of_the_runs(repo, tmp_path):
    pytest.importorskip("PyQt6.QtWidgets")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    asked = []

    def jobs_source(url, etag):
        asked.append((url, etag))
        return (rp.parse_jobs({"jobs": [job("pytest (core)", "in_progress",
                                            steps=[("Run tests", "in_progress", None)])]}), "j1", None)

    w = main_window.ReleaseWindow(repo, status_source=None, launch=launched.append,
                                  runs_source=lambda etag, head="": (None, etag), notify=lambda *a: None, claude_source=None,
                                  jobs_source=jobs_source)
    ticker = w.ticker
    assert ticker.isHidden()                                                   # no runs seen yet
    going = run(status="in_progress", n=2)
    going["jobs_url"] = "https://api.github.invalid/runs/2/jobs"
    w.build.checked((rp.parse_runs({"workflow_runs": [going, run(n=1)]}), "e1"))
    assert not ticker.isHidden() and asked == []                               # not signed in: the runs only
    assert ticker.line == "CI on main: in progress   |   CI on main: passed"
    assert "gh auth login" in ticker.toolTip() and ticker.clock.isActive()
    assert main_window.BLUE in ticker.dot.styleSheet()
    w.build.checked((None, "e1", rp.RateInfo(5000, 4900, 1_900_000_000, signed_in=True)))
    ticker.checker.stop(5000)                                                  # the worker: run it here instead
    ticker.fetched(ticker._fetch([(r.url, r.jobs_url, "", r.done) for r in ticker.wanted()]))
    assert asked[-1] == ("https://api.github.invalid/runs/2/jobs", "")
    assert ticker.line.startswith("CI on main: 0 of 1 jobs done · pytest (core): Run tests (1/1)")
    assert ticker.etags == {going["html_url"]: "j1"} and ticker.timer.isActive()
    assert ticker.target() == "https://github.invalid/jobs/1" and "gh auth login" not in ticker.toolTip()
    done = dict(going, status="completed", conclusion="success")
    w.build.checked((rp.parse_runs({"workflow_runs": [done, run(n=1)]}), "e2"))
    ticker.checker.stop(5000)
    assert ticker.wanted() == [] and not ticker.clock.isActive()               # all passed: nothing more to read
    assert ticker.line == "CI on main: passed   |   CI on main: passed" and main_window.GREEN in ticker.dot.styleSheet()
    # The whole line stays visible: it wraps instead of being cut off (owner, 01-11-2026).
    assert ticker.text.text() == ticker.line and ticker.text.wordWrap()
    short = ticker.text.heightForWidth(560)
    ticker.text.setText("A line far too long for one line " * 12)
    assert ticker.hasHeightForWidth() and ticker.text.heightForWidth(560) > short * 2
    w.close()
    assert not ticker.timer.isActive()


def test_window_ticker_runs_a_failed_run_again(repo, tmp_path):
    """Run again in the ticker (owner, 06-11-2026): shown while a run of the newest push failed, it starts that run's
    failed jobs again; a run canceled for a later one of its workflow does not count."""
    pytest.importorskip("PyQt6.QtWidgets")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import flow, main_window
    w = main_window.ReleaseWindow(repo, status_source=None, launch=launched.append,
                                  runs_source=lambda etag, head="": (None, etag), notify=lambda *a: None,
                                  claude_source=None, jobs_source=None)
    ticker, ran = w.ticker, []
    ticker.on_rerun = ran.append
    w.build.checked((rp.parse_runs({"workflow_runs": [run(n=12), run("CI Nexus", n=11)]}), "e1"))
    assert ticker.rerun_button.isHidden()                                      # all passed
    index = [run("Nexus index", n=14), run("Nexus index", conclusion="cancelled", n=13)]
    failed = dict(run(conclusion="failure", n=12), html_url="https://github.com/o/r/actions/runs/12")
    w.build.checked((rp.parse_runs({"workflow_runs": [*index, failed, run("CI Nexus", n=11)]}), "e2"))
    assert not ticker.rerun_button.isHidden() and "CI on main" in ticker.rerun_button.toolTip()
    assert [r.url for r in flow.failed_runs(ticker.runs)] == [failed["html_url"]]
    ticker.rerun_button.click()
    assert ran == ["gh run rerun 12 --failed"]
    w.close()

def test_fetch_runs_sends_the_etag(monkeypatch):
    import io
    import urllib.error
    sent = []

    rate = {"X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "57", "X-RateLimit-Reset": "1900000000"}

    class Response(io.BytesIO):
        headers = {"ETag": 'W/"new"', **rate}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        sent.append(request.get_header("If-none-match"))
        if sent[-1] == 'W/"new"':
            headers = dict(rate, **{"X-RateLimit-Remaining": "56"})
            raise urllib.error.HTTPError(request.full_url, 304, "Not Modified", headers, None)
        return Response(json.dumps({"workflow_runs": [run()]}).encode())

    monkeypatch.setattr(rp.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(rp, "_token", "")                                      # no login: never the real gh
    runs, etag, limit = rp.fetch_runs()
    assert [r.label for r in runs] == ["CI on main"] and etag == 'W/"new"' and sent == [None]
    assert limit == rp.RateInfo(60, 57, 1_900_000_000, signed_in=False)
    unchanged = rp.fetch_runs(etag)                                           # unchanged: 304, the limit still read
    assert unchanged[:2] == (None, 'W/"new"') and unchanged[2].remaining == 56
    assert "57 of 60 left until" in limit.text and limit.text.endswith("not signed in")
    assert rp.RateInfo.from_headers({}, False) is None


def test_fetch_runs_follows_a_full_page_with_the_rest_of_heads_runs(monkeypatch):
    """A release of 26 apps started 26 Release runs and as many index runs on its commit, so the page of 30 ended on
    that commit and the CI runs under them were never seen: the CI passes step never lit (owner, 04-11-2026)."""
    import io
    import urllib.error
    import urllib.parse
    sent: list[tuple[str, str | None]] = []
    page = [run("Release", f"app{n}-v1.0.0", n=100 + n, sha="head") for n in range(rp.RUNS_PAGE)]
    head = [*page, run(n=2, sha="head"), run("CI Nexus", n=1, sha="head")]
    answers = {"": page, "head": head}
    etags = {"": 'W/"page"', "head": 'W/"head"'}

    class Response(io.BytesIO):
        def __init__(self, body: bytes, etag: str):
            super().__init__(body)
            self.headers = {"ETag": etag}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
        sha = query.get("head_sha", [""])[0]
        sent.append((sha, request.get_header("If-none-match")))
        if sent[-1][1] == etags[sha]:
            raise urllib.error.HTTPError(request.full_url, 304, "Not Modified", {}, None)
        return Response(json.dumps({"workflow_runs": answers[sha]}).encode(), etags[sha])

    monkeypatch.setattr(rp.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(rp, "_token", "")
    monkeypatch.setattr(rp, "_pages", {})
    runs, etag, _limit = rp.fetch_runs(sha="head")
    assert len(runs) == rp.RUNS_PAGE + 2 and [r.workflow for r in runs[-2:]] == ["CI", "CI Nexus"]
    assert sent == [("", None), ("head", None)] and etag == 'W/"page"'
    assert flow.ci_state(runs, "head") == "passed"
    # Nothing changed on either page: None, as before, and the second page's ETag made its request free too.
    assert rp.fetch_runs(etag, sha="head")[0] is None and sent[2:] == [("", 'W/"page"'), ("head", 'W/"head"')]
    # A CI run under the page finished (Run CI again): the page is unchanged, the runs of HEAD are not.
    head[-2] = run(n=2, sha="head", conclusion="failure")
    etags["head"] = 'W/"head2"'
    runs, etag, _limit = rp.fetch_runs(etag, sha="head")
    assert runs is not None and flow.ci_state(runs, "head") == "failed" and etag == 'W/"page"'
    # Without HEAD, or when the page does not end on HEAD, the one request as before.
    answers[""] = [*page[:-1], run("Release", "app-v0.9.0", n=50, sha="older")]
    etags[""] = 'W/"page2"'
    runs, _etag, _limit = rp.fetch_runs(etag, sha="head")
    assert len(runs) == rp.RUNS_PAGE and sent[-1] == ("", 'W/"page"')
    assert len(rp.fetch_runs()[0]) == rp.RUNS_PAGE


def test_github_token_from_the_environment_or_a_gh_login(monkeypatch):
    monkeypatch.setattr(rp, "_token", None)
    monkeypatch.setenv("GH_TOKEN", "from-env")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert rp.github_token(run=lambda *a, **k: pytest.fail("gh asked although a token was set")) == "from-env"
    monkeypatch.setattr(rp, "_token", None)
    monkeypatch.delenv("GH_TOKEN")
    monkeypatch.setattr(rp.shutil, "which", lambda name: "/usr/bin/gh")
    asked = []

    def gh(argv, **kw):
        asked.append(argv)
        return subprocess.CompletedProcess(argv, 0, "gho_login\n", "")
    assert rp.github_token(run=gh) == "gho_login" and asked == [["/usr/bin/gh", "auth", "token"]]
    assert rp.github_token(run=gh) == "gho_login" and len(asked) == 1         # asked once per run
    monkeypatch.setattr(rp, "_token", None)
    assert rp.github_token(run=lambda argv, **kw: subprocess.CompletedProcess(argv, 1, "", "not logged in")) == ""


def test_token_warning():
    assert rp.token_warning("") == rp.token_warning("github_pat_abc") == ""
    assert "every repository" in rp.token_warning("gho_abc") and "every repository" in rp.token_warning("ghp_abc")


def test_github_token_asked_once_while_checks_overlap(monkeypatch):
    import threading
    import time
    monkeypatch.setattr(rp, "_token", None)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(rp.shutil, "which", lambda name: "/usr/bin/gh")
    asked = []

    def slow_gh(argv, **kw):
        asked.append(argv)
        time.sleep(0.3)                                                       # gh still answering ...
        return subprocess.CompletedProcess(argv, 0, "gho_login\n", "")
    got = []
    first = threading.Thread(target=lambda: got.append(rp.github_token(run=slow_gh)))
    first.start()
    time.sleep(0.05)
    got.append(rp.github_token(run=slow_gh))                                  # ... when a second check asks
    first.join()
    assert got == ["gho_login", "gho_login"] and len(asked) == 1


def test_fetch_runs_signs_in_and_reports_the_limit(monkeypatch):
    import urllib.error
    from email.message import Message
    sent = []

    def limited(reset):
        headers = Message()
        headers["X-RateLimit-Remaining"] = "0"
        headers["X-RateLimit-Reset"] = str(reset)
        return headers

    def urlopen(request, timeout):
        sent.append(request.get_header("Authorization"))
        if sent[-1] == "Bearer expired":
            raise urllib.error.HTTPError(request.full_url, 401, "Bad credentials", Message(), None)
        raise urllib.error.HTTPError(request.full_url, 403, "rate limit exceeded", limited(1_900_000_000), None)

    monkeypatch.setattr(rp.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(rp, "_token", "expired")
    with pytest.raises(rp.RateLimited) as caught:
        rp.fetch_runs()
    assert sent == ["Bearer expired", None]                                   # a refused login: on without it
    assert caught.value.reset == 1_900_000_000 and not caught.value.signed_in and rp._token == ""
    monkeypatch.setattr(rp, "_token", "gho_login")
    with pytest.raises(rp.RateLimited) as caught:
        rp.fetch_runs()
    assert sent[-1] == "Bearer gho_login" and caught.value.signed_in


def test_window_build_indicator_notifies_when_a_run_ends(repo, tmp_path):
    pytest.importorskip("PyQt6.QtWidgets")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QApplication
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    app = QApplication.instance() or QApplication([])          # noqa: F841 (kept alive for the window)
    from nexus_release_tool import main_window
    notes = []
    w = main_window.ReleaseWindow(repo, status_source=None, launch=launched.append,
                                  runs_source=lambda etag, head="": (None, etag), notify=lambda *a: notes.append(a))
    build = w.build
    assert not build.isHidden()
    build.checked((rp.parse_runs({"workflow_runs": [run(n=2), run("Release", "governor-v0.1.1", "in_progress")]}),
                   "e1"))
    assert build.state == "running" and build.value.text() == "Building" and notes == []
    assert build.caption.text() == "GitHub build" and main_window.BLUE in build.styleSheet()
    assert build.timer.interval() == main_window.BUILD_BUSY_MS
    assert build.target() == "https://github.invalid/runs/1"                  # the run still going
    assert "Release on governor-v0.1.1: in progress" in build.toolTip()
    build.checked((None, "e1"))                                               # unchanged
    assert build.state == "running" and notes == []
    build.checked((rp.parse_runs({"workflow_runs": [run(n=2), run("Release", "governor-v0.1.1",
                                                                  conclusion="failure")]}), "e2"))
    assert build.state == "failed" and build.value.text() == "Failed" and main_window.RED in build.styleSheet()
    assert notes == [("GitHub build failed", "Release on governor-v0.1.1: failure")]
    assert build.target() == "https://github.invalid/runs/1" and build.timer.interval() == main_window.BUILD_IDLE_MS
    assert build.rate.value.text() == "—" and "not known yet" in build.rate.toolTip()
    build.checked((None, "e2", rp.RateInfo(5000, 4905, 1_900_000_000, signed_in=True)))
    assert build.rate.value.text() == "4,905" and "4,905 of 5,000 left" in build.rate.toolTip()
    assert "signed in" in build.rate.toolTip() and "gh auth login" not in build.rate.toolTip()
    assert main_window.ORANGE not in build.rate.styleSheet() and main_window.RED not in build.rate.styleSheet()
    assert main_window.GREEN in build.rate.styleSheet()                    # a left edge while plenty are left
    build.checked((None, "e2", rp.RateInfo(60, 3, 1_900_000_000, signed_in=False)))
    assert main_window.ORANGE in build.rate.styleSheet() and "gh auth login" in build.rate.toolTip()
    build.checked(OSError("offline"))
    assert build.state == "unreachable" and "offline" in build.toolTip()
    import time
    build.checked(rp.RateLimited(time.time() + 1800, signed_in=False))
    assert build.state == "limited" and build.value.text() == "Limited" and "back at" in build.toolTip()
    assert "gh auth login" in build.toolTip()
    assert "0 of 60 left" in build.rate.toolTip() and main_window.RED in build.rate.styleSheet()
    assert build.timer.interval() >= 1800_000                                 # waits for the reset
    build.checked(rp.RateLimited(time.time() + 60, signed_in=True))
    assert "gh auth login" not in build.toolTip() and build.timer.interval() == main_window.BUILD_IDLE_MS
    w.close()
    assert main_window.ReleaseWindow(repo, status_source=None, runs_source=None).build.isHidden()


def test_title_names_the_checkouts_commit_and_date(window, repo):
    """No version: the tool is never released, so its header names the checkout's commit and its time."""
    from PyQt6.QtWidgets import QLabel
    head = subprocess.run(["git", "log", "-1", "--format=%h %ct"], cwd=repo, capture_output=True, text=True).stdout.split()
    when = rp.amsterdam_now(datetime.datetime.fromtimestamp(int(head[1]), datetime.timezone.utc))
    stamp = f"{head[0]} · {when:%d-%m-%Y %H:%M}"
    title = next(label.text() for label in window.findChildren(QLabel)
                 if label.text().startswith("Nexus Release Tool for PS5"))
    assert f">{stamp}</span>" in title and ">v" not in title


def test_window_withdraws(window, repo, monkeypatch):
    page = window.withdraw_page
    assert [page.app_box.itemText(i) for i in range(page.app_box.count())] == ["beta-v0.1.0"]
    assert page.state.text() == "Not withdrawn." and not page.back_button.isEnabled()
    warned = []
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a[2]))
    page.withdraw_button.click()                                    # no reason: refused
    assert warned and rp.withdrawn_reason(repo, "beta") == ""
    page.reason_edit.setText("Security: a key in the log.")
    page.withdraw_button.click()
    assert rp.withdrawn_reason(repo, "beta") == "Security: a key in the log."
    assert page.state.text() == "Withdrawn: Security: a key in the log." and page.back_button.isEnabled()
    assert "gh release edit beta-v0.1.0 --prerelease" in page.output.toPlainText()
    page.back_button.click()
    assert rp.withdrawn_reason(repo, "beta") == "" and page.state.text() == "Not withdrawn."


# --- Semantic versioning from the CHANGELOG entries -------------------------------------------------------------

def entry(path: Path, body: str, stamp: str = "15-10-2026 23:00:00") -> None:
    path.write_bytes(f"Changelog: {stamp}\n\n{body}\n\n".encode() + path.read_bytes())


def test_the_kind_of_change_sets_the_level():
    assert rp.suggested_level([]) == ("patch", "no CHANGELOG entries")
    assert rp.suggested_level(["Fixed. A crash.", "Added. A button."]) == ("minor", "1 Added, 1 Fixed")
    assert rp.suggested_level(["Breaking. The --old option went.", "Added. x"])[0] == "major"
    level, why = rp.suggested_level(["A change from before the rule.", "Fixed. y"])
    assert level == "patch" and "1 without Breaking./Added./Fixed. (counted as a fix)" in why
    assert rp.change_word("Added.") == "Added." and rp.change_word("Addedx. no") == ""


def test_an_added_entry_since_the_tag_asks_for_a_minor_release(repo):
    alpha = repo / "apps/alpha/CHANGELOG"
    entry(alpha, "Fixed. The window opens on the right screen.")
    assert rp.version_choices(repo, unit(repo, "alpha"))[0][:3] == ["0.1.1", "0.2.0", "1.0.0"]
    entry(alpha, "Added. A Check before push button.")
    entry(alpha, "Release 0.1.1.")                              # the tool's own entries count for nothing
    choices, why = rp.version_choices(repo, unit(repo, "alpha"))
    assert choices[0] == "0.2.0" and why == "minor: 1 Added, 1 Fixed since alpha-v0.1.0"
    entry(alpha, "Breaking. Its settings from 0.1 are not read any more.")
    assert rp.version_choices(repo, unit(repo, "alpha"))[0][0] == "1.0.0"


def test_counted_from_the_last_tag_not_a_bump_already_made(repo):
    """VERSION bumped to 0.1.1 (not tagged) and then a feature: 0.2.0 from alpha-v0.1.0 comes first. A VERSION bumped
    further already comes first itself."""
    alpha = unit(repo, "alpha")
    rp.set_version(repo, alpha, "0.1.1")
    entry(repo / "apps/alpha/CHANGELOG", "Added. x")
    assert rp.version_choices(repo, unit(repo, "alpha"))[0][:2] == ["0.2.0", "0.1.1"]
    rp.set_version(repo, unit(repo, "alpha"), "0.3.0")
    assert rp.version_choices(repo, unit(repo, "alpha"))[0][0] == "0.3.0"


def test_a_core_change_counts_for_the_apps_that_carry_it(repo):
    entry(repo / "core/CHANGELOG", "Added. A widget.")
    write(repo / "core/bazzite_console_core/widgets.py", "x = 1\n")
    assert rp.version_choices(repo, unit(repo, "alpha"))[0][0] == "0.2.0"     # alpha bundles core
    core = unit(repo, "core")
    assert rp.version_choices(repo, core)[0][0] == "0.2.0"


def test_a_first_release_is_offered_as_it_is(repo):
    choices, why = rp.version_choices(repo, unit(repo, "beta"))
    assert choices[0] == "0.1.0" and why == "the first release"
    entry(repo / "portal/CHANGELOG", "Added. The first portal.")          # a portal never tagged: the same
    assert rp.portal_suggestion(repo, unit(repo, "portal")) == (unit(repo, "portal").version, "the first release")


def test_the_portal_counts_apps_toml_since_its_last_tag(repo):
    """An app added to apps.toml and pushed before the portal release: the minimum (as check_manifest) and the
    suggestion both count it against the last portal tag, not the last push."""
    sh(repo, "tag", "portal-v0.1.0")
    write(repo / "portal/apps.toml", (repo / "portal/apps.toml").read_text() + card("gamma"))
    sh(repo, "commit", "-qam", "gamma")
    sh(repo, "branch", "-f", "pushed")
    assert rp.portal_minimum(repo, "pushed", "0.1.0") == ("0.2.0", "gamma was added")
    assert rp.portal_suggestion(repo, unit(repo, "portal")) == (
        "0.2.0", "minor: apps.toml changed since portal-v0.1.0 (gamma was added)")
    entry(repo / "portal/CHANGELOG", "Breaking. Reads only apps.toml format 2.")
    assert rp.portal_suggestion(repo, unit(repo, "portal"))[0] == "1.0.0"


def test_the_suites_names_and_icons(tmp_path):
    """The suite by its portal's name, with its portal's icon; the folder's name and no icon without them."""
    assert rp.suite_name(rp.CHECKOUT) == "Bazzite Console Suite"
    assert rp.suite_icon(rp.CHECKOUT).name == "bazzite-console-suite.webp"
    bare = tmp_path / "bare"
    (bare / "portal").mkdir(parents=True)
    assert rp.suite_name(bare) == "bare" and rp.suite_icon(bare) is None


def test_the_git_questions_are_asked_once_or_side_by_side(repo, monkeypatch):
    """load_units() reads the tags and the untracked files once, and asks each unit's two questions side by side; the
    window's step 1 reads its CHANGELOGs at the tags with one git cat-file (owner, 27-10-2026: the window was slow,
    some 20 ms per git process). The answers are those of one process per question."""
    calls = []
    real = rp.subprocess.run

    def run(args, *a, **k):
        calls.append(args[1])
        return real(args, *a, **k)
    monkeypatch.setattr(rp.subprocess, "run", run)
    units = rp.load_units(repo)
    assert calls.count("tag") == 1 and calls.count("for-each-ref") == 1 and calls.count("merge-base") == 1   # History: once
    untagged = [u.key for u in units if not u.last_tag]
    assert calls.count("rev-list") == len(untagged) and "beta" in untagged   # a never-tagged unit keeps its own count
    for unit in units:
        if unit.kind == "core":
            continue
        tags = rp.tags_of(repo, unit.key, unit.prefix)                  # one git process, as before
        assert unit.last_tag == (tags[-1] if tags else None), unit.key
        if unit.last_tag:
            assert unit.changed == rp.changed_since(repo, unit.last_tag,
                                                    rp.shipped_sources(repo, unit.key, unit.path)), unit.key
    assert [vars(u) for u in rp.load_units(repo)] == [vars(u) for u in units]       # the same every time
    shown = [u for u in units if u.kind != "portal"]
    calls.clear()
    blobs = rp.read_blobs(repo, rp.changelog_specs(shown))
    assert calls == ["cat-file"] and "alpha-v0.1.0:apps/alpha/CHANGELOG" in blobs
    assert [rp.version_choices(repo, u, blobs) for u in shown] == [rp.version_choices(repo, u) for u in shown]


def test_read_blobs_reads_each_file_or_none(repo):
    write(repo / "apps/alpha/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nFirst. Café × 2.\n")
    sh(repo, "commit", "-qam", "accents")
    found = rp.read_blobs(repo, ["HEAD:apps/alpha/CHANGELOG", "HEAD:no/such/file", "HEAD:apps/alpha/VERSION"])
    assert found == {"HEAD:apps/alpha/CHANGELOG": "Changelog: 01-01-2026 00:00:00\n\nFirst. Café × 2.\n",
                     "HEAD:no/such/file": None, "HEAD:apps/alpha/VERSION": "0.1.0\n"}
    assert rp.read_blobs(repo, []) == {}


def test_git_answers_are_utf8_on_every_system(repo):
    """git() reads git's output as UTF-8, whatever the locale: another encoding garbled a CHANGELOG's é and ×, so
    step 1 counted every entry of such a CHANGELOG as new since the tag."""
    write(repo / "apps/beta/CHANGELOG", "Changelog: 01-01-2026 00:00:00\n\nFixed. Naïve × 3.\n")
    sh(repo, "commit", "-qam", "accents")
    sh(repo, "tag", "beta-v0.1.0")
    assert rp.git(repo, "show", "beta-v0.1.0:apps/beta/CHANGELOG").endswith("Fixed. Naïve × 3.\n")
    beta = next(u for u in rp.load_units(repo) if u.key == "beta")
    assert rp.new_entries(repo, beta) == []                             # nothing new since its tag


def test_git_takes_no_optional_locks(repo, monkeypatch):
    """git() runs with GIT_OPTIONAL_LOCKS=0: the build pill's poll runs git status, which took .git/index.lock to
    refresh the index, and a poll during the Commands tab's git add -A or git commit made that fail."""
    seen = []
    real = rp.subprocess.run

    def run(*args, **kwargs):
        seen.append(kwargs.get("env") or {})
        return real(*args, **kwargs)
    monkeypatch.setattr(rp.subprocess, "run", run)
    assert rp.git(repo, "status", "--porcelain") is not None
    assert seen and seen[0].get("GIT_OPTIONAL_LOCKS") == "0" and "PATH" in seen[0]


def test_push_brings_in_what_github_has_first():
    """The release's Pin ... commit is on main after every release (owner, 31-10-2026: the push failed): git pull
    --rebase runs before the push, and before CI's jobs here."""
    assert rp.pull_command() == "git pull --rebase --autostash"
    assert rp.push_command() == f"git pull --rebase --autostash && {rp.CI_LOCAL} && git push"
