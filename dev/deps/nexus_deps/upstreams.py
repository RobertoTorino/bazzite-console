# SPDX-License-Identifier: GPL-3.0-or-later
"""The firmware the suite's apps work with, and its updates (owner, 09-11-2026: "we also check [...] for PlayStation
firmware updates"). catalogs/upstreams.json lists it, kept in sync with the apps (owner, 09-11-2026: a separate JSON
file, kept in sync): the names and launchers of the apps that use it are read from their portal's apps.toml by
sync() (`dev/deps/run.sh --sync-upstreams`); tests/test_upstreams.py fails while the file is stale.

The emulators are listed again (owner, 28-11-2026, the afternoon: "build the Emulators section"). Each emulator app
pins the build it was tested with on a board. Its card compares that pin with GitHub's latest release. A newer one
comes with a release of the app, after a test on a board, and is never installed from here. The pins and repositories
are read from each app's emulator.py by sync(), without importing the app.

* Sony publishes a version list for some firmware (the DualSense controllers, the PS4), compared with what was seen
  before, so a new version is news once.
* Sony's system software pages give the newest version of the PS5 and the PlayStation Portal (owner, 28-11-2026),
  read from the page's text and news once in the same way.

Each card's "i" links to Sony's pages for it: the system software pages and the steps to update a controller.

Every card is "by hand": its about (the card's "i") says what the update does and how to handle it."""

from __future__ import annotations

import argparse
import ast
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.error
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
Fetch = Callable[[str], object]          # a GitHub API URL -> its decoded JSON
SYNCED = ("repo", "pin", "version", "name", "launcher")


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


def _value(node: ast.AST, names: dict[str, object]) -> object:
    """A module constant's value: a literal, a name defined above it, an f-string of those, or str() of one."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if isinstance(node, ast.JoinedStr):
        parts = []
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                if part.format_spec is not None:
                    raise ValueError("a format spec")
                parts.append(str(_value(part.value, names)))
            else:
                parts.append(str(_value(part, names)))
        return "".join(parts)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str"
            and len(node.args) == 1 and not node.keywords):
        return str(_value(node.args[0], names))
    raise ValueError(f"not a constant: {ast.dump(node)[:60]}")


def constants(path: Path) -> dict[str, object]:
    """The module-level constants of a Python file, read without running it."""
    names: dict[str, object] = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            target, value = node.target.id, node.value
        else:
            continue
        try:
            names[target] = _value(value, names)
        except ValueError:
            pass
    return names


def emulator_apps(checkout: Path = CHECKOUT) -> set[str]:
    """Every app of the suite with a pinned emulator: an emulator.py with REPO and VERSION."""
    return {module.parents[1].name for module in (checkout / "apps").glob("*/*/emulator.py")
            if {"REPO", "VERSION"} <= constants(module).keys()}


def sync(data: dict, checkout: Path = CHECKOUT) -> dict:
    """The catalog with each app's name and launcher read from the portal's apps.toml again, and each emulator's
    repository and pins from its app's emulator.py; the hand-written rest as it is."""
    data = json.loads(json.dumps(data))
    for entry in [*data.get("github", []), *data.get("sony", [])]:
        for app in entry.get("apps", []):
            portal = _portal_app(checkout, app["app"])
            app["name"] = portal["name"]
            app["launcher"] = (portal.get("detect") or [""])[0]
            if "module" not in app:
                continue
            module = checkout / "apps" / app["app"] / app["module"]
            if not module.is_file():
                raise UpstreamError(f"{module.relative_to(checkout)} is missing")
            values = constants(module)
            for field, constant in app["constants"].items():
                if constant not in values:
                    raise UpstreamError(f"{module.relative_to(checkout)} has no constant {constant}")
                app[field] = str(values[constant])
            for field in SYNCED:                    # the synced fields after the hand-written ones, in one order
                if field in app:
                    app[field] = app.pop(field)
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


GH_FALLBACK = "/home/linuxbrew/.linuxbrew/bin/gh"       # Homebrew's gh, which a launcher's PATH lacks
_token: str | None = None                               # found once per run; "" when there is none


def github_token(run=subprocess.run) -> str:
    """GITHUB_TOKEN or GH_TOKEN, else the token of a gh login (gh auth token); "" without one. With a token GitHub
    allows 5,000 requests an hour instead of 60 for the whole address. It is only sent to GitHub's API and never
    stored here."""
    global _token
    if _token is None:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        gh = shutil.which("gh") or (GH_FALLBACK if os.access(GH_FALLBACK, os.X_OK) else "")
        if not token and gh:
            try:
                out = run([gh, "auth", "token"], capture_output=True, text=True, timeout=10)
                token = out.stdout.strip() if out.returncode == 0 else ""
            except (OSError, subprocess.SubprocessError):
                token = ""
        _token = token
    return _token


def _fetch(url: str, opener=urllib.request.urlopen) -> object:
    """GitHub's answer to an API request, signed in when the machine is (github_token). A refused token (401) is
    asked again without it; the hourly limit says until when and how to get the larger one."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = github_token() if url.startswith("https://api.github.com/") else ""
    for signed in ([True, False] if token else [False]):
        if signed:
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers.pop("Authorization", None)
        try:
            with opener(urllib.request.Request(url, headers=headers), timeout=TIMEOUT) as response:
                return json.loads(response.read(4 * 1024 * 1024))
        except urllib.error.HTTPError as exc:
            if signed and exc.code == 401:
                continue
            if exc.code in (403, 429) and exc.headers.get("x-ratelimit-remaining") == "0":
                try:
                    until = time.strftime(" until %H:%M", time.localtime(int(exc.headers.get("x-ratelimit-reset"))))
                except (TypeError, ValueError):
                    until = ""
                raise OSError(f"its hourly limit is used up{until}" + ("" if signed else
                              ". Signed in with gh (gh auth login) it is 5,000 requests an hour instead of 60")
                              ) from None
            raise
    raise OSError("no answer")              # not reached: the unsigned request returns or raises


def numbers(version: str) -> tuple[int, ...]:
    """"v.0.21.0" -> (0, 21, 0), "0.0.43" -> (0, 0, 43); trailing zeros dropped for comparing."""
    values = [int(found) for found in re.findall(r"\d+", version)]
    while values and values[-1] == 0:
        values.pop()
    return tuple(values)


def newer(compare: str, latest: dict, pin: str) -> bool:
    """Whether GitHub's latest release (tag_name, published_at) is newer than the app's pin: by build number, by
    the day or moment it was published (ISO 8601 in UTC, compared as text to the pin's length), or by version."""
    tag = str(latest.get("tag_name", "")).strip()
    if compare == "build":
        return tag.isdigit() and pin.isdigit() and int(tag) > int(pin)
    if compare == "published":
        return str(latest.get("published_at", ""))[:len(pin)] > pin
    return bool(numbers(tag)) and numbers(tag) > numbers(pin)


def check_github(entry: dict, fetch: Fetch = _fetch) -> Source:
    """An emulator's card: the build its app was tested with, and GitHub's latest release."""
    name, key, app = entry["name"], f"upstream-{entry['id']}", entry["apps"][0]
    kind = "Latest stable on GitHub" if entry["stable"] else "Latest build on GitHub (no stable releases)"
    try:
        latest = fetch(f"https://api.github.com/repos/{app['repo']}/releases/latest")
        if not isinstance(latest, dict) or not latest.get("tag_name"):
            raise ValueError("not a release")
    except (OSError, ValueError) as exc:
        return Source(key, name, error=f"GitHub could not be asked: {exc}", group="emulators",
                      about=_github_about(entry, {}))
    tag = str(latest["tag_name"])
    updates, note = (), ""
    if newer(entry["compare"], latest, app["pin"]):
        updates = (Update(f"{name} on GitHub", app["version"], tag),)
        note = f"A newer build is out. It comes with a release of {app['name']}, after a test on a board."
    return Source(key, name, updates, note=note, group="emulators", about=_github_about(entry, latest),
                  detail=f"Tested build in {app['name']}: {app['version']}. {kind}: {tag}.")


def _github_about(entry: dict, latest: dict) -> str:
    app = entry["apps"][0]
    page = str(latest.get("html_url") or f"https://github.com/{app['repo']}/releases")
    return (f"<p>{escape(entry['what'][0].upper() + entry['what'][1:])}.</p>"
            f"<p>{escape(app['name'])} installs the build it was tested with on a board: {escape(app['version'])}. "
            f"A newer build comes with a release of the app, after a test on a board. Nothing is installed from "
            f"here.</p><p><a href=\"{escape(page)}\">The release on GitHub</a></p>")


def parse_controllers(text: bytes, targets: dict[str, str]) -> dict[str, str]:
    """Sony's info.json: {"FwUpdate0044LatestVersion": "0x0217", ...} -> {"DualSense Edge (0x0044)": "0x0217"}."""
    data = json.loads(text)
    found = {}
    for target, label in targets.items():
        version = data.get(f"FwUpdate{int(target, 16):04X}LatestVersion")
        if version:
            found[f"{label} ({target})"] = str(version)
    return found


PAGE_VERSION = re.compile(r"\bVersion:?\s+(\d{1,2}\.\d{1,2}(?:\.\d{1,3})?)\b")
PS4_LABEL = re.compile(rb'<system_pup\b[^>]*?\blabel="(\d{1,2}\.\d{2})"')


def parse_ps4(text: bytes) -> dict[str, str]:
    """Sony's PS4 update list: the system_pup's label ("14.02"). Sony serves it over plain HTTP (its HTTPS has a
    chain of its own): no XML parser reads it, only this one attribute in its one shape, and it is only shown."""
    found = PS4_LABEL.search(text)
    if found is None:
        raise ValueError("no system software version in the list")
    return {"PS4": found.group(1).decode()}


def parse_page(text: bytes, label: str) -> dict[str, str]:
    """Sony's system software page: the first "Version: 26.07" (or "Version 7.3.2") of the text a person reads, the
    newest, as the page lists the versions newest first. Scripts, styles and tags are left out, and so are the site's
    own version numbers in them. Only shown, like the PS4's."""
    page = re.sub(rb"<(script|style)\b.*?</\1\s*>", b" ", text, flags=re.S | re.I)
    words = html.unescape(re.sub(rb"<[^>]*>", b" ", page).decode("utf-8", "replace"))
    found = PAGE_VERSION.search(words)
    if found is None:
        raise ValueError("no system software version on the page")
    return {label: found.group(1)}


def _pages(entry: dict) -> str:
    """The entry's pages at Sony, as links in its i."""
    return "".join(f'<p><a href="{escape(page["url"])}">{escape(page["text"])}</a></p>'
                   for page in entry.get("pages", []))


def check_sony(entry: dict, seen: dict[str, str] | None, get: Get = _get) -> Source:
    """Sony's latest versions, compared with *seen* (what was known at the last look): a version that changed is an
    update, once. No *seen* yet: this look is the first, nothing is new."""
    name, key = entry["name"], f"upstream-{entry['id']}"
    users = ", ".join(dict.fromkeys(app.get("name", app["app"]) for app in entry.get("apps", []))) or "the device"
    about = (f"<p>{escape(entry['what'][0].upper() + entry['what'][1:])}.</p>"
             f"<p>{escape(entry['how'].format(apps=users))}</p>" + _pages(entry))
    try:
        body = get(entry["url"])
        found = (parse_controllers(body, entry["targets"]) if entry["kind"] == "controllers" else
                 parse_page(body, entry["label"]) if entry["kind"] == "page" else parse_ps4(body))
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
         state: Path | None = None, fetch: Fetch = _fetch) -> tuple[Source, ...]:
    """Every card: the firmware, then the emulators. Sony's versions are compared with *section* of the state
    ("seen": the window, "notified": the reminder), which then holds the versions just read. A newer emulator build
    stays on its card until a release, and the reminder names it once."""
    catalog = catalog or load()
    remembered = read_state(state)
    known = remembered.setdefault(section, {})
    emulators = [check_github(entry, fetch) for entry in catalog.get("github", [])]
    if section == "notified":
        named = remembered.setdefault("named", {})
        emulators = [_named_once(source, named) for source in emulators]
    sources = []
    for entry in catalog.get("sony", []):
        source = check_sony(entry, known.get(entry["id"]), get)
        sources.append(source)
        if source.known:
            known[entry["id"]] = dict(source.known)
    write_state(remembered, state)
    return (*sources, *emulators)


def _named_once(source: Source, named: dict) -> Source:
    """The card without the newer builds the reminder named before; remembers what it names now."""
    if source.error:
        return source
    before = set(named.get(source.key, []))
    fresh = tuple(update for update in source.updates if update.latest not in before)
    named[source.key] = sorted(before | {update.latest for update in source.updates})
    return Source(source.key, source.name, fresh, note=source.note if fresh else "", group=source.group,
                  detail=source.detail, about=source.about)


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
