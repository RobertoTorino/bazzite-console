#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

# Removes everything packaging/bazzite/install-bisect-gui.sh set up for the current user. Does not
# touch your bisect results in ~/.local/share/ps5-cores-bisect or the unlock service - use Uninstall in CPU
# Tools, or "sudo ./ps5-cores-unlock.sh --uninstall", if you also want the unlock itself removed.
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

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true

echo "Removed PS5 CPU Tools (app, venv, launcher, menu entry, icon)."
echo "Your results in $DATA_HOME/ps5-cores-bisect were kept."
