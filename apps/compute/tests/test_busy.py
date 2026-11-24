# SPDX-License-Identifier: GPL-3.0-or-later
"""ps5-cu-bisect.sh's GPU load: gpu_busy_percent where the kernel reports it, else the engine time of every client
in /proc/<pid>/fdinfo between two samples. The script's own functions run in bash against a fake /proc and GPU."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="runs the script's bash functions")

SCRIPT = Path(__file__).resolve().parents[1] / "ps5-cu-bisect.sh"
PDEV = "0000:01:00.0"


def _functions() -> str:
    """The script's load functions, from BUSY's line to the end of gpu_busy()."""
    text = SCRIPT.read_text()
    match = re.search(r"^BUSY=0 .*?^gpu_busy\(\) \{.*?^\}\n", text, re.S | re.M)
    assert match, "gpu_busy() not found in the script"
    return match.group(0)


def _client(proc: Path, pid: int, fd: int, client: int, gfx: int, comp: int = 0, pdev: str = PDEV) -> None:
    info = proc / str(pid) / "fdinfo"
    info.mkdir(parents=True, exist_ok=True)
    (info / str(fd)).write_text(f"pos:\t0\ndrm-driver:\tamdgpu\ndrm-pdev:\t{pdev}\ndrm-client-id:\t{client}\n"
                                f"drm-engine-gfx:\t{gfx} ns\ndrm-engine-compute:\t{comp} ns\n")


def _run(tmp_path: Path, body: str) -> list[str]:
    gpu = tmp_path / PDEV
    gpu.mkdir(exist_ok=True)
    script = f"set -u\nGPU_DEV={gpu}\n{_functions()}PROC={tmp_path / 'proc'}\n{body}\n"
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, check=True)
    return out.stdout.split()


def test_the_kernel_sensor_comes_first(tmp_path):
    (tmp_path / PDEV).mkdir()
    (tmp_path / PDEV / "gpu_busy_percent").write_text("42\n")
    assert _run(tmp_path, "gpu_busy; echo $BUSY") == ["42"]


def test_engine_time_between_two_samples(tmp_path):
    proc = tmp_path / "proc"
    _client(proc, 100, 18, 7, gfx=5_000_000_000)
    _client(proc, 100, 19, 7, gfx=5_000_000_000)                 # the same client on a second file: counted once
    _client(proc, 200, 5, 9, gfx=0, comp=1_000_000_000)
    _client(proc, 300, 4, 3, gfx=0, pdev="0000:02:00.0")           # another GPU
    # The first call samples twice, one second apart. Nothing changed, so 0%.
    # Then 1 s of compute time over 2 s: 50%. Gfx time on the other GPU and a new client don't count.
    body = f"""
gpu_busy; echo $BUSY
sed -i 's/^drm-engine-compute:.*/drm-engine-compute:\\t2000000000 ns/' {proc}/200/fdinfo/5
sed -i 's/^drm-engine-gfx:.*/drm-engine-gfx:\\t9000000000 ns/' {proc}/300/fdinfo/4
mkdir -p {proc}/400/fdinfo
printf 'drm-pdev:\\t{PDEV}\\ndrm-client-id:\\t11\\ndrm-engine-gfx:\\t8000000000 ns\\n' >{proc}/400/fdinfo/3
BUSY_AT=$(( ${{EPOCHREALTIME/./}} - 2000000 ))
gpu_busy; echo $BUSY
"""
    first, second = _run(tmp_path, body)
    assert first == "0"
    assert second in ("49", "50")


def test_the_busier_engine_counts_and_load_stops_at_100(tmp_path):
    proc = tmp_path / "proc"
    _client(proc, 100, 18, 7, gfx=0, comp=0)
    body = f"""
gpu_busy
sed -i -e 's/^drm-engine-gfx:.*/drm-engine-gfx:\\t5000000000 ns/' -e 's/^drm-engine-compute:.*/drm-engine-compute:\\t500000000 ns/' {proc}/100/fdinfo/18
BUSY_AT=$(( ${{EPOCHREALTIME/./}} - 1000000 ))
gpu_busy; echo $BUSY
"""
    assert _run(tmp_path, body) == ["100"]
