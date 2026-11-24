# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop notifications through notify-send (the desktop's notification service), as Board Test's. The end of a CU
test is critical and never expires, so it waits on the screen until you click it (owner, 23-11-2026: know that the
test ended without watching the window)."""

from __future__ import annotations

import shutil

from PyQt6.QtCore import QProcess

from . import APP_NAME, ROOT

ICON_PATH = ROOT / "images" / "ps5-cu-bisect-128.png"


def notify(summary: str, body: str) -> bool:
    """Show a desktop notification that stays; False when the desktop offers no notify-send."""
    exe = shutil.which("notify-send")
    if not exe:
        return False
    args = ["--app-name", APP_NAME, "--icon", str(ICON_PATH), "--urgency", "critical", "--expire-time", "0",
            summary, body]
    ok, _pid = QProcess.startDetached(exe, args)
    return ok
