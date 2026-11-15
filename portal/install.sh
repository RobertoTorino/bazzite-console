#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs the portal and its required app for the logged-in user:
#
#   ./install.sh                         # install or update
#   ./install.sh --no-desktop-shortcut   # app menu entries only, no icons on the Desktop
#   ./install.sh --uninstall             # remove the portal, Board Test and (asked per app) the other apps;
#                                        # keeps settings and the wallpaper
#   ./install.sh --uninstall --purge     # also remove the portal's and Board Test's settings and state
#   ./install.sh --uninstall --all       # the whole suite: every other app too, without a question per app,
#                                        # after one confirmation; with --purge their settings go as well
set -euo pipefail

APP_ID="bazzite-console-suite"
APP_NAME="Bazzite Console Suite"
APP_KEY="board"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
SUITE_DIR="$DATA_DIR/$APP_ID"
VENV="$SUITE_DIR/venv"
VENV_USERS="$SUITE_DIR/venv-users"
PORTAL_DIR="$SUITE_DIR/portal"
STATE_DIR="$SUITE_DIR/state"            # what the portal remembers: the installed apps, downloads, the wallpaper
LAUNCHER="$HOME/.local/bin/$APP_ID"
MENU_ENTRY="$DATA_DIR/applications/$APP_ID.desktop"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
DESKTOP_ICON="$DESKTOP_DIR/$APP_ID.desktop"
OPT_DIR="${PS5_BOARD_TEST_OPT_DIR:-/opt}"     # where Board Test is installed; override only for testing
BT_ID="ps5-board-test"

SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
if [ -d "$SRC/bundled" ]; then
    APP_SRC=$(find "$SRC/bundled" -mindepth 2 -maxdepth 2 -type f -path '*/install.sh' -print -quit |
        sed 's|/install.sh$||')
    [ -n "$APP_SRC" ] || { echo "The required Board Test app is missing from this portal release." >&2; exit 1; }
else
    APP_SRC="$SRC/../apps/$APP_KEY"
fi

info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }
usage() { sed -n '5,11p' "$0" | sed 's/^# \{0,1\}//'; }

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
[ "$(id -u)" -ne 0 ] || die "Run this as your own user, not with sudo."

remove_menu_entries() {
    rm -f "$LAUNCHER" "$MENU_ENTRY" "$DESKTOP_ICON"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$DATA_DIR/applications" || true
}

release_venv() {
    rm -f "${VENV_USERS:?}/${APP_ID:?}-portal"
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
    python3 - "$manifest" "$STATE_DIR" "$checkout" "$1" "$DATA_DIR" "$OPT_DIR" "$APP_ID" "$BT_ID" <<'PY'
import json, os, re, subprocess, sys, tomllib
from pathlib import Path
manifest, state, checkout, staging = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
data_dir, opt_dir, own_ids = Path(sys.argv[5]), Path(sys.argv[6]), set(sys.argv[7:9])    # the portal, Board Test
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
        info "WARNING: --all removes the whole suite from this computer: $names, with the portal and Board Test."
        $PURGE && info "WARNING: --purge removes their settings, history and results as well."
        printf "Are you sure you want to delete everything permanently? [y/N] "
        read -r answer || answer=n
        case "${answer,,}" in
            y|yes) ;;
            *) info "Canceled: nothing was uninstalled."; exit 1 ;;
        esac
        mapfile -t chosen < <(cut -f1 <<<"$list")
    elif [ -n "$list" ] && { [ -t 0 ] || [ -n "${BAZZITE_CONSOLE_INTERACTIVE:-}" ]; }; then   # the variable: tests only
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
        info "Their own settings are kept: --purge applies to the portal and Board Test (with --all, to every app)."
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
# release folder its uninstaller runs from); records and folders of apps that are gone, and Board Test's, go.
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
    found=false
    installed_here "$LAUNCHER" "$MENU_ENTRY" "$DESKTOP_ICON" "$PORTAL_DIR" "$VENV_USERS/$APP_ID-portal" \
        "$OPT_DIR/$BT_ID" && found=true
    $PURGE && installed_here "${CONFIG_DIR:?}/$APP_ID" "${STATE_DIR:?}" && found=true
    if ! $found && [ -z "$(installed_apps "$STAGING/check" 2>/dev/null)" ]; then
        info "$APP_NAME is not installed: nothing to remove."
        exit 0
    fi
    uninstall_other_apps
    if [ -f "$OPT_DIR/$BT_ID/install.sh" ]; then
        info "Uninstalling Board Test"
        bt_args=(--uninstall)
        $PURGE && bt_args+=(--purge)
        bash "$OPT_DIR/$BT_ID/install.sh" "${bt_args[@]}"
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

[ "$(uname -s)" = Linux ] || die "This suite runs on Linux (Bazzite) only."
for file in "$SRC/apps.toml" "$SRC/requirements.txt" "$APP_SRC/install.sh"; do
    [ -f "$file" ] || die "Required file is missing: $file"
done
if [ -d "$SRC/bazzite_console_core" ]; then CORE_SRC="$SRC/bazzite_console_core"; else CORE_SRC="$SRC/../core/bazzite_console_core"; fi
[ -f "$CORE_SRC/__init__.py" ] || die "bazzite_console_core is missing."
[ -f "$APP_SRC/VERSION" ] || die "Board Test is missing its VERSION file."

info "Installing the required Board Test app"
bash "$APP_SRC/install.sh" --no-desktop-shortcut
info "Copying the portal to $PORTAL_DIR"
# The new portal is copied beside the installed one first and takes its place only then: the portal's own update
# runs this script from a folder inside the installed portal, which the removal below takes with it.
NEW_DIR="$SUITE_DIR/.portal.new"
rm -rf "${NEW_DIR:?}"
mkdir -p "$NEW_DIR"
(cd "$SRC" && tar --exclude='./tests' --exclude='__pycache__' --exclude='./.git' -cf - .) |
    tar -xf - -C "$NEW_DIR"
if [ "$CORE_SRC" != "$SRC/bazzite_console_core" ]; then
    mkdir -p "$NEW_DIR/bazzite_console_core"
    (cd "$CORE_SRC" && tar --exclude='__pycache__' -cf - .) | tar -xf - -C "$NEW_DIR/bazzite_console_core"
fi
# Up to portal 1.0.0 the portal kept what it remembers in its program folder, where every install removed it: move
# it to the state folder, once.
mkdir -p "$STATE_DIR"
for kept in "$PORTAL_DIR"/installed.json "$PORTAL_DIR"/releases "$PORTAL_DIR"/wallpapers.json \
            "$PORTAL_DIR"/wallpaper-example "$PORTAL_DIR"/wallpaper.*; do
    if [ -e "$kept" ] && [ ! -e "$STATE_DIR/${kept##*/}" ]; then
        mv "$kept" "$STATE_DIR/"
    fi
done
rm -rf "${PORTAL_DIR:?}"
mv "$NEW_DIR" "$PORTAL_DIR"
# A venv made by an older Python has no site-packages for the one that runs it now (a Bazzite update moves
# /usr/bin/python3 to the next version, and the venv's python links to it): make it again.
VENV_FITS='import os, sysconfig; raise SystemExit(not os.path.isdir(sysconfig.get_path("purelib")))'
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c "$VENV_FITS" 2>/dev/null; then
    rm -rf "${VENV:?}"
    mkdir -p "$SUITE_DIR"
    python3 -m venv "$VENV"
fi
mkdir -p "$VENV_USERS"
touch "$VENV_USERS/$APP_ID-portal"
"$VENV/bin/python" -m pip install -q --disable-pip-version-check --upgrade -r "$PORTAL_DIR/requirements.txt"

mkdir -p "$(dirname "$LAUNCHER")"
cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
cd "$PORTAL_DIR"
exec "$VENV/bin/python" -m bazzite_console_portal "\$@"
EOF
chmod 755 "$LAUNCHER"
mkdir -p "$(dirname "$MENU_ENTRY")"
cat >"$MENU_ENTRY" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$LAUNCHER
Icon=$PORTAL_DIR/images/$APP_ID-128.png
Terminal=false
Categories=System;
EOF
chmod 644 "$MENU_ENTRY"
if $DESKTOP_SHORTCUT && [ -d "$DESKTOP_DIR" ]; then
    cp "$MENU_ENTRY" "$DESKTOP_ICON"
    chmod 755 "$DESKTOP_ICON"
elif ! $DESKTOP_SHORTCUT; then
    rm -f "$DESKTOP_ICON"
fi
info "Installed. Start $APP_NAME from the app menu or run $LAUNCHER."
