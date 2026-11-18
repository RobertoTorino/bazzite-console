# SPDX-License-Identifier: GPL-3.0-or-later
"""The player where nothing can play (no audio output, as on CI): it never gets in the way."""

from __future__ import annotations

from remix_studio.player import Player


def test_without_an_output_nothing_plays_and_the_end_is_said_at_once(qapp, monkeypatch):
    player = Player()
    monkeypatch.setattr(player, "available", lambda: False)
    ended = []
    player.finished.connect(lambda: ended.append(True))

    assert player.output_name() == "" and not player.start() and not player.playing()
    player.feed(b"\x00\x00" * 200)
    assert not player.waiting and not player.timer.isActive()
    player.end()
    assert ended == [True]
    player.stop()
    player.close()


def test_play_without_an_output_says_so(qapp, monkeypatch):
    player = Player()
    monkeypatch.setattr(player, "available", lambda: False)
    assert not player.play(b"\x00\x00" * 200) and not player.playing()
