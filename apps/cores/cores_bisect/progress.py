# SPDX-License-Identifier: GPL-3.0-or-later

"""Where a core test stands, read from what ps5-cores-bisect.sh keeps in ~/.local/share/ps5-cores-bisect/: the
phase, the plan, the verdict of every item and the next attempt. The rules are the script's own (build_plan,
item_verdict, next_attempt and the verdict in summary); tests/test_progress.py holds them against the script's
--status. No Qt here, and nothing is written but the window's own file, tools-wizard.

The phases of the script: "control" runs on the stock 6 cores. When every control round passed, the script asks to
apply the core unlock, one SMU write that takes effect on the next warm restart, and the phase is "unlock-pending".
The first run after that restart finds the new cores, and the phase is "bisect": post-control (a stock core after the
unlock), each new core alone and both together (combined)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

FAIL_RE = re.compile(r"^(CRASH-LOAD|MCE|VERIFY-FAIL|LOAD-FAIL|OFFLINE|MPRIME-FAIL|RAS-ERROR)$")
CORES = range(8)                         # the SoC's 8 physical cores, 2 threads each


def state_dir() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share")) / "ps5-cores-bisect"


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def ids(text: str) -> list[int]:
    return [int(t) for t in text.split() if t.isdigit()]


@dataclass
class Attempt:
    round: int
    item: str
    outcome: str
    note: str = ""


def read_runs(path: Path) -> list[Attempt]:
    attempts = []
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return attempts
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 6:
            continue
        try:
            rnd = int(cols[2])
        except ValueError:
            continue
        attempts.append(Attempt(rnd, cols[3], cols[5], cols[10] if len(cols) > 10 else ""))
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


def verdict(attempts: list[Attempt], item: str) -> str:
    """none, good, bad or random, as item_verdict: aborted attempts don't count."""
    outs = [a.outcome for a in attempts if a.item == item and a.outcome != "ABORTED"]
    if not outs:
        return "none"
    fails = sum(1 for o in outs if FAIL_RE.match(o))
    if fails == 0:
        return "good"
    return "bad" if fails == len(outs) else "random"


def attempt_done(attempts: list[Attempt], rnd: int, item: str) -> bool:
    return any(a.round == rnd and a.item == item and a.outcome != "ABORTED" for a in attempts)


@dataclass
class Progress:
    started: bool = False
    phase: str = "control"
    base_cores: list[int] = field(default_factory=list)
    new_cores: list[int] = field(default_factory=list)
    rounds: int = 3
    time_secs: int = 600
    load_tool: str = "stress-ng"
    attempts: list[Attempt] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)   # round item boot cpus secs tool of an unfinished attempt
    last_boot: str = ""
    base_threads: int = 0                    # the threads online when the unlock was applied
    ras: bool = False                        # --rasdaemon, kept by the script like the other settings

    @property
    def items(self) -> list[str]:
        """The items of the phase, as build_plan."""
        if self.phase != "bisect":
            return ["control"]
        items = ["post-control", *(f"core{c}" for c in self.new_cores)]
        if len(self.new_cores) > 1:
            items.append("combined")
        return items

    def total(self, only: str = "") -> int:
        return self.rounds * sum(1 for it in self.items if not only or it == only)

    def done(self, only: str = "") -> int:
        return sum(1 for r in range(1, self.rounds + 1) for it in self.items
                   if (not only or it == only) and attempt_done(self.attempts, r, it))

    def next_attempt(self, only: str = "") -> tuple[int, str] | None:
        for r in range(1, self.rounds + 1):
            for it in self.items:
                if (not only or it == only) and not attempt_done(self.attempts, r, it):
                    return r, it
        return None

    def verdict(self, item: str) -> str:
        return verdict(self.attempts, item)

    def rounds_state(self, item: str) -> str:
        """none, running (rounds left, none failed), passed or failed, for control and post-control."""
        v = self.verdict(item)
        if v in ("bad", "random"):
            return "failed"
        if item == "control":
            if self.phase != "control":
                return "passed"                     # the script moves on only after every round passed
            left = self.next_attempt("control") is not None
        else:
            if self.phase != "bisect":
                return "none"
            left = self.next_attempt(item) is not None
        if left:
            return "none" if v == "none" else "running"
        return "passed"

    @property
    def control(self) -> str:
        return self.rounds_state("control") if self.started else "none"

    @property
    def post_control(self) -> str:
        return self.rounds_state("post-control") if self.started else "none"

    @property
    def crashed(self) -> bool:
        """An attempt of an earlier boot did not finish: the script asks what happened."""
        return len(self.pending) >= 3 and self.pending[2] != boot_id()

    @property
    def this_boot_used(self) -> bool:
        """An attempt ran in this boot already, so the next one needs a warm restart first."""
        return self.last_boot == boot_id()

    def bad(self) -> list[str]:
        return [it for it in self.items if it != "post-control" and self.verdict(it) == "bad"]

    def random(self) -> list[str]:
        return [it for it in self.items if it != "post-control" and self.verdict(it) == "random"]

    @property
    def finished(self) -> bool:
        return self.started and self.phase == "bisect" and self.next_attempt() is None

    @property
    def healthy(self) -> bool:
        """Every item passed every round: the script's "The core unlock looks safe on this board"."""
        return (self.finished and self.control == "passed"
                and all(self.verdict(it) == "good" for it in self.items))


def load(folder: Path | None = None) -> Progress:
    folder = folder or state_dir()
    cfg = read_config(folder / "config")

    def number(key: str, default: int) -> int:
        try:
            return int(cfg.get(key, "") or default)
        except ValueError:
            return default
    pending: list[str] = []
    try:
        pending = (folder / "pending").read_text().split()
    except OSError:
        pass
    try:
        last_boot = (folder / "lastboot").read_text().strip()
    except OSError:
        last_boot = ""
    return Progress(bool(cfg), cfg.get("PHASE") or "control", ids(cfg.get("BASE_CORES", "")),
                    ids(cfg.get("NEW_CORES", "")), number("ROUNDS", 3), number("TIME", 600),
                    cfg.get("LOAD_TOOL") or "stress-ng", read_runs(folder / "runs.tsv"), pending, last_boot,
                    number("BASE_THREADS", 0), cfg.get("RAS") == "1")


# ------------------------------------------------------------------------------------------- the cores online now
# Read from sysfs, which needs no root: the threads online and the core of each. The presence mask itself needs root,
# so the window reads it only in a scan.
CPU_DIR = Path("/sys/devices/system/cpu")


def online_cores(cpu_dir: Path | None = None) -> list[int]:
    """The core IDs of the online threads, sorted and once each, as the script's online_core_ids."""
    found = set()
    for topology in (cpu_dir or CPU_DIR).glob("cpu[0-9]*/topology/core_id"):
        try:
            found.add(int(topology.read_text().strip()))
        except (OSError, ValueError):
            continue
    return sorted(found)


def online_threads(cpu_dir: Path | None = None) -> int:
    """The threads online now, from the "0-11" list in sysfs; 0 when it can't be read."""
    try:
        text = ((cpu_dir or CPU_DIR) / "online").read_text().strip()
    except OSError:
        return 0
    count = 0
    for part in filter(None, text.split(",")):
        first, _, last = part.partition("-")
        try:
            count += int(last or first) - int(first) + 1
        except ValueError:
            return 0
    return count


# ------------------------------------------------------------------------------------------------ the window's own
# tools-wizard: key=value lines. phase: "stock" when you chose to stay at 6 cores. warnings: the warnings you accepted
# for this test, so they are asked once.

def wizard_file(folder: Path | None = None) -> Path:
    return (folder or state_dir()) / "tools-wizard"


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


# --------------------------------------------------------------------------------------------- the boot unlock
UNLOCK_UNIT = Path("/etc/systemd/system/ps5-cores-unlock.service")


def unlock_installed(path: Path | None = None) -> bool:
    """Whether ps5-cores-unlock.sh --install put its boot service in place (the unit file is world-readable)."""
    return (path or UNLOCK_UNIT).is_file()
