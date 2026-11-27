#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs Nexus Flight Recorder for the current user: a launcher, an app menu entry and a Desktop icon, all starting
# run.sh in this checkout (Linux). Nothing is copied: the app runs from the checkout it lives in, so it always runs
# the checkout's own code. It is not part of a portal's releases. Moving the checkout needs install.sh again.
#
#   ./install.sh                         # launcher, app menu entry and Desktop icon
#   ./install.sh --no-desktop-shortcut   # the same without the Desktop icon
#   ./install.sh --uninstall             # remove them; the checkout and the settings stay
#   ./install.sh --uninstall --purge     # also remove the settings; the checkout stays
#
#  * The recorder itself is a system service that the app's window installs, starts and stops, with your password.
#    This script never touches it. --uninstall says how to remove it when it is still there.
set -euo pipefail
APP=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd "$APP/../.." && pwd -P)          # the repository: the venvs

APP_ID="nexus-flight-recorder"
APP_NAME="Nexus Flight Recorder"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
LAUNCHER="$HOME/.local/bin/$APP_ID"
MENU_ENTRY="$DATA_DIR/applications/$APP_ID.desktop"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
DESKTOP_ICON="$DESKTOP_DIR/$APP_ID.desktop"
ICON="$APP/images/$APP_ID-128.png"
SERVICE="/etc/systemd/system/nexus-flight-recorder.service"

info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }
die()  { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

shortcut=true
uninstall=false
purge=false
for arg in "$@"; do
    case "$arg" in
        --no-desktop-shortcut) shortcut=false ;;
        --uninstall) uninstall=true ;;
        --purge) purge=true ;;
        -h|--help) sed -n '3,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "Unknown option: $arg (use --help)." ;;
    esac
done
$purge && ! $uninstall && die "--purge only goes with --uninstall."
[ "$(id -u)" -ne 0 ] || die "Run this as your own user, not with sudo."

if $uninstall; then
    info "Removing the launcher, the menu entry and the Desktop icon"
    rm -f "$LAUNCHER" "$MENU_ENTRY" "$DESKTOP_ICON"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$DATA_DIR/applications" || true
    if [ -e "$SERVICE" ]; then
        info "The recorder's system service is still installed. Remove it with:"
        info "  sudo /usr/bin/python3 -I $APP/nexus_flight_recorder/helper.py remove"
    fi
    if $purge; then
        info "Removing the settings"
        rm -rf "${CONFIG_DIR:?}/$APP_ID"
        info "$APP_NAME is removed. The checkout stays."
    else
        info "$APP_NAME is removed. The checkout and its settings stay."
    fi
    exit 0
fi

[ "$(uname -s)" = Linux ] || die "install.sh makes a Linux app menu entry. The app runs on Linux."
[ -x "$REPO/.venv-linux/bin/python" ] || [ -x "$REPO/.venv/bin/python" ] || [ -n "${PYTHON:-}" ] ||
    info "Note: there is no .venv-linux yet. Create it before you start the app, as CLAUDE.md says."

info "Creating the launcher $LAUNCHER"
mkdir -p "$(dirname "$LAUNCHER")"
cat >"$LAUNCHER" <<LAUNCH
#!/usr/bin/env bash
# $APP_NAME launcher, written by dev/flight/install.sh. Runs the app of this checkout.
[ -x "$APP/run.sh" ] || { echo "No checkout in $REPO anymore. Run dev/flight/install.sh again." >&2; exit 1; }
exec "$APP/run.sh" "\$@"
LAUNCH
chmod 755 "$LAUNCHER"

entry="[Desktop Entry]
Type=Application
Version=1.0
Name=$APP_NAME
GenericName=Nexus flight recorder
Comment=Record what the board does, one line per second ($REPO)
Exec=$LAUNCHER
Icon=$ICON
Terminal=false
Categories=Development;System;
Keywords=Nexus;flight recorder;sensors;crash;log;
StartupNotify=true
StartupWMClass=$APP_ID"
info "Adding the app menu entry"
mkdir -p "$(dirname "$MENU_ENTRY")"
printf '%s\n' "$entry" >"$MENU_ENTRY"
chmod 644 "$MENU_ENTRY"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$DATA_DIR/applications" || true
if $shortcut && [ -d "$DESKTOP_DIR" ]; then
    info "Adding the Desktop icon"
    printf '%s\n' "$entry" >"$DESKTOP_ICON"
    # KDE and GNOME only start Desktop launchers that are executable (GNOME also wants them trusted).
    chmod 755 "$DESKTOP_ICON"
    command -v gio >/dev/null 2>&1 && gio set "$DESKTOP_ICON" metadata::trusted true 2>/dev/null || true
elif ! $shortcut; then
    rm -f "$DESKTOP_ICON"
fi

info "Done. Start \"$APP_NAME\" from the app menu$($shortcut && echo ' or the Desktop'), or run: $APP_ID"
