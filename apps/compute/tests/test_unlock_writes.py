# SPDX-License-Identifier: GPL-3.0-or-later
"""The register writes of a CU unlock, in ps5-cu-bisect.sh and ps5-cu-unlock.sh: CC_GC_SHADER_ARRAY_CONFIG lists as
inactive exactly the WGPs a row's mask leaves off, and the always-on mask is not written. The values are the ones
read from a board at stock (0x07 with 0xfff80000, 0x0b with 0xfff40000). The scripts' own functions run in bash
with a reg_write that only prints."""

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
CC = {"0x07": "0xfff80000", "0x0b": "0xfff40000", "0x0f": "0xfff00000", "0x1b": "0xffe40000", "0x1f": "0xffe00000"}


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


@pytest.mark.parametrize("script", [BISECT, UNLOCK], ids=["bisect", "unlock"])
def test_cc_lists_the_wgps_the_mask_leaves_off(script):
    cc_of = _block(script, r"^cc_of\(\) \{.*?\}\n")
    out = _bash(f"{cc_of}for m in {' '.join(CC)}; do cc_of $m; echo; done").stdout.split()
    assert out == list(CC.values())


def _writes(masks: str, writes: str) -> list[str]:
    body = (f"set -u\nWRITES={writes}\nREG_CC=CC REG_SPI=SPI REG_RLC=RLC\nCC_NOW=''\n"
            "hex2() { printf '0x%02x' $(( $1 & 31 )); }\nreg_write() { echo \"$*\"; }\n"
            f"{_sequence()}apply_masks {masks}\n")
    out = _bash(body)
    assert out.returncode == 0, out.stderr
    return out.stdout.splitlines()


def test_the_unlock_writes_cc_and_spi_per_row_and_no_always_on_mask():
    assert _writes("0x0f,0x0f,0x0f,0x1b", "cc,spi") == [
        "CC 0xfff00000 0 0", "SPI 0x0f 0 0", "CC 0xfff00000 0 1", "SPI 0x0f 0 1",
        "CC 0xfff00000 1 0", "SPI 0x0f 1 0", "CC 0xffe40000 1 1", "SPI 0x1b 1 1"]


def test_stock_masks_write_the_chips_own_cc_values():
    lines = _writes("0x07,0x07,0x07,0x0b", "cc,spi")
    assert [line for line in lines if line.startswith("CC")] == [
        "CC 0xfff80000 0 0", "CC 0xfff80000 0 1", "CC 0xfff80000 1 0", "CC 0xfff40000 1 1"]


def test_writes_picks_the_registers():
    assert _writes("0x0f,0x0f,0x0f,0x1b", "spi") == ["SPI 0x0f 0 0", "SPI 0x0f 0 1", "SPI 0x0f 1 0", "SPI 0x1b 1 1"]
    assert _writes("0x0f,0x0f,0x0f,0x1b", "spi,rlc")[-1] == "RLC 0x1f"       # the union of the rows, on request


def test_the_default_writes_are_cc_and_spi():
    assert re.search(r'\bWRITES=cc,spi(\s|$)', BISECT.read_text(), re.M)


def test_the_unlock_script_never_clears_cc_or_writes_the_always_on_mask():
    text = UNLOCK.read_text()
    assert 'REG_CC" 0x0' not in text
    assert "mmRLC_PG_ALWAYS_ON_WGP_MASK" not in text


def _at_boot(tmp_path: Path, cc_now: str, service_active: bool) -> bool:
    fake = tmp_path / "bin"
    fake.mkdir(exist_ok=True)
    (fake / "systemctl").write_text(f"#!/bin/sh\nexit {0 if service_active else 3}\n")
    (fake / "systemctl").chmod(0o755)
    body = f"set -u\nWRITES=cc,spi\nCC_NOW='{cc_now}'\n{_sequence()}unlock_at_boot\n"
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
