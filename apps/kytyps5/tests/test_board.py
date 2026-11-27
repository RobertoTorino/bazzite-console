# SPDX-License-Identifier: GPL-3.0-or-later
"""The board check (board.py) on a /sys made in a temp folder: the figures as the system gives them, set against
what KytyPS5-Native asks. The app reads only; other boards than the owner's are fixtures too."""

from __future__ import annotations

from conftest import make_sys

from kytyps5_manager import board


def test_a_board_set_as_the_emulator_asks(tmp_path):
    found = board.read(make_sys(tmp_path))                  # the owner's board 1, 27-11-2026
    assert (found.vram_mib, found.gtt_mib) == (512, 14336)
    assert found.options == {"sched_policy": 2, "vm_update_mode": 0, "cwsr_enable": 0}
    assert found.found and found.vram_ok and found.gtt_ok and found.options_ok and found.ok


def test_each_setting_is_judged_by_itself(tmp_path):
    big = board.read(make_sys(tmp_path / "a", vram_mib=6144, gtt_mib=11776))
    assert not big.vram_ok and not big.gtt_ok and big.options_ok and not big.ok
    stock = board.read(make_sys(tmp_path / "b", options={"sched_policy": 0, "vm_update_mode": 3, "cwsr_enable": 1}))
    assert stock.vram_ok and stock.gtt_ok and not stock.options_ok and not stock.ok
    assert board.read(make_sys(tmp_path / "c", vram_mib=256, gtt_mib=16000)).ok       # a smaller split, a larger GTT


def test_an_option_the_driver_does_not_have(tmp_path):
    found = board.read(make_sys(tmp_path, options={"sched_policy": 2, "vm_update_mode": 0}))
    assert found.options["cwsr_enable"] is None and not found.options_ok


def test_the_card_is_found_by_its_driver_not_its_number(tmp_path):
    make_sys(tmp_path, vram_mib=8192, gtt_mib=1, driver="i915", card="card0")
    make_sys(tmp_path, vram_mib=512, card="card3")
    assert board.read(tmp_path).vram_mib == 512


def test_no_amdgpu_card(tmp_path):
    for root in (make_sys(tmp_path / "a", driver="nouveau"), make_sys(tmp_path / "b", vram_mib=None),
                 tmp_path / "nothing"):
        found = board.read(root)
        assert not found.found and found.vram_mib is None and found.gtt_mib is None and not found.ok
