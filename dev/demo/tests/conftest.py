# SPDX-License-Identifier: GPL-3.0-or-later
"""The compatibility core from run.sh and the app's package."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = Path(__file__).resolve().parents[1]
CORE = APP.parents[1] / "core"
for path in (APP.parents[1] / "dev" / "core_compat", CORE, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(scope="session")
def qapp():
    """The application with Nexus's theme, as create_app() sets it for this app."""
    from nexus_core import widgets
    from nexus_core.nexus import NEXUS
    from PyQt6.QtWidgets import QApplication
    widgets.set_theme(NEXUS)
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def settings_in_a_temp_folder(tmp_path):
    """The .ini settings in a temp folder: no test reads the user's own."""
    from PyQt6.QtCore import QSettings
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "config"))
