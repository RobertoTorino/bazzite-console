#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs the Bazzite Console Suite portal, PS5 Board Test and PS5 Quickfix, from the extracted portal release:
#
#   ./install.sh                         # install or update
#   ./install.sh --no-desktop-shortcut   # app menu entries only, no icons on the Desktop
#   ./install.sh --uninstall             # remove the portal, Board Test, Quickfix and (asked per app) the others;
#                                        # keeps settings, results and the wallpaper
#   ./install.sh --uninstall --purge     # also remove settings, history and results
#   ./install.sh --uninstall --all       # the whole suite: every other app too, without a question per app,
#                                        # after one confirmation; with --purge their settings go as well
#
# Run it as your own user, not with sudo: only Board Test's copy to /opt asks for the sudo password.
#  * ~/.local/share/bazzite-console-suite/portal: the portal, its apps.toml and the bazzite_console_core it was tested
#    with, a copy of your own that every install replaces. Installed from a checkout, it names the checkout
#    (suite-checkout) and installs the other apps from there.
#  * ~/.local/share/bazzite-console-suite/state: what the portal remembers (the apps it installed and their releases,
#    the wallpaper, the music).
#  * ~/.local/share/bazzite-console-suite/venv: the suite's shared venv with PyQt6 and pygame-ce (the portal's
#    controller reader), removed with the last suite app that uses it.
#  * ~/.local/bin/bazzite-console-suite, an app menu entry and a Desktop icon.
#  * PS5 Board Test and PS5 Quickfix, which the suite always includes, through their own installers (bundled in
#    the release).
# The other apps are installed from the portal, each with its own installer.
set -euo pipefail

APP_ID="bazzite-console-suite"
APP_NAME="Bazzite Console Suite"
OPT_DIR="${PS5_BOARD_TEST_OPT_DIR:-/opt}"            # where Board Test is installed; override only for testing
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
SUITE_DIR="$DATA_DIR/$APP_ID"
VENV="$SUITE_DIR/venv"
VENV_USERS="$SUITE_DIR/venv-users"
PORTAL_DIR="$SUITE_DIR/portal"          # the installed portal
STATE_DIR="$SUITE_DIR/state"            # what the portal remembers: the installed apps, downloads, the wallpaper
LAUNCHER="$HOME/.local/bin/$APP_ID"
MENU_ENTRY="$DATA_DIR/applications/$APP_ID.desktop"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
DESKTOP_ICON="$DESKTOP_DIR/$APP_ID.desktop"
BT_KEY="board"
BT_ID="ps5-board-test"
QUICKFIX_KEY="quickfix"
QUICKFIX_ID="ps5-quickfix"

SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# A release bundles bazzite_console_core and the pinned Board Test and Quickfix; in the suite checkout they live in
# core/ and apps/.
if [ -d "$SRC/bazzite_console_core" ]; then CORE_SRC="$SRC/bazzite_console_core"; else CORE_SRC="$SRC/../core/bazzite_console_core"; fi
bundled_app() {     # bundled_app KEY: the bundled release folder of the app, else its folder in the checkout
    local folder=""
    if [ -d "$SRC/bundled" ]; then
        folder=$(find "$SRC/bundled" -mindepth 1 -maxdepth 1 -type d -name "ps5-$1-v*" | sort -V | tail -1)
    fi
    echo "${folder:-$SRC/../apps/$1}"
}
BT_SRC=$(bundled_app "$BT_KEY")
QUICKFIX_SRC=$(bundled_app "$QUICKFIX_KEY")
release_tag() {     # release_tag FOLDER: its tag, or "local" for a folder of the checkout
    case "$1" in "$SRC/bundled/"*) basename "$1" ;; *) echo local ;; esac
}
BT_TAG=$(release_tag "$BT_SRC")
QUICKFIX_TAG=$(release_tag "$QUICKFIX_SRC")

info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }
die()  { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

usage() { sed -n '3,11p' "$0" | sed 's/^# \{0,1\}//'; }

DESKTOP_SHORTCUT=true
UNINSTALL=false
PURGE=false
ALL=false
for arg in "$@"; do
    case "$arg" in
        --no-desktop-shortcut) DESKTOP_SHORTCUT=false ;;
        --uninstall) UNINSTALL=true ;;
        --purge) PURGE=true ;;
        --all) ALL=true ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "Unknown option: $arg" ;;
    esac
done
$PURGE && ! $UNINSTALL && die "--purge only goes with --uninstall."
$ALL && ! $UNINSTALL && die "--all only goes with --uninstall."

[ "$(id -u)" -ne 0 ] || die "Run this as your own user, not with sudo: the portal, the venv and the launcher belong in your home folder."

remove_menu_entries() {
    rm -f "$LAUNCHER" "$MENU_ENTRY" "$DESKTOP_ICON"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$DATA_DIR/applications" || true
}

release_venv() {
    rm -f "${VENV_USERS:?}/${APP_ID:?}"
    rmdir "$VENV_USERS" 2>/dev/null || true
    if [ -d "$VENV_USERS" ]; then
        info "Keeping the suite venv: other suite apps still use it ($(ls "$VENV_USERS" | tr '\n' ' '))"
    else
        info "Removing the suite venv"
        rm -rf "${VENV:?}"
    fi
}

# Whether anything the uninstall removes is on this computer (paths and globs): without, it removes nothing, asks
# for no password and says the suite is not installed.
installed_here() {
    local path
    for path in "$@"; do
        compgen -G "$path" >/dev/null && return 0
    done
    return 1
}

# The other suite apps that are installed, one per line: key, name, the folder its uninstaller runs in (empty when
# there is none) and its uninstall commands, tab-separated. Read from the installed portal's apps.toml, the one
# that installed them; the folder is the release the portal kept, or the app staged afresh from the checkout. An app
# this portal no longer lists (dropped from the manifest, installed by an earlier portal) is found by the record and
# release folder the portal kept for it, else by its own installed copy (~/.local/share/<app-id>/app or
# /opt/<app-id>, an install.sh of this suite), and uninstalled with that installer.
installed_apps() {
    local manifest="$SRC/apps.toml" checkout=""
    [ -f "$PORTAL_DIR/apps.toml" ] && manifest="$PORTAL_DIR/apps.toml"
    if [ -f "$PORTAL_DIR/suite-checkout" ]; then checkout=$(cat "$PORTAL_DIR/suite-checkout")
    elif [ -f "$SRC/../tools/stage_app.py" ]; then checkout=$(cd "$SRC/.." && pwd -P); fi        # <checkout>/portal
    python3 - "$manifest" "$STATE_DIR" "$checkout" "$1" "$DATA_DIR" "$OPT_DIR" "$APP_ID" "$BT_ID" "$QUICKFIX_ID" <<'PY'
import json, os, re, subprocess, sys, tomllib
from pathlib import Path
manifest, state, checkout, staging = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
data_dir, opt_dir, own_ids = Path(sys.argv[5]), Path(sys.argv[6]), set(sys.argv[7:10])   # the portal, the required
tables = tomllib.loads(manifest.read_text(encoding="utf-8"))
apps = tables.get("apps", {})
suite = Path(checkout) if checkout else None                       # the suite: the checkout itself
try:
    records = json.loads((state / "installed.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    records = {}
records = records if isinstance(records, dict) else {}


def present(paths):
    return any(Path(os.path.expandvars(os.path.expanduser(p))).exists() for p in paths)


def installer_value(folder, name):
    """APP_ID or APP_NAME as the install.sh in *folder* sets it; "" when it does not."""
    try:
        text = (folder / "install.sh").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    found = re.search(rf'^{name}="([^"]*)"', text, re.M)
    return found[1] if found else ""


def row(key, name, folder, commands):
    print("\t".join((key, name, str(folder) if folder else "", commands)))


def suite_installer(folder):
    """Whether *folder* holds an install.sh of this suite's apps: one with the options every one of them has, that
    uses the suite's venv or bundles its core (another suite's apps may sit in /opt beside them)."""
    try:
        text = (folder / "install.sh").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return ("--no-desktop-shortcut)" in text and "--uninstall)" in text and "not with sudo" in text
            and ("bazzite-console-suite" in text or "bazzite_console_core" in text))


def kept_folder(key, record):
    """The release folder the portal kept for *key*: <tag>, or local-<key> for an install from the checkout."""
    return state / "releases" / (f"local-{key}" if record.startswith("local") else record)


app_ids = set()                         # the ids of the apps this portal lists: their launchers' names
for key, app in apps.items():
    app_ids |= {Path(p).name for p in app.get("detect", [])}
    if app.get("required") or not present(app.get("detect", [])):
        continue
    kept = [kept_folder(key, name) for name in (records.get(key, ""), "local", app.get("tag", "")) if name]
    folder = next((f for f in kept if f.is_dir()), None)
    if folder is None and suite and (suite / "apps" / key).is_dir():
        dest = staging / key
        if subprocess.run([sys.executable, str(Path(checkout) / "tools" / "stage_app.py"), key, str(dest)],
                          capture_output=True).returncode == 0:
            folder = dest
    row(key, app.get("name", key), folder, " && ".join(app.get("uninstall", [])))

# Apps this portal no longer lists: first by the record and release folder kept for them ...
found_ids = set()
releases = state / "releases"
candidates = {key: tag for key, tag in records.items() if key not in apps}
if releases.is_dir():
    for path in releases.iterdir():
        match = re.match(r"^(?:ps5-)?(.+)-v\d+\.\d+\.\d+$", path.name)
        key = match[1] if match else path.name.removeprefix("local-")
        if key not in apps and key not in candidates:
            candidates[key] = "local" if path.name.startswith("local-") else path.name
for key, tag in sorted(candidates.items()):
    folder = kept_folder(key, tag)
    app_id = installer_value(folder, "APP_ID")
    if (not app_id or app_id in own_ids or app_id in app_ids or not folder.is_dir()
            or not present([str(data_dir / app_id / "app"), str(opt_dir / app_id), f"~/.local/bin/{app_id}"])):
        continue
    found_ids.add(app_id)
    row(key, installer_value(folder, "APP_NAME") or key, folder, "bash install.sh --uninstall")
# ... else by their own installed copy: the places the suite's installers copy an app to.
copies = [p / "app" for p in data_dir.iterdir() if p.is_dir()] if data_dir.is_dir() else []
copies += [p for p in opt_dir.iterdir() if p.is_dir()] if opt_dir.is_dir() else []
for folder in sorted(copies):
    app_id = installer_value(folder, "APP_ID")
    if not app_id or app_id in own_ids or app_id in app_ids or app_id in found_ids or not suite_installer(folder):
        continue
    found_ids.add(app_id)
    row(app_id, installer_value(folder, "APP_NAME") or app_id, folder, "bash install.sh --uninstall")
PY
}

# Asks about every other installed suite app before anything is removed: uninstall it, skip it, or cancel the
# whole uninstall. Without a terminal nothing is asked and the apps stay, as they are named at the end. With --all,
# one confirmation instead, then every app goes (with --purge, their settings too); it needs a terminal.
uninstall_other_apps() {
    local list key name folder commands answer names
    local -a chosen=() failed=()
    list=$(installed_apps "$STAGING/apps") || die "Could not read the list of installed apps."
    if $ALL && [ -n "$list" ]; then
        { [ -t 0 ] || [ -n "${BAZZITE_CONSOLE_INTERACTIVE:-}" ]; } || die "--all needs a terminal to confirm; nothing was uninstalled."
        names=$(cut -f2 <<<"$list" | paste -sd, - | sed 's/,/, /g')
        info "WARNING: --all removes the whole suite from this computer: $names, with the portal, Board Test and Quickfix."
        $PURGE && info "WARNING: --purge removes their settings, history and results as well."
        printf "Are you sure you want to delete everything permanently? [y/N] "
        read -r answer || answer=n
        case "${answer,,}" in
            y|yes) ;;
            *) info "Canceled: nothing was uninstalled."; exit 1 ;;
        esac
        mapfile -t chosen < <(cut -f1 <<<"$list")
    elif [ -n "$list" ] && { [ -t 0 ] || [ -n "${BAZZITE_CONSOLE_INTERACTIVE:-}" ]; }; then   # BAZZITE_CONSOLE_INTERACTIVE: tests only
        info "Other suite apps are installed. For each: y = uninstall it, s = skip it (keep it), c = cancel."
        while IFS=$'\t' read -r key name folder commands <&3; do
            while true; do
                printf "Uninstall %s? [y/s/c] " "$name"
                read -r answer || answer=c
                case "${answer,,}" in
                    y|yes) chosen+=("$key"); break ;;
                    s|skip) break ;;
                    c|cancel) info "Canceled: nothing was uninstalled."; exit 1 ;;
                esac
            done
        done 3<<<"$list"
    fi
    while IFS=$'\t' read -r key name folder commands; do
        [ -n "$key" ] && [[ " ${chosen[*]} " == *" $key "* ]] || continue
        if [ -z "$folder" ]; then
            info "No uninstaller found for $name: remove it with its own install.sh --uninstall."
            failed+=("$name")
            continue
        fi
        info "Uninstalling $name"
        # --all --purge: the apps' own --purge too (the commands that are an install.sh --uninstall take it).
        $ALL && $PURGE && commands=$(sed 's/ --uninstall\( \|$\)/ --uninstall --purge\1/g' <<<"$commands")
        if (cd "$folder" && bash -c "$commands"); then
            forget_app "$key" "$folder"
        else
            info "The uninstall of $name failed; see above."
            failed+=("$name")
        fi
    done <<<"$list"
    [ ${#failed[@]} -eq 0 ] || info "Not uninstalled: ${failed[*]}"
    if $PURGE && [ ${#chosen[@]} -gt 0 ] && ! $ALL; then
        info "Their own settings are kept: --purge applies to the portal, Board Test and Quickfix (with --all, to every app)."
    fi
}

# Like the portal after an uninstall: drop the app from installed.json and the release folder it kept.
forget_app() {
    case "$2" in "${STATE_DIR:?}"/releases/?*) rm -rf "$2" ;; esac
    [ -f "$STATE_DIR/installed.json" ] || return 0
    python3 - "$STATE_DIR/installed.json" "$1" <<'PY'
import json, sys
from pathlib import Path
path, key = Path(sys.argv[1]), sys.argv[2]
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, ValueError):
    sys.exit(0)
if isinstance(data, dict) and data.pop(key, None) is not None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
PY
}

# After the uninstall without --purge: keep only what an app that is still installed needs (its record and the
# release folder its uninstaller runs from); records and folders of apps that are gone, and the required apps', go.
# The rest of the state (the wallpaper, the music) stays; an empty state folder goes.
prune_state() {
    local manifest="$SRC/apps.toml"
    [ -f "$PORTAL_DIR/apps.toml" ] && manifest="$PORTAL_DIR/apps.toml"
    [ -d "$STATE_DIR" ] || return 0
    python3 - "$manifest" "$STATE_DIR" <<'PY'
import json, os, re, shutil, sys, tomllib
from pathlib import Path
manifest, state = Path(sys.argv[1]), Path(sys.argv[2])
apps = tomllib.loads(manifest.read_text(encoding="utf-8")).get("apps", {})
try:
    records = json.loads((state / "installed.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    records = {}
records = records if isinstance(records, dict) else {}
def installed(key):
    app = apps.get(key)
    if app is None:
        return True                     # not in this portal's list: unknown, so kept
    return not app.get("required") and any(Path(os.path.expandvars(os.path.expanduser(p))).exists()
                                           for p in app.get("detect", []))
records = {k: v for k, v in records.items() if installed(k)}
keep = {f"local-{k}" if str(v).startswith("local") else v for k, v in records.items()}
releases = state / "releases"
if releases.is_dir():
    for path in releases.iterdir():
        match = re.match(r"^(?:ps5-)?(.+)-v\d+\.\d+\.\d+$", path.name)
        key = match[1] if match else path.name.removeprefix("local-")
        if path.name not in keep and (key in apps or key not in records):
            shutil.rmtree(path, ignore_errors=True)
    if not any(releases.iterdir()):
        releases.rmdir()
if records:
    tmp = state / "installed.tmp"
    tmp.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(state / "installed.json")
else:
    (state / "installed.json").unlink(missing_ok=True)
PY
    rmdir "$STATE_DIR" 2>/dev/null || true      # nothing remembered: nothing to keep
}

if $UNINSTALL; then
    STAGING=$(mktemp -d)                              # where apps are staged for their uninstallers
    trap 'rm -rf "${STAGING:?}"' EXIT
    mkdir "$STAGING/check" "$STAGING/apps"
    # Nothing of the portal, of Board Test, of Quickfix or of another suite app: nothing to uninstall.
    found=false
    installed_here "$LAUNCHER" "$MENU_ENTRY" "$DESKTOP_ICON" "$PORTAL_DIR" "$VENV_USERS/$APP_ID" \
        "$OPT_DIR/$BT_ID" "$DATA_DIR/$QUICKFIX_ID/app" && found=true
    $PURGE && installed_here "${STATE_DIR:?}" "${CONFIG_DIR:?}/$APP_ID" && found=true
    if ! $found && [ -z "$(installed_apps "$STAGING/check" 2>/dev/null)" ]; then
        info "$APP_NAME is not installed: nothing to remove."
        exit 0
    fi
    uninstall_other_apps
    if [ -f "$OPT_DIR/$BT_ID/install.sh" ]; then
        info "Uninstalling PS5 Board Test"
        bt_args=(--uninstall)
        $PURGE && bt_args+=(--purge)
        bash "$OPT_DIR/$BT_ID/install.sh" "${bt_args[@]}"
    fi
    if [ -f "$DATA_DIR/$QUICKFIX_ID/app/install.sh" ]; then
        info "Uninstalling PS5 Quickfix"
        quickfix_args=(--uninstall)
        $PURGE && quickfix_args+=(--purge)
        bash "$DATA_DIR/$QUICKFIX_ID/app/install.sh" "${quickfix_args[@]}"
    fi
    $PURGE || prune_state
    info "Removing the portal's launcher and menu entry"
    remove_menu_entries
    info "Removing the portal from $PORTAL_DIR"
    rm -rf "${PORTAL_DIR:?}"
    release_venv
    if $PURGE; then
        info "Removing the portal's settings and state"
        rm -rf "${STATE_DIR:?}" "${CONFIG_DIR:?}/${APP_ID:?}"
    fi
    rmdir "$SUITE_DIR" 2>/dev/null || true             # nothing of the suite left in it
    others=""
    if [ -d "$VENV_USERS" ]; then others=$(ls "$VENV_USERS" | tr '\n' ' '); fi
    [ -z "$others" ] || info "Still installed: $others- remove them with their own uninstallers (or reinstall the portal)."
    info "$APP_NAME is uninstalled."
    exit 0
fi

# --- Checks ------------------------------------------------------------------------------------
[ "$(uname -s)" = Linux ] || die "This suite runs on Linux (Bazzite) only."
for f in apps.toml requirements.txt bazzite_console_portal/__init__.py bazzite_console_portal/__main__.py; do
    [ -f "$SRC/$f" ] || die "$f is missing: run install.sh from the extracted release folder."
done
[ -f "$CORE_SRC/__init__.py" ] || die "bazzite_console_core is missing: run install.sh from the extracted release folder."
CORE_SRC=$(cd "$CORE_SRC" && pwd -P)
[ -f "$BT_SRC/install.sh" ] || die "PS5 Board Test is missing: run install.sh from the extracted release folder."
[ -f "$QUICKFIX_SRC/install.sh" ] || die "PS5 Quickfix is missing: run install.sh from the extracted release folder."
VERSION=$(sed -n 's/^__version__ = "\([0-9.]*\)"$/\1/p' "$SRC/bazzite_console_portal/__init__.py")
[ -n "$VERSION" ] || die "Could not read the version from bazzite_console_portal/__init__.py."
command -v python3 >/dev/null 2>&1 || die "python3 is not installed."
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || die "Python 3.11 or newer is needed."
python3 -c 'import venv, ensurepip' 2>/dev/null || die "python3 has no venv/ensurepip module."

info "Installing $APP_NAME $VERSION"

# --- 1. PS5 Board Test and PS5 Quickfix, always part of the suite -----------------------------------------
# First, while the release folder is whole: the portal's own update runs this script from a folder that the copy
# below may replace (an earlier portal kept its downloads in what is the portal's own folder now).
install_required() {    # install_required KEY NAME FOLDER TAG
    info "Installing $2 ($4)"
    local args=()
    $DESKTOP_SHORTCUT || args+=(--no-desktop-shortcut)
    bash "$3/install.sh" ${args[@]+"${args[@]}"}
    # Tell the portal which release it installed ("local" from a checkout), as it does for apps it installs.
    mkdir -p "$STATE_DIR"
    python3 - "$STATE_DIR/installed.json" "$1" "$4" <<'PY'
import json, sys
from pathlib import Path
path, key, tag = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
try:
    data = json.loads(path.read_text(encoding="utf-8"))
    data = data if isinstance(data, dict) else {}
except (OSError, ValueError):
    data = {}
data[key] = tag
tmp = path.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
tmp.replace(path)
PY
}
install_required "$BT_KEY" "PS5 Board Test" "$BT_SRC" "$BT_TAG"
install_required "$QUICKFIX_KEY" "PS5 Quickfix" "$QUICKFIX_SRC" "$QUICKFIX_TAG"

# --- 2. The portal's copy in the home folder -----------------------------------------------------
info "Copying the portal to $PORTAL_DIR"
# The new portal is copied beside the installed one first and takes its place only then. The bundled Board Test is
# installed by its own installer below, so it is not part of the portal's copy.
NEW_DIR="$SUITE_DIR/.portal.new"
rm -rf "${NEW_DIR:?}"
mkdir -p "$NEW_DIR"
(cd "$SRC" && tar --exclude='./bundled' --exclude='./tests' --exclude='./.git' --exclude='__pycache__' \
    --exclude='./requirements-dev.txt' -cf - .) | tar -xf - -C "$NEW_DIR"
if [ "$CORE_SRC" != "$SRC/bazzite_console_core" ]; then         # from the checkout: bundle core like a release
    mkdir -p "$NEW_DIR/bazzite_console_core"
    (cd "$CORE_SRC" && tar --exclude='__pycache__' -cf - .) | tar -xf - -C "$NEW_DIR/bazzite_console_core"
    # The installed portal installs the other apps from this checkout too, as when it runs from here: the
    # repository, one level up from <checkout>/portal.
    (cd "$SRC/.." && pwd -P) > "$NEW_DIR/suite-checkout"
fi
# The release's tarball beside the unpacked folder, as the install steps and check-release.sh leave it: its sha256
# goes beside the program, so the portal can tell a release built again under this version from the build it runs
# (build.sha256; the portal's update check reads the newest release's SHA256SUMS). A copy stays in the release
# folder, as the tarball is removed below: install.sh run again from that folder still records the build.
tarball="$SRC/../$(basename "$SRC").tar.gz"
if [ -f "$tarball" ]; then
    sha256sum "$tarball" > "$NEW_DIR/build.sha256"
    cp "$NEW_DIR/build.sha256" "$SRC/build.sha256" 2>/dev/null || true
fi
rm -rf "${PORTAL_DIR:?}"
mv "$NEW_DIR" "$PORTAL_DIR"
# The download is unpacked and recorded now: the tarball goes, and the SHA256SUMS beside it when it lists that
# tarball (another download's SHA256SUMS stays).
if [ -f "$tarball" ]; then
    sums="$(dirname "$tarball")/SHA256SUMS"
    removed=$(basename "$tarball")
    if [ -f "$sums" ] && awk -v a="$removed" '{ sub(/^\*/, "", $2) } $2 == a { f = 1 } END { exit !f }' "$sums"; then
        rm -f "$sums"
        removed="$removed and SHA256SUMS"
    fi
    rm -f "$tarball"
    info "Removed the download: $removed"
fi
cd "$SUITE_DIR"                         # the folder this ran from may be gone with the old copy

# --- 3. Shared suite venv with PyQt6 and pygame-ce ------------------------------------------------------------
# A venv made by an older Python has no site-packages for the one that runs it now (a Bazzite update moves
# /usr/bin/python3 to the next version, and the venv's python links to it): make it again.
VENV_FITS='import os, sysconfig; raise SystemExit(not os.path.isdir(sysconfig.get_path("purelib")))'
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c "$VENV_FITS" 2>/dev/null; then
    info "Creating the suite venv in $VENV"
    rm -rf "${VENV:?}"
    mkdir -p "$SUITE_DIR"
    python3 -m venv "$VENV"
fi
mkdir -p "$VENV_USERS"
touch "$VENV_USERS/$APP_ID"
info "Installing PyQt6 and pygame-ce into the venv (downloads ~110 MB the first time)"
"$VENV/bin/python" -m pip install -q --disable-pip-version-check --upgrade pip
"$VENV/bin/python" -m pip install -q --disable-pip-version-check --upgrade -r "$PORTAL_DIR/requirements.txt"
"$VENV/bin/python" -c 'import PyQt6.QtWidgets' || die "PyQt6 does not load from the venv."

# --- 4. Launcher, menu entry, Desktop icon ------------------------------------------------------
info "Creating the launcher $LAUNCHER"
mkdir -p "$(dirname "$LAUNCHER")"
cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
# $APP_NAME launcher, written by install.sh. Starts from the installed portal's folder, so Python imports the
# portal and the bazzite_console_core bundled there, never a copy from the current directory.
cd "$PORTAL_DIR" || { echo "$APP_NAME is not installed in $PORTAL_DIR; run install.sh again." >&2; exit 1; }
exec "$VENV/bin/python" -m bazzite_console_portal "\$@"
EOF
chmod 755 "$LAUNCHER"

DESKTOP_FILE_CONTENT="[Desktop Entry]
Type=Application
Version=1.0
Name=$APP_NAME
GenericName=PlayStation 5 tools
Comment=Install and start the PlayStation 5 tools for Bazzite
Exec=$LAUNCHER
Icon=$PORTAL_DIR/images/$APP_ID-128.png
Terminal=false
Categories=System;Settings;
Keywords=PS5;PlayStation;Bazzite;suite;portal;
StartupNotify=true
StartupWMClass=$APP_ID"

info "Adding the app menu entry"
mkdir -p "$(dirname "$MENU_ENTRY")"
printf '%s\n' "$DESKTOP_FILE_CONTENT" >"$MENU_ENTRY"
chmod 644 "$MENU_ENTRY"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$DATA_DIR/applications" || true

if $DESKTOP_SHORTCUT && [ -d "$DESKTOP_DIR" ]; then
    info "Adding the Desktop icon"
    printf '%s\n' "$DESKTOP_FILE_CONTENT" >"$DESKTOP_ICON"
    # KDE and GNOME only start Desktop launchers that are executable (GNOME also wants them trusted).
    chmod 755 "$DESKTOP_ICON"
    command -v gio >/dev/null 2>&1 && gio set "$DESKTOP_ICON" metadata::trusted true 2>/dev/null || true
elif ! $DESKTOP_SHORTCUT; then
    rm -f "$DESKTOP_ICON"
fi

info "Done. Start \"$APP_NAME\" from the app menu$($DESKTOP_SHORTCUT && echo ' or the Desktop'), or run: $APP_ID"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) info "Note: ~/.local/bin is not on your PATH, so the terminal command needs the full path: $LAUNCHER" ;; esac
# A portal window that is still open keeps running the old version, and starting the portal again only brings that
# window to the front: say so.
if command -v pgrep >/dev/null 2>&1 && pgrep -u "$(id -u)" -f -- '-m bazzite_console_portal' >/dev/null 2>&1; then
    info "A $APP_NAME window is still open with the version from before: close it, then start it again."
fi
