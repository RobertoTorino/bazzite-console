# SPDX-License-Identifier: GPL-3.0-or-later
"""The window: every app of the portal with its line in the article, and the pills that make the article. Preview
opens it in the browser, Export writes it to a new folder to share, Screenshots takes the stills of the portal again
(tools/portal_shots.py) and Text check runs tools/text_check.py on the article's words (copy.md). Publish writes the
article into the website's folder, a checkout of the repository GitHub Pages serves, then commits it as "see the
changelog" and pushes (owner, 25-11-2026). Its caption says how many files differ, so you see when the site is
behind."""

from __future__ import annotations

import configparser
import datetime
import importlib.util
import os
import re
import sys
from html import escape
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QRectF, QSize, Qt, QUrl
from PyQt6.QtGui import QCloseEvent, QColor, QDesktopServices, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from bazzite_console_core.nexus import header as nexus_header
from bazzite_console_core.platform import private
from bazzite_console_core.settings import open_settings
from bazzite_console_core.theme import GREEN, GREY, ORANGE, RED
from bazzite_console_core.widgets import (ActionPill, InfoButton, MetricBox, RefreshButton, StatusText, Terminal,
                                          accent, hint_label, same_width)

from . import APP_ID, APP_NAME, CHECKOUT, INFO, LOGO_PATH
from . import article

# The repository of this suite's website: Publish takes no other (owner, 26-11-2026: the PS5 article went to the
# BC-250 website, as both twins shared one settings file)
WEBSITE_REPO = "RobertoTorino/console-suite"
WIKI = "https://robertotorino.github.io/bazzite-console/development/dashboard/#marketing"
PREVIEW = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / APP_ID / "preview"
SHOTS_TOOL = CHECKOUT / "tools" / "portal_shots.py"
TEXT_CHECK = CHECKOUT / "tools" / "text_check.py"
ABOUT = ("Nexus Marketing writes an article that presents the portal and every app in it. The article is a "
         "web page to share. The page takes the apps from the portal's apps.toml and the words from copy.md "
         "beside the app. The license and the disclaimer come from the suite's README. "
         "<b>Preview</b> opens the article in the browser. <b>Export</b> writes it to a new folder. "
         "<b>Screenshots</b> takes the stills of the portal again. "
         "<b>Text check</b> runs the suite's text check on copy.md. "
         "<b>Publish</b> writes the article into the website's folder, commits it and pushes it to GitHub. "
         f"<a href='{WIKI}'>Wiki</a>")
COLUMNS = ("App", "Category", "Line in the article")


def stills_current(folder: Path = article.SHOTS) -> bool | None:
    """Whether the stills show the portal as it is now: their stamp against tools/portal_tour.py's fingerprint.
    None without stills."""
    try:
        stamp = (folder / "portal.stamp").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    spec = importlib.util.spec_from_file_location("portal_tour", CHECKOUT / "tools" / "portal_tour.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return stamp == module.fingerprint()


def origin(folder: Path | None) -> str:
    """The GitHub repository the checkout in *folder* pushes to, as owner/name; empty when it has none."""
    if folder is None:
        return ""
    config = configparser.ConfigParser()
    try:
        config.read(folder / ".git" / "config", encoding="utf-8")
        url = config.get('remote "origin"', "url")
    except (OSError, configparser.Error):
        return ""
    found = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{found.group(1)}/{found.group(2)}" if found else ""


def website_url(folder: Path | None) -> str | None:
    """The address of the website the folder publishes to: its CNAME (a domain of its own) when it has one, else
    GitHub Pages' address of its origin on GitHub, https://<owner>.github.io/<repository>/. None without either."""
    if folder is None:
        return None
    try:
        domain = (folder / "CNAME").read_text(encoding="utf-8").strip()
    except OSError:
        domain = ""
    if domain:
        return f"https://{domain}/"
    owner, _, name = origin(folder).partition("/")
    return f"https://{owner.lower()}.github.io/{name}/" if name else None


class GlobeButton(QToolButton):
    """A small round globe, of the info symbol's size and look, that opens the website (owner, 25-11-2026). Core has
    no such symbol, so it is drawn here: a circle with its equator and a meridian, in white."""

    SIZE = InfoButton.SIZE

    def __init__(self, tooltip: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setIcon(self._globe())
        self.setIconSize(QSize(self.SIZE - 8, self.SIZE - 8))
        self.setStyleSheet(
            f"QToolButton {{ border:1px solid {accent()}; border-radius:{self.SIZE // 2}px; background:{accent()}; "
            "padding:0; } QToolButton:hover, QToolButton:focus { border-color:white; }"
            f"QToolButton:disabled {{ background:{GREY}; border-color:{GREY}; }}")

    def _globe(self) -> QIcon:
        side = 4 * (self.SIZE - 8)                  # drawn large, scaled down sharp
        pixmap = QPixmap(side, side)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("white"), side / 11))
        edge = QRectF(side / 11, side / 11, side - 2 * side / 11, side - 2 * side / 11)
        painter.drawEllipse(edge)
        painter.drawEllipse(edge.adjusted(edge.width() * 0.28, 0, -edge.width() * 0.28, 0))   # a meridian
        painter.drawLine(int(edge.left()), int(edge.center().y()), int(edge.right()), int(edge.center().y()))
        painter.end()
        return QIcon(pixmap)


class EditButton(QToolButton):
    """A small round pencil, of the info symbol's size and look, beside the line that names copy.md: it opens the
    file in the default editor for its type (owner, 26-11-2026)."""

    SIZE = InfoButton.SIZE

    def __init__(self, tooltip: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText("✎")
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setStyleSheet(
            f"QToolButton {{ border:1px solid {accent()}; border-radius:{self.SIZE // 2}px; color:white; "
            f"background:{accent()}; font-weight:800; padding:0 0 1px 0; }}"
            "QToolButton:hover, QToolButton:focus { border-color:white; }")


class MainWindow(QMainWindow):
    def __init__(self, stills=stills_current):
        """*stills*: stills_current, or a test's own."""
        super().__init__()
        self.stills = stills
        self.settings = open_settings(INFO, self)
        self.process: QProcess | None = None
        self.queue: list[list[str]] = []            # the commands still to run after the one that runs
        self.current: bool | None = None           # the stills against the portal: stills_current()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 720)

        central = QWidget()
        layout = QVBoxLayout(central)
        header = nexus_header(LOGO_PATH, APP_NAME, CHECKOUT)  # the checkout's commit, never a version
        self.state = StatusText()
        header.add_state(self.state)
        header.add_action(InfoButton(ABOUT, "What Nexus Marketing does"))
        self.globe_button = GlobeButton("Open the website")
        self.globe_button.clicked.connect(self.open_website)
        header.add_action(self.globe_button)
        self.refresh_button = RefreshButton("Read the portal and the words again")
        self.refresh_button.clicked.connect(self.refresh)
        header.add_action(self.refresh_button)
        self.apps_box = MetricBox("Apps with a line", GREY)
        self.shots_box = MetricBox("Screenshots", GREY)
        self.preview_pill = ActionPill("Preview", "In the browser", "Open the article in the browser")
        self.preview_pill.clicked.connect(self.on_preview)
        self.export_pill = ActionPill("Export", "To a new folder", "Write the article and its pictures to a new "
                                                                   "folder that you choose")
        self.export_pill.clicked.connect(self.on_export)
        self.shots_pill = ActionPill("Screenshots", "Of the portal", "Take the stills of the portal again")
        self.shots_pill.clicked.connect(self.on_shots)
        self.check_pill = ActionPill("Text check", "Of the words", "Check copy.md with the text check")
        self.check_pill.clicked.connect(self.on_text_check)
        self.publish_pill = ActionPill("Publish", "Choose the folder", "Write the article into the website's "
                                                                       "folder, commit it and push it to GitHub")
        self.publish_pill.clicked.connect(self.on_publish)
        boxes = [self.apps_box, self.shots_box, self.preview_pill, self.export_pill, self.shots_pill, self.check_pill,
                 self.publish_pill]
        same_width(boxes)
        for box in boxes:
            header.add_second(box)
        header.second_row.addStretch(1)
        layout.addLayout(header)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        heading = self.table.horizontalHeader()
        heading.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        heading.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        heading.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 3)
        words = QHBoxLayout()
        where = hint_label("The words are in dev/marketing/nexus_marketing/copy.md. Edit them there, then read them "
                           "again with the arrows.")
        where.setWordWrap(False)                    # one line, with the pencil right after it
        words.addWidget(where)
        self.edit_button = EditButton("Open copy.md in your text editor")
        self.edit_button.clicked.connect(self.open_copy)
        words.addWidget(self.edit_button)
        words.addStretch(1)
        layout.addLayout(words)
        self.output = Terminal()
        layout.addWidget(self.output, 1)
        self.line = QLabel()
        self.line.setWordWrap(True)
        layout.addWidget(self.line)
        self.setCentralWidget(central)
        self.refresh()

    # --- reading -----------------------------------------------------------------------------------------------
    def refresh(self) -> None:
        entries = article.apps()
        names = article.categories()
        lines = article.table(article.read_copy().get("Apps", []))
        self.table.setRowCount(len(entries))
        for row, app in enumerate(entries):
            line = lines.get(app.key, "")
            cells = [QTableWidgetItem(app.name), QTableWidgetItem(names.get(app.category, app.category)),
                     QTableWidgetItem(line or "No line yet. Add one to copy.md.")]
            if not line:
                cells[2].setForeground(QColor(RED))
            for column, cell in enumerate(cells):
                self.table.setItem(row, column, cell)
        problems = article.missing()
        covered = sum(1 for app in entries if lines.get(app.key))
        self.apps_box.set_value(f"{covered} of {len(entries)}")
        self.apps_box.set_colour(GREEN if covered == len(entries) else RED)
        current = self.current = self.stills()
        self.shots_box.set_value({True: "Current", False: "Out of date", None: "None"}[current])
        self.shots_box.set_colour({True: GREEN, False: ORANGE, None: RED}[current])
        if problems:
            self.state.set_status("Words missing", "warn", "copy.md lacks a line the portal needs.")
            self.say("\n".join(problems), ok=False)
        elif current is not True:
            self.state.set_status("Screenshots", "warn", "Take the screenshots of the portal again.")
            self.say("The portal changed after the last screenshots." if current is False
                     else "The portal has no screenshots yet.", ok=False)
        else:
            self.state.set_status("Ready", "ok", "The article covers every app of the portal.")
            self.say("The article covers every app of the portal.")
        self._show_website()
        self._busy(self.process is not None)

    # --- the website -------------------------------------------------------------------------------------------
    def key(self, name: str) -> str:
        """A setting of this suite's twin: both twins share the app's ID, so its settings file."""
        return f"{suite_slug()}/{name}"

    def website(self) -> Path | None:
        """The website's folder, a checkout of WEBSITE_REPO; None when none is chosen or it is no such checkout."""
        chosen = self.settings.value(self.key("website_folder"), "")
        return Path(chosen) if chosen and is_website(Path(chosen)) else None

    def _show_website(self) -> None:
        folder = self.website()
        self.changed = article.changes(article.build(), folder) if folder else []
        if folder is None:
            caption, tip = "Choose the folder", "Choose the website's folder, a checkout of its repository."
        elif self.changed:
            count = len(self.changed)
            caption = f"{count} change{'s' if count > 1 else ''}"
            tip = "These files differ from the website:\n" + "\n".join(self.changed)
        else:
            caption, tip = "Up to date", f"The website's folder has the article as it is. {private(folder)}"
        self.publish_pill.caption.setText(caption)
        self.publish_pill.setToolTip(tip)
        url = website_url(folder)
        self.globe_button.setEnabled(url is not None)
        self.globe_button.setToolTip(f"Open the website, {url}" if url else
                                     "Open the website. Choose its folder with Publish first.")

    def open_copy(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(article.COPY)))

    def open_website(self) -> None:
        url = website_url(self.website())
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def choose_website(self) -> bool:
        """Asks for the website's folder and keeps it. False when none was chosen or it is no git checkout."""
        chosen = QFileDialog.getExistingDirectory(self, "The website's folder", str(self.website() or Path.home()))
        if not chosen:
            return False
        if not (Path(chosen) / ".git").exists():
            self.say("That folder is no git checkout. Choose the folder of the website's repository.", ok=False)
            return False
        if not is_website(Path(chosen)):
            self.say(f"That folder is no checkout of {WEBSITE_REPO}, this suite's website. Choose that one.", ok=False)
            return False
        self.settings.setValue(self.key("website_folder"), chosen)
        self.refresh()
        return True

    def on_publish(self) -> None:
        """One click (owner, 25-11-2026: a menu was not found): the folder first when there is none, then the question
        and the publish. Other folder… in the question takes another folder and asks again."""
        if self.process is not None or (self.website() is None and not self.choose_website()):
            return
        folder = self.website()
        if not self.changed:
            self.say("The website is up to date. There is nothing to publish.")
            return
        count = len(self.changed)
        box = QMessageBox(QMessageBox.Icon.Question, "Publish", "Publish the article to the website?\n\n"
                          f"{count} file{'s' if count > 1 else ''} change in {private(folder)}.\n"
                          f'They are committed as "{article.COMMIT_MESSAGE}".\n'
                          "The commit is pushed to GitHub. The website shows it a minute or two later.", parent=self)
        yes = box.addButton(QMessageBox.StandardButton.Yes)
        other = box.addButton("Other folder…", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.No)
        box.exec()
        if box.clickedButton() is other:
            if self.choose_website():
                self.on_publish()
            return
        if box.clickedButton() is not yes:
            return
        article.publish(article.build(), folder)
        self._run("Publishing", *article.publish_commands(folder))

    # --- the article -------------------------------------------------------------------------------------------
    def on_preview(self) -> None:
        PREVIEW.mkdir(parents=True, exist_ok=True)
        # one file, as a browser in a sandbox gets nothing beside it; one per suite, as both twins share the app's ID
        page = PREVIEW / f"{suite_slug()}.html"
        page.write_text(article.single(article.build()), encoding="utf-8", newline="\n")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(page)))
        self.say(f"The preview is in {private(PREVIEW)}.")

    def on_export(self) -> None:
        settings = self.settings
        start = settings.value(self.key("export_folder"), str(Path.home()))
        chosen = QFileDialog.getExistingDirectory(self, "Export the article to", start)
        if not chosen:
            return
        settings.setValue(self.key("export_folder"), chosen)
        folder = export_folder(Path(chosen))
        article.write(article.build(), folder)
        if folder == Path(chosen):                      # a git checkout: Publish's count follows
            self._show_website()
            self.say(f"The article is in {private(folder)}. Publish commits it and pushes it.")
            return
        self.say(f"The article is in {private(folder)}. Open index.html there, or put the folder on a web server.")

    # --- the tools ---------------------------------------------------------------------------------------------
    def on_shots(self) -> None:
        self._run("Taking the screenshots", [sys.executable, str(SHOTS_TOOL), str(article.SHOTS)])

    def on_text_check(self) -> None:
        self._run("Checking the words",
                  [sys.executable, str(TEXT_CHECK), "--details", str(article.COPY.relative_to(CHECKOUT))])

    def _run(self, doing: str, *commands: list[str]) -> None:
        """Runs *commands* one after the other, their output below the table. A command that fails stops the rest."""
        if self.process is not None:
            return
        self.queue = list(commands)
        self.doing = doing
        self.output.set_text("")
        self.state.set_status(doing, "neutral", doing + ".")
        self._busy(True)
        self._next()

    def _next(self) -> None:
        command = self.queue.pop(0)
        process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONPATH", str(CHECKOUT / "core"))
        environment.insert("QT_QPA_PLATFORM", "offscreen")
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(CHECKOUT))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._done)
        self.process = process
        self.output.set_text(self.output.toPlainText() + "$ " + private(" ".join(command)) + "\n")
        process.start(command[0], command[1:])

    def _read(self) -> None:
        if self.process is not None:
            text = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
            self.output.set_text(self.output.toPlainText() + private(text))

    def _done(self, code: int, _status) -> None:
        self._read()
        self.process = None
        if code == 0 and self.queue:
            self._next()
            return
        self.queue = []
        self.refresh()
        if code == 0 and self.doing == "Publishing":
            self.say("Published. The website shows the new article in a minute or two.")
        if code:
            self.say(f"It ended with exit code {code}. Its output is above.", ok=False)

    # --- the window --------------------------------------------------------------------------------------------
    def _busy(self, busy: bool) -> None:
        self.refresh_button.setEnabled(not busy)
        self.shots_pill.setEnabled(not busy and self.current is not True)  # current stills: nothing to take again
        self.check_pill.setEnabled(not busy)
        # off when the website has the article as it is: what is published cannot be published again
        self.publish_pill.setEnabled(not busy and (self.website() is None or bool(self.changed)))

    def say(self, text: str, ok: bool = True) -> None:
        self.line.setText(escape(text).replace("\n", "<br>"))
        self.line.setStyleSheet("font-weight:600;" + ("" if ok else f"color:{RED};"))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        if self.process is not None:
            self.process.kill()
            self.process.waitForFinished(2000)
        super().closeEvent(event)


def is_website(folder: Path) -> bool:
    """Whether *folder* is a checkout of this suite's website, WEBSITE_REPO."""
    return (folder / ".git").exists() and origin(folder).lower() == WEBSITE_REPO.lower()


def suite_slug() -> str:
    """The suite's name for a file name: "BC250 Bazzite Suite" becomes bc250-bazzite-suite."""
    return re.sub(r"[^a-z0-9]+", "-", article.suite_name().lower()).strip("-")


def export_folder(parent: Path, now: datetime.datetime | None = None) -> Path:
    """A new folder in *parent* for the article, named by the date and time. It never takes a folder that is there
    already, so an export never writes over anything. A git checkout, as the website's, gets the article itself:
    its files go straight in, over the old ones (owner, 26-11-2026: the dated folder landed in the repository)."""
    if (parent / ".git").exists():
        return parent
    stamp = (now or datetime.datetime.now()).strftime("%Y-%m-%d-%H%M%S")
    name = suite_slug() + "-article"
    folder = parent / f"{name}-{stamp}"
    number = 2
    while folder.exists():
        folder = parent / f"{name}-{stamp}-{number}"
        number += 1
    return folder
