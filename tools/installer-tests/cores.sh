#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/cores/install.sh: install from the checkout (root-owned versioned /opt copy, one venv, one
# launcher: CPU Tools' one window), the separate unlock window of before removed, --no-desktop-shortcut, a staged
# release replacing it, the refusal to run as root, and uninstall with and without --purge. Runs with the shims from shims.sh (CI).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NEXUS=$SUITE                        # the repository: the Nexus tools (stage_app.py) and core/
T=/tmp/ps5-cores-bisect-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
V=$(tr -d '[:space:]' < "$SUITE/apps/cores/VERSION")
APP=ps5-cores-bisect
L=$T/opt/$APP

echo "== 1. install the app from the suite checkout"
bash "$SUITE/apps/cores/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "versioned /opt copy" "[ -f $T/opt/$APP-v$V/ps5-cores-bisect.sh ]"
check "symlink" "[ \"\$(readlink $L)\" = $APP-v$V ]"
check "scripts executable" "[ -x $L/ps5-cores-bisect.sh ] && [ -x $L/ps5-cores-unlock.sh ]"
check "no staging folder left" "! ls -d $T/opt/.$APP-* >/dev/null 2>&1"
check "no caches copied" "! find $L/ -name __pycache__ | grep -q ."
check "own venv" "[ -x $D/$APP-app/venv/bin/python ]"
check "bisect launcher" "grep -qF 'exec \"$D/$APP-app/venv/bin/python\" -m cores_bisect' $HOME/.local/bin/ps5-cores-bisect-gui"
check "launcher cds into the /opt link" "grep -q \"cd \\\"$L\\\"\" $HOME/.local/bin/ps5-cores-bisect-gui"
check "menu entry" "grep -qx 'Exec=$HOME/.local/bin/ps5-cores-bisect-gui' $D/applications/ps5-cores-bisect-gui.desktop && grep -qx 'Name=PS5 CPU Tools' $D/applications/ps5-cores-bisect-gui.desktop"
check "icon from /opt" "grep -qx 'Icon=$L/images/$APP-128.png' $D/applications/ps5-cores-bisect-gui.desktop && [ -f $L/images/$APP.webp ]"
check "desktop icon, executable" "[ -x $HOME/Desktop/ps5-cores-bisect-gui.desktop ]"
check "no unlock window" "[ ! -e $HOME/.local/bin/ps5-cores-unlock-gui ] && [ ! -e $D/applications/ps5-cores-unlock.desktop ] && [ ! -e $L/cores_unlock ]"

echo "== 2. an update removes the separate unlock window of before; without the Desktop icon"
touch "$HOME/.local/bin/ps5-cores-unlock-gui" "$D/applications/ps5-cores-unlock.desktop" "$HOME/Desktop/ps5-cores-unlock.desktop"
bash "$SUITE/apps/cores/install.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "unlock launcher and entries removed" "[ ! -e $HOME/.local/bin/ps5-cores-unlock-gui ] && [ ! -e $D/applications/ps5-cores-unlock.desktop ] && [ ! -e $HOME/Desktop/ps5-cores-unlock.desktop ]"
check "launcher kept, Desktop icon removed" "[ -x $HOME/.local/bin/ps5-cores-bisect-gui ] && [ ! -e $HOME/Desktop/ps5-cores-bisect-gui.desktop ]"
bash "$SUITE/apps/cores/install.sh" --bisect-only > "$T/log2b" 2>&1; rc=$?
check "--bisect-only is gone" "[ $rc -ne 0 ] && grep -q 'Unknown option' $T/log2b"

echo "== 3. install a staged release with a new version"
rm -rf "$T/stage"; /usr/bin/python3 "$NEXUS/tools/stage_app.py" cores "$T/stage" > /dev/null
check "manual bundled" "[ -f $T/stage/MANUAL.md ]"
echo 9.9.9 > "$T/stage/VERSION"
bash "$T/stage/install.sh" > "$T/log3" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "new version linked" "[ \"\$(readlink $L)\" = $APP-v9.9.9 ]"
check "old version removed" "[ ! -d $T/opt/$APP-v$V ]"
check "launcher back" "[ -x $HOME/.local/bin/ps5-cores-bisect-gui ]"

echo "== 4. refuses to run as root"
fakeroot -- bash "$T/stage/install.sh" > "$T/log4" 2>&1; rc=$?
check "exit non-zero" "[ $rc -ne 0 ]"
check "says why" "grep -q 'not with sudo' $T/log4"

echo "== 5. uninstall keeps results and settings"
mkdir -p "$D/$APP" "$XDG_CONFIG_HOME/$APP" && touch "$D/$APP/run.log" "$XDG_CONFIG_HOME/$APP/settings.ini"
bash "$T/stage/install.sh" --uninstall > "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "/opt copy gone" "[ ! -e $L ] && ! ls -d $T/opt/$APP-v* >/dev/null 2>&1"
check "venv gone" "[ ! -e $D/$APP-app ]"
check "launchers, menu entries and icons gone" "! ls $HOME/.local/bin/ps5-cores-* $D/applications/ps5-cores-* $HOME/Desktop/ps5-cores-* 2>/dev/null | grep -q ."
check "results and settings kept" "[ -f $D/$APP/run.log ] && [ -f $XDG_CONFIG_HOME/$APP/settings.ini ]"

echo "== 6. uninstall --purge"
bash "$SUITE/apps/cores/install.sh" > "$T/log6" 2>&1 &&
    bash "$SUITE/apps/cores/install.sh" --uninstall --purge >> "$T/log6" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "results and settings gone" "[ ! -e $D/$APP ] && [ ! -e $XDG_CONFIG_HOME/$APP ]"
bash "$SUITE/apps/cores/install.sh" --purge > "$T/log6b" 2>&1; rc=$?
check "--purge alone refused" "[ $rc -ne 0 ] && grep -q 'only goes with --uninstall' $T/log6b"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 2 3 4 5 6; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
