# SPDX-License-Identifier: GPL-3.0-or-later
"""What the quickfixes read, as your own user: the files and the kernel's own reports. Every reader takes its roots
(/boot, /etc, /proc, /sys, /var, the home folder) so the tests give it a folder of their own."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import system

ROOT = Path("/")


# ------------------------------------------------------------------------------------------------- Quickfix
@dataclass(frozen=True)
class Tool:
    command: str                # what the tests look for on PATH
    package: str                # what the installer installs
    used_by: str                # the tests that use it


@dataclass(frozen=True)
class Group:
    option: str                 # install-requirements.sh's option for it
    name: str
    what: str                   # how it is installed, in a few words
    tools: tuple[Tool, ...]


# The groups of Board Test's development/tools/install-requirements.sh, in its order (tests/test_catalog.py reads the
# script and keeps the two the same).
GROUPS: tuple[Group, ...] = (
    Group("--rpms", "RPM packages", "Layered with rpm-ostree: active after a reboot.", (
        Tool("stress-ng", "stress-ng", "41 (CPU load), 42 (CPU score), 49 (memory bandwidth)"),
        Tool("sensors", "lm_sensors", "22 (temperatures and fans)"),
        Tool("vkmark", "vkmark", "41 (GPU load, when memtest_vulkan and vkpeak are missing)"),
        Tool("nvme", "nvme-cli", "10 (SMART health)"),
        Tool("fio", "fio", "43 (random 4K read)"),
    )),
    Group("--bins", "Binaries", "The latest releases from their GitHub projects, into ~/.local/bin.", (
        Tool("memtest_vulkan", "memtest_vulkan", "41 (GPU load and a VRAM error check)"),
        Tool("vkpeak", "vkpeak", "42 (GPU score), 41 (GPU load, when memtest_vulkan is missing)"),
    )),
    Group("--speedtest", "Speed test", "Ookla's CLI, into ~/.local/bin; running it accepts Ookla's license and "
          "privacy terms.", (
        Tool("speedtest", "Ookla speedtest", "44 (Internet Speed; speedtest-cli works too)"),
    )),
    Group("--dev", "Development extras", "Layered with rpm-ostree: active after a reboot.", (
        Tool("sqlite3", "sqlite", "no test: the app's history database, during development"),
    )),
)
# Already on Bazzite: what the tests use besides.
BUILT_IN = (Tool("glmark2", "glmark2", "41 (GPU load, last resort)"),
            Tool("vulkaninfo", "vulkan-tools", "20, 21 (Vulkan, compute units)"),
            Tool("smartctl", "smartmontools", "10 (SMART health)"))
INSTALLER = "development/tools/install-requirements.sh"             # in Board Test's folder
BOARD_TEST = Path("/opt/ps5-board-test")
BREW_BIN = Path("/home/linuxbrew/.linuxbrew/bin")                  # Homebrew on Bazzite


def find_tool(command: str, home: Path | None = None, path: str | None = None) -> str:
    """Where the tests would find *command*: PATH, then ~/.local/bin and Homebrew (test-board.sh's find_tool);
    "" when it is not there."""
    found = shutil.which(command, path=path if path is not None else os.environ.get("PATH", ""))
    if found:
        return found
    home = home or Path.home()
    for folder in (home / ".local" / "bin", BREW_BIN):
        candidate = folder / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def installer(board_test: Path = BOARD_TEST, checkout: Path | None = None) -> Path | None:
    """Board Test's install-requirements.sh: the installed one, else the checkout's (apps/board beside this app)."""
    checkout = checkout or Path(__file__).resolve().parents[2] / "board"
    for folder in (board_test, checkout):
        script = folder / INSTALLER
        if script.is_file():
            return script
    return None


# --------------------------------------------------------------------------------------------- MangoHud Config
MANGOHUD_CONF = ".config/MangoHud/MangoHud.conf"                # in the home folder
LOG_FOLDER = "mangohud-logs"                                    # in the home folder
LOG_INTERVAL = 500


def mangohud_conf(home: Path | None = None) -> Path:
    return (home or Path.home()) / MANGOHUD_CONF


def conf_values(text: str) -> dict[str, str]:
    """MangoHud's key=value lines (a bare key is "1"); comments and blank lines left out; the last one counts."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip() if _ else "1"
    return values


def with_logging(text: str, folder: Path) -> str:
    """*text* with MangoHud's log turned on: output_folder, autostart_log and log_interval set (a line that sets one
    is replaced where it is, the others are added at the end); every other line stays."""
    want = {"output_folder": str(folder), "autostart_log": "1", "log_interval": str(LOG_INTERVAL)}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        key = line.split("#", 1)[0].partition("=")[0].strip()
        if key in want:
            lines[i] = f"{key}={want.pop(key)}"
    if want:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# FPS log, read by PS5 Board Test (written by PS5 Quickfix)")
        lines += [f"{key}={value}" for key, value in want.items()]
    return "\n".join(lines) + "\n"


def logging_on(values: dict[str, str]) -> bool:
    return bool(values.get("output_folder")) and values.get("autostart_log", "0") not in ("", "0")


def log_files(folder: Path) -> list[Path]:
    try:
        return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == ".csv")
    except OSError:
        return []


# --------------------------------------------------------------------------------------------- Game Memory Map
@dataclass(frozen=True)
class MapCount:
    value: int                  # vm.max_map_count now; 0 when it cannot be read
    ours: bool                  # our sysctl.d file is there


def mapcount(root: Path = ROOT) -> MapCount:
    try:
        value = int((root / "proc" / "sys" / "vm" / "max_map_count").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        value = 0
    return MapCount(value, (root / "etc" / system.MAPCOUNT_CONF).is_file())


# ------------------------------------------------------------------------------------------ Persistent Journal
@dataclass(frozen=True)
class Journal:
    persistent: bool            # /var/log/journal is there: journald keeps the journal on the disk
    ours: bool                  # the quickfix made it


def journal(root: Path = ROOT) -> Journal:
    folder = root / "var" / system.JOURNAL_DIR
    return Journal(folder.is_dir(), (folder / system.JOURNAL_MARK).is_file())


# ------------------------------------------------------------------------------------------- Boot Command Line
@dataclass(frozen=True)
class Cmdline:
    path: Path                  # /boot/efi/cmdline.txt, or one of the fallback lines beside it
    text: str | None            # its text; "" when it is not there, None when your user may not read it
    backups: int                # the quickfix's dated backups beside it

    @property
    def exists(self) -> bool:
        return self.text is None or self.path.is_file()


def cmdline_files(root: Path = ROOT) -> list[str]:
    """The command lines on the loader's partition: cmdline.txt always, the fallback lines when they are there."""
    folder = root / "boot" / system.CMDLINE_DIR
    names = [system.CMDLINES[0]]
    for name in system.CMDLINES[1:]:
        try:
            if (folder / name).is_file():
                names.append(name)
        except OSError:                 # a folder your user may not read: the Read button shows cmdline.txt
            pass
    return names


def cmdline(root: Path = ROOT, name: str = system.CMDLINES[0]) -> Cmdline:
    path = root / "boot" / system.CMDLINE_DIR / name
    try:
        text: str | None = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        text = ""
    except OSError:
        text = None
    try:
        backups = sum(1 for _ in path.parent.glob(f"{path.name}.bak-*"))
    except OSError:
        backups = 0
    return Cmdline(path, text, backups)
