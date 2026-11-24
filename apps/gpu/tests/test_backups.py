# SPDX-License-Identifier: GPL-3.0-or-later
"""The Backups page's list: config.toml.bak-<stamp> newest first, and the config.toml.pre-oc-bisect that PS5 GPU OC
Bisect's --install left (owner, 24-11-2026)."""

from __future__ import annotations

import os
from datetime import datetime


def test_both_kinds_of_backup_are_listed(backend, config_file):
    (config_file.parent / "config.toml.bak-20261120-101500").write_text("a")
    (config_file.parent / "config.toml.bak-20261122-090000").write_text("b")
    old = config_file.parent / "config.toml.pre-oc-bisect"
    old.write_text("c")
    when = datetime(2026, 11, 21, 12, 0).timestamp()
    os.utime(old, (when, when))
    names = [b.path.name for b in backend.list_backups()]
    assert names == ["config.toml.bak-20261122-090000", "config.toml.pre-oc-bisect", "config.toml.bak-20261120-101500"]


def test_without_the_old_backup_only_the_stamped_ones(backend, config_file):
    (config_file.parent / "config.toml.bak-20261120-101500").write_text("a")
    assert [b.path.name for b in backend.list_backups()] == ["config.toml.bak-20261120-101500"]
