# SPDX-License-Identifier: GPL-3.0-or-later
from hdmi_cec import cec, media, watcher
from hdmi_cec.runner import Result
from conftest import INFO, NACK, POWER_ON, UNCONFIGURED

STANDBY = POWER_ON.replace("pwr-state: on (0x00)", "pwr-state: standby (0x01)")


class Board:
    """The TV's power as a sequence of answers, and the media players on the session bus."""

    def __init__(self, powers, playing=()):
        self.powers = list(powers)
        self.playing = set(playing)                     # the media players that play
        self.calls, self.slept = [], []

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[:2] == ["busctl", "--user"]:
            if argv[2] == "list":
                return Result(0, "".join(f"{media.PREFIX}{p} 123 {p} admin :1.9 - - -\n" for p in ("firefox", "mpv"))
                              + "org.kde.KWin 99 kwin_wayland admin :1.2 - - -\n")
            player = argv[3].removeprefix(media.PREFIX)
            if argv[2] == "get-property":
                return Result(0, 's "Playing"\n' if player in self.playing else 's "Paused"\n')
            if argv[-1] == "Pause":
                self.playing.discard(player)
            elif argv[-1] == "Play":
                self.playing.add(player)
            return Result(0, "")
        if "--give-device-power-status" in argv:
            return Result(0, self.powers.pop(0))
        return Result(0, INFO)

    def paused(self):
        return [c for c in self.calls if c[-1] == "Pause"]


def make(powers, pause=True, playing=()):
    board = Board(powers, playing)
    w = watcher.Watcher(run=board, sleep=board.slept.append, pause_media=pause)
    w.adapter = cec.parse_info("/dev/cec0", INFO)
    return w, board


def test_no_answer_counts_as_off_only_after_three():
    w, board = make([POWER_ON, NACK, NACK, POWER_ON], playing={"mpv"})          # a glitch: nothing paused
    for _ in range(4):
        w.step()
    assert board.paused() == []
    w, board = make([POWER_ON, NACK, NACK, NACK, POWER_ON], playing={"mpv"})    # unplugged and back
    for _ in range(5):
        w.step()
    assert len(board.paused()) == 1 and board.playing == {"mpv"}


def test_on_at_start_does_nothing():
    w, board = make([POWER_ON, POWER_ON], playing={"mpv"})
    w.step()
    w.step()
    assert board.paused() == [] and board.playing == {"mpv"}


def test_without_pause_nothing_happens():
    w, board = make([POWER_ON, STANDBY, POWER_ON], pause=False, playing={"mpv"})
    for _ in range(3):
        w.step()
    assert board.paused() == [] and board.playing == {"mpv"}


def test_pause_while_the_tv_is_off():
    w, board = make([POWER_ON, STANDBY, STANDBY, POWER_ON], playing={"mpv"})
    w.step()
    w.step()
    assert board.playing == set() and w.paused == [media.PREFIX + "mpv"]
    w.step()
    w.step()
    assert board.playing == {"mpv"} and w.paused == []
    pauses = [c for c in board.calls if c[-1] == "Pause"]
    assert pauses == [["busctl", "--user", "call", media.PREFIX + "mpv", media.PATH, media.PLAYER, "Pause"]]


def test_find_adapter_takes_the_one_with_a_display_and_the_users_name(tmp_path):
    dev = tmp_path / "dev"
    dev.mkdir()
    for name in ("cec0", "cec1"):
        (dev / name).touch()
    calls = []

    def run(argv):
        calls.append(argv)
        if "--playback" in argv:
            return Result(0, INFO.replace("ps5-cec", "cec-usb"))
        return Result(0, UNCONFIGURED.replace("1.0.0.0", "f.f.f.f") if argv[2].endswith("cec0") else
                      UNCONFIGURED.replace("ps5-cec", "cec-usb"))
    config = tmp_path / "config"
    (config / "cecd/config.d").mkdir(parents=True)
    (config / "cecd/config.d/99-ps5-hdmi-cec.toml").write_text('osd_name = "Lounge PC"\n')
    w = watcher.Watcher(run=run, sleep=lambda s: None, config_dir=config)
    adapter = w.find_adapter(dev)
    assert adapter.device == str(dev / "cec1") and adapter.configured
    assert ["cec-ctl", "-d", str(dev / "cec1"), "--playback", "--osd-name", "Lounge PC"] in calls


def test_find_adapter_renames_a_playback_adapter_unless_cecd_runs(tmp_path):
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "cec0").touch()
    for cecd, renamed in ((False, True), (True, False)):
        calls = []

        def run(argv):
            calls.append(argv)
            if argv[0] == "systemctl":
                return Result(0 if cecd else 3, "active\n" if cecd else "inactive\n")
            return Result(0, INFO)                      # configured, named "Playback"
        w = watcher.Watcher(run=run, sleep=lambda s: None, config_dir=tmp_path / "config")
        w.find_adapter(dev)
        assert any("--playback" in c for c in calls) == renamed
