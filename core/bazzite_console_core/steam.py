# SPDX-License-Identifier: GPL-3.0-or-later
"""Steam's own files, for apps that add non-Steam games for Game Mode: finding Steam and its users, closing it while
its files change, and the shortcuts in shortcuts.vdf with their artwork. Only the standard library here.

Steam keeps non-Steam games per user in userdata/<user>/config/shortcuts.vdf, a binary key-value file: a map is
0x00, its name and its entries up to 0x08; a string is 0x01, its name and its text; a number is 0x02, its name and
4 bytes, little-endian; names and texts end with a zero byte. A shortcut's appid is the one Steam gives a non-Steam
game, the CRC-32 of its program and name with the top bit set; its artwork goes into userdata/<user>/config/grid/
under that number: <id>p.png (the library's portrait, 2:3, 600 × 900), <id>.png (the wide one, 920 × 430),
<id>_hero.png (the banner, up to 3840 × 1240) and <id>_logo.png (on the banner, transparent, up to 1280 × 720).

Steam holds its settings in memory and rewrites its files when it exits, so a change while it runs would be lost:
with_steam_closed() closes Steam first (steam -shutdown) and starts it again in the background as the desktop starts
it at login (Bazzite's bazzite-steam -silent, elsewhere steam -silent). The other shortcuts in the file stay as they
are."""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import threading
import time
import zlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

STEAM_DIRS = (                          # the native Steam (Bazzite's), its older link, the Flatpak's
    "~/.local/share/Steam",
    "~/.steam/steam",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam",
)
SHUTDOWN_TIMEOUT = 30.0
START_TIMEOUT = 120.0                   # play(): how long a Steam that was started may take to come up
PLAY_TRIES = 3                          # play(): how often the game's address is given
PLAY_PAUSE = 30.0                       # play(): seconds a game may take to run before the address is given again
MAP, STRING, INT32, END = 0, 1, 2, 8
ART = {"p": (600, 900), "": (920, 430), "_hero": (3840, 1240), "_logo": (1280, 720)}

Run = Callable[[list[str]], None]


class SteamError(Exception):
    pass


class ShortcutError(Exception):
    pass


# --- Steam itself ----------------------------------------------------------------------------------------------

def installed() -> bool:
    """Whether Steam's program is here, signed in once or not: steam on PATH (owner, 30-10-2026: the
    portal's RT Steam only where there is a Steam to open)."""
    return shutil.which("steam") is not None


def find_steam(home: Path | None = None) -> Path | None:
    """The Steam folder with users in it, or None when Steam was never used here."""
    for folder in STEAM_DIRS:
        path = Path(folder.replace("~", str(home), 1) if home else os.path.expanduser(folder))
        if (path / "userdata").is_dir():
            return path.resolve()
    return None


def user_folders(steam: Path) -> list[Path]:
    """userdata/<user>/config of every Steam user."""
    return sorted(p for p in (steam / "userdata").glob("*/config") if p.is_dir())


def steam_running(proc: Path = Path("/proc")) -> bool:
    """Whether a Steam client process runs (its process name is steam). A finished one that its parent has not
    collected yet (a zombie, state Z) does not count: on the owner's board (13-10-2026) the app's own finished
    steam -shutdown was one, and Steam seemed not to close."""
    for folder in proc.glob("[0-9]*"):
        try:
            if (folder / "comm").read_text().strip() != "steam":
                continue
            state = (folder / "stat").read_text().rsplit(")", 1)[1].split()[0]
        except (OSError, IndexError):
            continue
        if state not in ("Z", "X"):
            return True
    return False


def game_mode() -> bool:
    """Bazzite's Game Mode: Steam's gamescope session."""
    return "gamescope" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()


def start_command() -> list[str]:
    """Steam started again after with_steam_closed(), in the background as the desktop starts it at login."""
    return ["bazzite-steam" if shutil.which("bazzite-steam") else "steam", "-silent"]


def shutdown_command() -> list[str]:
    return ["steam", "-shutdown"]


def play_url(number: int) -> str:
    """The steam:// address that starts the non-Steam game whose shortcut has appid *number* (its 32 bits, as
    Change.number): Steam's game id for a shortcut is that appid in the high half with 0x02000000 below it. Steam
    starts first when it does not run (owner, 29-10-2026: a game started from its manager, through Steam)."""
    return f"steam://rungameid/{((number & 0xFFFFFFFF) << 32) | 0x02000000}"


def takes_commands(home: Path | None = None, proc: Path = Path("/proc")) -> bool:
    """Whether a running Steam takes a steam:// address now, as Steam's own start script tells: the process its pid
    file names has Steam's command pipe open. A Steam that is still starting does not, and neither does a pid file
    left by one that ended."""
    folder = (home or Path.home()) / ".steam"
    try:
        pid = (folder / "steam.pid").read_text().strip()
        if not pid.isdigit():
            return False
        # Both resolved: the home folder is a link on Bazzite (/home to /var/home), and the process names the
        # pipe by the other spelling. Compared as written, Steam never seemed ready (the board, 20-11-2026).
        pipe = os.path.realpath(folder / "steam.pipe")
        return any(os.path.realpath(os.readlink(link)) == pipe for link in (proc / pid / "fd").iterdir())
    except OSError:
        return False


def play(url: str, open_url: Callable[[str], bool], started: Callable[[], bool], run: Run | None = None,
         running: Callable[[], bool] = steam_running, ready: Callable[[], bool] = takes_commands,
         timeout: float = START_TIMEOUT, tries: int = PLAY_TRIES, pause: float = PLAY_PAUSE,
         sleep: Callable[[float], None] = time.sleep) -> None:
    """Starts a game by its steam:// address (play_url()) and waits until it runs (*started*). A Steam that does
    not run is started first and waited for: started with the address itself, Steam came up and never started the
    game (owner's board, 20-11-2026). The address is given again, at most *tries* times with *pause* seconds
    between, while the game does not run: a Steam that only just took commands may still drop it. Raises
    SteamError when Steam does not come up, the address cannot be opened or the game does not start."""
    if not ready():
        if not running():
            (run or _run)(start_command())
        waited = 0.0
        while not ready():
            if waited >= timeout:
                raise SteamError(f"Steam did not start within {timeout:g} seconds.")
            sleep(1)
            waited += 1
    for _ in range(tries):
        if not open_url(url):
            raise SteamError("xdg-open is missing.")
        waited = 0.0
        while waited < pause:
            if started():
                return
            sleep(1)
            waited += 1
    raise SteamError("Steam did not start it: look in Steam, which may be asking something.")


def _run(command: list[str]) -> None:
    """Starts a Steam command in the background; a thread collects it when it ends, so it leaves no zombie."""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    threading.Thread(target=process.wait, name="steam-command", daemon=True).start()


def with_steam_closed(change: Callable[[], None], run: Run = _run, running: Callable[[], bool] = steam_running,
                      timeout: float = SHUTDOWN_TIMEOUT, sleep: Callable[[float], None] = time.sleep) -> bool:
    """Runs *change* (an edit of Steam's files) with Steam closed: closed first when it runs, and started again after.
    Returns whether Steam was restarted. Nothing is changed when Steam does not close."""
    was_running = running()
    if was_running:
        run(shutdown_command())
        waited = 0.0
        while running():
            if waited >= timeout:
                raise SteamError(f"Steam did not close within {timeout:g} seconds; nothing was changed.")
            sleep(0.5)
            waited += 0.5
    try:
        change()
    finally:
        if was_running:
            run(start_command())
    return was_running


def write_atomic(path: Path, data: bytes) -> None:
    """Writes through a temporary file beside it, so Steam never finds half a file; the file's mode is kept."""
    temporary = path.with_name(path.name + ".bazzite-console-tmp")
    temporary.write_bytes(data)
    if path.exists():
        os.chmod(temporary, path.stat().st_mode & 0o7777)
    temporary.replace(path)


# --- The binary key-value format -------------------------------------------------------------------------------

def _cstring(data: bytes, at: int) -> tuple[str, int]:
    end = data.index(b"\0", at)
    return data[at:end].decode("utf-8", errors="replace"), end + 1


def _read_map(data: bytes, at: int) -> tuple[dict, int]:
    result: dict = {}
    while True:
        kind = data[at]
        at += 1
        if kind == END:
            return result, at
        name, at = _cstring(data, at)
        if kind == MAP:
            result[name], at = _read_map(data, at)
        elif kind == STRING:
            result[name], at = _cstring(data, at)
        elif kind == INT32:
            result[name] = struct.unpack_from("<i", data, at)[0]
            at += 4
        else:
            raise ShortcutError(f"shortcuts.vdf: an entry of an unknown kind ({kind}).")


def read_vdf(data: bytes) -> dict:
    """The file as nested dicts: maps, texts (str) and numbers (int)."""
    if not data:
        return {}
    try:
        result, _at = _read_map(data, 0)
    except (IndexError, ValueError, struct.error) as error:
        raise ShortcutError("shortcuts.vdf is damaged.") from error
    return result


def _write_map(values: dict) -> bytes:
    out = bytearray()
    for name, value in values.items():
        key = name.encode("utf-8") + b"\0"
        if isinstance(value, dict):
            out += bytes([MAP]) + key + _write_map(value)
        elif isinstance(value, bool) or isinstance(value, int):
            out += bytes([INT32]) + key + struct.pack("<i", int(value))
        else:
            out += bytes([STRING]) + key + str(value).encode("utf-8") + b"\0"
    return bytes(out + bytes([END]))


def write_vdf(values: dict) -> bytes:
    return _write_map(values)


# --- Shortcuts -------------------------------------------------------------------------------------------------

def appid(exe: str, name: str) -> int:
    """Steam's number for a non-Steam game (unsigned): the CRC-32 of its program and name, top bit set."""
    return zlib.crc32((exe + name).encode("utf-8")) | 0x80000000


def as_int32(value: int) -> int:
    return value - (1 << 32) if value >= 1 << 31 else value


def shortcut_icon(logo: Path) -> Path:
    """The icon file for a shortcut: for an app's WebP icon the PNG beside it (images/<id>-128.png), as Steam may not
    read WebP; any other picture as it is."""
    png = logo.with_name(f"{logo.stem}-128.png")
    return png if logo.suffix.lower() == ".webp" and png.is_file() else logo


def shortcut_entry(exe: str, name: str, start_dir: str, icon: str, launch_options: str, tags: Sequence[str]) -> dict:
    """A shortcut's fields, in the order Steam writes them. *exe* and *start_dir* as Steam keeps them, in quotes."""
    return {
        "appid": as_int32(appid(exe, name)),
        "AppName": name,
        "Exe": exe,
        "StartDir": start_dir,
        "icon": icon,
        "ShortcutPath": "",
        "LaunchOptions": launch_options,
        "IsHidden": 0,
        "AllowDesktopConfig": 1,
        "AllowOverlay": 1,
        "OpenVR": 0,
        "Devkit": 0,
        "DevkitGameID": "",
        "DevkitOverrideAppID": 0,
        "LastPlayTime": 0,
        "FlatpakAppID": "",
        "tags": {str(n): tag for n, tag in enumerate(tags)},
    }


Match = Callable[[dict], bool]


def put_shortcut(values: dict, new: dict, ours: Match) -> dict:
    """The file's contents with *new* added, or replacing the shortcut *ours* recognizes (its play time kept); the
    other shortcuts stay, numbered 0, 1, ... in their order. When *ours* recognizes several (the same game in Steam
    more than once; owner, 20-11-2026), the first is replaced and the others go, the latest play time kept."""
    shortcuts, placed = [], False
    played = max((int(field(item, "LastPlayTime", 0) or 0) for item in values.get("shortcuts", {}).values()
                  if ours(item)), default=0)
    for item in values.get("shortcuts", {}).values():
        if not ours(item):
            shortcuts.append(item)
        elif not placed:
            shortcuts.append({**new, "LastPlayTime": played})
            placed = True
    if not placed:
        shortcuts.append(new)
    return {**values, "shortcuts": {str(n): item for n, item in enumerate(shortcuts)}}


def remove_shortcut(values: dict, ours: Match) -> dict:
    shortcuts = [item for item in values.get("shortcuts", {}).values() if not ours(item)]
    return {**values, "shortcuts": {str(n): item for n, item in enumerate(shortcuts)}}


def doubles(steam: Path, key: Callable[[dict], str]) -> dict[str, int]:
    """What is in Steam more than once (owner, 20-11-2026: "multiple entries for the same game"): per *key* (what a
    shortcut starts; "" for a shortcut that is not the caller's), how many shortcuts one Steam user has too many.
    Empty when every game is there once."""
    extra: dict[str, int] = {}
    for config in user_folders(steam):
        path = config / "shortcuts.vdf"
        try:
            values = read_vdf(path.read_bytes()) if path.is_file() else {}
        except (OSError, ShortcutError):
            continue
        counts: dict[str, int] = {}
        for item in values.get("shortcuts", {}).values():
            name = key(item)
            if name:
                counts[name] = counts.get(name, 0) + 1
        for name, count in counts.items():
            if count > 1:
                extra[name] = max(extra.get(name, 0), count - 1)
    return extra


def shortcuts(steam: Path) -> list[dict]:
    """Every Steam user's non-Steam games; a file that cannot be read is left out."""
    found = []
    for config in user_folders(steam):
        path = config / "shortcuts.vdf"
        try:
            values = read_vdf(path.read_bytes()) if path.is_file() else {}
        except (OSError, ShortcutError):
            continue
        found += values.get("shortcuts", {}).values()
    return found


def has_shortcut(steam: Path, ours: Match) -> bool:
    return any(ours(item) for item in shortcuts(steam))


@dataclass(frozen=True)
class Change:
    """One shortcut to add (or bring up to date) or, with *remove*, to take out. *ours* recognizes the one made
    before, whatever its name now; *art* holds the images by their suffix in ART, as PNG bytes."""
    entry: dict
    ours: Match
    art: dict[str, bytes] = field(default_factory=dict)
    remove: bool = False

    @property
    def number(self) -> int:
        return self.entry["appid"] & 0xFFFFFFFF


def field(item: dict, name: str, default="") -> object:
    """A shortcut's field by name, whatever its case in the file: Steam has written AppName as appname and Exe as exe
    in some versions (29-10-2026), and keeps a shortcut's fields as it found them."""
    if name in item:
        return item[name]
    wanted = name.lower()
    return next((value for key, value in item.items() if key.lower() == wanted), default)


def _number(item: dict) -> int:
    """The number a shortcut's artwork is filed under: from its program and name, as appid() gives it."""
    return appid(str(field(item, "Exe")), str(field(item, "AppName")))


def shortcut_number(steam: Path, ours: Match) -> int | None:
    """The appid of the shortcut *ours* recognizes, as Steam's file has it for the first user with one (its 32
    bits, for play_url()); from its program and name when the file names none. None when no user has the shortcut."""
    for item in shortcuts(steam):
        if ours(item):
            number = field(item, "appid", None)
            return (number if isinstance(number, int) else _number(item)) & 0xFFFFFFFF
    return None


def write_shortcuts(steam: Path, changes: Sequence[Change]) -> list[int]:
    """For every Steam user: the shortcuts in shortcuts.vdf and their artwork in grid/, each file written once.
    A shortcut renamed gets a new number, so the artwork under its old one goes. Steam must be closed. Returns the
    shortcuts' appids."""
    folders = user_folders(steam)
    if not folders:
        raise ShortcutError("Steam has no users on this system yet.")
    numbers = {change.number for change in changes if not change.remove}
    for config in folders:
        path = config / "shortcuts.vdf"
        values = read_vdf(path.read_bytes()) if path.is_file() else {}
        # The numbers of the shortcuts each change finds: a renamed one's, and one taken out that another program
        # started (a game manager's play mode, 30-10-2026), so the artwork under its number goes too
        renamed = set()
        for change in changes:
            renamed |= {_number(item) for item in values.get("shortcuts", {}).values() if change.ours(item)}
            values = remove_shortcut(values, change.ours) if change.remove else put_shortcut(values, change.entry,
                                                                                            change.ours)
        write_atomic(path, write_vdf(values))
        grid = config / "grid"
        for number in renamed - numbers:
            for suffix in ART:
                (grid / f"{number}{suffix}.png").unlink(missing_ok=True)
        for change in changes:
            for suffix in ART:
                image = grid / f"{change.number}{suffix}.png"
                if change.remove:
                    image.unlink(missing_ok=True)
                elif suffix in change.art:
                    grid.mkdir(exist_ok=True)
                    write_atomic(image, change.art[suffix])
    return [change.number for change in changes]
