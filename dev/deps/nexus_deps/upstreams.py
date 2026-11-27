# SPDX-License-Identifier: GPL-3.0-or-later
"""The firmware the suite's apps work with, and its updates (owner, 09-11-2026: "we also check [...] for PlayStation
firmware updates"). catalogs/upstreams.json lists it, kept in sync with the apps (owner, 09-11-2026: a separate JSON
file, kept in sync): the names and launchers of the apps that use it are read from their portal's apps.toml by
sync() (`dev/deps/run.sh --sync-upstreams`); tests/test_upstreams.py fails while the file is stale.

No emulator is listed (owner, 28-11-2026): each emulator app fetches the versions from GitHub and installs the one
chosen there, which is the only way to choose one.

* Sony publishes a version list for some firmware (the DualSense controllers, the PS4), compared with what was seen
  before, so a new version is news once.
* Other firmware has no list a program can read (the PS5, the PlayStation Portal), and its card says how to check
  on the device.

Every card is "by hand": its about (the card's "i") says what the update does and how to handle it."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
import urllib.request
from collections.abc import Callable
from html import escape
from pathlib import Path

from . import CATALOGS, CHECKOUT
from .system import Source, Update

CATALOG = CATALOGS / "upstreams.json"
TIMEOUT = 15
USER_AGENT = "nexus-deps"
Get = Callable[[str], bytes]             # a URL -> its body


class UpstreamError(Exception):
    pass


# --- The catalog and its sync with the apps -------------------------------------------------------------------

def load(path: Path = CATALOG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _portal_app(checkout: Path, app: str) -> dict:
    path = checkout / "portal" / "apps.toml"
    entry = tomllib.loads(path.read_text(encoding="utf-8")).get("apps", {}).get(app)
    if entry is None:
        raise UpstreamError(f"{app} is not in {path.relative_to(checkout)}")
    return entry


def sync(data: dict, checkout: Path = CHECKOUT) -> dict:
    """The catalog with each app's name and launcher read from the portal's apps.toml again; the rest as it is."""
    data = json.loads(json.dumps(data))
    for entry in data.get("sony", []):
        for app in entry.get("apps", []):
            portal = _portal_app(checkout, app["app"])
            app["name"] = portal["name"]
            app["launcher"] = (portal.get("detect") or [""])[0]
    return data


def write(path: Path = CATALOG, checkout: Path = CHECKOUT) -> bool:
    """Write the synced catalog; True when it changed."""
    old = path.read_text(encoding="utf-8")
    new = dump(sync(load(path), checkout))
    if new != old:
        path.write_text(new, encoding="utf-8")
    return new != old


def dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# --- Asking ---------------------------------------------------------------------------------------------------

def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read(4 * 1024 * 1024)


def parse_controllers(text: bytes, targets: dict[str, str]) -> dict[str, str]:
    """Sony's info.json: {"FwUpdate0044LatestVersion": "0x0217", ...} -> {"DualSense Edge (0x0044)": "0x0217"}."""
    data = json.loads(text)
    found = {}
    for target, label in targets.items():
        version = data.get(f"FwUpdate{int(target, 16):04X}LatestVersion")
        if version:
            found[f"{label} ({target})"] = str(version)
    return found


PS4_LABEL = re.compile(rb'<system_pup\b[^>]*?\blabel="(\d{1,2}\.\d{2})"')


def parse_ps4(text: bytes) -> dict[str, str]:
    """Sony's PS4 update list: the system_pup's label ("14.02"). Sony serves it over plain HTTP (its HTTPS has a
    chain of its own): no XML parser reads it, only this one attribute in its one shape, and it is only shown."""
    found = PS4_LABEL.search(text)
    if found is None:
        raise ValueError("no system software version in the list")
    return {"PS4": found.group(1).decode()}


def check_sony(entry: dict, seen: dict[str, str] | None, get: Get = _get) -> Source:
    """Sony's latest versions, compared with *seen* (what was known at the last look): a version that changed is an
    update, once. No *seen* yet: this look is the first, nothing is new."""
    name, key = entry["name"], f"upstream-{entry['id']}"
    users = ", ".join(dict.fromkeys(app.get("name", app["app"]) for app in entry.get("apps", []))) or "the device"
    about = f"<p>{escape(entry['what'][0].upper() + entry['what'][1:])}.</p><p>{escape(entry['how'].format(apps=users))}</p>"
    if entry["kind"] == "on-device":
        return Source(key, name, group="apps", checked=False, about=about,
                      detail="Checked on the device itself: the i says where.")
    try:
        body = get(entry["url"])
        found = (parse_controllers(body, entry["targets"]) if entry["kind"] == "controllers" else parse_ps4(body))
    except (OSError, ValueError) as exc:
        return Source(key, name, error=f"Sony's list could not be read: {exc}", group="apps", about=about)
    seen = seen or {}
    updates = tuple(Update(label, seen[label], version) for label, version in found.items()
                    if label in seen and seen[label] != version)
    note = (f"New from Sony: {', '.join(f'{update.name} {update.latest}' for update in updates)}. "
            + entry["how"].format(apps=users)) if updates else ""
    detail = "Latest: " + ", ".join(f"{label} {version}" for label, version in found.items()) + "."
    return Source(key, name, updates, note=note, group="apps", detail=detail, about=about,
                  known=tuple(found.items()))


# --- Every upstream, and what was seen ------------------------------------------------------------------------

def state_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / "nexus-deps" / "upstreams.json"


def read_state(path: Path | None = None) -> dict:
    try:
        data = json.loads((path or state_path()).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(data: dict, path: Path | None = None) -> None:
    path = path or state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass                            # nothing remembered: the next look says it again


def read(section: str = "seen", catalog: dict | None = None, get: Get = _get,
         state: Path | None = None) -> tuple[Source, ...]:
    """Every firmware's card. Sony's versions are compared with *section* of the state ("seen": the window,
    "notified": the reminder), which then holds the versions just read."""
    catalog = catalog or load()
    remembered = read_state(state)
    known = remembered.setdefault(section, {})
    sources = []
    for entry in catalog.get("sony", []):
        source = check_sony(entry, known.get(entry["id"]), get)
        sources.append(source)
        if source.known:
            known[entry["id"]] = dict(source.known)
    write_state(remembered, state)
    return tuple(sources)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nexus_deps.upstreams", description="catalogs/upstreams.json, in sync with "
                                     "the portal's apps.toml")
    parser.add_argument("--write", action="store_true", help="write the synced catalog")
    args = parser.parse_args(argv)
    if args.write:
        print("upstreams.json " + ("updated" if write() else "was in sync"))
        return 0
    stale = dump(sync(load())) != CATALOG.read_text(encoding="utf-8")
    print("upstreams.json is stale: run dev/deps/run.sh --sync-upstreams" if stale else "upstreams.json in sync")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
