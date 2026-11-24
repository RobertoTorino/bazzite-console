#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs PS5 CU Unlock, one window for the bisect and the unlock, as a desktop app, from a clone or the
# extracted release tarball:
#
#   ./install.sh                         # install or update the app
#   ./install.sh --no-desktop-shortcut   # app menu entry only, no icon on the Desktop
#   ./install.sh --uninstall             # remove the app. Results, settings and logs stay
#   ./install.sh --uninstall --purge     # also remove results, settings, logs and the autostart entries
#
# Run it as your own user, not with sudo; nothing here needs root. The app gets a venv with PyQt6 under
# ~/.local/share/ps5-bisect-gui, a launcher in ~/.local/bin, an app menu entry and a Desktop icon. The work is
# done by packaging/bazzite/install-bisect-gui.sh (and its uninstaller), which can also be run on its own; it
# removes the separate unlock window of before (uninstall-gui.sh).
set -euo pipefail

APP_NAME="PS5 CU Unlock"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_DIR="$DATA_DIR/ps5-cu-bisect"                # the bisect script's runs, logs and results
SETTINGS_DIR="$CONFIG_DIR/ps5-cu-bisect"            # both GUIs' settings (QSettings organization)
AUTO_UNIT="$CONFIG_DIR/systemd/user/ps5-cu-bisect-auto.service"
WATCH_ENTRY="$CONFIG_DIR/autostart/ps5-cu-bisect-watch.desktop"

SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGING="$SRC/packaging/bazzite"

info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }
die()  { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }
usage() { sed -n '3,10p' "$0" | sed 's/^# \{0,1\}//'; }

DESKTOP_SHORTCUT=true
UNINSTALL=false
PURGE=false
for arg in "$@"; do
    case "$arg" in
        --no-desktop-shortcut) DESKTOP_SHORTCUT=false ;;
        --uninstall) UNINSTALL=true ;;
        --purge) PURGE=true ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "Unknown option: $arg" ;;
    esac
done
$PURGE && ! $UNINSTALL && die "--purge only goes with --uninstall."
[ "$(id -u)" -ne 0 ] || die "Run this as your own user, not with sudo: the venvs and the launchers belong in your home folder."
for f in install-bisect-gui.sh uninstall-bisect-gui.sh uninstall-gui.sh; do
    [ -f "$PACKAGING/$f" ] || die "packaging/bazzite/$f is missing: run install.sh from a clone or the extracted release folder."
done

# Whether anything the uninstall removes is on this computer (paths and globs): without, it removes nothing, asks
# for no password and says the app is not installed.
installed_here() {
    local path
    for path in "$@"; do
        compgen -G "$path" >/dev/null && return 0
    done
    return 1
}

if $UNINSTALL; then
    # What the uninstallers (packaging/bazzite) remove: the app, and the separate unlock window of before
    found=false
    desktop=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
    installed_here "$DATA_DIR/ps5-bisect-gui" "$DATA_DIR/ps5-unlock-cu-gui" \
        "${XDG_BIN_HOME:-$HOME/.local/bin}/ps5-bisect-gui" "${XDG_BIN_HOME:-$HOME/.local/bin}/ps5-unlock-cu-gui" \
        "$DATA_DIR/applications/ps5-cu-bisect.desktop" "$DATA_DIR/applications/ps5-cu-unlock.desktop" \
        "$DATA_DIR/icons/hicolor/"*/apps/ps5-cu-bisect*.png "$desktop/ps5-cu-bisect.desktop" \
        "$desktop/ps5-cu-unlock.desktop" && found=true
    $PURGE && installed_here "$AUTO_UNIT" "$WATCH_ENTRY" "${STATE_DIR:?}" "${SETTINGS_DIR:?}" && found=true
    if ! $found; then
        info "$APP_NAME is not installed: nothing to remove."
        exit 0
    fi
    info "Removing $APP_NAME"
    bash "$PACKAGING/uninstall-bisect-gui.sh"
    bash "$PACKAGING/uninstall-gui.sh" >/dev/null
    if $PURGE; then
        info "Removing the autostart entries, results, logs and settings"
        if [ -f "$AUTO_UNIT" ]; then
            systemctl --user disable --now ps5-cu-bisect-auto.service 2>/dev/null || true
            rm -f "$AUTO_UNIT"
            systemctl --user daemon-reload 2>/dev/null || true
        fi
        rm -f "$WATCH_ENTRY"
        rm -rf "${STATE_DIR:?}" "${SETTINGS_DIR:?}"
    fi
    info "$APP_NAME is uninstalled."
    exit 0
fi

[ "$(uname -s)" = Linux ] || die "This app runs on Linux (Bazzite) only."
OPTIONS=()
$DESKTOP_SHORTCUT || OPTIONS+=(--no-desktop-shortcut)
info "Installing $APP_NAME"
bash "$PACKAGING/install-bisect-gui.sh" "${OPTIONS[@]}"
info "$APP_NAME is installed."
