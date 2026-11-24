#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Installs PS5 GPU Manager for the current user, so it shows up in the application menu like any
# other app. It puts a private venv with PyQt6 and the app in ~/.local/share, a launcher in ~/.local/bin
# and a desktop entry with icon. It layers nothing with rpm-ostree and needs no root.
#
#   ./install.sh                         install or update
#   ./install.sh --no-desktop-shortcut   app menu entry only, no icon on the Desktop
#   ./install.sh --uninstall             remove everything it installed; keeps its settings and profiles
#   ./install.sh --uninstall --purge     also remove its settings, profiles, the start-at-login entry and the
#                                        GPU sweep's results
#   ./install.sh --run                   install and start the app
#
# Run it as your own user, not with sudo. It never touches the governor's own config.toml and its backups, except
# once: PS5 GPU OC Bisect, which the GPU sweep replaces, goes with its results. When an attempt of it was cut
# off, its test config is still in place, and the installer puts your own config back first. Removing its copy in
# /opt and that restore ask for the sudo password.

set -euo pipefail

APP_ID="ps5-governor-manager"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$DATA_HOME/$APP_ID"
VENV_DIR="$APP_DIR/venv"
APPS_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/128x128/apps"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
SWEEP_ID="ps5-gpu-sweep"               # the GPU sweep window: its results, settings and resume entry
OLD_ID="ps5-gpu-oc-bisect"             # PS5 GPU OC Bisect, merged into GPU Manager (owner, 24-11-2026)
OPT_DIR="${PS5_OPT_DIR:-/opt}"         # override only for testing

say()  { printf '\033[1;35m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# Whether anything the uninstall removes is on this computer (paths and globs): without, it removes nothing, asks
# for no password and says the app is not installed.
installed_here() {
    local path
    for path in "$@"; do
        compgen -G "$path" >/dev/null && return 0
    done
    return 1
}

# PS5 GPU OC Bisect goes completely (owner, 24-11-2026: removed, results not kept): its copy in /opt, launcher,
# menu entry, Desktop icon, venv, results and settings. Its config.toml.pre-oc-bisect backup stays, and the Backups
# page lists it.
remove_oc_bisect() {
    local state="$DATA_HOME/$OLD_ID" gov="/etc/cyan-skillfish-governor-smu/config.toml"
    installed_here "$OPT_DIR/$OLD_ID" "$OPT_DIR/$OLD_ID-v*" "$BIN_DIR/$OLD_ID-gui" "$APPS_DIR/$OLD_ID-gui.desktop" \
        "$DESKTOP_DIR/$OLD_ID-gui.desktop" "$DATA_HOME/$OLD_ID-app" "$state" "$CONFIG_DIR/$OLD_ID" || return 0
    say "Removing PS5 GPU OC Bisect: GPU Manager's GPU sweep replaces it"
    if [[ -f "$state/test-config-active" && -f "$state/governor-config.orig" ]]; then
        say "Its last attempt was cut off, so its test config is still in $gov: putting your own config back (sudo)"
        sudo cp "$state/governor-config.orig" "$gov" && sudo systemctl restart cyan-skillfish-governor-smu ||
            fail "could not put back $gov from $state/governor-config.orig. Copy it back by hand, then run this again."
    fi
    if installed_here "$OPT_DIR/$OLD_ID" "$OPT_DIR/$OLD_ID-v*"; then
        say "Removing $OPT_DIR/$OLD_ID (sudo)"
        sudo rm -rf "${OPT_DIR:?}/$OLD_ID" "$OPT_DIR/$OLD_ID"-v*
    fi
    rm -f "$BIN_DIR/$OLD_ID-gui" "$APPS_DIR/$OLD_ID-gui.desktop" "$DESKTOP_DIR/$OLD_ID-gui.desktop"
    rm -rf "$DATA_HOME/$OLD_ID-app" "${state:?}" "${CONFIG_DIR:?}/$OLD_ID"
}

uninstall() {
    found=false
    installed_here "$APP_DIR" "$BIN_DIR/$APP_ID" "$APPS_DIR/$APP_ID.desktop" "$ICON_DIR/$APP_ID.png" \
        "$DESKTOP_DIR/$APP_ID.desktop" "$DATA_HOME/icons/hicolor/512x512/apps/$APP_ID.png" && found=true
    installed_here "$CONFIG_DIR/autostart/$SWEEP_ID-resume.desktop" && found=true
    $PURGE && installed_here "${CONFIG_DIR:?}/$APP_ID" "$CONFIG_DIR/autostart/$APP_ID.desktop" \
        "$DATA_HOME/$SWEEP_ID" "$CONFIG_DIR/$SWEEP_ID" && found=true
    if ! $found; then
        say "$APP_ID is not installed: nothing to remove."
        exit 0
    fi
    say "Removing $APP_ID"
    rm -rf "$APP_DIR"
    rm -f "$BIN_DIR/$APP_ID" "$APPS_DIR/$APP_ID.desktop" "$ICON_DIR/$APP_ID.png" "$DESKTOP_DIR/$APP_ID.desktop" \
          "$DATA_HOME/icons/hicolor/512x512/apps/$APP_ID.png" "$CONFIG_DIR/autostart/$SWEEP_ID-resume.desktop"
    command -v update-desktop-database >/dev/null && update-desktop-database -q "$APPS_DIR" || true
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$DATA_HOME/icons/hicolor" 2>/dev/null || true
    if $PURGE; then
        say "Removing the settings, profiles, the start-at-login entry and the GPU sweep's results"
        rm -rf "${CONFIG_DIR:?}/$APP_ID" "${CONFIG_DIR:?}/$SWEEP_ID" "${DATA_HOME:?}/$SWEEP_ID"
        rm -f "$CONFIG_DIR/autostart/$APP_ID.desktop"
    fi
    say "Done. The governor's config.toml and backups were left untouched."
}

RUN=false
DESKTOP_SHORTCUT=true
UNINSTALL=false
PURGE=false
for arg in "$@"; do
    case "$arg" in
        --uninstall) UNINSTALL=true ;;
        --purge) PURGE=true ;;
        --run) RUN=true ;;
        --no-desktop-shortcut) DESKTOP_SHORTCUT=false ;;
        -h|--help) sed -n '3,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) fail "unknown option: $arg (try --help)" ;;
    esac
done
$PURGE && ! $UNINSTALL && fail "--purge only goes with --uninstall"
[[ "$(id -u)" -ne 0 ]] || fail "run this as your own user, not with sudo: the app, venv and launcher belong in your home folder"
if $UNINSTALL; then uninstall; exit 0; fi

[[ -f "$SRC_DIR/gpu_governor/__main__.py" ]] || fail "run this script from the unpacked release directory"
command -v python3 >/dev/null || fail "python3 is required"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || fail "Python 3.11 or newer is required"
python3 -c 'import venv, ensurepip' 2>/dev/null || fail "python3 venv/ensurepip modules are missing"

say "Installing the app to $APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR" "$APPS_DIR" "$ICON_DIR"
rm -rf "$APP_DIR/gpu_governor" "$APP_DIR/ps5_governor" "$APP_DIR/images"   # and the package before its rename
cp -R "$SRC_DIR/gpu_governor" "$SRC_DIR/images" "$APP_DIR/"
install -m 755 "$SRC_DIR/$SWEEP_ID.sh" "$APP_DIR/$SWEEP_ID.sh"
cp "$SRC_DIR/requirements.txt" "$SRC_DIR/LICENSE" "$SRC_DIR/README.md" "$APP_DIR/" 2>/dev/null || true
find "$APP_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +

# A venv made by an older Python has no site-packages for the one that runs it now (a Bazzite update moves
# /usr/bin/python3 to the next version, and the venv's python links to it): make it again.
VENV_FITS='import os, sysconfig; raise SystemExit(not os.path.isdir(sysconfig.get_path("purelib")))'
if [[ ! -x "$VENV_DIR/bin/python" ]] || ! "$VENV_DIR/bin/python" -c "$VENV_FITS" 2>/dev/null; then
    say "Creating the virtual environment"
    rm -rf "${VENV_DIR:?}"
    python3 -m venv "$VENV_DIR"
fi
say "Installing PyQt6 into the virtual environment (this takes a moment the first time)"
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade -r "$SRC_DIR/requirements.txt"

remove_oc_bisect

say "Installing the launcher, desktop entry and icon"
cat > "$BIN_DIR/$APP_ID" <<EOF
#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
cd "$APP_DIR" && exec "$VENV_DIR/bin/python" -m gpu_governor "\$@"
EOF
chmod 755 "$BIN_DIR/$APP_ID"

# The desktop entry points at the launcher by absolute path, so it works even when ~/.local/bin
# is not on PATH of the session that spawns menu entries.
sed "s|^Exec=.*|Exec=$BIN_DIR/$APP_ID|" "$SRC_DIR/$APP_ID.desktop" > "$APPS_DIR/$APP_ID.desktop"
chmod 644 "$APPS_DIR/$APP_ID.desktop"
if $DESKTOP_SHORTCUT && [[ -d "$DESKTOP_DIR" ]]; then
    cp "$APPS_DIR/$APP_ID.desktop" "$DESKTOP_DIR/$APP_ID.desktop"
    # KDE and GNOME only start Desktop launchers that are executable (GNOME also wants them trusted).
    chmod 755 "$DESKTOP_DIR/$APP_ID.desktop"
    command -v gio >/dev/null && gio set "$DESKTOP_DIR/$APP_ID.desktop" metadata::trusted true 2>/dev/null || true
else
    rm -f "$DESKTOP_DIR/$APP_ID.desktop"
fi
cp "$SRC_DIR/images/$APP_ID-128.png" "$ICON_DIR/$APP_ID.png"
rm -f "$DATA_HOME/icons/hicolor/512x512/apps/$APP_ID.png"   # the 512 px icon of before
command -v update-desktop-database >/dev/null && update-desktop-database -q "$APPS_DIR" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$DATA_HOME/icons/hicolor" 2>/dev/null || true

say "Installed. Find \"PS5 GPU Manager\" in the application menu$($DESKTOP_SHORTCUT && echo ' or on the Desktop'), or run: $BIN_DIR/$APP_ID"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "    (note: $BIN_DIR is not on your PATH in this shell)" ;;
esac

if $RUN; then
    exec "$BIN_DIR/$APP_ID"
fi
