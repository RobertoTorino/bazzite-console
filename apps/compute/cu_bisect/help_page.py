# SPDX-License-Identifier: GPL-3.0-or-later
"""The Help page (owner, 19-11-2026: "a real styled page", not the raw text): ps5-cu-bisect.sh's own --help,
the single source of what the options do, turned into a page. Its parts, in the order the script prints them:

  * the first line, "name - what it does.": the page's title and its summary, then what the window does (WINDOW),
    the first paragraph (owner, 19-11-2026: the text of the title's info symbol moved here);
  * paragraphs: text in plain sentences, under "How it works";
  * a list of terms ("  control   the same register writes ..."): a table of the term and its meaning;
  * the "Usage:" block: the command line, then a table of each option and what it does, under "Options";
  * a line that is a link: the page's last line.

A line indented deeper than its block's first continues the entry above it. No Qt here, so the tests read it alone."""

from __future__ import annotations

import html
import re

WINDOW = ("This window runs <code>ps5-cu-bisect.sh</code> for you, in four steps. The scan reads the board. "
          "The safety check tests the unlock method. Then each locked WGP is tested, and you choose 24, 32 or 40 CUs. "
          "The window restarts the board between attempts and goes on after the login. Below is the script's own "
          "help, for the options under <b>Show advanced</b>.")

_TERM = re.compile(r"^  (\S(?:.*?\S)?)\s{2,}(\S.*)$")             # "  control   the same register writes"
_OPTION = re.compile(r"^\s{2,6}(-\S.*?)\s{2,}(\S.*)$")            # "  -t, --time SECS       GPU load per attempt"


def _blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = [[]]
    for line in text.rstrip().splitlines():
        if line.strip():
            blocks[-1].append(line.rstrip())
        elif blocks[-1]:
            blocks.append([])
    return [block for block in blocks if block]


def _entries(lines: list[str], pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    """(name, what) for each line *pattern* matches; a line it does not match continues the entry above."""
    entries: list[tuple[str, str]] = []
    for line in lines:
        found = pattern.match(line)
        if found and (pattern is _OPTION or line[2] != " "):
            entries.append((found.group(1), found.group(2)))
        elif entries:
            name, what = entries[-1]
            entries[-1] = (name, f"{what} {line.strip()}")
    return entries


def _table(entries: list[tuple[str, str]], code: bool) -> str:
    def name(text: str) -> str:
        return f"<code>{html.escape(text)}</code>" if code else f"<b>{html.escape(text)}</b>"
    rows = "".join(f"<tr><td class='name'>{name(n)}</td><td>{html.escape(w)}</td></tr>" for n, w in entries)
    return f"<table>{rows}</table>"


def _is_terms(block: list[str]) -> bool:
    return all(line.startswith("  ") for line in block) and bool(_TERM.match(block[0]))


def help_html(text: str, window: str = "") -> str:
    """The body of the Help page from the script's --help *text*; *window* (rich text) is its first paragraph."""
    blocks = _blocks(text)
    if not blocks:
        return "<p>No help text.</p>"
    first, *rest = blocks
    title, _sep, summary = first[0].partition(" - ")
    parts = [f"<h1>{html.escape(title)}</h1>"]
    lead = " ".join([summary, *first[1:]]).strip()
    if lead:
        parts.append(f"<p class='lead'>{html.escape(lead)}</p>")
    if window:
        parts.append(f"<p>{window}</p>")
    heading = False
    for block in rest:
        if block[0].startswith("Usage:"):
            parts.append("<h2>Options</h2>")
            parts.append(f"<p><code>{html.escape(block[0].removeprefix('Usage:').strip())}</code></p>")
            parts.append(_table(_entries(block[1:], _OPTION), code=True))
        elif len(block) == 1 and re.match(r"^https?://\S+$", block[0]):
            url = html.escape(block[0], quote=True)
            parts.append(f"<p class='more'>More in the wiki and the code: <a href='{url}'>{url}</a></p>")
        else:
            if not heading:
                parts.append("<h2>How it works</h2>")
                heading = True
            if _is_terms(block):
                parts.append(_table(_entries(block, _TERM), code=False))
            else:
                parts.append(f"<p>{html.escape(' '.join(line.strip() for line in block))}</p>")
    return "".join(parts)


def page_style(accent: str, muted: str, line: str) -> str:
    """The page's look in the suite's theme: the accent for the headings, a muted lead, ruled tables."""
    return (f"h1 {{ font-size:22px; font-weight:800; margin:0 0 4px 0; }}"
            f"h2 {{ font-size:16px; font-weight:700; color:{accent}; margin:18px 0 6px 0; }}"
            f"p {{ margin:0 0 8px 0; line-height:135%; }}"
            f"p.lead {{ color:{muted}; font-size:14px; }}"
            f"p.more {{ color:{muted}; margin-top:14px; }}"
            f"table {{ border-collapse:collapse; margin:4px 0 10px 0; }}"
            f"td {{ padding:5px 10px; border-bottom:1px solid {line}; vertical-align:top; }}"
            f"td.name {{ white-space:nowrap; }}"
            f"a {{ color:{accent}; }}")
