# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus's design for the development apps (dev/: Nexus Dashboard for PS5, Nexus Release Tool, Nexus Demo Recorder,
Nexus Installer Tests, Nexus Sound Lab, Nexus Deps; owner, 26-10-2026: a development app takes Nexus's look, not a
suite's): the colors of the Nexus page, ink, silver and teal, as a theme for core's widgets, set with
create_app(theme=NEXUS). The states (the working tree, a build, a release) keep the state family every app shares.

A development app is never released and has no version (owner, 15-11-2026): its header names the checkout's last
commit and its time instead (checkout_stamp(), header()), so it says which code runs."""

from __future__ import annotations

import datetime
import os
import subprocess
from pathlib import Path

from .theme import Theme, muted

INK = "#010101"                         # the window, the header, the dialogs; every other row
MAIN = "#0f0f0f"                        # the fields, lists and tables; the top of a sheen
SILVER = "#c0c0c0"                      # the text
TEAL = "#17b6a7"                        # the accent: selection, focus, hover, the main action
EDGE = "#66808080"                      # the page's dimmed silver at 40 %: borders and the neutral edge

NEXUS = Theme("Nexus", True, window=INK, base=MAIN, alt=INK, text=SILVER, button=MAIN, button_low=INK, edge=EDGE,
              accent=TEAL, accent_text=INK)


def amsterdam_now(now: datetime.datetime | None = None) -> datetime.datetime:
    """Europe/Amsterdam time without a tz database: CET, CEST from the last Sunday of March to the last Sunday of
    October, switching at 01:00 UTC."""
    utc = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)

    def last_sunday(month: int) -> datetime.datetime:
        day = datetime.datetime(utc.year, month, 31, 1, tzinfo=datetime.timezone.utc)
        return day - datetime.timedelta(days=(day.weekday() + 1) % 7)

    summer = last_sunday(3) <= utc < last_sunday(10)
    return (utc + datetime.timedelta(hours=2 if summer else 1)).replace(tzinfo=None)


def checkout_commit(root: Path) -> tuple[str, str]:
    """The checkout's last commit, short, and its time in Amsterdam ("c109b51", "15-10-2026 03:46"); ("", "")
    outside a git checkout."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h %ct"], cwd=root, capture_output=True, text=True,
                             env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}).stdout.split()
    except OSError:
        return "", ""
    if len(out) != 2 or not out[1].isdigit():
        return "", ""
    when = amsterdam_now(datetime.datetime.fromtimestamp(int(out[1]), datetime.timezone.utc))
    return out[0], f"{when:%d-%m-%Y %H:%M}"


def checkout_stamp(root: Path) -> str:
    """The checkout's last commit and its time in Amsterdam ("c109b51 · 15-10-2026 03:46"), what a development app's
    header shows in place of a version; "" outside a git checkout."""
    commit, when = checkout_commit(root)
    return f"{commit} · {when}" if commit else ""


def header(logo: str | Path, name: str, root: Path):
    """A development app's AppHeader (core's widgets): its icon and name, with the checkout's stamp where a released
    app shows its version."""
    from .widgets import AppHeader, current_theme
    found = AppHeader(logo, name)
    stamp = checkout_stamp(root)
    if stamp:
        found.title.setText(f"{name}  <span style='color:{muted(current_theme())}; font-size:14px;'>{stamp}</span>")
    return found


__all__ = ["EDGE", "INK", "MAIN", "NEXUS", "SILVER", "TEAL", "amsterdam_now", "checkout_commit", "checkout_stamp",
           "header"]
