# SPDX-License-Identifier: GPL-3.0-or-later
"""test-board.sh's awk programs give the same results under gawk, which Bazzite has, and mawk, which Debian and
Ubuntu have (24-11-2026: a byte count printed as 1.7e+10, IGNORECASE and asort() worked under gawk alone). Each
program is read from the script itself and runs under every awk installed here."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="runs the script's awk programs")

SCRIPT = Path(__file__).resolve().parents[1] / "test-board.sh"
AWKS = [name for name in ("gawk", "mawk") if shutil.which(name)]


@pytest.fixture(params=AWKS or [pytest.param("", marks=pytest.mark.skip(reason="no gawk or mawk installed"))])
def awk(request) -> str:
    return request.param


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _program(pattern: str) -> str:
    """The awk program in the script that *pattern* finds, as its first group."""
    match = re.search(pattern, _text(), re.S)
    assert match, f"not found in test-board.sh: {pattern}"
    return match.group(1)


def _variable(name: str) -> str:
    match = re.search(rf'^{name}="(.*)"$', _text(), re.M)
    assert match, f"{name} not found in test-board.sh"
    return match.group(1)


def _run(awk: str, args: list[str], stdin: str) -> str:
    return subprocess.run([awk, *args], input=stdin, capture_output=True, text=True, timeout=30,
                          check=True).stdout


def test_byte_counts_stay_whole_numbers(awk):
    zram = _program(r"--output DISKSIZE 2>/dev/null \| awk '(.*?)'\)")
    total = _program(r"MEM_BYTES=\$\(awk '(.*?)' /proc/meminfo\)")
    # Debian's mawk writes a whole number over 2^31 as 5e+09 with print, a newer mawk writes it in full.
    assert "printf" in zram and "printf" in total
    assert _run(awk, [zram], "8589934592\n8589934592\n").strip() == "17179869184"
    assert _run(awk, [total], "MemTotal:       16384000 kB\n").strip() == "16777216000"


def test_kernel_faults_match_in_any_case_and_benign_blocks_drop(awk):
    program = _program(r"scan_kernel_faults\(\) \{\n    awk -v panic=\"\$PANIC_RE\" -v benign=\"\$PANIC_BENIGN_RE\" '(.*?)'\n\}")
    args = ["-v", f"panic={_variable('PANIC_RE')}", "-v", f"benign={_variable('PANIC_BENIGN_RE')}", program]
    log = "\n".join(["kernel: usb 1-1: new device", "kernel: KERNEL PANIC - not syncing: Fatal exception",
                     *[f"kernel: line {i}" for i in range(8)],
                     "kernel: WARNING: at dal_irq_service_set+0x10", "kernel: Call Trace:", "kernel: done"]) + "\n"
    out = _run(awk, args, log)
    assert "KERNEL PANIC - not syncing" in out                  # upper case still counts as a hit
    assert "dal_irq_service_set" not in out                     # a known-benign block is dropped as a whole


def test_an_oops_line_counts_on_its_own(awk):
    """Oops as a word, also without a Call Trace beside it (24-11-2026: \\b, passed with awk -v, became a backspace
    and the word never matched). The same pattern holds for grep -E, which reads it in the combined stress test."""
    program = _program(r"scan_kernel_faults\(\) \{\n    awk -v panic=\"\$PANIC_RE\" -v benign=\"\$PANIC_BENIGN_RE\" '(.*?)'\n\}")
    panic = _variable("PANIC_RE")
    args = ["-v", f"panic={panic}", "-v", f"benign={_variable('PANIC_BENIGN_RE')}", program]
    assert "Oops: 0000 [#1] SMP" in _run(awk, args, "kernel: Oops: 0000 [#1] SMP\n")
    assert _run(awk, args, "kernel: whoopsie-daemon started\n") == ""
    grep = subprocess.run(["grep", "-EI", panic], input="kernel: Oops: 0000 [#1] SMP\nwhoopsie\n",
                          capture_output=True, text=True, timeout=30).stdout
    assert grep == "kernel: Oops: 0000 [#1] SMP\n"


def test_mangohud_lows_need_no_asort(awk):
    program = _program(r"head -c 20000000 \| awk -F, '(.*?)'\)")
    times = [16.0 + (i % 7) * 0.5 for i in range(1000)] + [80.0] * 5 + [40.0] * 15
    csv = "os,cpu,gpu\nfps,frametime,cpu_load\n" + "".join(f"60,{t},10\n" for t in times)
    fields = _run(awk, ["-F,", program], csv).split()
    ordered, n = sorted(times), len(times)
    k1, k2 = max(1, n // 100), max(1, n // 1000)
    median = ordered[n // 2 - 1]
    expected = ["OK", str(n), f"{sum(times) / 1000:.0f}", f"{1000 * n / sum(times):.1f}",
                f"{1000 * k1 / sum(ordered[-k1:]):.1f}", f"{1000 * k2 / sum(ordered[-k2:]):.1f}",
                f"{100 * sum(t > 2 * median for t in times) / n:.2f}"]
    assert fields == expected
