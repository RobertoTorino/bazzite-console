# SPDX-License-Identifier: GPL-3.0-or-later
"""The Help page made from the script's own --help: its title, its sections and its tables."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cores_bisect.help_page import WINDOW, help_html

SCRIPT = Path(__file__).resolve().parents[1] / "ps5-cores-bisect.sh"


def _help() -> str:
    return subprocess.run(["bash", str(SCRIPT), "--help"], capture_output=True, text=True, check=True).stdout


def test_the_scripts_help_becomes_a_page():
    page = help_html(_help())
    assert page.startswith("<h1>ps5-cores-bisect.sh</h1><p class='lead'>finds out whether the PS5&#x27;s 2 fused-off")
    assert page.index("<h2>How it works</h2>") < page.index("<h2>Options</h2>")
    assert "<td class='name'><b>control</b></td>" in page and "<td class='name'><b>post-control</b></td>" in page
    assert "<td class='name'><code>-t, --time SECS</code></td><td>CPU load per attempt" in page
    assert "<td class='name'><code>--mprime-bin PATH</code></td><td>mprime binary" in page   # one space before
    # a continued line belongs to the option above it
    assert "login until every item is done. This needs the autostart unit, see the wiki.</td>" in page
    assert page.count("<td class='name'><code>-") == 13                       # every option of Usage
    assert "<a href='https://github.com/RobertoTorino/bazzite-console/tree/main/apps/cores'>" in page


def test_a_sentence_above_a_list_of_terms_is_its_paragraph():
    """'For a longer, harsher burn-in ...' then --load and --rasdaemon: a paragraph and a table, not one run-on line."""
    page = help_html(_help())
    assert "<p>For a longer, harsher burn-in there are two optional extras, both off by default:</p><table>" in page
    assert "<td class='name'><b>--rasdaemon</b></td>" in page


def test_what_the_window_does_is_the_first_paragraph():
    page = help_html(_help(), WINDOW)
    first = page.index("<p>This window runs <code>ps5-cores-bisect.sh</code>")
    assert page.index("<p class='lead'>") < first < page.index("<h2>How it works</h2>")


def test_text_is_escaped_and_an_empty_help_says_so():
    assert "&lt;b&gt;" in help_html("tool - a <b> test")
    assert help_html("") == "<p>No help text.</p>"
