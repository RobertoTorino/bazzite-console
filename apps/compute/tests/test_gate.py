# SPDX-License-Identifier: GPL-3.0-or-later
"""The unlock gate: a mask is accepted only after ps5-cu-bisect.sh retested it as its own baseline and every
round passed, with 3, 4 or 5 WGPs on every row (24 to 40 CUs, even or uneven)."""

from __future__ import annotations

import pytest

from cu_bisect.gate import check, cu_count, even_level

FULL = "0x1f,0x1f,0x1f,0x1f"
PASSED = [(1, "control", "PASS"), (2, "control", "PASS"), (3, "control", "PASS")]


def test_cu_counts_and_levels():
    assert cu_count("0x07,0x07,0x07,0x07") == 24
    assert cu_count("0x0f,0x0f,0x0f,0x0f") == 32
    assert cu_count(FULL) == 40
    assert even_level(FULL) == 5 and even_level("0x07,0x07,0x07,0x07") == 3
    assert even_level("0x1f,0x0f,0x1f,0x1f") is None          # uneven rows
    assert even_level("0x03,0x03,0x03,0x03") is None          # 2 per row is not a level


def test_no_results(state):
    state()
    result = check()
    assert not result.accepted and "Run that script first" in result.reasons[0]


def test_a_fully_retested_mask_is_accepted(state):
    state(FULL, rounds=3, runs=PASSED)
    result = check()
    assert result.accepted and result.masks == FULL and result.cu_total == 40
    assert "passed 3 retest round(s)" in result.reasons[0]


@pytest.mark.parametrize(("kwargs", "reason"), [
    ({"base": "none"}, "No usable baseline"),
    ({"base": FULL, "runs": PASSED, "pending": True}, "still marked as in progress"),
    ({"base": "0x03,0x03,0x03,0x03", "runs": PASSED}, "Every row needs 3, 4 or 5 WGPs"),
    ({"base": "0x1f,0x03,0x1f,0x1f", "runs": PASSED}, "5/2/5/5 WGPs on the 4 rows"),
    ({"base": FULL}, "No attempts recorded"),
    ({"base": FULL, "runs": [*PASSED, (1, "SE0.SH0.WGP4", "PASS")]}, "under individual test"),
    ({"base": FULL, "runs": PASSED[:2]}, "Only 2 of 3 retest round(s)"),
    ({"base": FULL, "runs": [*PASSED[:2], (3, "control", "DRIFT")]}, "round 3: DRIFT"),
    ({"base": FULL, "runs": [*PASSED[:2], (3, "control", "ABORTED")]}, "round 3: ABORTED"),
])
def test_rejections(state, kwargs, reason):
    state(**kwargs)
    result = check()
    assert not result.accepted
    assert any(reason in line for line in result.reasons), result.reasons


def test_a_retested_uneven_mask_is_accepted_and_says_what_it_gives(state):
    state("0x1f,0x1f,0x0f,0x1f", runs=PASSED)
    result = check()
    assert result.accepted and result.cu_total == 38
    assert "5/5/4/5 WGPs" in result.reasons[0] and "runs as fast as 36 CUs" in result.reasons[1]
    state("0x0f,0x07,0x07,0x0b", runs=PASSED)
    assert check().cu_total == 26 and "runs as fast as 24 CUs" in check().reasons[1]
    state("0x0f,0x1f,0x0f,0x1f", runs=PASSED)               # 9 WGPs in each engine: it runs like its count
    assert check().accepted and check().cu_total == 36 and len(check().reasons) == 1
