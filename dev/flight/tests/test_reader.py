# SPDX-License-Identifier: GPL-3.0-or-later
"""The reader finds the days, takes the minutes around a time and gives each value's last, lowest and highest."""

from __future__ import annotations

import pytest

from nexus_flight_recorder import reader


def test_the_days_newest_first(recordings):
    (recordings / "notes.csv").write_text("x\n")
    assert reader.days(recordings) == ["2026-11-27", "2026-11-26"]


@pytest.mark.parametrize(("text", "at"), [("00:46", (0, 46)), ("0.46", (0, 46)), (" 23:59 ", (23, 59)),
                                         ("24:00", None), ("7", None), ("now", None), ("12:60", None)])
def test_times(text, at):
    assert reader.parse_time(text) == at


def test_the_minutes_around_a_time(recordings):
    window = reader.around("2026-11-27", (0, 46), recordings)
    assert (window.start, window.end, window.lines) == ("00:41:00", "00:51:00", 601)
    stats = {s.name: s for s in window.stats}
    clock = stats["GPU clock"]
    assert (clock.low, clock.high, clock.last) == (1000.0, 1850.0, 1850.0) and clock.text(clock.high) == "1850 MHz"
    assert stats["Memory in use"].text(stats["Memory in use"].last) == "4096 MiB"
    assert stats["Swap in use"].text(stats["Swap in use"].high) == "512 MiB"
    assert stats["Memory pressure"].text(stats["Memory pressure"].low) == "0.50"
    assert window.busiest == [("steam", 301), ("code", 300)] and window.boots == 2


def test_without_a_time_the_last_ten_minutes(recordings):
    window = reader.around("2026-11-27", None, recordings)
    assert (window.start, window.end, window.lines) == ("00:43:00", "00:52:59", 600)


def test_no_lines(recordings):
    for window in (reader.around("2026-11-27", (12, 0), recordings), reader.around("2026-11-26", None, recordings),
                   reader.around("2026-11-01", None, recordings)):
        assert window.lines == 0 and window.busiest == [] and all(s.last is None for s in window.stats)
        assert window.stats[0].text(None) == ""


def test_sizes():
    assert reader.size_text(0) == "0 KB" and reader.size_text(4096) == "4 KB" and reader.size_text(13 << 20) == "13.0 MB"
