#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs Nexus Garbage Remover for the current user: a launcher, an app menu entry, a Desktop icon and the hourly
# reminder, all starting run.sh in this checkout (Linux). Nothing is copied: the app runs from the checkout it lives
# in, so it always runs the checkout's own code. It is not part of a portal's releases. Moving the checkout needs
# install.sh again.
#
#   ./install.sh                         # launcher, app menu entry, Desktop icon and the hourly reminder
#   ./install.sh --no-desktop-shortcut   # the same without the Desktop icon
#   ./install.sh --uninstall             # remove them; the checkout and the settings stay
#   ./install.sh --uninstall --purge     # also remove the settings; the checkout stays
#
#  * ~/.config/systemd/user/nexus-garbage-remover-reminder.service and .timer: every hour the app measures the
#    garbage on this machine and shows a desktop notification when there is 1 GB or more, once a day, with a
#    button that opens it (it deletes nothing by itself).
set -euo pipefail
APP=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd "$APP/../.." && pwd -P)          # the repository: the venvs

APP_ID="nexus-garbage-remover"
APP_NAME="Nexus Garbage Remover"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
LAUNCHER="$HOME/.local/bin/$APP_ID"
MENU_ENTRY="$DATA_DIR/applications/$APP_ID.desktop"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
DESKTOP_ICON="$DESKTOP_DIR/$APP_ID.desktop"
ICON="$APP/images/$APP_ID-128.png"
REMINDER="nexus-garbage-remover-reminder"
UNIT_DIR="$CONFIG_DIR/systemd/user"

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
        -h|--help) sed -n '3,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "Unknown option: $arg (use --help)." ;;
    esac
done
$purge && ! $uninstall && die "--purge only goes with --uninstall."
[ "$(id -u)" -ne 0 ] || die "Run this as your own user, not with sudo."

# remove_timer NAME: a systemd user timer and its service, stopped and gone
remove_timer() {
    [ -e "$UNIT_DIR/$1.timer" ] || [ -e "$UNIT_DIR/$1.service" ] || return 0
    systemctl --user disable --now "$1.timer" >/dev/null 2>&1 || true
    rm -f "$UNIT_DIR/$1.timer" "$UNIT_DIR/$1.service" "$UNIT_DIR/timers.target.wants/$1.timer"
    systemctl --user daemon-reload >/dev/null 2>&1 || true
}

if $uninstall; then
    info "Removing the hourly reminder"
    remove_timer "$REMINDER"
    info "Removing the launcher, the menu entry and the Desktop icon"
    rm -f "$LAUNCHER" "$MENU_ENTRY" "$DESKTOP_ICON"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$DATA_DIR/applications" || true
    if $purge; then
        info "Removing the settings"
        rm -rf "${CONFIG_DIR:?}/$APP_ID"
        info "$APP_NAME is removed. The checkout stays."
    else
        info "$APP_NAME is removed. The checkout and its settings stay."
    fi
    exit 0
fi

[ "$(uname -s)" = Linux ] || die "install.sh makes a Linux app menu entry and a systemd timer. The app runs on Linux."
[ -x "$REPO/.venv-linux/bin/python" ] || [ -x "$REPO/.venv/bin/python" ] || [ -n "${PYTHON:-}" ] ||
    info "Note: there is no .venv-linux yet. Create it before you start the app, as CLAUDE.md says."

info "Creating the launcher $LAUNCHER"
mkdir -p "$(dirname "$LAUNCHER")"
cat >"$LAUNCHER" <<LAUNCH
#!/usr/bin/env bash
# $APP_NAME launcher, written by dev/garbage/install.sh. Runs the app of this checkout.
[ -x "$APP/run.sh" ] || { echo "No checkout in $REPO anymore. Run dev/garbage/install.sh again." >&2; exit 1; }
exec "$APP/run.sh" "\$@"
LAUNCH
chmod 755 "$LAUNCHER"

entry="[Desktop Entry]
Type=Application
Version=1.0
Name=$APP_NAME
GenericName=Nexus garbage remover
Comment=Find and delete the garbage on this machine ($REPO)
Exec=$LAUNCHER
Icon=$ICON
Terminal=false
Categories=Development;System;
Keywords=Nexus;garbage;cleanup;crash dumps;cache;trash;
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

info "Adding the hourly reminder ($REMINDER.timer)"
mkdir -p "$UNIT_DIR"
cat >"$UNIT_DIR/$REMINDER.service" <<EOF
# Written by $APP_NAME's install.sh: a desktop notification when there is much garbage on this machine.
[Unit]
Description=$APP_NAME: is there much garbage?

[Service]
Type=oneshot
ExecStart=$LAUNCHER --remind
EOF
cat >"$UNIT_DIR/$REMINDER.timer" <<EOF
# Written by $APP_NAME's install.sh; --uninstall removes it.
[Unit]
Description=$APP_NAME: hourly look for garbage

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=5min

[Install]
WantedBy=timers.target
EOF
systemctl --user daemon-reload >/dev/null 2>&1 || true
if ! systemctl --user enable --now "$REMINDER.timer" >/dev/null 2>&1; then
    # No user session to ask (an install over ssh, say): enable it as systemctl would, for the next login.
    mkdir -p "$UNIT_DIR/timers.target.wants"
    ln -sfn "../$REMINDER.timer" "$UNIT_DIR/timers.target.wants/$REMINDER.timer"
    info "Note: the reminder starts with your next login."
fi
info "Done. Start \"$APP_NAME\" from the app menu$($shortcut && echo ' or the Desktop'), or run: $APP_ID"
