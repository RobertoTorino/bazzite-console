# SPDX-License-Identifier: GPL-3.0-or-later
"""What KytyPS5-Native needs from the board, read and never set: the app only checks (owner, 27-11-2026). This suite has no app
that sets them.

The figures come from the system: the GPU's own memory (mem_info_vram_total) and the GTT (mem_info_gtt_total) of the
card the amdgpu driver runs, and the driver's options under /sys/module/amdgpu/parameters. What the emulator asks is
its README's (Requirements), written for the AMD BC-250: the 512 MB split for big games, a GTT of 14 GiB, and the driver options sched_policy=2,
vm_update_mode=0 and cwsr_enable=0."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SYS = Path("/sys")
VRAM_MIB = 512                          # the split the emulator asks for big games
GTT_MIB = 14 * 1024                     # the GTT it asks (ttm.pages_limit=3670016)
OPTIONS = {"sched_policy": 2, "vm_update_mode": 0, "cwsr_enable": 0}    # the driver options it recommends


def _int(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="ascii", errors="replace").split()[0])
    except (OSError, ValueError, IndexError):
        return None


@dataclass(frozen=True)
class Board:
    vram_mib: int | None                # the GPU's own memory; None: no amdgpu card answers
    gtt_mib: int | None
    options: dict[str, int | None]      # the driver's options as they are now

    @property
    def vram_ok(self) -> bool:
        return self.vram_mib is not None and self.vram_mib <= VRAM_MIB

    @property
    def gtt_ok(self) -> bool:
        return self.gtt_mib is not None and self.gtt_mib >= GTT_MIB

    @property
    def options_ok(self) -> bool:
        return all(self.options.get(name) == value for name, value in OPTIONS.items())

    @property
    def found(self) -> bool:
        return self.vram_mib is not None

    @property
    def ok(self) -> bool:
        return self.vram_ok and self.gtt_ok and self.options_ok


def read(sys_root: Path = SYS) -> Board:
    """The board as it runs now. The card is the one whose driver is amdgpu, whatever its number."""
    device = None
    for candidate in sorted((sys_root / "class" / "drm").glob("card*/device")):
        try:
            driver = (candidate / "driver").resolve().name
        except OSError:
            continue
        if driver == "amdgpu" and (candidate / "mem_info_vram_total").is_file():
            device = candidate
            break
    vram = _int(device / "mem_info_vram_total") if device else None
    gtt = _int(device / "mem_info_gtt_total") if device else None
    params = sys_root / "module" / "amdgpu" / "parameters"
    return Board(vram >> 20 if vram is not None else None, gtt >> 20 if gtt is not None else None,
                 {name: _int(params / name) for name in OPTIONS})
