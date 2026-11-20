# SPDX-License-Identifier: GPL-3.0-or-later

"""Turns the launcher GUI's choices into a ps5-cu-bisect.sh command line, and the validation
that goes with it - kept free of any Qt import so it's easy to unit-test on its own."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

MASK_RE = re.compile(r"^0x[0-9a-fA-F]{1,2}(,0x[0-9a-fA-F]{1,2}){3}$")

# label -> masks (None = "auto-detect", i.e. don't pass --baseline at all). Short labels, so the field stays narrow
# (owner, 19-11-2026); what each one is, with its masks, is in BASELINE_TIPS, the choice's tooltip.
BASELINE_PRESETS: dict[str, str | None] = {
    "Auto-detect": None,
    "Stock, 24 CUs": "0x07,0x07,0x07,0x07",
    "Unlocked, 40 CUs": "0x1f,0x1f,0x1f,0x1f",
    "Custom...": "",
}
BASELINE_TIPS: dict[str, str] = {
    "Auto-detect": "This boot's own clean masks, the stock driver state: no --baseline is passed. The safest choice.",
    "Stock, 24 CUs": "0x07,0x07,0x07,0x07: 3 WGPs on every row, as the board comes.",
    "Unlocked, 40 CUs": "0x1f,0x1f,0x1f,0x1f: all 5 WGPs on every row.",
    "Custom...": "Any other 4-row mask, typed in the field beside it, as --baseline takes it.",
}


@dataclass
class BisectOptions:
    time_secs: int = 180
    rounds: int = 3
    baseline: str = ""           # resolved mask string, empty = auto-detect
    control_only: bool = False
    same_boot: bool = False
    unattended: bool = False     # --auto
    no_watch: bool = False

    def validate(self) -> list[str]:
        errors = []
        if self.time_secs < 60:
            errors.append("Load time must be at least 60 seconds.")
        if not 1 <= self.rounds <= 9:
            errors.append("Rounds must be between 1 and 9.")
        elif not self.control_only and self.rounds < 2:
            errors.append("Rounds must be at least 2 (control-only runs may use 1).")
        if self.baseline and not MASK_RE.match(self.baseline):
            errors.append("Baseline needs 4 masks, e.g. 0x07,0x07,0x07,0x07")
        return errors

    def to_args(self) -> list[str]:
        args = ["-t", str(self.time_secs), "-r", str(self.rounds)]
        if self.baseline:
            args += ["--baseline", self.baseline]
        if self.control_only:
            args.append("--control-only")
        if self.same_boot:
            args.append("--same-boot")
        if self.unattended:
            args.append("--auto")
        if self.no_watch:
            args.append("--no-watch")
        return args

    def to_command(self, script: str) -> str:
        """Full shell command line, quoted for safe use with ``bash -lc``."""
        return shlex.join(["bash", script, *self.to_args()])
