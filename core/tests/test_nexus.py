# SPDX-License-Identifier: GPL-3.0-or-later
"""nexus.py: the development apps' design and their header, which names the checkout's commit in place of a
version."""

from __future__ import annotations

import datetime
import subprocess

from bazzite_console_core import nexus


def test_amsterdam_time_is_cet_in_winter_and_cest_in_summer():
    utc = datetime.timezone.utc
    assert nexus.amsterdam_now(datetime.datetime(2026, 1, 15, 12, 0, tzinfo=utc)) == datetime.datetime(2026, 1, 15, 13)
    assert nexus.amsterdam_now(datetime.datetime(2026, 7, 15, 12, 0, tzinfo=utc)) == datetime.datetime(2026, 7, 15, 14)
    # The switches: the last Sundays of March (29-03-2026) and October (25-10-2026), at 01:00 UTC.
    assert nexus.amsterdam_now(datetime.datetime(2026, 3, 29, 0, 59, tzinfo=utc)).hour == 1
    assert nexus.amsterdam_now(datetime.datetime(2026, 3, 29, 1, 0, tzinfo=utc)).hour == 3
    assert nexus.amsterdam_now(datetime.datetime(2026, 10, 25, 0, 59, tzinfo=utc)).hour == 2
    assert nexus.amsterdam_now(datetime.datetime(2026, 10, 25, 1, 0, tzinfo=utc)).hour == 2


def _commit(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_AUTHOR_DATE": "2026-11-15T06:20:00Z", "GIT_COMMITTER_DATE": "2026-11-15T06:20:00Z", "HOME": str(root)}
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=env)
    (root / "README").write_text("x\n")
    subprocess.run(["git", "add", "README"], cwd=root, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "x"], cwd=root, check=True, env=env)
    return root, subprocess.run(["git", "log", "-1", "--format=%h"], cwd=root, capture_output=True,
                                text=True).stdout.strip()


def test_the_stamp_names_the_commit_and_its_time(tmp_path):
    root, sha = _commit(tmp_path)
    assert nexus.checkout_commit(root) == (sha, "15-11-2026 07:20")
    assert nexus.checkout_stamp(root) == f"{sha} · 15-11-2026 07:20"
    elsewhere = tmp_path / "not-a-checkout"
    elsewhere.mkdir()
    assert nexus.checkout_stamp(elsewhere) == "" and nexus.checkout_commit(elsewhere) == ("", "")


def test_the_header_shows_the_stamp_without_a_version(qapp, tmp_path):
    root, sha = _commit(tmp_path)
    head = nexus.header(tmp_path / "logo.webp", "Nexus Sound Lab", root)
    text = head.title.text()
    assert text.startswith("Nexus Sound Lab  <span") and f">{sha} · 15-11-2026 07:20</span>" in text
    assert ">v" not in text
    assert nexus.header(tmp_path / "logo.webp", "Nexus Sound Lab", tmp_path / "nowhere").title.text() == \
        "Nexus Sound Lab"
