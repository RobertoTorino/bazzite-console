# SPDX-License-Identifier: GPL-3.0-or-later
"""The window of the suite ticked in the first column (every suite in the checkout, tools/suites.py, with its
portal's tag; hidden while there is one). The steps and the withdrawals are the ticked suite's; GitHub is the
repository's.

Nexus release: the release as numbered steps, from your own changes to the portal published, and Contents, what it
holds (release_page.py, flow.py). Retract app: a pinned release withdrawn in apps.toml, tested on a console (Test
withdrawal); the portal that removes it from the consoles is the next release. Remove suite: what of the suite is
installed on this machine, removed (check-release.sh remove). The release by hand, a tag at a time (Release apps
with its Apply, Pin and release Portal with its Pin and Bump, Publish and Test on this board), went on
15-11-2026 (owner: its Bump wrote a portal release while the release's draft waited for its device test, which then
went out as a second release of the same apps); tools/tag-release.sh still tags one release from a terminal. Each
page's explanation sits behind a round "i" in its first row (parts.py), not in a paragraph on the page (owner,
01-11-2026).
The header is a row of pills, as the apps' status boxes (owner, 20-10-2026): Refresh, whether GitHub built the last
push (CI, Release, Manual; it notifies when a build it saw running passes or fails), how many of GitHub's API
requests are left (green, orange under a tenth, red at none), GitHub status: green while githubstatus.com reports
GitHub up, red while it reports a problem; a click opens that page, and Claude tokens today: what Claude Code on
this machine used, from its transcripts; a click opens Claude's usage page. Under the pills, the ticker says where
the newest push's workflow runs stand: the job that runs and its step (owner, 28-10-2026). The launchers that are no
release steps (the local apps and the wikis, the installer tests, the portal tour, Close issues) are Nexus
Dashboard's since 04-11-2026 (owner: the release tool is the release, the dashboard the place for working on a
suite).
The Commands tab is a command line in the checkout (command_line.py), where the steps' pills run their commands and
what each step wrote shows under a line that names it (one output tab, owner, 01-11-2026); its Commands menu offers
the commands the last step showed."""

from __future__ import annotations

import os
import shlex
import shutil
import time
from pathlib import Path

from PyQt6.QtCore import QProcess, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSystemTrayIcon,
                             QTabWidget, QVBoxLayout, QWidget)

from nexus_core.platform import launch_in_terminal
from nexus_core.theme import BLUE, GREEN, GREY, ORANGE, RED
from nexus_core.updates import UpdateChecker
from nexus_core.widgets import AppHeader, MetricBox, Pill, accent_button, same_width

from . import APP_NAME, LOGO_PATH, CHECKOUT, __version__
from . import flow
from . import plan as rp
from .command_line import CommandLine
from .parts import StepLog, info_row
from .release_page import ReleasePage
from .style import CHECK_STYLESHEET, NEXUS, TAB_TITLE_STYLESHEET

SUITE_KEY = "suite"                     # the chosen suite, in the settings
# every command line's output, a file a day (command_line.py)
COMMAND_LOG_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "nexus-release-tool" / "commands"
# A selected cell and the input field being typed in: a teal outline (Nexus's accent) with rounded corners on a
# transparent background, not the desktop's solid highlight. The line edit inside an editable combo box keeps the
# combo's frame. The tables' grid lines are the thin dimmed-silver edge of the theme, as the border around a table
# (owner, 26-10-2026: Qt's own lines were brighter and heavier).
SELECTION_STYLESHEET = (
    "QTableWidget { outline:0; selection-background-color:transparent; selection-color:palette(text); "
    f"gridline-color:{NEXUS.edge}; }}"
    "QTableWidget::item { border:2px solid transparent; border-radius:6px; }"
    f"QTableWidget::item:selected {{ background:transparent; color:palette(text); border-color:{NEXUS.accent}; }}"
    f"QLineEdit:focus {{ background:transparent; border:2px solid {NEXUS.accent}; border-radius:6px; }}"
    "QComboBox QLineEdit:focus { border:none; }"
)


class WithdrawPage(QWidget):
    """Withdrawing a release: marked in apps.toml (and, with the commands shown, on GitHub); tested on a console before
    the portal release that removes it from the consoles."""

    def __init__(self, window: "ReleaseWindow"):
        super().__init__()
        self.release_window = window
        self.app_box = QComboBox()
        self.app_box.currentIndexChanged.connect(lambda _: self._show_state())
        self.state = QLabel()
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Why: what is wrong with this release (shown on the consoles)")
        self.withdraw_button = accent_button("Retract", "Mark the pinned release withdrawn in apps.toml, with a "
                                             "CHANGELOG entry in the app")
        self.withdraw_button.clicked.connect(self.withdraw)
        self.back_button = QPushButton("Take back")
        self.back_button.setToolTip("Remove the mark again (after a test, or a mistake)")
        self.back_button.clicked.connect(self.take_back)
        # The withdrawal tested on a console with the app installed (the tab Test on this board until 15-11-2026,
        # whose other tests the release tab's Device test does)
        self.test_button = QPushButton("Test withdrawal")
        self.test_button.setToolTip("On a console with the app installed: install the portal from this checkout and "
                                    "start it (check-release.sh local); it must show the app as not available and "
                                    "remove it")
        self.test_button.clicked.connect(self.test)
        self.output = StepLog(self, "Retract app", window.step_wrote)       # shows in Commands
        row = QHBoxLayout()
        row.addWidget(QLabel("App:"))
        row.addWidget(self.app_box)
        row.addWidget(self.state, 1)
        reason_row = QHBoxLayout()
        reason_row.addWidget(self.reason_edit, 1)
        reason_row.addWidget(self.withdraw_button)
        reason_row.addWidget(self.back_button)
        reason_row.addWidget(self.test_button)
        lay = QVBoxLayout(self)
        lay.addLayout(info_row(
            "Retract marks a pinned release withdrawn, with the reason the consoles show; test it, then release the "
            "portal.",
            "For a release that must not be used any more (privacy, security, any reason):<br>"
            "<b>1.</b> Retract: apps.toml marks the pinned release withdrawn, with the reason the consoles show.<br>"
            "<b>2.</b> <b>Test withdrawal</b> on a console that has the app installed: the portal from this checkout "
            "shows it as \"App not available\" and removes it. Take back undoes the mark.<br>"
            "<b>3.</b> Mark the release on GitHub with the command shown (it stays, as a pre-release, so no update "
            "check offers it), then release the portal on the release tab, from Commit your changes: it removes the "
            "app from the consoles."))
        lay.addLayout(row)
        lay.addLayout(reason_row)
        lay.addStretch(1)
        self.units: list[rp.Unit] = []

    def fill(self, units: list[rp.Unit]) -> None:
        current = self.app_box.currentData()
        self.units = rp.withdrawable(self.release_window.root, units, self.release_window.suite)
        self.app_box.blockSignals(True)
        self.app_box.clear()
        for unit in self.units:
            self.app_box.addItem(unit.pinned_tag, unit.key)
        if current in [u.key for u in self.units]:
            self.app_box.setCurrentIndex([u.key for u in self.units].index(current))
        self.app_box.blockSignals(False)
        self._show_state()

    def unit(self) -> rp.Unit | None:
        key = self.app_box.currentData()
        return next((u for u in self.units if u.key == key), None)

    def _show_state(self) -> None:
        unit = self.unit()
        reason = rp.withdrawn_reason(self.release_window.root, unit.key, self.release_window.suite) if unit else ""
        self.state.setText(f"Withdrawn: {reason}" if reason else "Not withdrawn.")
        self.state.setStyleSheet(f"color:{ORANGE}; font-weight:600;" if reason else "")
        self.withdraw_button.setEnabled(unit is not None and not reason)
        self.back_button.setEnabled(bool(reason))

    def withdraw(self) -> None:
        unit = self.unit()
        reason = self.reason_edit.text().strip()
        if unit is None:
            return
        if not reason:
            QMessageBox.warning(self, "Retract", "Say why the release is withdrawn: the consoles show it.")
            return
        root = self.release_window.root
        changed = rp.withdraw(root, unit, reason, suite=self.release_window.suite)
        commands = rp.withdraw_commands(unit.pinned_tag, reason)
        self.output.set_text("\n".join([f"{unit.pinned_tag}: withdrawn in " +
                                        ", ".join(p.relative_to(root).as_posix() for p in changed), "", commands]))
        self.release_window.offer(commands)
        self.reason_edit.clear()
        self.release_window.reload()

    def take_back(self) -> None:
        unit = self.unit()
        if unit is None:
            return
        rp.withdraw(self.release_window.root, unit, "", suite=self.release_window.suite)
        self.output.set_text(f"{unit.pinned_tag}: no longer withdrawn in portal/apps.toml (and a CHANGELOG entry). "
                             "Marked on GitHub already? Edit that release back: gh release edit "
                             f"{unit.pinned_tag} --prerelease=false --title {unit.pinned_tag}")
        self.release_window.reload()

    def test(self) -> None:
        """The suite's check-release script in a terminal: it installs the portal from this checkout and keeps it
        running there."""
        window = self.release_window
        path = rp.check_script(window.root, window.suite)
        if not (window.root / path).is_file():
            self.output.set_text(f"This suite has no {path}.")
            return
        try:
            window.launch(f"{shlex.quote(str(window.root / path))} local")
        except RuntimeError as exc:
            self.output.set_text(str(exc))
            return
        self.output.set_text("A terminal installs the portal from this checkout and starts it. With the app "
                             "installed, the portal says it is not available any more and removes it; its tile then "
                             "shows \"App not available\". Close the portal there to finish.")


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class RemovePage(QWidget):
    """Remove suite: what of the suite is installed on this machine, removed with each part's own uninstaller
    (check-release.sh remove, in a terminal). It was on the tab Test on this board, whose tests the release tab's
    Device test and Retract's Test withdrawal do since 15-11-2026."""

    def __init__(self, window: "ReleaseWindow"):
        super().__init__()
        self.release_window = window
        self.remove_button = QPushButton("Remove suite")
        self.remove_button.setToolTip("Show what of the suite is installed on this machine and whether a test put it "
                                      "there, then remove it all: every app, the portal and Board Test, each with "
                                      "its own uninstaller (check-release.sh remove). Settings stay")
        self.remove_button.clicked.connect(self.remove)
        self.output = StepLog(self, "Remove suite", window.step_wrote, opens=False)   # lines while you click
        row = QHBoxLayout()
        row.addWidget(self.remove_button)
        row.addStretch(1)
        lay = QVBoxLayout(self)
        lay.addLayout(info_row(
            "Remove suite shows what of the suite is installed here and removes it all, in a terminal.",
            "<b>Remove suite</b> lists what of the suite is installed on this machine and whether a test put it there, "
            "then removes it all: every app, the portal and Board Test, each with its own uninstaller "
            "(check-release.sh remove). Settings stay. A test on a machine without the suite removes what it "
            "installed when the portal closes; a machine that had the suite keeps it."))
        lay.addLayout(row)
        lay.addStretch(1)

    def remove(self) -> None:
        window = self.release_window
        path = rp.check_script(window.root, window.suite)
        if not (window.root / path).is_file():
            self.output.appendPlainText(f"This suite has no {path}.")
            return
        try:
            window.launch(f"{shlex.quote(str(window.root / path))} remove")
        except RuntimeError as exc:
            self.output.appendPlainText(str(exc))
            return
        self.output.appendPlainText("A terminal lists what of the suite is installed here, then removes it: every "
                                    "app, the portal and Board Test. Board Test asks for the sudo password.")


NOTIFY_MS = 10_000                      # how long a notification from the tray icon shows
_tray: QSystemTrayIcon | None = None    # made at the first notification, kept while the app runs


def tray_notify(summary: str, body: str) -> bool:
    """A notification from the app's icon in the notification area, Qt's QSystemTrayIcon: Windows shows it as one of
    its own notifications (owner, 28-10-2026: Windows has no notify-send, so none came there). A click on it, or on
    the icon, brings the window to the front. False without a notification area."""
    global _tray
    app = QApplication.instance()
    if app is None or not QSystemTrayIcon.isSystemTrayAvailable():
        return False
    if _tray is None:
        _tray = QSystemTrayIcon(QIcon(str(LOGO_PATH)), app)
        _tray.setToolTip(APP_NAME)
        _tray.messageClicked.connect(_raise_window)
        _tray.activated.connect(lambda _reason: _raise_window())
    _tray.show()
    _tray.showMessage(summary, body, _tray.icon(), NOTIFY_MS)
    return True


def _raise_window() -> None:
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, ReleaseWindow) and widget.isVisible():
            if widget.isMinimized():
                widget.showNormal()
            widget.raise_()
            widget.activateWindow()


def desktop_notify(summary: str, body: str) -> bool:
    """A desktop notification through notify-send (Linux); without it (Windows), from the tray icon (tray_notify).
    False when the desktop has neither."""
    exe = shutil.which("notify-send")
    if not exe:
        return tray_notify(summary, body)
    ok, _pid = QProcess.startDetached(exe, ["--app-name", APP_NAME, "--icon", str(LOGO_PATH), summary, body])
    return ok


BUILD_BUSY_MS = 30_000                  # how often to look while a build runs
BUILD_IDLE_MS = 300_000                 # and otherwise (unchanged answers do not count against GitHub's limit)
BUILD_SOON_MS = 10_000                  # while a pushed HEAD has no run yet: GitHub starts its CI seconds after a push
BUILD_LOOK = {"running": (BLUE, "Building"), "passed": (GREEN, "Passed"), "failed": (RED, "Failed"),
              "": (GREY, "No builds")}

class BuildIndicator(Pill):
    """Whether GitHub built the newest push: CI, Release and Manual on its commit. Looks every 30 s while a build
    runs, every 10 s while the pushed HEAD has no run yet, and every 5 minutes otherwise; a run seen running that
    finishes gives a desktop notification. A click opens the run that failed (or still runs), else the Actions page. When GitHub's hourly limit is used up
    it says until when and waits till then. Requests carry the token of a gh login when there is one
    (plan.github_token)."""

    def __init__(self, window: "ReleaseWindow", source, notify):
        super().__init__("—", "GitHub build")
        self.release_window = window
        self.source = source            # rp.fetch_runs(etag, head): (runs | None when unchanged, etag)
        self.notify = notify
        self.etag = ""
        self.head = ""                          # the checkout's HEAD at the last look
        self.runs: list[rp.BuildRun] = []
        self.seen: dict[str, rp.BuildRun] = {}
        self.clicked.connect(self.open)
        self.checker = UpdateChecker(self)
        self.checker.finished.connect(self.checked)
        self.timer = QTimer(self, singleShot=True)
        self.timer.timeout.connect(self.check)
        self.rate = MetricBox("GitHub API left")    # GitHub's hourly limit: placed beside it by the window
        self.rate.setVisible(source is not None)
        self.signed_in = False                  # the last answer came with a token: the ticker reads the jobs
        self.show_state("", "Not looked yet.")
        self.show_rate(None)
        self.setVisible(source is not None)

    def check(self) -> None:
        if self.source is None:
            return
        etag, head = self.etag, (rp.git(self.release_window.root, "rev-parse", "HEAD") or "").strip()
        self.head = head
        self.checker.start(lambda: self._fetch(etag, head))

    def _fetch(self, etag: str, head: str) -> object:
        """Worker thread: the runs (those of HEAD complete, rp.fetch_runs), or the error to show."""
        try:
            return self.source(etag, head)
        except (OSError, ValueError) as exc:
            return exc

    def checked(self, result: object) -> None:
        if isinstance(result, rp.RateLimited):
            self.show_rate(result.rate)
            back = time.strftime("%H:%M", time.localtime(result.reset))
            hint = "" if result.signed_in else \
                "\n\nSigned in with gh (gh auth login), GitHub allows 5,000 requests an hour instead of 60."
            self.show_state("", f"{result}; looking again then.{hint}", limited=back)
            self.timer.start(max(BUILD_IDLE_MS, int((result.reset - time.time()) * 1000) + 5_000))
            return
        if isinstance(result, Exception):
            self.show_state("", f"GitHub could not be reached: {result}", unreachable=True)
            self.timer.start(BUILD_IDLE_MS)
            return
        runs, self.etag, *rate = result         # the limit as a third value (rp.fetch_runs); tests may leave it out
        if rate:
            self.show_rate(rate[0])
        finished: list[rp.BuildRun] = []
        if runs is not None:
            finished = rp.just_finished(self.seen, runs)
            self.runs, self.seen = runs, {r.url: r for r in runs}
        # Told about: the runs of the suite ticked and Nexus's own, as the ticker shows them.
        told = [r for r in finished if r.file not in self.release_window.ticker.hidden]
        if told:
            self.announce(told)
        self.release_window.release_page.show_state()   # the Nexus release's run, from the same runs
        latest = rp.latest_push(self.runs)
        state = rp.build_state(latest)
        self.show_state(state, self.details(latest))
        self.release_window.ticker.show_runs(latest, self.signed_in)
        running = any(not r.done for r in self.runs)
        self.timer.start(BUILD_SOON_MS if self.awaiting_head() else BUILD_BUSY_MS if running else BUILD_IDLE_MS)

    def awaiting_head(self) -> bool:
        """HEAD is pushed and GitHub has no run of it yet (owner, 05-11-2026: CI ran on GitHub while the CI passes
        step said it had none, as the look right after the push came before GitHub started it, and the next one
        came 5 minutes later)."""
        if not self.head or any(r.sha == self.head for r in self.runs):
            return False
        window = self.release_window
        return rp.git(window.root, "merge-base", "--is-ancestor", self.head, window.base()) is not None

    def details(self, latest: list[rp.BuildRun]) -> str:
        if not latest:
            return "No workflow runs on GitHub."
        head = f"{latest[0].sha[:7]} {latest[0].title}"
        return "\n".join([head, *(f"{r.label}: {'replaced by a later run' if rp.superseded(r, latest) else r.outcome}"
                                  for r in latest), "", "Click to open it on GitHub."])

    def show_state(self, state: str, tooltip: str, unreachable: bool = False, limited: str = "") -> None:
        if limited:
            color, text, self.state = ORANGE, "Limited", "limited"
            tooltip = f"GitHub's limit is reached, back at {limited}.\n\n{tooltip}"
        else:
            color, text = (GREY, "Offline") if unreachable else BUILD_LOOK[state]
            self.state = "unreachable" if unreachable else state
        self.set_colour(color)
        self.set_value(text, tooltip)

    def show_rate(self, rate: "rp.RateInfo | None") -> None:
        """How many of GitHub's requests are left this hour: none left is GitHub's limit, not a fault here."""
        if rate is None:
            value, color, now = "—", GREY, "The limit is not known yet."
        else:
            self.signed_in = rate.signed_in
            value, now = f"{rate.remaining:,}", f"{rate.text}."
            color = RED if rate.remaining == 0 else ORANGE if rate.remaining < rate.limit / 10 else GREEN
        sign_in = "" if rate is not None and rate.signed_in else \
            " Signed in with gh (gh auth login), it is 5,000 an hour instead of 60."
        self.rate.set_colour(color)
        self.rate.set_value(value, f"{now}\n\n"
            "GitHub's API answers a limited number of requests an hour; answers that did not change since the last "
            "look do not count. The limit is shared by everything on this network that asks GitHub without signing "
            f"in.{sign_in} When none are left, nothing is broken: GitHub answers again after the time shown.")

    def announce(self, finished: list[rp.BuildRun]) -> None:
        failed = [r for r in finished if not r.passed and not rp.superseded(r, self.runs)]
        summary = f"GitHub build {'failed' if failed else 'passed'}"
        body = "\n".join(f"{r.label}: {r.outcome}" for r in (failed or finished))
        self.notify(summary, body)
        QApplication.alert(self.release_window)

    def target(self) -> str:
        latest = rp.latest_push(self.runs)
        pick = next((r for r in latest if r.done and not r.passed and not rp.superseded(r, latest)), None) or \
            next((r for r in latest if not r.done), None)
        return pick.url if pick else rp.ACTIONS_URL.format(repo_url=rp.pin_app.REPO_URL)

    def open(self) -> None:
        QDesktopServices.openUrl(QUrl(self.target()))

    def stop(self) -> None:
        self.timer.stop()
        self.checker.stop(2000)


JOBS_BUSY_MS = 10_000                   # how often the ticker reads the jobs while a run runs
TICK_MS = 1000                          # and counts its time


class WorkflowTicker(QFrame):
    """Between the header's pills and the tabs: where GitHub's workflows on the newest push stand (owner,
    28-10-2026: no switching to the browser for it), those of the suite ticked and Nexus's own; the other suites'
    CI and releases are left out (owner, 28-10-2026). Each run that runs with its jobs done of all, the job that runs
    and its step, and the time since it started, counted every second; a failed run names its job and step; a run
    that passed says so. Signed in with gh it reads the jobs of every run that runs every 10 seconds, and of a run
    that failed once (unchanged answers do not count against GitHub's limit); without a token, the 60 requests an
    hour are the build pill's, so it shows the runs only. A click opens the job that runs (or failed), else the run.
    While a run shown has failed, Run again starts its failed jobs again (gh run rerun --failed; owner, 06-11-2026).
    Hidden until GitHub shows a run. The line wraps to as many lines as it needs, never wider than the window
    (owner, 01-11-2026: cut off at one line, the end was not visible)."""

    def __init__(self, source):
        super().__init__()
        self.source = source            # rp.fetch_jobs(url, etag): (jobs | None when unchanged, etag, rate)
        self.pushed: list[rp.BuildRun] = []     # every run of the newest push
        self.hidden: set[str] = set()           # the workflow files left out: the other suites'
        self.runs: list[rp.BuildRun] = []       # the runs shown
        self.jobs: dict[str, list[rp.BuildJob]] = {}    # by the run's url
        self.etags: dict[str, str] = {}
        self.final: set[str] = set()            # the runs whose jobs were read after they finished
        self.signed_in = False
        self.line = ""
        self.on_rerun = None                    # the window's: runs a command in the Commands tab
        self.setObjectName("ticker")
        self.setStyleSheet(f"#ticker {{ border:1px solid {NEXUS.edge}; border-radius:6px; }}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dot = QLabel("●")
        self.text = QLabel()
        self.text.setWordWrap(True)                                             # wrapped, never wider
        self.text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.text, 1)
        self.rerun_button = accent_button("Run again")
        self.rerun_button.setCursor(Qt.CursorShape.ArrowCursor)
        self.rerun_button.clicked.connect(self.rerun)
        self.rerun_button.setVisible(False)
        lay.addWidget(self.rerun_button, 0, Qt.AlignmentFlag.AlignTop)
        self.checker = UpdateChecker(self)
        self.checker.finished.connect(self.fetched)
        self.timer = QTimer(self, singleShot=True)
        self.timer.timeout.connect(self.fetch)
        self.clock = QTimer(self, interval=TICK_MS)
        self.clock.timeout.connect(self.render)
        self.setVisible(False)

    def follow(self, hidden: set[str]) -> None:
        """Another suite ticked: leave out the runs of these workflow files (the other suites' CI and releases)."""
        self.hidden = hidden
        self.show_runs(self.pushed, self.signed_in)

    def show_runs(self, runs: list[rp.BuildRun], signed_in: bool) -> None:
        """The build pill looked: these are the newest push's runs; the ticker shows those of the suite ticked and
        Nexus's own."""
        self.pushed, self.signed_in = runs, signed_in
        self.runs = [r for r in runs if r.file not in self.hidden]
        urls = {r.url for r in self.runs}
        self.jobs = {url: jobs for url, jobs in self.jobs.items() if url in urls}
        self.etags = {url: etag for url, etag in self.etags.items() if url in urls}
        self.fetch()
        self.render()

    def wanted(self) -> list[rp.BuildRun]:
        """The runs whose jobs to read: those that run, and a failed one not read since it finished."""
        if self.source is None or not self.signed_in:
            return []
        return [r for r in self.runs if r.jobs_url and (not r.done or (not r.passed and r.url not in self.final))]

    def fetch(self) -> None:
        wanted = [(r.url, r.jobs_url, self.etags.get(r.url, ""), r.done) for r in self.wanted()]
        if wanted:
            self.checker.start(lambda: self._fetch(wanted))

    def _fetch(self, wanted: list[tuple[str, str, str, bool]]) -> dict:
        """Worker thread: each run's jobs (None when unchanged) with its ETag; a run GitHub did not answer for keeps
        what was read before."""
        found = {}
        for url, jobs_url, etag, done in wanted:
            try:
                jobs, etag, *_rate = self.source(jobs_url, etag)
            except (OSError, ValueError):
                continue
            found[url] = (jobs, etag, done)
        return found

    def fetched(self, found: dict) -> None:
        urls = {r.url for r in self.runs}
        for url, (jobs, etag, done) in found.items():
            if url not in urls:                 # a newer push meanwhile
                continue
            if jobs is not None:
                self.jobs[url] = jobs
            self.etags[url] = etag
            if done:
                self.final.add(url)
        self.render()

    def render(self) -> None:
        now = time.time()
        self.setVisible(bool(self.runs))
        state = rp.build_state(self.runs)
        running = state == "running"
        if running and not self.clock.isActive():
            self.clock.start()
        elif not running:
            self.clock.stop()
        if running and self.wanted() and not self.timer.isActive():
            self.timer.start(JOBS_BUSY_MS)
        failed = flow.failed_runs(self.runs)
        self.rerun_button.setVisible(bool(failed))
        if failed:
            self.rerun_button.setToolTip("Start the failed jobs of " + ", ".join(r.label for r in failed) + " again, on "
                                         "the same commit: " + flow.rerun_ci_command(failed))
        if not self.runs:
            return
        self.dot.setStyleSheet(f"color:{BUILD_LOOK[state][0]};")
        self.line = rp.ticker_line(self.runs, self.jobs, now)
        self.text.setText(self.line)
        sign_in = "" if self.signed_in or self.source is None else \
            "\n\nSigned in with gh (gh auth login), the ticker shows each job and the step it is at too."
        self.setToolTip(rp.ticker_details(self.runs, self.jobs, now) + sign_in + "\n\nClick to open it on GitHub.")

    def target(self) -> str:
        return rp.ticker_target(self.runs, self.jobs)

    def rerun(self) -> None:
        failed = flow.failed_runs(self.runs)
        if failed and self.on_rerun is not None:
            self.on_rerun(flow.rerun_ci_command(failed))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton and self.target():
            open_url(self.target())
        super().mouseReleaseEvent(event)

    def stop(self) -> None:
        self.timer.stop()
        self.clock.stop()
        self.checker.stop(2000)


class GitHubStatusIndicator(Pill):
    """GitHub status: green while githubstatus.com reports every part of GitHub working, red while it
    reports a problem (a build that waits in "queued" may be GitHub's), gray while it is not known. Looks every 5
    minutes; a click opens the status page."""

    def __init__(self, source):
        super().__init__("—", "GitHub status")
        self.source = source            # rp.fetch_github_status
        self.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(rp.STATUS_PAGE)))
        self.checker = UpdateChecker(self)
        self.checker.finished.connect(self.checked)
        self.timer = QTimer(self, singleShot=True)
        self.timer.timeout.connect(self.check)
        self.show_state("", "Not looked yet.")
        self.setVisible(source is not None)

    def check(self) -> None:
        if self.source is not None:
            self.checker.start(self._fetch)

    def _fetch(self) -> object:
        """Worker thread: the status, or the error to show."""
        try:
            return self.source()
        except (OSError, ValueError) as exc:
            return exc

    def checked(self, result: object) -> None:
        self.timer.start(BUILD_IDLE_MS)
        if isinstance(result, Exception):
            self.show_state("", f"githubstatus.com could not be reached: {result}")
            return
        lines = [result.description or "No status given.", *result.incidents, *result.affected]
        self.show_state("up" if result.up else "down", "\n".join(lines))

    def show_state(self, state: str, details: str) -> None:
        self.state = state
        self.set_colour({"up": GREEN, "down": RED}.get(state, GREY))
        self.set_value({"up": "Up", "down": "Problem"}.get(state, "Unknown"),
                       f"{details}\n\nClick to open {rp.STATUS_PAGE}")

    def stop(self) -> None:
        self.timer.stop()
        self.checker.stop(2000)


class ClaudeUsageIndicator(Pill):
    """Claude tokens today: what Claude Code on this machine used since midnight, read from its own transcripts
    (plan.fetch_claude_usage), blue once known; the tooltip adds the last 5 hours (Claude's usage window), the kinds
    and the models. Hidden without Claude Code here. Looks every 5 minutes; a click opens Claude's usage page, which
    shows the plan's limits (they are not on this machine)."""

    def __init__(self, source):
        super().__init__("\u2014", "Claude tokens today")
        self.source = source            # rp.fetch_claude_usage: (today, last 5 hours) | None
        self.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(rp.CLAUDE_USAGE_PAGE)))
        self.checker = UpdateChecker(self)
        self.checker.finished.connect(self.checked)
        self.timer = QTimer(self, singleShot=True)
        self.timer.timeout.connect(self.check)
        self.set_value("\u2014", f"Not looked yet.\n\nClick to open {rp.CLAUDE_USAGE_PAGE}")
        self.setVisible(source is not None)

    def check(self) -> None:
        if self.source is not None:
            self.checker.start(self._fetch)

    def _fetch(self) -> object:
        """Worker thread: the usage, None without Claude Code, or the error to show."""
        try:
            return self.source()
        except (OSError, ValueError) as exc:
            return exc

    def checked(self, result: object) -> None:
        self.timer.start(BUILD_IDLE_MS)
        if result is None:
            self.setVisible(False)
            return
        if isinstance(result, Exception):
            self.set_colour(GREY)
            self.set_value("\u2014", f"Claude Code's transcripts could not be read: {result}")
            return
        today, recent = result
        self.set_colour(BLUE)
        self.set_value(rp.short_count(today.total), "\n".join([
            f"Today: {today.total:,} tokens in {today.messages:,} answers.",
            f"Last 5 hours: {recent.total:,} tokens in {recent.messages:,} answers.", "",
            f"Input {today.input:,}, output {today.output:,}, cache written {today.cache_write:,}, "
            f"cache read {today.cache_read:,}.",
            *(f"{model}: {tokens:,}" for model, tokens in today.models), "",
            "Claude Code on this machine, from its transcripts; other machines and claude.ai are not in it.",
            f"Click to open {rp.CLAUDE_USAGE_PAGE} for the plan's limits."]))

    def stop(self) -> None:
        self.timer.stop()
        self.checker.stop(2000)


class SuiteList(QListWidget):
    """The suites of the checkout as the window's first column, left of the steps (owner, 27-10-2026: in place of a
    chooser in the header): each portal with its icon, its name and the tag of its current version. The checkmark is
    the suite this window releases, always exactly one; a click on a row, or on its box, moves it there and calls
    *chosen* with the suite's folder. Hidden while the checkout holds one suite."""

    WIDTH = 230

    def __init__(self, root: Path, suites: list[str], current: str | None, chosen):
        super().__init__()
        self.root, self.chosen = root, chosen
        self.setFixedWidth(self.WIDTH)
        self.setIconSize(QSize(32, 32))
        self.setSpacing(2)
        self.setToolTip("The suite this window releases: its apps, its portal and its pins. The git buttons, the "
                        "wikis and GitHub are the repository's, whatever the suite.")
        for name in suites:
            icon = rp.suite_icon(root, name)
            item = QListWidgetItem(QIcon(str(icon)) if icon else QIcon(), "")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            self.addItem(item)
        self.show_texts()
        self.check(current)
        self.itemClicked.connect(lambda item: self._pick(item.data(Qt.ItemDataRole.UserRole)))
        self.itemChanged.connect(self._box)
        self.setVisible(len(suites) > 1)

    def show_texts(self) -> None:
        """Each row's name and its portal's tag, read again (after a release the version moved)."""
        self.blockSignals(True)
        for row in range(self.count()):
            item = self.item(row)
            name = item.data(Qt.ItemDataRole.UserRole)
            version_file = rp.suite_dir(self.root, name) / "portal" / "VERSION"
            version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "?"
            item.setText(f"{rp.suite_name(self.root, name)}\n{rp.tag_prefix(self.root, name)}portal-v{version}")
            item.setToolTip(f"{name}/: its apps, its portal and its pins")
        self.blockSignals(False)

    def check(self, name: str | None) -> None:
        self.blockSignals(True)
        for row in range(self.count()):
            item = self.item(row)
            mine = item.data(Qt.ItemDataRole.UserRole) == name
            item.setCheckState(Qt.CheckState.Checked if mine else Qt.CheckState.Unchecked)
        self.blockSignals(False)

    def current(self) -> str | None:
        return next((self.item(row).data(Qt.ItemDataRole.UserRole) for row in range(self.count())
                     if self.item(row).checkState() == Qt.CheckState.Checked), None)

    def _box(self, item: QListWidgetItem) -> None:
        """The box of a row clicked: checking it picks that suite; unchecking the checked one keeps it checked."""
        name = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self._pick(name)
        else:
            self.check(name)

    def _pick(self, name: str) -> None:
        self.check(name)
        self.chosen(name)


class ReleaseWindow(QMainWindow):
    def __init__(self, root: Path = CHECKOUT, launch=launch_in_terminal,
                 runs_source=rp.fetch_runs, notify=desktop_notify, settings=None,
                 status_source=rp.fetch_github_status, claude_source=rp.fetch_claude_usage,
                 suite: str | None = None, jobs_source=rp.fetch_jobs):
        """*runs_source* reads the GitHub Actions runs (None: no build indicator and no ticker); *jobs_source* the
        jobs of a run, for the ticker (None: the runs only); *notify* shows a desktop
        notification; *settings* keeps the command line's history and the chosen suite (None: this session only);
        *status_source* reads githubstatus.com (None: no GitHub status); *claude_source* reads Claude Code's usage
        (None: no Claude pill); *suite* is the suite
        to open with (a folder name from plan.suites(); None: the one remembered, else the first)."""
        super().__init__()
        self.root = root
        self.settings = settings
        self.base_ref = "origin/main"           # the last push, which the steps compare with (tests use another)
        self.suites = rp.suites(root)
        remembered = str(settings.value(SUITE_KEY, "")) if settings is not None else ""
        self.suite = suite or (remembered if remembered in self.suites else self.suites[0] if self.suites else None)
        self.launch = launch
        self.units: list[rp.Unit] = []
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 760)
        self.setStyleSheet(SELECTION_STYLESHEET + CHECK_STYLESHEET)
        stamp = rp.checkout_stamp(root)                 # never released: the commit says which code runs
        header = AppHeader(LOGO_PATH, APP_NAME, f"{__version__} · {stamp}" if stamp else __version__)
        # The suites, the first column left of the steps; hidden while the checkout holds one suite.
        self.suite_list = SuiteList(root, self.suites, self.suite, self.choose_suite)
        # The header's pills, all as wide as the widest (owner, 20-10-2026).
        self.refresh_pill = Pill("Refresh", "Click to refresh", "Read the checkout and its tags again, for changes "
                                 "made in a terminal; what you entered stays")
        self.refresh_pill.clicked.connect(self.refresh)
        self.build = BuildIndicator(self, runs_source, notify)
        self.build.checker.finished.connect(self.refreshed)     # after the build's own slot: the steps are drawn
        self.ticker = WorkflowTicker(jobs_source)       # between the pills and the tabs, fed by the build's looks
        self.ticker.hidden = rp.other_suites_workflows(root, self.suite)
        self.ticker.on_rerun = self.run_git
        self.github_status = GitHubStatusIndicator(status_source)
        self.claude = ClaudeUsageIndicator(claude_source)
        self.tabs = QTabWidget()
        pills = [self.refresh_pill, self.build, self.build.rate, self.github_status, self.claude]
        for pill in pills:
            header.add_second(pill)
        same_width(pills)
        header.second_row.addStretch(1)
        # The release is one action, Start new release (owner, 30-10-2026), and its steps; the release by hand, a tag
        # at a time (the tabs Release apps, Pin and release Portal and Test on this board, with the manual mode
        # for a repository without a release workflow), went on 15-11-2026 (owner: its Bump made a portal release
        # while the release tab's draft waited for its device test). Remove suite keeps a tab of its own.
        self.release_page = ReleasePage(self)
        self.tabs.addTab(self.release_page, "Nexus release")
        # What the release holds, a tab of its own (owner, 01-11-2026: with the steps it was squeezed)
        self.tabs.addTab(self.release_page.contents, "Contents")
        self.withdraw_page = WithdrawPage(self)
        self.tabs.addTab(self.withdraw_page, "Retract app")
        self.remove_page = RemovePage(self)
        self.tabs.addTab(self.remove_page, "Remove suite")
        self.commands = CommandLine(root, settings, finished=self.command_finished,   # a commit or push: read it again
                                    log_dir=COMMAND_LOG_DIR if settings is not None else None, terminal=self.launch)
        # One output tab (owner, 01-11-2026: Logs was mostly empty): Commands is the command line with its output,
        # where what a step wrote (the release, Retract) shows too, under a line
        # that names the step (step_wrote()).
        self.commands_tab = self.tabs.addTab(self.commands, "Commands")
        self.tabs.setTabToolTip(self.commands_tab, "The command line: runs a command in the checkout and shows its "
                                                   "output, with what each step wrote; Commands offers what the "
                                                   "last step showed")
        self.seen = ""                          # the checkout as last read: fingerprint()
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addLayout(header)
        lay.addWidget(self.ticker)
        self.bad_tags = QLabel()
        self.bad_tags.setWordWrap(True)
        self.bad_tags.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.bad_tags.setStyleSheet("color:#c62828; font-weight:600;")
        lay.addWidget(self.bad_tags)
        columns = QHBoxLayout()
        # Twice the layout's spacing between the header's pills and the tabs (owner, 28-10-2026: too close).
        columns.setContentsMargins(0, lay.spacing(), 0, 0)
        self.suite_column = QWidget()                   # "Portals" over the list; hidden with it
        column = QVBoxLayout(self.suite_column)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)                            # the title sits on the list as a tab on its page
        title = QLabel("Portals")                       # as wide as the column (owner, 28-10-2026)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(TAB_TITLE_STYLESHEET)
        column.addWidget(title)
        column.addWidget(self.suite_list, 1)
        self.suite_column.setVisible(not self.suite_list.isHidden())
        columns.addWidget(self.suite_column)
        columns.addWidget(self.tabs, 1)
        lay.addLayout(columns, 1)
        self.setCentralWidget(central)
        self.reload()
        self.build.check()
        self.github_status.check()
        self.claude.check()

    def choose_suite(self, name: str) -> None:
        """Another suite ticked in the first column: the steps, the pins and the console tests show it from now on,
        and the next start opens with it."""
        if not name or name == self.suite:
            return
        self.suite = name
        if self.settings is not None:
            self.settings.setValue(SUITE_KEY, name)
        self.ticker.follow(rp.other_suites_workflows(self.root, name))
        self.refresh()

    def offer(self, commands: str) -> None:
        """A step showed the commands to run next: the Commands menu lists them."""
        self.commands.offer(commands)

    def step_wrote(self, page: QWidget, name: str, text: str, opens: bool) -> None:
        """A step's log (StepLog): it shows in Commands under the step's name, and Commands opens when the step
        that wrote it is the tab open (*opens*)."""
        self.commands.note(name, text)
        if opens and self.tabs.currentWidget() is page and text.strip():
            self.tabs.setCurrentIndex(self.commands_tab)

    def run_git(self, command: str) -> None:
        if self.commands.run_now(command):
            self.tabs.setCurrentIndex(self.commands_tab)
        self.release_page.show_state()          # the pills rest while the command runs

    def confirm_git(self, title: str, what: str, command: str) -> bool:
        """Push and tag reach GitHub: they ask first, with the command and what it sends, and say when the token on
        this machine reaches more than this repository."""
        warning = rp.token_warning(rp.github_token())
        text = f"{what}\n\n{command}" + (f"\n\n\u26a0 {warning}" if warning else "") + "\n\nGo ahead?"
        return QMessageBox.question(self, title, text) == QMessageBox.StandardButton.Yes

    def push(self) -> None:
        commits = (rp.git(self.root, "log", "--oneline", f"{self.base()}..HEAD") or "").strip()
        if self.confirm_git("git push", f"Push to GitHub:\n\n{commits}", rp.push_command()):
            self.run_git(rp.push_command())

    def fingerprint(self) -> str:
        """The checkout as the window reads it: HEAD, the last push, the working tree and the tags. A command that
        left them as they were needs no reload (owner, 01-11-2026: the window was slow, and read the checkout again
        after every command)."""
        return "\n".join(rp.git(self.root, *args) or "" for args in (
            ("rev-parse", "HEAD"), ("rev-parse", "-q", "--verify", self.base()), ("status", "--porcelain"),
            ("for-each-ref", "--format=%(refname) %(objectname)", "refs/tags")))

    def command_finished(self) -> None:
        """A command ended: the checkout is read again when it changed anything, else only the steps' pills and
        GitHub's state."""
        if self.fingerprint() != self.seen:
            self.refresh()
            return
        self.release_page.show_state()
        self.build.check()
        self.github_status.check()
        self.claude.check()

    def base(self) -> str:
        return self.base_ref

    def refresh(self) -> None:
        """reload(), keeping what was entered (the release's versions and notes: ReleasePage.fill). The pill says it is at it until GitHub's runs are in (owner, 05-11-2026:
        it seemed to do nothing, or to be very slow): the checkout is read here, GitHub's runs in a thread."""
        self.refresh_pill.caption.setText("Refreshing…")
        self.refresh_pill.caption.repaint()             # drawn before the checkout is read, which holds the window
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.reload()
        finally:
            QApplication.restoreOverrideCursor()
        if self.build.source is None:
            self.refreshed()
        self.build.check()                      # a push from a terminal: its build; refreshed() when it is in
        self.github_status.check()
        self.claude.check()

    def refreshed(self, _result: object = None) -> None:
        """GitHub's runs are in (or could not be had: the build pill says so): the time of this refresh."""
        if self.refresh_pill.caption.text() == "Refreshing…":
            self.refresh_pill.caption.setText(f"Refreshed {time.strftime('%H:%M')}")

    def reload(self) -> None:
        units = self.units = rp.load_units(self.root, self.suite)
        self.suite_list.show_texts()                    # a portal bumped meanwhile shows its new tag
        self.release_page.fill()
        self.withdraw_page.fill(units)
        problems = rp.bad_tags(self.root, units)
        self.bad_tags.setText("\n".join(
            f"\u26a0 {p}: release.yml cannot build it. Delete it (git tag -d {p.split()[0]} && git push origin "
            f":refs/tags/{p.split()[0]}), commit and push the bump, then tag again with {rp.TAG_SCRIPT} "
            f"{p.split()[0]}." for p in problems))
        self.bad_tags.setVisible(bool(problems))
        self.seen = self.fingerprint()

    def closeEvent(self, event) -> None:
        self.build.stop()
        self.ticker.stop()
        if _tray is not None:                           # no icon left behind in the notification area
            _tray.hide()
        self.github_status.stop()
        self.claude.stop()
        self.commands.shutdown()
        super().closeEvent(event)
