# SPDX-License-Identifier: GPL-3.0-or-later

"""Decides whether ps5-cu-bisect.sh's own recorded results accept a combined mask for install.

Nothing here runs the bisect script or any register write; it only reads the state the script already
keeps in ~/.local/share/ps5-cu-bisect/. A mask is only accepted once that state proves:

  - it was retested as its own baseline (umr-config BASE), with every WGP in it unlocked, so the
    recorded run has no individual "SEx.SHy.WGPn" items left, only "control";
  - every round of that retest is recorded with outcome PASS (no crash, no drift, no mismatch);
  - no attempt is still marked as in progress (umr-pending would mean an interrupted run); and
  - every one of the 4 shader-array rows has 3, 4 or 5 WGPs unlocked: 24 CUs (3 on every row, stock) up to 40 CUs
    (5 on every row, max). The two shader engines (SE0 and SE1, two rows each) run in step: a mask runs like 4 CUs
    for each WGP in its smaller engine (measured, see the CU Unlock wiki chapter). A mask with more WGPs in one
    engine is accepted, and the result says what it runs like.

This mirrors the "retest the combination" step ps5-cu-bisect.sh's own summary suggests
(--reset && --baseline <masks> --control-only --rounds N) - the GUI just checks that step was actually
done and passed.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

STATE_DIR = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share")) / "ps5-cu-bisect"
CONFIG = STATE_DIR / "umr-config"
RUNS = STATE_DIR / "umr-runs.tsv"
PENDING = STATE_DIR / "umr-pending"

MASK_RE = re.compile(r"^0x[0-9a-fA-F]{1,2}(,0x[0-9a-fA-F]{1,2}){3}$")
# Outcomes that count as a failed attempt in ps5-cu-bisect.sh (same FAIL_RE as the script).
FAIL_RE = re.compile(r"^(CRASH-APPLY|CRASH-LOAD|FAULT|ERRORS|LOAD-FAIL|DRIFT|MISMATCH)$")
INCOMPLETE = {"ABORTED", "SKIPPED", ""}
# WGPs per shader-array row -> total CUs of the even levels; a row of an installable mask has one of these counts.
LEVELS = {3: 24, 4: 32, 5: 40}


def popcount(n: int) -> int:
    return bin(n & 0x1F).count("1")


def cu_count(masks: str) -> int:
    return sum(popcount(int(m, 16)) for m in masks.split(",")) * 2


def even_level(masks: str) -> int | None:
    """WGPs-per-row if `masks` is one of the three allowed even levels, else None."""
    counts = {popcount(int(m, 16)) for m in masks.split(",")}
    if len(counts) != 1:
        return None
    level = counts.pop()
    return level if level in LEVELS else None


@dataclass
class GateResult:
    accepted: bool
    masks: str | None = None
    cu_total: int | None = None
    # Human-readable lines: the reason(s) it was rejected, or a confirmation of what passed.
    reasons: list[str] = field(default_factory=list)


def _read_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    if CONFIG.is_file():
        for line in CONFIG.read_text(errors="replace").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k] = v
    return cfg


def check() -> GateResult:
    if not CONFIG.is_file():
        return GateResult(False, reasons=[
            f"No ps5-cu-bisect.sh results found in {STATE_DIR}. Run that script first."])

    cfg = _read_config()
    base = cfg.get("BASE", "")
    if not MASK_RE.match(base):
        return GateResult(False, reasons=[f"No usable baseline recorded ({base or 'none'!r})."])

    if PENDING.is_file():
        return GateResult(False, masks=base, reasons=[
            "An attempt is still marked as in progress, because umr-pending exists. Finish that bisect run, "
            "or restart and let it resume. Only then can the results accept this mask."])

    rows = [int(m, 16) for m in base.split(",")]
    counts = [popcount(m) for m in rows]
    if any(c not in LEVELS for c in counts):
        return GateResult(False, masks=base, reasons=[
            f"The recorded baseline ({base}) unlocks {'/'.join(map(str, counts))} WGPs on the 4 rows. Every row "
            "needs 3, 4 or 5 WGPs: 24 CUs (stock) up to 40 CUs (max)."])

    try:
        rounds = int(cfg.get("ROUNDS", "0") or 0)
    except ValueError:
        rounds = 0

    if not RUNS.is_file():
        return GateResult(False, masks=base, reasons=["No attempts recorded yet for this baseline."])

    items: set[str] = set()
    control: dict[int, str] = {}
    for line in RUNS.read_text(errors="replace").splitlines():
        cols = line.split("\t")
        if len(cols) < 6:
            continue
        round_s, item, outcome = cols[2], cols[3], cols[5]
        items.add(item)
        if item == "control":
            try:
                control[int(round_s)] = outcome
            except ValueError:
                pass

    extra = sorted(items - {"control"})
    if extra:
        return GateResult(False, masks=base, reasons=[
            f"This baseline still has {len(extra)} WGP(s) under individual test ({', '.join(extra[:4])}"
            f"{', ...' if len(extra) > 4 else ''}). That's a bisect run, not yet the retest of a final, "
            "fully combined mask. Retest it with the command below.",
            f"./ps5-cu-bisect.sh --reset && ./ps5-cu-bisect.sh --baseline {base} --control-only --rounds 1"])

    if rounds < 1 or len(control) < rounds:
        return GateResult(False, masks=base, reasons=[
            f"Only {len(control)} of {rounds or '?'} retest round(s) are recorded so far."])

    failed = {r: o for r, o in control.items() if FAIL_RE.match(o) or o in INCOMPLETE}
    if failed:
        bad = ", ".join(f"round {r}: {o or 'incomplete'}" for r, o in sorted(failed.items()))
        return GateResult(False, masks=base, reasons=[f"The retest did not pass every round ({bad})."])

    total = cu_count(base)
    if len(set(counts)) != 1:
        speed = 4 * min(counts[0] + counts[1], counts[2] + counts[3])
        reasons = [f"{base} ({total} CUs, {'/'.join(map(str, counts))} WGPs on the 4 shader-array rows) passed "
                   f"{rounds} retest round(s) as its own baseline."]
        if speed != total:
            reasons.append(f"Its two halves differ, so it runs as fast as {speed} CUs.")
        return GateResult(True, masks=base, cu_total=total, reasons=reasons)
    return GateResult(True, masks=base, cu_total=total, reasons=[
        f"{base} ({total} CUs, {counts[0]} WGPs on each of the 4 shader-array rows) passed "
        f"{rounds} retest round(s) as its own baseline."])
