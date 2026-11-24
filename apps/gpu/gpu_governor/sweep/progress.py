# SPDX-License-Identifier: GPL-3.0-or-later

"""Where a GPU sweep stands, read from what ps5-gpu-sweep.sh keeps in ~/.local/share/ps5-gpu-sweep/: the snapshot
of the governor's config, the plan, the verdict of every step and the next attempt. The rules are the script's own
(build_plan, item_verdict, item_pruned, next_attempt and the install's margin pick); tests/test_sweep_progress.py
holds them against the script. No Qt here, and nothing is written but the window's own file, sweep-wizard.

The parts of a sweep: "control" is the config's top point, unchanged. "oc" raises the clock one step at a time at a
fixed voltage, and "uv" lowers the voltage one step at a time at the top clock. Install writes the best step that
passed every round."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

FAIL_RE = re.compile(r"^(CRASH-LOAD|FAULT|ERRORS|LOAD-FAIL|NO-REACH|GOV-FAIL)$")
PARTS = ("control", "oc", "uv")
GOVERNORS = ("smu", "tt")
ETC = Path("/etc")

# The script's defaults and rails (ps5-gpu-sweep.sh).
DEFAULTS = {"TIME": 180, "ROUNDS": 3, "MAX_FREQ": 2200, "MIN_VOLT": 850, "FREQ_STEP": 50, "VOLT_STEP": 25}


def state_dir() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share")) / "ps5-gpu-sweep"


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def safe_points(text: str) -> list[tuple[int, int]]:
    """(frequency, voltage) of every [[safe-points]] block, lowest frequency first, as the script's all_safepoints."""
    points, inside, f, v = [], False, "", ""
    for line in text.splitlines():
        if line.startswith("[[safe-points]]"):
            inside, f, v = True, "", ""
            continue
        if line.startswith("["):
            inside = False
        if not inside:
            continue
        body = line.split("#", 1)[0]
        if re.match(r"\s*frequency\s*=", body):
            f = re.sub(r"[^0-9]", "", body)
        elif re.match(r"\s*voltage\s*=", body):
            v = re.sub(r"[^0-9]", "", body)
        if f and v:
            points.append((int(f), int(v)))
            f, v = "", ""
    return sorted(points)


def config_path(governor: str, etc: Path | None = None) -> Path:
    return (etc or ETC) / f"cyan-skillfish-governor-{governor}" / "config.toml"


def service_active(governor: str) -> bool:
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", f"cyan-skillfish-governor-{governor}"],
                              timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def find_governor(etc: Path | None = None, active=None) -> str:
    """smu or tt as the script's find_governor: the one whose service runs, else the only one with a config; "" when
    none is there, or both are and neither runs."""
    active = active or service_active
    found = [g for g in GOVERNORS if os.access(config_path(g, etc), os.R_OK)]
    for governor in found:
        if active(governor):
            return governor
    return found[0] if len(found) == 1 else ""


def read_points(path: Path) -> list[tuple[int, int]]:
    try:
        return safe_points(path.read_text(errors="replace"))
    except OSError:
        return []


@dataclass
class Attempt:
    round: int
    item: str
    freq: str
    volt: str
    outcome: str
    note: str = ""


def read_runs(path: Path) -> list[Attempt]:
    """runs.tsv: time, boot, round, step, MHz, mV, outcome, errors, faults, max temp, max clock, max busy, note."""
    attempts = []
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return attempts
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 7:
            continue
        try:
            rnd = int(cols[2])
        except ValueError:
            continue
        attempts.append(Attempt(rnd, cols[3], cols[4], cols[5], cols[6], cols[12] if len(cols) > 12 else ""))
    return attempts


def read_config(path: Path) -> dict[str, str]:
    cfg: dict[str, str] = {}
    try:
        for line in path.read_text(errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                cfg.setdefault(key, value)          # cfg_get takes the first
    except OSError:
        pass
    return cfg


def part(item: str) -> str:
    return item.split(":", 1)[0]


@dataclass
class Progress:
    started: bool = False
    governor: str = ""
    top: tuple[int, int] | None = None              # the snapshot's top safe-point
    points: list[tuple[int, int]] = field(default_factory=list)
    rounds: int = DEFAULTS["ROUNDS"]
    time_secs: int = DEFAULTS["TIME"]
    max_freq: int = DEFAULTS["MAX_FREQ"]
    min_volt: int = DEFAULTS["MIN_VOLT"]
    freq_step: int = DEFAULTS["FREQ_STEP"]
    volt_step: int = DEFAULTS["VOLT_STEP"]
    oc_volt: int = 0
    sweep: str = "oc,uv,"
    attempts: list[Attempt] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)   # round item freq volt boot of an unfinished attempt
    installed: str = ""                                # "freq volt backup" after --install

    # --------------------------------------------------------------- the plan
    @property
    def items(self) -> list[str]:
        """The steps, as build_plan: control, then oc:FREQ up to the highest clock, then uv:VOLT down to the lowest."""
        if self.top is None:
            return []
        top_f, top_v = self.top
        items = ["control"]
        if "oc," in self.sweep and self.freq_step > 0:
            items += [f"oc:{f}" for f in range(top_f + self.freq_step, self.max_freq + 1, self.freq_step)]
        if "uv," in self.sweep and self.volt_step > 0:
            items += [f"uv:{v}" for v in range(top_v - self.volt_step, self.min_volt - 1, -self.volt_step)]
        return items

    def point(self, item: str) -> tuple[int, int]:
        top_f, top_v = self.top or (0, 0)
        name, _, value = item.partition(":")
        if name == "oc":
            return int(value), self.oc_volt or top_v
        if name == "uv":
            return top_f, int(value)
        return top_f, top_v

    def items_of(self, name: str) -> list[str]:
        return [it for it in self.items if part(it) == name]

    # ------------------------------------------------------------- verdicts
    def tries(self, item: str) -> list[str]:
        return [a.outcome for a in self.attempts if a.item == item and a.outcome not in ("ABORTED", "SKIPPED")]

    def verdict(self, item: str) -> str:
        """none, good, bad, failing or random, as item_verdict: aborted and skipped attempts don't count."""
        outs = self.tries(item)
        if not outs:
            return "none"
        fails = sum(1 for o in outs if FAIL_RE.match(o))
        if fails == 0:
            return "good"
        if fails == len(outs):
            return "bad" if len(outs) >= 2 else "failing"
        return "random"

    def skipped(self, item: str) -> bool:
        return any(a.item == item and a.outcome == "SKIPPED" for a in self.attempts)

    def pruned(self, item: str) -> bool:
        """An easier step of the same ladder fails every time, as item_pruned."""
        name = part(item)
        if name == "control":
            return False
        for prev in self.items:
            if prev == item:
                return False
            if part(prev) == name and self.verdict(prev) == "bad":
                return True
        return False

    def attempt_done(self, rnd: int, item: str) -> bool:
        return any(a.round == rnd and a.item == item and a.outcome != "ABORTED" for a in self.attempts)

    def outcome(self, rnd: int, item: str) -> str:
        found = [a.outcome for a in self.attempts if a.round == rnd and a.item == item and a.outcome != "ABORTED"]
        return found[-1] if found else ""

    def next_attempt(self, only: str = "") -> tuple[int, str] | None:
        """The first attempt without a result, as next_attempt: every round of a step before the next step; a pruned
        step counts as done (the script records it as SKIPPED)."""
        for item in self.items:
            if only and part(item) != only:
                continue
            for rnd in range(1, self.rounds + 1):
                if self.attempt_done(rnd, item) or self.pruned(item):
                    continue
                return rnd, item
        return None

    def total(self, only: str = "") -> int:
        return sum(self.rounds for it in self.items if (not only or part(it) == only)
                   and not (self.pruned(it) and not self.tries(it)))

    def done(self, only: str = "") -> int:
        return sum(1 for it in self.items for r in range(1, self.rounds + 1)
                   if (not only or part(it) == only) and self.attempt_done(r, it) and not self.skipped(it))

    def state(self, name: str) -> str:
        """none, running (attempts left, some done), passed or failed (the control only) of a part."""
        if not self.started or not self.items_of(name):
            return "none"
        if name == "control" and self.verdict("control") in ("bad", "failing", "random"):
            return "failed"
        if self.next_attempt(name) is None:
            return "passed"
        return "running" if self.done(name) else "none"

    @property
    def crashed(self) -> bool:
        """An attempt of an earlier boot did not finish: the script asks what happened."""
        return len(self.pending) >= 5 and self.pending[4] != boot_id()

    @property
    def finished(self) -> bool:
        return self.started and self.state("control") == "passed" and self.next_attempt() is None

    def best(self) -> tuple[int, int] | None:
        """The step Install writes, as best_point: the best GOOD step of each ladder, one step back as the margin;
        None when nothing beats the top point."""
        if self.top is None:
            return None
        best_f, best_v = self.top
        prev_f = prev_v = None
        for item in self.items:
            if item == "control" or self.verdict(item) != "good":
                continue
            f, v = self.point(item)
            if part(item) == "oc":
                prev_f, best_f, best_v = best_f, f, v
            else:
                prev_v, best_v = best_v, v
        if prev_f is not None:
            best_f = prev_f
        if prev_v is not None:
            best_v = prev_v
        return None if (best_f, best_v) == self.top else (best_f, best_v)

    def install_plan(self) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        """The lower safe-points Install keeps and the ones it drops: a voltage above the new top's goes (owner,
        24-11-2026)."""
        best = self.best()
        if best is None:
            return [], []
        lower = [p for p in self.points if p[0] < best[0]]
        return [p for p in lower if p[1] <= best[1]], [p for p in lower if p[1] > best[1]]


def load(folder: Path | None = None) -> Progress:
    folder = folder or state_dir()
    cfg = read_config(folder / "config")

    def number(key: str) -> int:
        try:
            return int(cfg.get(key, "") or DEFAULTS[key])
        except ValueError:
            return DEFAULTS[key]
    points = read_points(folder / "governor-config.orig")
    pending: list[str] = []
    try:
        pending = (folder / "pending").read_text().split()
    except OSError:
        pass
    top = points[-1] if points else None
    try:
        oc_volt = int(cfg.get("OC_VOLT", "") or 0)
    except ValueError:
        oc_volt = 0
    return Progress(bool(cfg) and top is not None, cfg.get("GOVERNOR", ""), top, points, number("ROUNDS"),
                    number("TIME"), number("MAX_FREQ"), number("MIN_VOLT"), number("FREQ_STEP"), number("VOLT_STEP"),
                    oc_volt, cfg.get("SWEEP") or "oc,uv,", read_runs(folder / "runs.tsv"), pending,
                    cfg.get("INSTALLED", ""))


# ------------------------------------------------------------------------------------------------ the window's own
# sweep-wizard: key=value lines. keep: 1 when you chose to keep your own config.

def wizard_file(folder: Path | None = None) -> Path:
    return (folder or state_dir()) / "sweep-wizard"


def read_wizard(folder: Path | None = None) -> dict[str, str]:
    return read_config(wizard_file(folder))


def write_wizard(values: dict[str, str], folder: Path | None = None) -> None:
    path = wizard_file(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = read_wizard(folder)
    data.update(values)
    path.write_text("".join(f"{k}={v}\n" for k, v in data.items() if v != ""))


def forget(folder: Path | None = None) -> None:
    """Start over: the window's own file goes with the script's --reset."""
    wizard_file(folder).unlink(missing_ok=True)
