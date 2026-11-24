#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

# Self-install for Bazzite (and any other immutable/rpm-ostree-based desktop): sets up
# cores_bisect, the one window for the core bisect and the core unlock (PS5 Core Unlock), in a private venv
# under ~/.local, with a launcher, .desktop entry and icon. Nothing here touches rpm-ostree or needs root - the
# window starts ps5-cores-bisect.sh in a terminal, and only its Install, Uninstall and Root status run
# ps5-cores-unlock.sh through sudo. The separate unlock window of before (ps5-cores-unlock-gui) is removed.
#
# Usage: run from inside a clone (or release archive) of this repo:
#   bash packaging/bazzite/install-bisect-gui.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

for f in cores_bisect/__main__.py ps5-cores-bisect.sh ps5-cores-unlock.sh \
         images/ps5-cores-bisect.webp images/ps5-cores-bisect-128.png requirements.txt VERSION; do
  if [ ! -e "$REPO_ROOT/$f" ]; then
    echo "error: $f not found under $REPO_ROOT - run this from a clone of ps5-cores-bisect" >&2
    exit 1
  fi
done

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
APP_DIR="$DATA_HOME/ps5-cores-bisect-gui"
APP_SRC="$APP_DIR/app"
VENV_DIR="$APP_DIR/venv"
LAUNCHER="$BIN_HOME/ps5-cores-bisect-gui"
DESKTOP_FILE="$DATA_HOME/applications/ps5-cores-bisect.desktop"
ICON_DIR="$DATA_HOME/icons/hicolor/128x128/apps"
ICON_FILE="$ICON_DIR/ps5-cores-bisect.png"

echo "==> Copying app files to $APP_SRC"
rm -rf "$APP_SRC"
mkdir -p "$APP_SRC/images"
cp -R "$REPO_ROOT/cores_bisect" "$APP_SRC/"
rm -rf "$APP_SRC/cores_bisect/__pycache__"
cp "$REPO_ROOT/ps5-cores-bisect.sh" "$REPO_ROOT/ps5-cores-unlock.sh" "$APP_SRC/"
chmod +x "$APP_SRC/ps5-cores-bisect.sh" "$APP_SRC/ps5-cores-unlock.sh"
cp "$REPO_ROOT/requirements.txt" "$REPO_ROOT/VERSION" "$APP_SRC/"
cp "$REPO_ROOT/images/ps5-cores-bisect.webp" "$REPO_ROOT/images/ps5-cores-bisect-128.png" "$APP_SRC/images/"

echo "==> Creating venv in $VENV_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet --upgrade -r "$APP_SRC/requirements.txt"

echo "==> Checking that PyQt6 loads in this venv"
if ! "$VENV_DIR/bin/python" -c "from PyQt6.QtWidgets import QApplication" 2>"$APP_DIR/import-check.log"; then
  echo "error: PyQt6 installed but failed to import - see $APP_DIR/import-check.log" >&2
  echo "       this is usually a missing system Qt/X11 library, for example libxcb-cursor0." >&2
  cat "$APP_DIR/import-check.log" >&2
  exit 1
fi
rm -f "$APP_DIR/import-check.log"

echo "==> Installing launcher: $LAUNCHER"
mkdir -p "$BIN_HOME"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
# Launched from a menu there is no terminal to see a crash on, so stdout/stderr always go to a log
# file too - check it first if the app ever fails to start (e.g. a bouncing launcher icon that
# never shows a window).
LOG="$APP_DIR/launch.log"
cd "$APP_SRC" && exec "$VENV_DIR/bin/python" -m cores_bisect --script "$APP_SRC/ps5-cores-bisect.sh" \
  --unlock-script "$APP_SRC/ps5-cores-unlock.sh" "\$@" >"\$LOG" 2>&1
EOF
chmod +x "$LAUNCHER"

echo "==> Installing desktop entry and icon"
mkdir -p "$(dirname "$DESKTOP_FILE")" "$ICON_DIR"
cp "$REPO_ROOT/images/ps5-cores-bisect-128.png" "$ICON_FILE"
rm -f "$DATA_HOME/icons/hicolor/512x512/apps/ps5-cores-bisect.png"   # the 512 px icon of before
# Use the icon's absolute path rather than the bare theme name: Bazzite's gamescope/Big Picture
# session (and some freshly-logged-in desktop sessions) look up app icons before the hicolor
# icon cache is rebuilt, which otherwise leaves a blank placeholder in the launcher.
sed -e "s#^Exec=.*#Exec=$LAUNCHER#" -e "s#^Icon=.*#Icon=$ICON_FILE#" \
  "$REPO_ROOT/packaging/common/ps5-cores-bisect.desktop" > "$DESKTOP_FILE"

# The separate unlock window of before: this window has it now.
if [ -e "$BIN_HOME/ps5-cores-unlock-gui" ] || [ -e "$DATA_HOME/ps5-cores-unlock-gui" ]; then
  echo "==> Removing the separate unlock window of earlier versions. This window has it now."
  bash "$SCRIPT_DIR/uninstall-gui.sh" >/dev/null
fi

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
command -v kbuildsycoca5 >/dev/null 2>&1 && kbuildsycoca5 --noincremental >/dev/null 2>&1 || true

cat <<EOF

Done. PS5 Core Unlock is installed for your user account only:
  - app + venv: $APP_DIR
  - launcher:   $LAUNCHER
  - menu entry: $DESKTOP_FILE

Launch it from your app menu, or run: $LAUNCHER
If it ever fails to open, for example a bouncing launcher icon that never shows a window, check:
  $APP_DIR/launch.log
To remove it again: bash "$SCRIPT_DIR/uninstall-bisect-gui.sh"
EOF
