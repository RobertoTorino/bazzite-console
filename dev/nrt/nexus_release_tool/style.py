# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus's design for the window (owner, 26-10-2026: a development app takes Nexus's look, not a suite's): the theme
and its colors come from core's nexus.py since 02-11-2026, every development app's; this module keeps the window's
own style sheets on them. The states (the working tree, a build, a release) keep the state family every app shares."""

from pathlib import Path

from bazzite_console_core.nexus import EDGE, INK, MAIN, NEXUS, SILVER, TEAL   # noqa: F401 (the window imports them from here)

# The checkboxes (the table's ticks): a teal box with a teal checkmark, as the selected tab's
# edge, where the platform's own box was dark on dark (owner, 28-10-2026).
CHECK_IMAGE = (Path(__file__).resolve().parent / "check.svg").as_posix()
CHECK_STYLESHEET = (
    "QCheckBox::indicator, QListView::indicator, QTableView::indicator { width:14px; height:14px; "
    f"border:1px solid {TEAL}; border-radius:3px; background:{MAIN}; }}"
    "QCheckBox::indicator:checked, QListView::indicator:checked, QTableView::indicator:checked { "
    f"image:url({CHECK_IMAGE}); }}"
    "QCheckBox::indicator:disabled, QListView::indicator:disabled, QTableView::indicator:disabled { "
    f"border-color:{EDGE}; }}"
)
