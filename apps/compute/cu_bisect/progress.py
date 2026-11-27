# SPDX-License-Identifier: GPL-3.0-or-later

"""Where a CU test stands, read from what ps5-cu-bisect.sh keeps in ~/.local/share/ps5-cu-bisect/: the plan,
the verdict of every item, the next attempt and the levels the healthy WGPs allow. The rules are the script's own
(build_plan, item_verdict, next_attempt and the even trim in summary); tests/test_progress.py holds them against the
script's --status. No Qt here, and nothing is written but the window's own file, tools-wizard, and the copy of a
finished bisect run that the combined test keeps (bisect-runs.tsv, bisect-config)."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ROWS = ("SE0.SH0", "SE0.SH1", "SE1.SH0", "SE1.SH1")
FAIL_RE = re.compile(r"^(CRASH-APPLY|CRASH-LOAD|FAULT|ERRORS|LOAD-FAIL|DRIFT|MISMATCH)$")
LEVELS = {3: 24, 4: 32, 5: 40}          # WGPs on every row -> CUs: the only masks that can be installed


def state_dir() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share")) / "ps5-cu-bisect"


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def popcount(n: int) -> int:
    return bin(n & 0x1F).count("1")


def masks_of(text: str) -> list[int]:
    return [int(m, 16) & 0x1F for m in text.split(",")]


def hex_masks(rows: list[int]) -> str:
    return ",".join(f"0x{m & 0x1F:02x}" for m in rows)


def cu_count(text: str) -> int:
    return sum(popcount(m) for m in masks_of(text)) * 2


def item_bit(item: str) -> tuple[int, int]:
    """'SE1.SH0.WGP3' -> (row 2, bit 3)."""
    row, wgp = item.rsplit(".WGP", 1)
    return ROWS.index(row), int(wgp)


def plan(base: str, control_only: bool) -> list[tuple[str, str]]:
    """(item, masks): control, then baseline + one locked WGP per row and bit, as build_plan."""
    items = [("control", base)]
    if control_only:
        return items
    rows = masks_of(base)
    for i, row in enumerate(ROWS):
        for b in range(5):
            if rows[i] >> b & 1:
                continue
            m = list(rows)
            m[i] |= 1 << b
            items.append((f"{row}.WGP{b}", hex_masks(m)))
    return items


@dataclass
class Attempt:
    round: int
    item: str
    masks: str
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
        attempts.append(Attempt(rnd, cols[3], cols[4], cols[5], cols[12] if len(cols) > 12 else ""))
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
    """none, good, bad or random, as item_verdict: aborted and skipped attempts don't count."""
    outs = [a.outcome for a in attempts if a.item == item and a.outcome not in ("ABORTED", "SKIPPED")]
    if not outs:
        return "none"
    fails = sum(1 for o in outs if FAIL_RE.match(o))
    if fails == 0:
        return "good"
    return "bad" if fails == len(outs) else "random"


def attempt_done(attempts: list[Attempt], rnd: int, item: str) -> bool:
    return any(a.round == rnd and a.item == item and a.outcome != "ABORTED" for a in attempts)


def trim(rows: list[int], level: int) -> list[int]:
    """Each row down to its *level* lowest set bits, as summary's even trim."""
    out = []
    for row in rows:
        kept = 0
        for bit in range(5):
            if popcount(kept) >= level:
                break
            if row >> bit & 1:
                kept |= 1 << bit
        out.append(kept)
    return out


@dataclass
class Progress:
    base: str = ""
    rounds: int = 3
    time_secs: int = 180
    control_only: bool = False
    attempts: list[Attempt] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)   # round item phase boot masks of an unfinished attempt
    last_boot: str = ""

    @property
    def started(self) -> bool:
        return bool(self.base)

    @property
    def items(self) -> list[tuple[str, str]]:
        return plan(self.base, self.control_only) if self.base else []

    def total(self, only: str = "") -> int:
        return self.rounds * sum(1 for it, _ in self.items if not only or it == only)

    def done(self, only: str = "") -> int:
        return sum(1 for r in range(1, self.rounds + 1) for it, _ in self.items
                   if (not only or it == only) and attempt_done(self.attempts, r, it))

    def next_attempt(self, only: str = "") -> tuple[int, str] | None:
        for r in range(1, self.rounds + 1):
            for it, _ in self.items:
                if (not only or it == only) and not attempt_done(self.attempts, r, it):
                    return r, it
        return None

    def verdict(self, item: str) -> str:
        return verdict(self.attempts, item)

    @property
    def control(self) -> str:
        """none, running (rounds left, none failed), passed or failed."""
        if not self.started:
            return "none"
        v = self.verdict("control")
        if v in ("bad", "random"):
            return "failed"
        if self.next_attempt("control") is not None:
            return "none" if v == "none" else "running"
        return "passed"

    @property
    def crashed(self) -> bool:
        """An attempt of an earlier boot did not finish: the script asks what happened."""
        return len(self.pending) >= 4 and self.pending[3] != boot_id()

    @property
    def this_boot_used(self) -> bool:
        """An attempt ran in this boot already, so the next one needs a restart first."""
        return self.last_boot == boot_id()

    def good(self) -> list[str]:
        return [it for it, _ in self.items if it != "control" and self.verdict(it) == "good"]

    def healthy_rows(self) -> list[int]:
        """The baseline with every WGP that passed every round."""
        rows = masks_of(self.base)
        for it in self.good():
            r, b = item_bit(it)
            rows[r] |= 1 << b
        return rows

    def levels(self) -> dict[int, str]:
        """CUs -> mask for every even level the healthy WGPs reach: 24 always, 32 and 40 when every row has them."""
        rows = self.healthy_rows()
        top = min(popcount(m) for m in rows)
        return {LEVELS[n]: hex_masks(trim(rows, n)) for n in sorted(LEVELS) if n <= top}

    def uneven(self) -> list[tuple[int, list[int], str]]:
        """Every count above the highest even level, up to all healthy WGPs, as (CUs, WGPs per row, mask), each with
        the rows that give it the most speed (owner, 27-11-2026: what the board can already run is not shown again,
        every count above it is). The two shader engines (SE0 and SE1, two rows each) run in step, and inside an
        engine the rows add up: measured on a board with vkpeak, 27-11-2026, the speed is 4 CUs for each WGP in the
        smaller engine (speed_cus). So the WGPs go to the two engines as evenly as the healthy ones allow, and inside
        an engine to its two rows as evenly as they allow. A count with one WGP more in an engine runs like the
        count 2 below. Each row keeps its lowest healthy WGPs, as the even levels do."""
        healthy = self.healthy_rows()
        rows = [popcount(m) for m in healthy]
        top = min(rows)
        engines = (rows[0] + rows[1], rows[2] + rows[3])
        out = []
        for wgps in range(4 * top + 1, sum(rows) + 1):
            each = min(wgps // 2, *engines)
            first = min(each + (wgps - 2 * each), engines[0])
            totals = (first, wgps - first)
            cur = []
            for total, (a, b) in zip(totals, ((rows[0], rows[1]), (rows[2], rows[3]))):
                low = min(total // 2, a, b)
                one = max(low, total - b) if a >= b else low
                cur += [one, total - one]
            out.append((sum(cur) * 2, cur, hex_masks([trim([healthy[i]], cur[i])[0] for i in range(4)])))
        return out

def speed_cus(text: str) -> int:
    """The CUs a mask runs like: 4 for each WGP in the smaller of the two shader engines (see Progress.uneven)."""
    rows = [popcount(m) for m in masks_of(text)]
    return 4 * min(rows[0] + rows[1], rows[2] + rows[3])

def load(folder: Path | None = None) -> Progress:
    folder = folder or state_dir()
    cfg = read_config(folder / "umr-config")

    def number(key: str, default: int) -> int:
        try:
            return int(cfg.get(key, "") or default)
        except ValueError:
            return default
    pending: list[str] = []
    try:
        pending = (folder / "umr-pending").read_text().split()
    except OSError:
        pass
    try:
        last_boot = (folder / "umr-lastboot").read_text().strip()
    except OSError:
        last_boot = ""
    base = cfg.get("BASE", "")
    if not re.match(r"^0x[0-9a-fA-F]{1,2}(,0x[0-9a-fA-F]{1,2}){3}$", base):
        base = ""
    return Progress(base, number("ROUNDS", 3), number("TIME", 180), cfg.get("CONTROL_ONLY") == "1",
                    read_runs(folder / "umr-runs.tsv"), pending, last_boot)


# ------------------------------------------------------------------------------------------------ the window's own
# tools-wizard: key=value lines. phase: empty while the bisect runs, "combined" during the combined test of a level,
# "stock" when you chose to stay at 24 CUs. level: the CUs of the combined test. warnings: the warnings you accepted
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


def keep_bisect(folder: Path | None = None) -> None:
    """Copies the finished bisect run before the combined test's --reset deletes it, for the map and the levels."""
    folder = folder or state_dir()
    for name, copy in (("umr-runs.tsv", "bisect-runs.tsv"), ("umr-config", "bisect-config")):
        if (folder / name).is_file():
            shutil.copyfile(folder / name, folder / copy)


def kept_bisect(folder: Path | None = None) -> Progress | None:
    """The bisect run keep_bisect copied, or None."""
    folder = folder or state_dir()
    if not (folder / "bisect-config").is_file():
        return None
    cfg = read_config(folder / "bisect-config")
    try:
        rounds = int(cfg.get("ROUNDS", "3") or 3)
    except ValueError:
        rounds = 3
    return Progress(cfg.get("BASE", ""), rounds, attempts=read_runs(folder / "bisect-runs.tsv"))


def forget(folder: Path | None = None) -> None:
    """Start over: the window's own files go with the script's --reset."""
    folder = folder or state_dir()
    for name in ("tools-wizard", "bisect-runs.tsv", "bisect-config"):
        (folder / name).unlink(missing_ok=True)


# --------------------------------------------------------------------------------------------- the boot unlock
UNLOCK_MASKS = Path("/etc/ps5-cu-bisect/masks")


def installed_masks(path: Path | None = None) -> str:
    """The masks ps5-cu-unlock.service applies at boot, or '' when it is not installed. The file is
    world-readable."""
    try:
        text = (path or UNLOCK_MASKS).read_text().strip()
    except OSError:
        return ""
    return text if re.match(r"^0x[0-9a-fA-F]{1,2}(,0x[0-9a-fA-F]{1,2}){3}$", text) else ""


def boot_time(stat: Path = Path("/proc/stat")) -> float:
    """When this boot started, in seconds since the epoch (btime in /proc/stat), or 0 when unknown."""
    try:
        for line in stat.read_text().splitlines():
            if line.startswith("btime "):
                return float(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def unlock_on(path: Path | None = None, stat: Path = Path("/proc/stat")) -> bool:
    """True when the installed masks were saved before this boot started, so the boot service has applied them.
    Install writes nothing to the GPU (a live write can freeze the board), so a newer file waits for a restart."""
    if not installed_masks(path):
        return False
    started = boot_time(stat)
    try:
        return bool(started) and (path or UNLOCK_MASKS).stat().st_mtime < started
    except OSError:
        return False
