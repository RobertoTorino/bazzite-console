# SPDX-License-Identifier: GPL-3.0-or-later
"""Help: renders the app's chapter of the suite manual (and the other .md files it links to) inside the app.

A release ships the chapter as MANUAL.md (tools/stage_app.py copies docs/apps/board.md); in the checkout
the chapter itself is read. Links to other chapters of the manual open the published manual in the browser."""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QPalette, QTextCursor, QTextDocument
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QListWidget, QTextBrowser, QVBoxLayout, QWidget

from bazzite_console_core import SUITE_MANUAL_URL
from bazzite_console_core.widgets import ActionPill, same_width

from . import LOGO_PATH

DOCS_DIR = Path(__file__).resolve().parent.parent
MANUAL_PAGE = "apps/board.md"                # the chapter, under the suite's docs/
_ATTR_LIST = re.compile(r"\{\s*[.#][^}]*\}")         # MkDocs' { .class } after an image


def manual_path(app_dir: Path = DOCS_DIR) -> Path:
    """MANUAL.md of a release or an installed copy, the chapter in the checkout, else the README."""
    for path in (app_dir / "MANUAL.md", app_dir.parent.parent / "docs" / MANUAL_PAGE):
        if path.is_file():
            return path
    return app_dir / "README.md"


def manual_markdown(text: str, app_dir: Path = DOCS_DIR) -> str:
    """The chapter as Qt can show it: no MkDocs attribute lists, and its pictures from the app's images/."""
    text = _ATTR_LIST.sub("", text)
    return text.replace("](../assets/bazzite/", f"]({(app_dir / 'images').as_posix()}/")


def online_url(link: str) -> str:
    """A relative link of the chapter as the address of that page in the published manual."""
    path, _, fragment = link.partition("#")
    page = posixpath.normpath(posixpath.join(posixpath.dirname(MANUAL_PAGE), path))
    if page == "index.md" or page.endswith("/index.md"):
        page = page.removesuffix("index.md")
    else:
        page = page.removesuffix(".md") + "/"
    return SUITE_MANUAL_URL + page + (f"#{fragment}" if fragment else "")


# Qt's Markdown import gives tables no borders and code no background; this restyles the HTML it produces.
# A readable page (owner, 22-11-2026): larger type, room between lines and above headings, plain bullets.
_CSS = """
p, li { line-height: 130%; }
p { margin-bottom: 10px; }
h1 { font-size: 30px; margin: 0 0 6px 0; }
h2 { font-size: 23px; margin-top: 34px; margin-bottom: 8px; }
h3 { font-size: 18px; margin-top: 22px; margin-bottom: 4px; }
table { border-collapse: collapse; margin: 10px 0 16px 0; }
th { background: #3a3f4b; color: white; padding: 7px 10px; text-align: left; }
td { border: 1px solid #4a4f58; padding: 6px 10px; }
pre { background: #1a1b20; color: #e8e8e8; padding: 12px; font-family: monospace; font-size: 14px; }
code { background: rgba(127,127,127,0.20); font-family: monospace; font-size: 14px; }
ul { list-style-type: disc; }
ul ul { list-style-type: disc; }
"""
FONT_PX = 16                                # the text's size
COLUMN = 860                                # the reading column's width at most, in pixels: about 90 characters
LOGO_PX = 72                                # the app's icon above the title, in place of the chapter's large picture
_PICTURE = re.compile(r"^!\[[^\]]*\]\([^)]*\)[ \t]*$", re.M)
_HEADING = re.compile(r"^(#{1,2}) (.+?)\s*$")


def headings(text: str) -> list[tuple[int, str]]:
    """The page's title and sections (# and ##) for the contents list, outside code blocks."""
    found, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        match = None if fenced else _HEADING.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2)))
    return found


def _slug(text: str) -> str:
    return re.sub(r"[^\w\- ]", "", text.lower()).strip().replace(" ", "-")


class ReadmeView(QWidget):
    """The chapter as a readable page: a contents list on the left, a search field, Back and Wiki, and the text in a
    column of about 90 characters."""

    def __init__(self, path: Path | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.contents = QListWidget()
        self.contents.setFixedWidth(260)
        self.contents.setWordWrap(True)
        self.contents.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.contents.setStyleSheet("QListWidget { border: none; padding: 12px 6px; font-size: 14px; }"
                                    "QListWidget::item { padding: 6px 8px; }")
        self.contents.itemClicked.connect(lambda item: self._scroll_to_heading(_slug(item.text())))
        layout.addWidget(self.contents)

        right = QVBoxLayout()
        right.setContentsMargins(16, 10, 16, 0)
        bar = QHBoxLayout()
        self.find = QLineEdit()
        self.find.setPlaceholderText("Find in the help")
        self.find.setClearButtonEnabled(True)
        self.find.setMinimumHeight(40)
        self.find.setMaximumWidth(360)
        self.find.returnPressed.connect(self.find_next)
        bar.addWidget(self.find)
        bar.addStretch(1)
        self.back = ActionPill("Back", "The page before", "Back to the page before, after you followed a link")
        self.back.clicked.connect(self._go_back)
        self.wiki = ActionPill("Wiki", "Open it in the browser", "This page in the wiki, in your browser")
        self.wiki.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.wiki_url())))
        same_width([self.back, self.wiki])
        bar.addWidget(self.back)
        bar.addWidget(self.wiki)
        right.addLayout(bar)

        self.browser = QTextBrowser()
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        palette = self.browser.palette()
        palette.setColor(QPalette.ColorRole.Base, palette.color(QPalette.ColorRole.Window))
        self.browser.setPalette(palette)
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._follow)
        self.browser.verticalScrollBar().valueChanged.connect(self._follow_scroll)
        right.addWidget(self.browser, 1)
        layout.addLayout(right, 1)

        self._history: list[Path] = []
        path = path or manual_path()
        self._manual = path
        self._current = path
        self.load(path)

    def load(self, path: Path, push: bool = False) -> None:
        if push:
            self._history.append(self._current)
        self._current = path
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.browser.setPlainText(f"Could not read {path}: {exc}")
            return
        doc = QTextDocument(self.browser)
        doc.setMetaInformation(QTextDocument.MetaInformation.DocumentUrl, QUrl.fromLocalFile(str(path)).toString())
        doc.setBaseUrl(QUrl.fromLocalFile(str(path.parent) + "/"))
        doc.setDocumentMargin(24)
        font = self.browser.font()
        font.setPixelSize(FONT_PX)
        doc.setDefaultFont(font)
        logo = ""
        if path == self._manual:
            text = _PICTURE.sub("", manual_markdown(text), count=1)          # the large picture at the top
            if LOGO_PATH.is_file():
                logo = f'<img src="{QUrl.fromLocalFile(str(LOGO_PATH)).toString()}" width="{LOGO_PX}">'
        doc.setMarkdown(text, QTextDocument.MarkdownFeature.MarkdownDialectGitHub)
        html = doc.toHtml()
        if logo:
            html = html.replace("<h1", logo + "<h1", 1)
        doc.setDefaultStyleSheet(_CSS)
        doc.setHtml(html)
        self.browser.setDocument(doc)
        self.contents.clear()
        for level, title in headings(text):
            self.contents.addItem(title)
            if level == 1:
                item = self.contents.item(self.contents.count() - 1)
                bold = item.font()
                bold.setBold(True)
                item.setFont(bold)
        if self.contents.count():
            self.contents.setCurrentRow(0)
        self.back.setEnabled(bool(self._history))

    def wiki_url(self) -> str:
        """The page shown now, in the published wiki."""
        if self._current == self._manual:
            return online_url(posixpath.basename(MANUAL_PAGE))
        return online_url(self._current.name)

    def find_next(self) -> None:
        """The next place the search field's text is on the page, from the top again after the last one."""
        text = self.find.text()
        if text and not self.browser.find(text):
            self.browser.moveCursor(QTextCursor.MoveOperation.Start)
            self.browser.find(text)

    def _follow_scroll(self, _value: int) -> None:
        """The contents list marks the section that is at the top of the page."""
        top = self.browser.cursorForPosition(QPoint(0, 0)).block()
        while top.isValid() and not top.blockFormat().headingLevel():
            top = top.previous()
        if top.isValid():
            for row in range(self.contents.count()):
                if _slug(self.contents.item(row).text()) == _slug(top.text()):
                    self.contents.blockSignals(True)
                    self.contents.setCurrentRow(row)
                    self.contents.blockSignals(False)
                    break

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        spare = max(0, self.browser.width() - COLUMN) // 2
        self.browser.setViewportMargins(spare, 0, spare, 0)

    def _follow(self, url: QUrl) -> None:
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return
        if not url.path() and url.fragment():
            self._scroll_to_heading(url.fragment())
            return
        target = (self._current.parent / url.path()).resolve() if not url.isLocalFile() else Path(url.toLocalFile())
        if target.suffix.lower() == ".md" and target.is_file():
            self.load(target, push=True)
        elif target.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        elif self._current == self._manual and not url.isLocalFile():
            # Another chapter of the manual, which the app does not ship.
            link = url.path() + (f"#{url.fragment()}" if url.fragment() else "")
            QDesktopServices.openUrl(QUrl(online_url(link)))

    def _scroll_to_heading(self, fragment: str) -> None:
        """GitHub-style #anchor -> the heading with that slug (Qt's Markdown import adds no anchors)."""
        block = self.browser.document().begin()
        while block.isValid():
            if block.blockFormat().headingLevel() and _slug(block.text()) == fragment.lower():
                cursor = QTextCursor(block)
                self.browser.setTextCursor(cursor)
                bar = self.browser.verticalScrollBar()
                bar.setValue(bar.maximum())
                self.browser.ensureCursorVisible()     # from the bottom, so the heading lands at the top
                return
            block = block.next()

    def _go_back(self) -> None:
        if self._history:
            self.load(self._history.pop())
