# SPDX-License-Identifier: GPL-3.0-or-later
"""Steam's files (bazzite_console_core.steam) on Steam folders made in a temp folder: the binary format, the appid, shortcuts
added, updated and removed beside others, several in one write, closing Steam for a change, and finding Steam."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from bazzite_console_core import steam

OTHER = {"appid": -1234, "AppName": "RetroArch", "Exe": '"/usr/bin/retroarch"', "StartDir": '"/usr/bin/"',
         "LaunchOptions": "", "LastPlayTime": 1700000000, "tags": {"0": "Emulators"}}


def _steam(tmp_path: Path, users: int = 1, with_other: bool = True) -> Path:
    for n in range(users):
        config = tmp_path / "Steam" / "userdata" / str(1000 + n) / "config"
        config.mkdir(parents=True)
        if with_other:
            (config / "shortcuts.vdf").write_bytes(steam.write_vdf({"shortcuts": {"0": OTHER}}))
    return tmp_path / "Steam"


def _game(name: str, options: str) -> steam.Change:
    entry = steam.shortcut_entry('"/bin/run"', name, '"/bin/"', "/icon.png", options, ["PS4", "PS5"])
    return steam.Change(entry, lambda item, options=options: item.get("LaunchOptions") == options)


def test_the_binary_format_by_hand():
    data = (b"\x00shortcuts\x00" + b"\x000\x00" + b"\x02appid\x00" + struct.pack("<i", -5) +
            b"\x01AppName\x00Game\x00" + b"\x00tags\x00\x01" + b"0\x00x\x00\x08" + b"\x08" + b"\x08" + b"\x08")
    values = steam.read_vdf(data)
    assert values == {"shortcuts": {"0": {"appid": -5, "AppName": "Game", "tags": {"0": "x"}}}}
    assert steam.write_vdf(values) == data
    assert steam.read_vdf(b"") == {}
    with pytest.raises(steam.ShortcutError):
        steam.read_vdf(b"\x00shortcuts\x00\x05x\x00")
    with pytest.raises(steam.ShortcutError, match="damaged"):
        steam.read_vdf(b"\x00shortcuts\x00\x01AppName")


def test_the_entry_and_its_appid():
    entry = steam.shortcut_entry('"/bin/run"', "Game", '"/bin/"', "/i.png", "-g x", ["A", "B"])
    number = steam.appid('"/bin/run"', "Game")
    assert number == zlib.crc32(b'"/bin/run"Game') | 0x80000000 and number >= 1 << 31
    assert entry["appid"] == steam.as_int32(number) == number - (1 << 32) and steam.as_int32(5) == 5
    assert list(entry)[:7] == ["appid", "AppName", "Exe", "StartDir", "icon", "ShortcutPath", "LaunchOptions"]
    assert entry["tags"] == {"0": "A", "1": "B"} and entry["LastPlayTime"] == 0


def test_the_shortcut_icon_is_the_png_beside_a_webp_icon(tmp_path):
    logo, png = tmp_path / "app.webp", tmp_path / "app-128.png"
    logo.write_bytes(b"W")
    assert steam.shortcut_icon(logo) == logo                                  # no PNG beside it: the logo itself
    png.write_bytes(b"P")
    assert steam.shortcut_icon(logo) == png
    assert steam.shortcut_icon(tmp_path / "icon0.png") == tmp_path / "icon0.png"     # a PNG as it is


def test_several_shortcuts_in_one_write(tmp_path):
    folder = _steam(tmp_path, users=2)
    first, second = _game("Game one", "-g /a"), _game("Game two", "-g /b")
    art = {"p": b"P", "": b"W", "_hero": b"H", "_logo": b"L"}
    first = steam.Change(first.entry, first.ours, art)
    numbers = steam.write_shortcuts(folder, [first, second])
    assert numbers == [first.number, second.number]
    for config in steam.user_folders(folder):                             # every Steam user gets them
        values = steam.read_vdf((config / "shortcuts.vdf").read_bytes())
        assert [item["AppName"] for item in values["shortcuts"].values()] == ["RetroArch", "Game one", "Game two"]
        assert values["shortcuts"]["0"] == OTHER                          # the other one stays as it was
        assert sorted(p.name for p in (config / "grid").iterdir()) == sorted(
            f"{first.number}{suffix}.png" for suffix in steam.ART)        # artwork only where given
        assert not list(config.glob("*.bazzite-console-tmp"))
    assert len(steam.shortcuts(folder)) == 6 and steam.has_shortcut(folder, second.ours)


def test_update_keeps_the_play_time_and_remove_takes_the_artwork(tmp_path):
    folder = _steam(tmp_path)
    game = _game("Game", "-g /a")
    steam.write_shortcuts(folder, [steam.Change(game.entry, game.ours, {"p": b"P"})])
    config = steam.user_folders(folder)[0]
    values = steam.read_vdf((config / "shortcuts.vdf").read_bytes())
    values["shortcuts"]["1"]["LastPlayTime"] = 1750000000
    (config / "shortcuts.vdf").write_bytes(steam.write_vdf(values))
    renamed = _game("Game, renamed", "-g /a")
    steam.write_shortcuts(folder, [steam.Change(renamed.entry, renamed.ours, {"p": b"R"})])
    values = steam.read_vdf((config / "shortcuts.vdf").read_bytes())
    assert len(values["shortcuts"]) == 2 and values["shortcuts"]["1"]["AppName"] == "Game, renamed"
    assert values["shortcuts"]["1"]["LastPlayTime"] == 1750000000
    assert [p.name for p in (config / "grid").iterdir()] == [f"{renamed.number}p.png"]   # the old number's went
    steam.write_shortcuts(folder, [steam.Change(renamed.entry, renamed.ours, remove=True)])
    assert steam.read_vdf((config / "shortcuts.vdf").read_bytes()) == {"shortcuts": {"0": OTHER}}
    assert not list((config / "grid").iterdir())


def test_a_shortcut_of_another_program_taken_out_takes_its_artwork(tmp_path):
    """A shortcut made before a game manager's play mode starts the emulator itself, so its number is another's than
    the change that takes it out (30-10-2026): the artwork under the number it has goes."""
    folder = _steam(tmp_path)
    old = _game("Game", "-g /a")
    steam.write_shortcuts(folder, [steam.Change(old.entry, old.ours, {"p": b"P", "_hero": b"H"})])
    entry = steam.shortcut_entry('"/bin/manager"', "Game", '"/bin/"', "/icon.png", "-g /a", ["PS4", "PS5"])
    assert steam.Change(entry, old.ours).number != old.number
    steam.write_shortcuts(folder, [steam.Change(entry, old.ours, remove=True)])
    config = steam.user_folders(folder)[0]
    assert steam.read_vdf((config / "shortcuts.vdf").read_bytes()) == {"shortcuts": {"0": OTHER}}
    assert not list((config / "grid").iterdir())


def test_a_rename_keeps_artwork_whose_number_is_taken_again(tmp_path):
    """Two shortcuts that swap names: each number is in use after the change, so no artwork goes."""
    folder = _steam(tmp_path)
    a, b = _game("A", "-g /a"), _game("B", "-g /b")
    steam.write_shortcuts(folder, [steam.Change(a.entry, a.ours, {"p": b"A"}),
                                   steam.Change(b.entry, b.ours, {"p": b"B"})])
    swapped = [_game("B", "-g /a"), _game("A", "-g /b")]
    steam.write_shortcuts(folder, swapped)
    grid = steam.user_folders(folder)[0] / "grid"
    assert sorted(p.name for p in grid.iterdir()) == sorted([f"{a.number}p.png", f"{b.number}p.png"])


def test_no_users_and_a_damaged_file(tmp_path):
    with pytest.raises(steam.ShortcutError, match="no users"):
        steam.write_shortcuts(tmp_path / "nowhere", [_game("Game", "-g /a")])
    folder = _steam(tmp_path, with_other=False)
    (steam.user_folders(folder)[0] / "shortcuts.vdf").write_bytes(b"\x00shortcuts\x00\x05")
    assert steam.shortcuts(folder) == []                                   # left out, not an error


def test_find_steam(tmp_path):
    assert steam.find_steam(tmp_path) is None
    flatpak = tmp_path / ".var/app/com.valvesoftware.Steam/.local/share/Steam/userdata"
    flatpak.mkdir(parents=True)
    assert steam.find_steam(tmp_path) == flatpak.parent
    native = tmp_path / ".local/share/Steam/userdata"
    native.mkdir(parents=True)
    assert steam.find_steam(tmp_path) == native.parent                    # the native one first


def test_closed_for_a_change_and_started_again():
    commands, state, changed = [], {"running": True, "polls": 0}, []

    def run(command):
        commands.append(command)

    def running():
        if commands:
            state["polls"] += 1
            state["running"] = state["polls"] <= 2                        # closes after a moment
        return state["running"]
    assert steam.with_steam_closed(lambda: changed.append(state["running"]), run, running, sleep=lambda s: None)
    assert changed == [False] and commands == [steam.shutdown_command(), steam.start_command()]
    assert steam.with_steam_closed(lambda: None, run, lambda: False) is False and len(commands) == 2


def test_steam_that_does_not_close_changes_nothing():
    commands, changed = [], []
    with pytest.raises(steam.SteamError, match="did not close"):
        steam.with_steam_closed(lambda: changed.append(1), commands.append, lambda: True, timeout=1.0,
                                sleep=lambda s: None)
    assert commands == [steam.shutdown_command()] and changed == []


def test_steam_running_reads_process_names(tmp_path, monkeypatch):
    def process(pid, name, state="S"):
        (tmp_path / str(pid)).mkdir()
        (tmp_path / str(pid) / "comm").write_text(name + "\n")
        (tmp_path / str(pid) / "stat").write_text(f"{pid} ({name}) {state} 1 {pid} {pid} 0 -1\n")
    process(10, "bash")
    process(11, "steamwebhelper")
    process(12, "steam", "Z")               # a finished steam -shutdown not collected yet (the owner's board, 13-10-2026)
    assert not steam.steam_running(tmp_path)
    process(13, "steam")
    assert steam.steam_running(tmp_path)


def test_signed_in_reads_the_newest_state_of_the_connection_log(tmp_path):
    """Steam's connection log as the owner's board wrote it (22-11-2026), with the account and addresses left out."""
    proc, folder = tmp_path / "proc", tmp_path / "Steam"
    (proc / "20").mkdir(parents=True)
    (proc / "20" / "comm").write_text("steam\n")
    (proc / "20" / "stat").write_text("20 (steam) S 1 20 20 0 -1\n")
    log = folder / steam.CONNECTION_LOG
    log.parent.mkdir(parents=True)
    assert not steam.signed_in(folder, proc)                        # no log yet
    log.write_text("[2026-11-22 10:03:25] [Logging On, 4, 7] [U:1:1] RecvMsgClientLogOnResponse() : [U:1:1] 'OK'\n"
                   "[2026-11-22 10:03:25] [Logged On, 4, 7] [U:1:1] RecvMsgClientLogOnResponse() : processing complete\n"
                   "a line without a state\n")
    assert steam.signed_in(folder, proc)
    with log.open("a") as more:
        more.write("[2026-11-22 10:05:46] [Logged On, 4, 7] [U:1:1] LogOff()\n"
                   "[2026-11-22 10:05:46] [Logging Off, 4, 7] [U:1:1] AsyncDisconnect( bDontWaitOnTCPShutdown: false )\n"
                   "[2026-11-22 10:05:47] [Logged Off, 0, 0] [U:1:1] Log session ended\n")
    assert not steam.signed_in(folder, proc)                        # signed out
    log.write_text("[2026-11-22 10:03:25] [Logged On, 4, 7] [U:1:1] RecvMsgClientLogOnResponse() : processing complete\n")
    (proc / "20" / "comm").write_text("bash\n")
    assert not steam.signed_in(folder, proc)                        # the log says so, but Steam does not run
    assert not steam.signed_in(None, proc)                          # no Steam at all


def test_game_mode(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "gamescope")
    assert steam.game_mode()
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    assert not steam.game_mode()


def test_steam_closes_with_its_own_command():
    assert steam.shutdown_command() == ["steam", "-shutdown"]          # as before Windows (29-10-2026)


def test_installed_is_steams_program(tmp_path, monkeypatch):
    """The portal's RT Steam shows only where Steam's program is (owner, 30-10-2026)."""
    monkeypatch.setattr(steam.shutil, "which", lambda name: str(tmp_path / name))
    assert steam.installed()                            # never signed in yet (no userdata): there, to be opened
    monkeypatch.setattr(steam.shutil, "which", lambda name: None)
    assert not steam.installed()


def test_a_shortcut_is_started_by_its_game_id():
    """A game started from its manager goes through Steam (owner, 29-10-2026): steam://rungameid/ with the shortcut's
    appid in the high half."""
    assert steam.play_url(0x9ABCDEF0) == f"steam://rungameid/{(0x9ABCDEF0 << 32) | 0x02000000}"
    assert steam.play_url(steam.as_int32(0x9ABCDEF0)) == steam.play_url(0x9ABCDEF0)   # signed as in the file


def test_the_number_of_a_shortcut_as_steams_file_has_it(tmp_path):
    """What Start game hands to play_url() (owner, 12-11-2026): the shortcut's appid from Steam's own file, its 32
    bits; from its program and name when the file names none; None for a game that has no shortcut."""
    folder = _steam(tmp_path)
    game = _game("Game", "-g one")
    assert steam.shortcut_number(folder, game.ours) is None
    assert steam.write_shortcuts(folder, [game]) == [game.number]
    assert steam.shortcut_number(folder, game.ours) == game.number == steam.appid('"/bin/run"', "Game")
    assert steam.shortcut_number(folder, lambda item: item.get("AppName") == "RetroArch") == -1234 & 0xFFFFFFFF
    assert steam.shortcut_number(folder, lambda item: False) is None
    path = folder / "userdata" / "1000" / "config" / "shortcuts.vdf"
    values = steam.read_vdf(path.read_bytes())
    for item in values["shortcuts"].values():
        item.pop("appid")                                                     # a file without the numbers
    path.write_bytes(steam.write_vdf(values))
    assert steam.shortcut_number(folder, game.ours) == game.number



def test_steam_takes_commands_when_its_process_has_the_pipe_open(tmp_path):
    """As Steam's own start script tells a running Steam: the process the pid file names has the command pipe open.
    A pid file left behind, or a Steam that is still starting, takes none."""
    home, proc = tmp_path / "home", tmp_path / "proc"
    (home / ".steam").mkdir(parents=True)
    assert not steam.takes_commands(home, proc)                              # no pid file
    (home / ".steam" / "steam.pid").write_text("42\n")
    assert not steam.takes_commands(home, proc)                              # a pid file left behind
    (proc / "42" / "fd").mkdir(parents=True)
    (proc / "42" / "fd" / "3").symlink_to("/dev/null")
    assert not steam.takes_commands(home, proc)                              # still starting
    (proc / "42" / "fd" / "7").symlink_to(home / ".steam" / "steam.pipe")
    assert steam.takes_commands(home, proc)
    # A home folder that is a link, as Bazzite's (/home to /var/home): the process names the pipe by the other
    # spelling, and Steam never seemed ready (the board, 20-11-2026)
    (tmp_path / "link").symlink_to(home)
    assert steam.takes_commands(tmp_path / "link", proc)


def test_play_starts_steam_first_and_waits_for_the_game():
    """Start game with Steam closed (owner's board, 20-11-2026: Steam came up and the game never started): Steam is
    started and waited for, then the game's address is given, again while the game does not run."""
    ran, opened, slept = [], [], []
    state = {"ready": 0, "started": 0}

    def ready() -> bool:
        state["ready"] += 1
        return state["ready"] > 3

    def started() -> bool:
        state["started"] += 1
        return len(opened) == 2                                              # the first address was dropped

    steam.play("steam://rungameid/1", lambda url: opened.append(url) or True, started, run=ran.append,
               running=lambda: False, ready=ready, pause=2, sleep=slept.append)
    assert ran == [steam.start_command()] and opened == ["steam://rungameid/1"] * 2
    assert len(slept) == 2 + 2                                               # for Steam, then for the first address

    ran.clear(), opened.clear()
    steam.play("steam://rungameid/1", lambda url: opened.append(url) or True, lambda: True, run=ran.append,
               running=lambda: True, ready=lambda: True, sleep=slept.append)
    assert ran == [] and len(opened) == 1                                    # a running Steam: the address at once


def test_play_says_what_went_wrong():
    nothing = lambda _seconds: None
    with pytest.raises(steam.SteamError, match="did not start within 2 seconds"):
        steam.play("steam://x", lambda url: True, lambda: True, run=lambda command: None, running=lambda: False,
                   ready=lambda: False, timeout=2, sleep=nothing)
    with pytest.raises(steam.SteamError, match="xdg-open is missing"):
        steam.play("steam://x", lambda url: False, lambda: True, ready=lambda: True, sleep=nothing)
    opened = []
    with pytest.raises(steam.SteamError, match="Steam did not start it"):
        steam.play("steam://x", lambda url: opened.append(url) or True, lambda: False, ready=lambda: True, tries=2,
                   pause=1, sleep=nothing)
    assert len(opened) == 2


def test_a_game_in_steam_more_than_once_is_counted_and_one_is_left(tmp_path):
    """Owner, 20-11-2026 ("multiple entries for the same game in Steam"): doubles() says how many shortcuts a game
    has too many, and writing the game again leaves one, with the latest play time; the others' shortcuts stay."""
    folder = _steam(tmp_path)
    game, other = _game("Game", "-g one"), _game("Other", "-g two")
    steam.write_shortcuts(folder, [game, other])
    key = lambda item: str(steam.field(item, "LaunchOptions")) if str(steam.field(item, "Exe")) == '"/bin/run"' else ""
    assert steam.doubles(folder, key) == {}
    path = folder / "userdata" / "1000" / "config" / "shortcuts.vdf"
    values = steam.read_vdf(path.read_bytes())
    items = list(values["shortcuts"].values())
    again = {**items[1], "AppName": "Game (old name)", "LastPlayTime": 77}
    lower = {("exe" if k == "Exe" else "launchoptions" if k == "LaunchOptions" else k): v for k, v in items[1].items()}
    path.write_bytes(steam.write_vdf({"shortcuts": {str(n): i for n, i in enumerate([*items, again, lower])}}))
    assert steam.doubles(folder, key) == {"-g one": 2}                          # three of it: two too many
    seen = lambda item: steam.field(item, "LaunchOptions") == "-g one"
    steam.write_shortcuts(folder, [steam.Change(game.entry, seen)])
    after = list(steam.read_vdf(path.read_bytes())["shortcuts"].values())
    assert [i["AppName"] for i in after] == ["RetroArch", "Game", "Other"] and after[1]["LastPlayTime"] == 77
    assert steam.doubles(folder, key) == {}


def test_steam_starts_without_our_sdl_variables():
    """Steam started with SDL's dummy video driver crashed on every window (the owner's machine, 22-11-2026)."""
    env = {"PATH": "/usr/bin", "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "pipewire", "SDL_VIDEO_X11_WMCLASS": "-c",
           "SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS": "1", "PYGAME_HIDE_SUPPORT_PROMPT": "1"}
    assert steam.steam_environment(env) == {"PATH": "/usr/bin", "SDL_AUDIODRIVER": "pipewire"}   # the user's stays
