# SPDX-License-Identifier: GPL-3.0-or-later
"""What the dashboard finds in the checkout: the suites (tools/suites.py, as every Nexus tool reads them), and the
Nexus apps in dev/ with their names, icons and start scripts (run.sh). An app starts in its own
session, so it keeps running when the dashboard closes; its output goes to a log in the cache folder."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import APP_ID, CHECKOUT

LOG_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / APP_ID / "apps"
_CONSTANT = re.compile(r'^(APP_NAME|APP_ID)\s*=\s*"([^"]+)"', re.M)


def _suites_module(root: Path = CHECKOUT):
    spec = importlib.util.spec_from_file_location("nexus_suites", root / "tools" / "suites.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def suites(root: Path = CHECKOUT) -> list[str]:
    """The suites of the checkout, their folder names, sorted."""
    try:
        found = [p for p in _suites_module(root).suites(root) if p != root]
        return [p.name for p in found] if found else ([root.name] if (root / "portal" / "apps.toml").is_file() else [])
    except (OSError, AttributeError):
        return []


def suite_system(root: Path, suite: str) -> str:
    """The system the suite is made for (its SYSTEM file: bazzite), "" without one."""
    try:
        folder = root if suite in {root.name, "."} else root / suite
        return (folder / "SYSTEM").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def suite_name(root: Path, suite: str) -> str:
    """The suite's name, as its portal calls itself (APP_NAME in portal/<package>/__init__.py); the folder's name
    without one."""
    folder = root if suite in {root.name, "."} else root / suite
    for init in sorted((folder / "portal").glob("*/__init__.py")):
        consts = dict(_CONSTANT.findall(init.read_text(encoding="utf-8")))
        if "APP_NAME" in consts:
            return consts["APP_NAME"]
    return suite


@dataclass(frozen=True)
class DevApp:
    """One Nexus app of dev/, started with its run script."""

    folder: Path                        # dev/<name>/
    app_id: str
    name: str
    version: str
    icon: Path | None

    @property
    def key(self) -> str:
        return self.folder.name

    @property
    def script(self) -> Path:
        return self.folder / "run.sh"

    @property
    def runs_here(self) -> bool:
        return self.script.is_file()

    @property
    def log(self) -> Path:
        return LOG_DIR / f"{self.key}.log"


def dev_apps(root: Path = CHECKOUT, me: str = APP_ID) -> list[DevApp]:
    """Every Nexus app in dev/ but this one, in the order of the dashboard: the release tool first, then the
    rest by name. An app is a folder with VERSION and a package with APP_NAME."""
    found = []
    for folder in sorted(p for p in (root / "dev").iterdir() if p.is_dir() and (p / "VERSION").is_file()):
        for init in sorted(folder.glob("*/__init__.py")):
            consts = dict(_CONSTANT.findall(init.read_text(encoding="utf-8")))
            if "APP_NAME" not in consts or consts.get("APP_ID") == me:
                continue
            icon = folder / "images" / f"{consts.get('APP_ID', '')}.webp"
            found.append(DevApp(folder, consts.get("APP_ID", folder.name), consts["APP_NAME"],
                                (folder / "VERSION").read_text(encoding="utf-8").strip(),
                                icon if icon.is_file() else None))
            break
    return sorted(found, key=lambda app: (app.key != "nrt", app.name))


def start(app: DevApp, args: tuple[str, ...] = ()) -> subprocess.Popen:
    """Starts *app* with its run script in its own session; its output goes to its log."""
    app.log.parent.mkdir(parents=True, exist_ok=True)
    command = ["bash", str(app.script), *args]
    with open(app.log, "wb") as out:
        return subprocess.Popen(command, cwd=app.folder, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, start_new_session=True)
