# SPDX-License-Identifier: GPL-3.0-or-later
"""A release (owner, 30-10-2026): the one action of the Nexus Release Tool, Start new release, and what follows it.
No Qt here; the page is release_page.py.

The release holds the apps that need a release, the portal, and core when it changed since its last version. The
owner sees each version first and may type another (owner: "keep the override"); the portal's version is worked out
when Start writes it (at least what the app releases need, check_manifest.py's rule), unless one is typed. Start
writes the release, as steps 1 and 2 would (the versions and their copies, the "Release x.y.z." entries, the new tags
in apps.toml with their sha256 left for the workflow, the portal's version and its entry), then one command commits
it, pushes it and starts release.yml on that commit. The workflow builds, publishes and pins; the portal ends as a
draft. The device test installs that draft on this device (check-release.sh draft on a console); Publish makes it a
release, which makes the portal tag and GitHub's Latest release. A run that failed is started again from where it
stopped (gh run rerun --failed); one that should not go on is stopped (gh run cancel)."""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from . import plan as rp

AUTO = "auto"                           # the portal's version, worked out when Start writes the release
RELEASE_WORKFLOW = "release.yml"        # the release workflow, started on the release commit (workflow_dispatch)
WORKFLOW_NAME = "Release"               # its name on GitHub, as the runs list it
_RUN_ID = re.compile(r"/actions/runs/(\d+)")


def releases_on_github(root: Path) -> bool:
    """Whether the suite's release runs on GitHub: its release workflow (release.yml) can be started on a release
    commit (workflow_dispatch)."""
    workflow = root / ".github" / "workflows" / RELEASE_WORKFLOW
    text = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    return "workflow_dispatch:" in text or "workflow_call:" in text


@dataclass
class Pick:
    """One row of the release: an app, the portal or core, with the versions offered (the first one is the
    suggestion), why, and what the owner chose."""
    unit: rp.Unit
    choices: list[str]
    why: str
    version: str = ""                   # the chosen one; "" or AUTO: the suggestion
    notes: str = ""

    @property
    def label(self) -> str:
        return self.unit.key


def picks(root: Path) -> list[Pick]:
    """What a release would hold now: each portal app that needs a release and the portal; core when it changed
    since its last version and an app on the release bundles that change."""
    found: list[Pick] = []
    units = rp.load_units(root)
    if releases_on_github(root):
        blobs = rp.read_blobs(root, rp.changelog_specs(units))
        apps = [u for u in units if u.kind == "app" and not u.standalone and u.needs_release]
        for unit in apps:
            choices, why = rp.version_choices(root, unit, blobs)
            found.append(Pick(unit, choices, why, choices[0]))
        portal = next(u for u in units if u.kind == "portal")
        if apps or portal.needs_release:
            found.append(Pick(portal, [AUTO, *rp.next_versions(portal.version).values()],
                              "worked out at Start: at least what its app releases ask (check_manifest.py) and its "
                              "own CHANGELOG entries", AUTO))
    core = next((u for u in units if u.kind == "core" and not u.current and u.in_apps), None)
    if core is not None:
        choices, why = rp.version_choices(root, core)
        found.append(Pick(core, choices, why, choices[0]))
    return found


def problems(chosen: list[Pick]) -> list[str]:
    """What is wrong with the versions typed, before anything is written."""
    found = []
    for pick in chosen:
        version = pick.version.strip() or AUTO
        if version == AUTO and pick.unit.kind == "portal":
            continue
        released = pick.unit.released or pick.unit.kind == "core"
        if msg := rp.check_new_version(pick.unit.version, version, released):
            found.append(f"{pick.label}: {msg}")
    return found


def higher(a: str, b: str) -> str:
    return a if rp.version_tuple(a) >= rp.version_tuple(b) else b


def write(root: Path, chosen: list[Pick], base: str = "origin/main") -> tuple[list[str], list[str]]:
    """Writes the release: the apps (version, copies, entry, the new tag in apps.toml), then the portal, then core.
    Returns the log and the release's tags (the apps' and the portal's)."""
    log: list[str] = []
    tags: list[str] = []
    for pick in (p for p in chosen if p.unit.kind == "app"):
        unit, new = pick.unit, pick.version.strip() or pick.choices[0]
        if new != unit.version:
            rp.set_version(root, unit, new)
        text = rp.release_text(new, pick.notes)
        rp.add_changelog_entry(root, unit, text, base=base)
        rp.pin(root, unit, "")                      # the new tag; its sha256 is the workflow's
        tags.append(unit.tag)
        log.append(f"{unit.key}: {new}, \"{text}\", apps.toml pins {unit.tag}")
    portal_pick = next((p for p in chosen if p.unit.kind == "portal"), None)
    if portal_pick is not None:
        portal = portal_pick.unit
        typed = portal_pick.version.strip()
        suggested, why = rp.portal_suggestion(root, portal)
        minimum, need = rp.portal_minimum(root, base, portal.version)
        new = typed if typed and typed != AUTO else suggested
        if minimum and rp.version_tuple(minimum) > rp.version_tuple(new):
            log.append(f"portal: {new} is less than CI asks ({need}): {minimum}")
            new = minimum
        if new != portal.version:
            rp.set_version(root, portal, new)
        text = rp.portal_text(new, rp.changed_pins(root, base), portal_pick.notes, rp.changed_withdrawals(root, base))
        rp.add_changelog_entry(root, portal, text, base=base)
        tags.append(portal.tag)
        log.append(f"portal: {new} ({why}), \"{text}\"")
    for pick in (p for p in chosen if p.unit.kind == "core"):
        new = pick.version.strip() or pick.choices[0]
        if new != pick.unit.version:
            rp.set_version(root, pick.unit, new)
        text = f"Version {new}." + (f" {pick.notes.strip()}" if pick.notes.strip() else "")
        rp.add_changelog_entry(root, pick.unit, text, base=base)
        log.append(f"core: {new}, \"{text}\"")
    return log, tags


# The wiki's Portal Tour keeps up with the portal (owner, 15-11-2026): while the portal's window or tiles changed since
# it was recorded, an orange banner offers to record it, and the release waits. The owner records it.
RECORD_VIDEO = "tools/record-tour.sh --wiki"
VIDEO_STALE = ("The portal changed since the wiki's Portal Tour was recorded (its window or its tiles): record a new "
               "video before the release.")


def video_reason(root: Path, python: str = sys.executable) -> str:
    """Why the portal video must be recorded first ("" when it is current, or the suite has no tour): what
    tools/portal_tour.py --check says. A check that cannot run holds the release too."""
    script = root / "tools" / "portal_tour.py"
    if not script.is_file():
        return ""
    try:
        done = subprocess.run([python, str(script), "--check"], cwd=root, capture_output=True, text=True,
                              timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"The portal video check could not run ({exc}): the release waits until it does."
    return "" if done.returncode == 0 else VIDEO_STALE


def ready(root: Path, base: str = "origin/main") -> list[str]:
    """Why Start new release cannot go yet ([] when it can): the working tree must be clean and HEAD must be what
    was pushed last, so the release commit holds the release and nothing else."""
    reasons = []
    dirty = rp.git(root, "status", "--porcelain")
    if dirty is None:
        return ["This folder is not a git checkout."]
    if dirty.strip():
        reasons.append("The working tree has changes: commit and push them first, or put them away.")
    head = (rp.git(root, "rev-parse", "HEAD") or "").strip()
    pushed = (rp.git(root, "rev-parse", "--verify", "-q", base) or "").strip()
    if not pushed:
        reasons.append(f"No {base} here: git fetch first.")
    elif head != pushed:
        ahead = int((rp.git(root, "rev-list", "--count", f"{base}..HEAD") or "0").strip() or 0)
        behind = rp.behind(root, base)
        reasons.append(f"HEAD has {ahead} commit{'s' if ahead != 1 else ''} not pushed: push them first."
                       if ahead else f"{base} has {behind} commit{'s' if behind != 1 else ''} this checkout does "
                       "not: git pull first.")
    return reasons


_CLOBBER = re.compile(r"^\s*!\s*\[rejected\]\s+(\S+)\s+->\s+\S+\s+\(would clobber existing tag\)", re.M)
WAITS = "The release reads the last release of each part from the tags, so it waits until they can be fetched."


@dataclass(frozen=True)
class FetchFailed:
    """git fetch --tags failed: git's own words, and the tags here that point to another commit than GitHub's, which
    git refuses to move ("would clobber existing tag"; owner, 03-11-2026: a tag made here on the commit before the
    one the release was published from, and Start only said the fetch failed)."""
    error: str
    clobbered: tuple[str, ...] = ()

    def explain(self) -> str:
        """The message for the window: why, and for a clobbered tag what to do (GitHub's tag is the published one)."""
        text = "git fetch --tags failed:\n\n" + (self.error.strip() or "(git said nothing)")
        if self.clobbered:
            one = len(self.clobbered) == 1
            text += (f"\n\nThe tag{'' if one else 's'} {', '.join(self.clobbered)} here point{'s' if one else ''} to "
                     f"another commit than GitHub's. GitHub's is the one the release was published from, so drop "
                     f"{'this one' if one else 'these'} and fetch again:\n\n"
                     + "\n".join(f"git tag -d {tag}" for tag in self.clobbered) + "\ngit fetch --tags")
        return text + "\n\n" + WAITS


def fetch_tags(root: Path) -> list[str] | FetchFailed:
    """git fetch --tags from origin: the tags it brought ([] none, or no origin), FetchFailed when it failed (offline,
    or a tag here that git will not move). The release reads each part's last release from this checkout's tags,
    and a portal is tagged on GitHub when it is published (owner, 31-10-2026: a portal tag not fetched, so the
    next release kept its version and CI refused it)."""
    if "origin" not in (rp.git(root, "remote") or "").split():
        return []
    before = set((rp.git(root, "tag", "--list") or "").split())
    result = rp.git_run(root, "fetch", "--tags", "origin")
    if result.returncode != 0:
        return FetchFailed(result.stderr, tuple(_CLOBBER.findall(result.stderr)))
    return sorted(set((rp.git(root, "tag", "--list") or "").split()) - before)


def catch_up(root: Path, base: str = "origin/main") -> int | None:
    """What *base* has that HEAD lacks (fetched already) brought in under this checkout's commits (git rebase, as git
    pull --rebase does) before Start writes the release: the commits it brought (0: none), None when git could not
    (a conflict, or changes not committed)."""
    behind = rp.behind(root, base)
    if not behind:
        return 0
    if (rp.git(root, "status", "--porcelain") or "").strip():
        return None
    if rp.git(root, "rebase", "--quiet", base) is None:
        rp.git(root, "rebase", "--abort")
        return None
    return behind


def unpushed_release(root: Path, base: str = "origin/main") -> str:
    """HEAD's subject when HEAD is a release commit Start made that is not pushed yet, right on top of *base* (the
    push stopped: CI's jobs here found something, or the network); "" otherwise."""
    subject = (rp.git(root, "log", "-1", "--format=%s") or "").strip()
    parent = (rp.git(root, "rev-parse", "-q", "--verify", "HEAD^") or "").strip()
    pushed = (rp.git(root, "rev-parse", "-q", "--verify", base) or "").strip()
    return subject if subject.startswith("Release ") and pushed and parent == pushed else ""


def commit_message(tags: list[str]) -> str:
    return f"Release {', '.join(tags)}"


def push_and_start_command() -> str:
    """The release commit pushed and release.yml started on it."""
    return (f'git push origin HEAD:main && gh workflow run {RELEASE_WORKFLOW} --ref main -f commit="$(git rev-parse '
            f'HEAD)" && echo \'Started {RELEASE_WORKFLOW} on \'"$(git rev-parse --short HEAD)"')


def start_command(message: str) -> str:
    """The one command Start runs in the command line (bash): the release commit, its push, and release.yml started
    on it."""
    return f"git commit -a -q -m {shlex.quote(message)} && {push_and_start_command()}"


def release_run(runs: list[rp.BuildRun], sha: str = "") -> rp.BuildRun | None:
    """The newest run of release.yml that Start started, on main (on *sha* when given): GitHub lists the newest
    first. A run on a tag is not one: the portal tag Publish makes starts release.yml too, on the pin commit, and
    that run ends at once (owner, 15-11-2026: taken for the release, it made the release seem not written and lit
    Start new release again)."""
    return next((r for r in runs if (r.file == RELEASE_WORKFLOW or r.workflow == WORKFLOW_NAME) and r.ref == "main"
                 and (not sha or r.sha == sha)), None)


def run_id(run: rp.BuildRun) -> str:
    found = _RUN_ID.search(run.url)
    return found[1] if found else ""


def restart_command() -> str:
    """A release whose run failed, started again on HEAD (its fix, pushed and passed CI): release.yml on that commit,
    nothing written anew; what is out already is skipped."""
    return (f'gh workflow run {RELEASE_WORKFLOW} --ref main -f commit="$(git rev-parse HEAD)" && '
            f'echo \'Started {RELEASE_WORKFLOW} on \'"$(git rev-parse --short HEAD)"')


def stop_command(run: rp.BuildRun) -> str:
    return f"gh run cancel {run_id(run)}"


def resume_command(run: rp.BuildRun) -> str:
    """Started again from where it stopped: only the jobs that failed or were canceled, and what needs them."""
    return f"gh run rerun {run_id(run)} --failed"


# --- The steps, in their order (owner, 30-10-2026: "if I open NRT I want to see exactly what has to be done in their
# logical sequence", each action a pill) ---------------------------------------------------------------------------

STEPS = (
    ("pull", "Get up to date", "Bring in what was pushed from the other machine."),
    ("commit", "Commit your changes", "Everything changed here, in one commit, after the version and manifest checks."),
    ("push", "Push them", "Your commits to GitHub: what GitHub has that this checkout lacks comes in under them first "
                          "(git pull --rebase), then CI's jobs run here (tools/ci-local.sh)."),
    ("ci", "CI passes", "GitHub's CI on that commit. Nothing to press: wait until it passed."),
    ("start", "Start new release", "Check the versions on the Contents tab, then start: it writes the release, commits and pushes "
                                   "it and starts the release on GitHub."),
    ("run", "The release on GitHub", "Builds and publishes the apps, pins them and makes the portal a draft."),
    ("test", "Device test", "Installs the draft portal on this device and starts it: test it as a user would."),
    ("publish", "Publish", "The test passed: publish the portal. Not OK leaves it a draft."),
    ("finish", "Bring in the pin commit", "The release wrote a commit Pin ... on main: pull it."),
)
KEYS = tuple(key for key, _title, _what in STEPS)


@dataclass
class Facts:
    """What the steps are read from: the checkout and the runs the window's header fetched."""
    behind: int = 0                     # commits on the last push that HEAD lacks
    dirty: bool = False                 # changes not committed
    ahead: int = 0                      # commits not pushed
    ci: str = "none"                    # CI on HEAD: none, building, passed, failed; unknown without GitHub
    unpushed: str = ""                  # a release commit Start made whose push stopped
    something: bool = False             # something to release
    run: rp.BuildRun | None = None      # the release run of this release, while it lasts
    drafts: list[str] = field(default_factory=list)     # its portals not published yet
    restart: bool = False               # HEAD is not the run's commit: a failed run starts again on HEAD, the fix
    rejected: list[str] = field(default_factory=list)   # its drafts the device test failed (Not OK), still drafts
    push_failed: str = ""               # the last Push of these commits ended badly: why (push_failure)


_CI_TOTAL = re.compile(r"^(\d+) jobs? from ci\.yml", re.M)
_CI_JOB = re.compile(r"^\s+(ok|FAIL|skip)\s+(\S+)", re.M)
CI_WAITING = "waiting until it ends"    # tools/ci-local.sh: another run goes on; this one waits for it
CI_LOGS = "~/.cache/bazzite-console-ci-local/logs"


@dataclass(frozen=True)
class LocalCI:
    """Where tools/ci-local.sh stands, read from its output so far (the Push step runs it before git push; owner,
    15-11-2026: the push seemed to hang and a failed job went unseen, while the header showed the last push as
    passed)."""
    total: int = 0                      # its jobs ("46 jobs from ci.yml"); 0 before it says
    done: int = 0                       # the jobs that ended: ok, FAIL or skip
    failed: tuple[str, ...] = ()        # the jobs that failed, by name
    waiting: bool = False               # another run goes on, this one waits

    @property
    def started(self) -> bool:
        return bool(self.total) or self.waiting

    def line(self) -> str:
        """In words, for the Push step and the header's ticker."""
        if self.waiting and not self.total:
            return "Another ci-local.sh run is going on this computer: the push waits until it ends."
        text = f"CI's jobs here, before the push: {self.done} of {self.total} done"
        return text + (f"; failed: {', '.join(self.failed)}" if self.failed else "") + "."


def local_ci(output: str) -> LocalCI:
    """tools/ci-local.sh's progress in *output* (the Push command's output so far)."""
    total = _CI_TOTAL.search(output)
    jobs = _CI_JOB.findall(output)
    return LocalCI(total=int(total[1]) if total else 0, done=len(jobs),
                   failed=tuple(name for state, name in jobs if state == "FAIL"), waiting=CI_WAITING in output)


def push_failure(output: str, code: int | None) -> str:
    """Why the Push command ended badly, for its step; "" when it went well. *code*: its exit code, None when it
    was stopped."""
    if code == 0:
        return ""
    if code is None or code == 130:
        return "The push was stopped: nothing was pushed. Push again."
    failed = local_ci(output).failed
    if failed:
        return (f"CI failed here on {', '.join(failed)}, so nothing was pushed. Its output is on the Commands tab, each "
                f"job's log in {CI_LOGS}. Fix it, Commit and Push; when it was no fault of the code (a crash that "
                "does not come again), Push again.")
    return f"The push ended with exit code {code}, so nothing was pushed: the Commands tab says why. Then Push again."


def ci_runs(runs: list[rp.BuildRun], sha: str) -> list[rp.BuildRun]:
    """The CI runs on *sha* (ci*.yml) that the release waits for."""
    return [r for r in runs if r.sha == sha and (r.file.startswith("ci") or r.workflow.startswith("CI"))]


def ci_state(runs: list[rp.BuildRun], sha: str) -> str:
    """CI on *sha* (ci_runs): building while one runs, passed when every one passed, failed when one failed; none
    before GitHub has one."""
    found = ci_runs(runs, sha)
    if not found:
        return "none"
    if any(not r.done for r in found):
        return "building"
    return "passed" if all(r.passed for r in found) else "failed"


def failed_ci(runs: list[rp.BuildRun], sha: str) -> list[rp.BuildRun]:
    """The CI runs on *sha* that ended badly: what Run CI again starts again."""
    return [r for r in ci_runs(runs, sha) if r.done and not r.passed]


def failed_runs(runs: list[rp.BuildRun]) -> list[rp.BuildRun]:
    """The runs of *runs* that ended badly, not counting one canceled for a later run of its workflow: what the
    ticker's Run again starts again (owner, 06-11-2026)."""
    return [r for r in runs if r.done and not r.passed and not rp.superseded(r, runs)]


def not_asked(runs: list[rp.BuildRun], asked: set[tuple[str, int]]) -> list[rp.BuildRun]:
    """The failed *runs* no Run again was pressed for: *asked* holds each run's (url, attempt) when it was pressed.
    Until GitHub shows the next attempt, the run still reads as failed, and a second press failed with "This workflow
    is already running" (owner, 15-11-2026); a rerun that fails again is a new attempt, asked anew."""
    return [r for r in runs if (r.url, r.attempt) not in asked]


def rerun_ci_command(runs: list[rp.BuildRun]) -> str:
    """Run CI again (owner, 30-10-2026: CI failed while GitHub's Actions were degraded): each failed CI run's failed
    jobs started again (gh run rerun --failed), on the same commit."""
    return " && ".join(f"gh run rerun {run_id(r)} --failed" for r in runs)


def cycle_run(root: Path, runs: list[rp.BuildRun], rejected: Iterable[str] = ()) -> rp.BuildRun | None:
    """The newest release run, while its release lasts: HEAD is its commit, or that commit with only the release's
    Pin ... commits on top (after git pull). Once other work is committed on top, it lasts while a portal draft of
    it is neither published nor *rejected* (Not OK): the device test and Publish stay to do (owner, 04-11-2026: a fix
    pushed before a portal's device test, and NRT offered a new release instead). None after that."""
    run = release_run(runs)
    if run is None or not run.sha:
        return None
    if rp.git(root, "merge-base", "--is-ancestor", run.sha, "HEAD") is None:
        return None
    if run.done and not run.passed:
        return run                          # written and pushed, not out: it lasts, fixes on top, until a run passes
    subjects = (rp.git(root, "log", "--format=%s", f"{run.sha}..HEAD") or "").splitlines()
    if all(s.startswith("Pin ") for s in subjects if s.strip()):
        return run
    waiting = [t for t in waiting_portals(root, run.sha) if not published(root, runs, t)
               and t not in set(rejected)]
    return run if run.passed and waiting else None


def published(root: Path, runs: list[rp.BuildRun], tag: str) -> bool:
    """Whether a portal draft is published: its tag is here, or GitHub ran something on it."""
    return bool((rp.git(root, "tag", "-l", tag) or "").strip()) or any(r.ref == tag for r in runs)


def pushed_elsewhere(root: Path, runs: list[rp.BuildRun]) -> rp.BuildRun | None:
    """GitHub's newest run on main when its commit is not in this checkout: a push git has not fetched yet (owner,
    30-10-2026: the release's Pin ... commit, so step 9 stayed dark while git pull (new) was lit)."""
    pushed = next((r for r in runs if r.ref == "main"), None)
    if pushed is None or not pushed.sha or rp.git(root, "cat-file", "-e", f"{pushed.sha}^{{commit}}") is not None:
        return None
    return pushed


def current_step(facts: Facts) -> str:
    """The step to do now, its key in STEPS; "" when there is nothing to do."""
    run = facts.run
    if run is not None and run.done and not run.passed:
        # The release is written and pushed but its run failed (30-10-2026: CI failed on the release commit): its
        # fix is committed, pushed and passes CI, and the run starts again on it (restart), never a new release
        if facts.dirty:
            return "commit"
        if facts.ahead:
            return "push"
        if facts.restart and facts.ci in ("none", "building", "failed"):
            return "ci"
        return "run"
    if run is not None and not facts.dirty and not (facts.ahead and not facts.unpushed):
        if not run.passed:
            return "run"                    # running, or ended badly: Resume or Stop
        if facts.drafts:
            return "test"
        return "finish" if facts.behind else ""
    if facts.unpushed:
        return "start"                      # its push stopped: Push and start
    if facts.behind:
        return "pull"
    if facts.dirty:
        return "commit"
    if facts.ahead:
        return "push"
    if facts.ci in ("none", "building", "failed"):
        return "ci"
    return "start" if facts.something else ""


def step_states(facts: Facts) -> dict[str, str]:
    """Each step's state: done, now, failed (the step to do now, which went wrong) or later."""
    now = current_step(facts)
    if not now:                             # nothing to do: every step of a release done, or none to make
        return {key: "done" for key in KEYS}
    at = KEYS.index(now)
    states = {key: "done" if i < at else "later" for i, key in enumerate(KEYS)}
    states[now] = "failed" if (now == "ci" and facts.ci == "failed") or (now == "push" and facts.push_failed) or \
        (now == "run" and facts.run is not None and facts.run.done and not facts.run.passed) else "now"
    if now == "test" and facts.drafts and set(facts.drafts) <= set(facts.rejected):
        states["test"] = "failed"          # Not OK (owner, 30-10-2026: it seemed to do nothing): the fix comes next
    elif now == "test":
        states["publish"] = "now"          # the test is the owner's: Publish or Not OK once it is done
    if now in ("pull", "commit", "push", "ci", "start"):
        for key in ("run", "test", "publish", "finish"):
            states[key] = "later"
    run = facts.run
    if run is not None and run.done and not run.passed and now in ("commit", "push", "ci"):
        states["start"], states["run"] = "done", "failed"     # written already; its fix goes through 2 to 4 first
    return states


def dirty_paths(root: Path) -> list[str]:
    """The files the Commit step commits: changed ones and new ones."""
    changed = (rp.git(root, "diff", "--name-only", "HEAD") or "").splitlines()
    new = (rp.git(root, "ls-files", "--others", "--exclude-standard") or "").splitlines()
    return [p for p in changed + new if p.strip()]


def commit_work_command(root: Path, message: str, base: str, python: str) -> str:
    """The Commit step: everything staged (with the exec bits CI checks), then the commit after the version and
    manifest checks, as the git commit button runs them."""
    return f"{rp.add_command()} && " + rp.commit_command(message, base, False, python)


def waiting_portals(root: Path, at: str = "") -> list[str]:
    """The portal tag, as portal/VERSION says: what a device test and Publish work on after a release ran (a draft
    until published); [] when the release does not run on GitHub. *at*: as the release run's own commit has it, not
    the checkout (owner, 07-11-2026: the portal's version raised in a commit after a published release made NRT offer
    the device test of a draft no run had built, instead of Start new release)."""
    return [f"{rp.tag_prefix(root)}portal-v{portal_version(root, at)}"] if releases_on_github(root) else []


def portal_version(root: Path, at: str = "") -> str:
    """portal/VERSION in the checkout, or at commit *at* when given (the checkout's when that commit has none)."""
    if at:
        kept = rp.git(root, "show", f"{at}:portal/VERSION")
        if kept is not None:
            return kept.strip()
    return (root / "portal" / "VERSION").read_text(encoding="utf-8").strip()


def publish_command(tag: str) -> str:
    """The owner's yes after the device test: the draft becomes a release, which makes its tag (on the pin commit),
    and GitHub's Latest, so the releases page opens on the portal and not on an app. The new tag is fetched at once,
    so the step sees the release published when the command ends (owner, 06-11-2026: Publish stayed lit until
    GitHub's runs were read again, and was pressed twice), and main with it: the pin commit, which the workflow
    pushed with its token and so has no run of its own on main, lights Bring in the pin commit (owner, 15-11-2026)."""
    return f"gh release edit {tag} --draft=false --latest && git fetch origin main tag {tag}"


def device_test_line(root: Path, tag: str) -> str:
    """The check script with its draft mode, for a terminal."""
    script = str(root / rp.CHECK_SCRIPT)
    return f"{shlex.quote(script)} draft {tag}"
