# SPDX-License-Identifier: GPL-3.0-or-later
"""What the dashboard finds in the checkout: the suite (the repository itself: its name, as its portal calls itself),
and the development apps in dev/ with their names, icons and run.sh. An app starts in its own session, so it keeps
running when the dashboard closes; its output goes to a log in the cache folder."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import APP_ID, CHECKOUT

LOG_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / APP_ID / "apps"
_CONSTANT = re.compile(r'^(APP_NAME|APP_ID)\s*=\s*"([^"]+)"', re.M)


def suite_name(root: Path = CHECKOUT) -> str:
    """The suite's name, as its portal calls itself (APP_NAME in portal/<package>/__init__.py); the folder's name
    without one."""
    for init in sorted((root / "portal").glob("*/__init__.py")):
        consts = dict(_CONSTANT.findall(init.read_text(encoding="utf-8")))
        if "APP_NAME" in consts:
            return consts["APP_NAME"]
    return root.name


@dataclass(frozen=True)
class DevApp:
    """One development app of dev/, started with its run.sh."""

    folder: Path                        # dev/<name>/
    app_id: str
    name: str
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
    """Every development app in dev/ but this one, in the order of the dashboard: the release tool first, then the
    rest by name. An app is a folder with a package with APP_NAME."""
    found = []
    for folder in sorted(p for p in (root / "dev").iterdir() if p.is_dir()):
        for init in sorted(folder.glob("*/__init__.py")):
            consts = dict(_CONSTANT.findall(init.read_text(encoding="utf-8")))
            if "APP_NAME" not in consts or consts.get("APP_ID") == me:
                continue
            icon = folder / "images" / f"{consts.get('APP_ID', '')}.webp"
            found.append(DevApp(folder, consts.get("APP_ID", folder.name), consts["APP_NAME"],
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
