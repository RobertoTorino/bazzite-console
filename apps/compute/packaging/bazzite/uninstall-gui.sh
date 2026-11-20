#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

# Removes the separate unlock window of before (PS5 CU Unlock, ps5-unlock-cu-gui) for the current user:
# CU Tools' one window has the unlock now, and install-bisect-gui.sh runs this on an update. Does not touch
# /etc/ps5-cu-bisect or the systemd unit - use Uninstall in CU Tools, or "sudo ./ps5-cu-unlock.sh
# --uninstall", if you also want the unlock itself removed.
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
APP_DIR="$DATA_HOME/ps5-unlock-cu-gui"
LAUNCHER="$BIN_HOME/ps5-unlock-cu-gui"
DESKTOP_FILE="$DATA_HOME/applications/ps5-cu-unlock.desktop"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
ICON_FILE="$DATA_HOME/icons/hicolor/128x128/apps/ps5-cu-bisect-unlock.png"
OLD_ICON="$DATA_HOME/icons/hicolor/512x512/apps/ps5-cu-bisect-unlock.png"   # the 512 px icon of before

rm -rf "$APP_DIR"
rm -f "$LAUNCHER" "$DESKTOP_FILE" "$ICON_FILE" "$OLD_ICON" "$DESKTOP_DIR/ps5-cu-unlock.desktop"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true

echo "Removed PS5 CU Unlock GUI (app, venv, launcher, menu entry, icon, Desktop icon)."
