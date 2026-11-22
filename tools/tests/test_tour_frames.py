# SPDX-License-Identifier: GPL-3.0-or-later
"""What the video tours share (tools/tour_frames.py): the video's size, the temporary home for an offscreen Qt, the
window's place, the music under a video and what a crashed ffmpeg leaves (owner, 22-11-2026: its test went with the
Windows code on 15-11-2026)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tour_frames  # noqa: E402


@pytest.fixture(autouse=True)
def layout(monkeypatch):
    """Each test starts at 1080p and 120 %, and the environment and the import path come back after it."""
    monkeypatch.setattr(tour_frames, "ZOOM", 1.0)
    monkeypatch.setattr(tour_frames, "SCALE", 1.2)
    monkeypatch.setattr(sys, "path", list(sys.path))
    for var in ("HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "QT_QPA_PLATFORM",
                "QT_SCALE_FACTOR", "QT_SCREEN_SCALE_FACTORS"):
        monkeypatch.setenv(var, os.environ.get(var, ""))


def test_the_video_size_is_the_layout_times_its_multiple():
    assert tour_frames.size() == (1920, 1080)
    tour_frames.set_size("2160p")
    assert tour_frames.size() == (3840, 2160)
    tour_frames.set_size("1440p")
    assert tour_frames.size() == (2560, 1440)
    with pytest.raises(KeyError):
        tour_frames.set_size("8k")


def test_the_home_is_a_temp_folder_with_one_screen_of_the_videos_size(tmp_path):
    tour_frames.set_size("2160p")
    tour_frames.prepare_home(tmp_path)
    assert os.environ["HOME"] == str(tmp_path) and os.environ["XDG_CONFIG_HOME"] == str(tmp_path / ".config")
    assert (tmp_path / ".local" / "share").is_dir() and (tmp_path / ".cache").is_dir()
    screen = json.loads((tmp_path / "screen.json").read_text(encoding="utf-8"))["screens"][0]
    assert (screen["width"], screen["height"]) == (3840, 2160)
    assert os.environ["QT_QPA_PLATFORM"] == f"offscreen:configfile={tmp_path / 'screen.json'}"
    assert float(os.environ["QT_SCALE_FACTOR"]) == pytest.approx(2.4)     # 120 % at twice the layout
    assert sys.path[0] == str(tour_frames.ROOT / "core")


def test_the_window_fills_the_video():
    calls = []

    class Window:
        def move(self, x, y):
            calls.append(("move", x, y))

        def resize(self, w, h):
            calls.append(("resize", w, h))
    tour_frames.place(Window())
    assert calls == [("move", 0, 0), ("resize", 1600, 900)]
    tour_frames.set_scale(1.5)
    calls.clear()
    tour_frames.place(Window())
    assert calls == [("move", 0, 0), ("resize", 1280, 720)]


def test_the_music_loops_under_the_picture_and_fades_out(monkeypatch, tmp_path):
    seen = []

    def run(argv, **_kwargs):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(tour_frames.subprocess, "run", run)
    assert tour_frames.add_music(tmp_path / "v.mp4", tmp_path / "m.ogg", tmp_path / "out.mp4", 30.0) == 0
    argv = seen[0]
    assert argv[0] == "ffmpeg" and argv[argv.index("-stream_loop") + 1] == "-1"
    assert argv[argv.index("-c:v") + 1] == "copy"                         # the picture as it is
    assert argv[argv.index("-af") + 1] == "afade=t=out:st=28.000:d=2.0" and argv[argv.index("-t") + 1] == "30.000"


class Image:
    """A frame as QImage gives it: its bytes, and a row stride that may hold padding."""

    def __init__(self, width: int, height: int, stride: int):
        self.data = bytes(range(256))[:stride] * height
        self.stride = stride

    def constBits(self):  # noqa: N802 (QImage's name)
        data = self.data
        return type("Bits", (), {"asstring": lambda _self, n: data[:n]})()

    def sizeInBytes(self):  # noqa: N802
        return len(self.data)

    def bytesPerLine(self):  # noqa: N802
        return self.stride


class Pipe:
    def __init__(self, broken: bool = False):
        self.written, self.broken = [], broken

    def write(self, data):
        if self.broken:
            raise BrokenPipeError
        self.written.append(data)

    def close(self):
        if self.broken:
            raise BrokenPipeError


def recorder(pipe: Pipe, code: int = 0):
    made = tour_frames.Recorder.__new__(tour_frames.Recorder)
    made.fps, made.frames, made.width, made.height = 30, 0, 2, 2
    made.ffmpeg = type("Ffmpeg", (), {"stdin": pipe, "wait": lambda _self: code})()
    return made


def test_a_frame_goes_to_ffmpeg_without_the_rows_padding():
    pipe = Pipe()
    made = recorder(pipe)
    made.emit(Image(2, 2, 8), count=3)                                    # 2 x 3 bytes a row, padded to 8
    assert made.frames == 3 and len(pipe.written) == 3
    assert pipe.written[0] == bytes(range(6)) * 2


def test_a_crashed_ffmpeg_ends_the_recording_with_a_message(capsys):
    made = recorder(Pipe(broken=True), code=-11)
    made.frames = 300
    with pytest.raises(SystemExit) as stop:
        made.emit(Image(2, 2, 6))
    assert stop.value.code == 1
    assert "ffmpeg crashed (signal 11) after 10 s of video" in capsys.readouterr().err
    assert made.finish() == -11                                           # closing the gone pipe raises nothing
