# SPDX-License-Identifier: GPL-3.0-or-later
"""The register writes of a CU unlock, in ps5-cu-bisect.sh and ps5-cu-unlock.sh: CC_GC_SHADER_ARRAY_CONFIG is
cleared, SPI_PG_ENABLE_STATIC_WGP_MASK gets each row's mask, and RLC_PG_ALWAYS_ON_WGP_MASK the union of the rows.
This is the write every boot unlock used until 27-11-2026. A write that set CC to the mask's inverse and left RLC
alone hung the GPU when the boot service wrote it (two boards, 27-11-2026); these tests keep it out until it has
passed at boot. The scripts' own functions run in bash with a reg_write that only prints."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="runs the scripts' bash functions")

APP = Path(__file__).resolve().parents[1]
BISECT = APP / "ps5-cu-bisect.sh"
UNLOCK = APP / "ps5-cu-unlock.sh"


def _bash(script: str, path: Path | None = None) -> subprocess.CompletedProcess:
    env = {"PATH": f"{path}:/usr/bin:/bin"} if path else None
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, env=env)


def _block(script: Path, pattern: str) -> str:
    match = re.search(pattern, script.read_text(), re.S | re.M)
    assert match, f"{pattern} not found in {script.name}"
    return match.group(0)


def _sequence() -> str:
    """The bisect script's unlock sequence, from writes() to the end of apply_masks()."""
    return _block(BISECT, r"^writes\(\) \{.*?^apply_masks\(\) \{.*?^\}\n")


def _writes(masks: str, writes: str) -> list[str]:
    body = (f"set -u\nWRITES={writes}\nREG_CC=CC REG_SPI=SPI REG_RLC=RLC\nCC_NOW=''\n"
            "hex2() { printf '0x%02x' $(( $1 & 31 )); }\nreg_write() { echo \"$*\"; }\n"
            f"{_sequence()}apply_masks {masks}\n")
    out = _bash(body)
    assert out.returncode == 0, out.stderr
    return out.stdout.splitlines()


def test_the_unlock_clears_cc_writes_spi_per_row_and_the_always_on_mask():
    assert _writes("0x0f,0x0f,0x0f,0x1b", "cc,spi,rlc") == [
        "CC 0x0", "CC 0x0 0 0", "SPI 0x0f 0 0", "CC 0x0 0 1", "SPI 0x0f 0 1",
        "CC 0x0 1 0", "SPI 0x0f 1 0", "CC 0x0 1 1", "SPI 0x1b 1 1", "RLC 0x1f"]


def test_a_higher_count_writes_the_union_of_its_rows():
    assert _writes("0x1f,0x1f,0x0f,0x1f", "cc,spi,rlc")[-1] == "RLC 0x1f"
    assert _writes("0x07,0x07,0x07,0x0b", "cc,spi,rlc")[-1] == "RLC 0x0f"


def test_writes_picks_the_registers():
    assert _writes("0x0f,0x0f,0x0f,0x1b", "spi") == ["SPI 0x0f 0 0", "SPI 0x0f 0 1", "SPI 0x0f 1 0", "SPI 0x1b 1 1"]
    assert _writes("0x0f,0x0f,0x0f,0x1b", "spi,rlc")[-1] == "RLC 0x1f"
    assert not any(line.startswith("RLC") for line in _writes("0x0f,0x0f,0x0f,0x1b", "cc,spi"))


def test_the_default_writes_are_all_three_registers():
    assert re.search(r'\bWRITES=cc,spi,rlc(\s|$)', BISECT.read_text(), re.M)


def test_neither_script_writes_the_masks_inverse_to_cc():
    """The write of 27-11-2026 that hung the GPU at boot: CC = the inactive WGPs, computed from the mask."""
    for script in (BISECT, UNLOCK):
        text = script.read_text()
        assert "cc_of" not in text and "~$1" not in text, script.name


def test_the_unlock_script_writes_what_the_test_writes():
    """ps5-cu-unlock.sh applies the same three writes as the test's apply_masks, with its own helpers."""
    block = _block(UNLOCK, r"^  local m i union=0\n.*?^  reg_write_global \"\$REG_RLC\".*?\n")
    body = ("set -u\nREG_CC=CC REG_SPI=SPI REG_RLC=RLC\nROWS=(a b c d)\ndie() { echo \"DIE $*\"; exit 1; }\n"
            "hex2() { printf '0x%02x' $(( $1 & 31 )); }\nreg_write_rc() { echo \"$*\"; }\n"
            "reg_write_global() { echo \"$*\"; }\napply() {\n" + block + "}\napply 0x1f,0x1f,0x0f,0x1f\n")
    out = _bash(body)
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == [
        "CC 0x0", "CC 0x0 0 0", "SPI 0x1f 0 0", "CC 0x0 0 1", "SPI 0x1f 0 1",
        "CC 0x0 1 0", "SPI 0x0f 1 0", "CC 0x0 1 1", "SPI 0x1f 1 1", "RLC 0x1f"]


def _at_boot(tmp_path: Path, cc_now: str, service_active: bool) -> bool:
    fake = tmp_path / "bin"
    fake.mkdir(exist_ok=True)
    (fake / "systemctl").write_text(f"#!/bin/sh\nexit {0 if service_active else 3}\n")
    (fake / "systemctl").chmod(0o755)
    body = f"set -u\nWRITES=cc,spi,rlc\nCC_NOW='{cc_now}'\n{_sequence()}unlock_at_boot\n"
    return _bash(body, fake).returncode == 0


def test_unlock_at_boot(tmp_path):
    stock = "0xfff80000 0xfff80000 0xfff80000 0xfff40000"
    assert not _at_boot(tmp_path, stock, False)
    assert _at_boot(tmp_path, stock, True)                                   # the boot service ran
    assert _at_boot(tmp_path, "0xffe00000 0xffe00000 0xffe00000 0xffe00000", False)   # no WGP inactive on any row
    assert _at_boot(tmp_path, "0x00000000 0x00000000 0x00000000 0x00000000", False)
    assert not _at_boot(tmp_path, "0xffe00000 0xffe00000 0xffe00000 0xffe40000", False)
    assert not _at_boot(tmp_path, "", False)                                 # CC could not be read


def _validate(masks: str) -> subprocess.CompletedProcess:
    helpers = _block(UNLOCK, r"^ROWS=.*?^validate_mask\(\) \{.*?^\}\n")
    return _bash(f"{helpers}\nvalidate_mask {masks}")


@pytest.mark.parametrize("masks", ["0x07,0x07,0x07,0x0b", "0x0f,0x0f,0x0f,0x1b", "0x1f,0x1f,0x1f,0x1f",
                                   "0x0f,0x1f,0x0f,0x1f", "0x0f,0x07,0x07,0x1b"])
def test_a_mask_that_runs_like_its_count_is_accepted_without_a_note(masks):
    result = _validate(masks)
    assert result.returncode == 0 and result.stdout == ""


@pytest.mark.parametrize(("masks", "counts", "speed", "cus"), [
    ("0x1f,0x1f,0x0f,0x1f", "5/5/4/5", 36, 38), ("0x0f,0x07,0x07,0x0b", "4/3/3/3", 24, 26),
    ("0x1f,0x0f,0x07,0x07", "5/4/3/3", 24, 30), ("0x07,0x07,0x0f,0x1b", "3/3/4/4", 24, 28)])
def test_a_mask_with_unequal_halves_is_accepted_and_says_what_it_gives(masks, counts, speed, cus):
    result = _validate(masks)
    assert result.returncode == 0
    assert f"Mask {masks} - {counts} WGPs" in result.stdout
    assert f"{speed} CUs while it draws the power of {cus} CUs." in result.stdout


@pytest.mark.parametrize("masks", ["0x03,0x07,0x07,0x07", "0x1f,0x1f,0x1f,0x01"])
def test_a_row_under_three_wgps_is_refused(masks):
    result = _validate(masks)
    assert result.returncode == 1 and "Every row needs 3, 4 or 5 WGPs" in result.stderr


@pytest.mark.parametrize(("vram_mib", "avail_mib", "size_mib"), [
    (512, 11234, 1024),             # a 512 MB split: 384 MiB is refused by memtest_vulkan, so the floor
    (6144, 9000, 4500),             # three quarters of 6 GB is over half the free memory: half of it
    (2048, 9000, 1536),             # three quarters of the VRAM
    (512, 1500, 384),               # too little memory for the floor: as before
    (0, 8000, 4000)])               # no VRAM figure: half the free memory
def test_the_gpu_loads_size(tmp_path, vram_mib, avail_mib, size_mib):
    """The size memtest_vulkan gets: at least 1024 MiB when the memory is there (a board, 27-11-2026)."""
    (tmp_path / "mem_info_vram_total").write_text(str(vram_mib << 20))
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "awk").write_text("#!/bin/sh\necho " + str(avail_mib << 10) + "\n")
    (fake / "awk").chmod(0o755)
    block = _block(BISECT, r"^MEMTEST_MIN_MIB=.*?^memtest_bytes\(\) \{.*?^\}\n")
    out = _bash("GPU_DEV=" + str(tmp_path) + "\n" + block + "memtest_bytes\n", fake)
    assert out.returncode == 0, out.stderr
    assert int(out.stdout) == size_mib << 20
