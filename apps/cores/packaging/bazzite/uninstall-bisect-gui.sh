#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

# Removes everything packaging/bazzite/install-bisect-gui.sh set up for the current user, and the window's
# autostart entry that goes on with a running core test after a login (it would start the removed launcher). Does not
# touch your bisect results in ~/.local/share/ps5-cores-bisect or the unlock service - use Uninstall in Core
# Unlock, or "sudo ./ps5-cores-unlock.sh --uninstall", if you also want the unlock itself removed.
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
APP_DIR="$DATA_HOME/ps5-cores-bisect-gui"
LAUNCHER="$BIN_HOME/ps5-cores-bisect-gui"
DESKTOP_FILE="$DATA_HOME/applications/ps5-cores-bisect.desktop"
ICON_FILE="$DATA_HOME/icons/hicolor/128x128/apps/ps5-cores-bisect.png"
OLD_ICON="$DATA_HOME/icons/hicolor/512x512/apps/ps5-cores-bisect.png"   # the 512 px icon of before

rm -rf "$APP_DIR"
rm -f "$LAUNCHER" "$DESKTOP_FILE" "$ICON_FILE" "$OLD_ICON"
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/ps5-core-unlock-resume.desktop"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true

echo "Removed the app, venv, launcher, menu entry and icon of PS5 Core Unlock."
echo "Your results in $DATA_HOME/ps5-cores-bisect stay."
