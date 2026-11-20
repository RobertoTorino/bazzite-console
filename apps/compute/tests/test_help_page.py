# SPDX-License-Identifier: GPL-3.0-or-later
"""The Help page made from the script's own --help: its title, its sections and its tables."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cu_bisect.help_page import WINDOW, help_html

SCRIPT = Path(__file__).resolve().parents[1] / "ps5-cu-bisect.sh"


def _help() -> str:
    return subprocess.run(["bash", str(SCRIPT), "--help"], capture_output=True, text=True, check=True).stdout


def test_the_scripts_help_becomes_a_page():
    page = help_html(_help())
    assert page.startswith("<h1>ps5-cu-bisect.sh</h1><p class='lead'>finds out whether CU-unlock crashes")
    assert page.index("<h2>How it works</h2>") < page.index("<h2>Options</h2>")
    assert "<td class='name'><b>control</b></td>" in page and "<td class='name'><b>WGP step</b></td>" in page
    assert "<td class='name'><code>-t, --time SECS</code></td><td>GPU load per attempt" in page
    # a continued line belongs to the option above it
    assert "(default: the live masks of a clean boot = the stock driver state)</td>" in page
    assert page.count("<td class='name'><code>-") == 11                       # every option of Usage
    assert "<a href='https://github.com/RobertoTorino/bazzite-console/tree/main/apps/compute'>" in page


def test_what_the_window_does_is_the_first_paragraph():
    page = help_html(_help(), WINDOW)
    first = page.index("<p>This window starts <code>ps5-cu-bisect.sh</code>")
    assert page.index("<p class='lead'>") < first < page.index("<h2>How it works</h2>")


def test_text_is_escaped_and_an_empty_help_says_so():
    assert "&lt;b&gt;" in help_html("tool - a <b> test")
    assert help_html("") == "<p>No help text.</p>"
