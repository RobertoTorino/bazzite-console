#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/compute's installer as the portal runs it (packaging/bazzite/install-bisect-gui.sh: one window for
# the bisect and the unlock): from the checkout, without the Desktop icon, over the separate unlock window of before
# (which it removes), from a staged release, an unknown option, and the uninstallers, which keep the bisect results;
# then the app's install.sh, which runs them, with its options. Runs with the shims from shims.sh (CI).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NEXUS=$SUITE                        # the repository: the Nexus tools (stage_app.py) and core/
T=/tmp/ps5-cu-bisect-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
B=$D/ps5-bisect-gui
U=$D/ps5-unlock-cu-gui            # the separate unlock window of before
L=$HOME/.local/bin/ps5-bisect-gui
printf '#!/bin/sh\necho "sudo called: $*" >&2\nexit 1\n' > "$T/shims/sudo"
old_unlock() {   # what the separate unlock window of before left on the computer
    mkdir -p "$U/app" "$D/applications" "$D/icons/hicolor/128x128/apps" "$HOME/Desktop"
    touch "$HOME/.local/bin/ps5-unlock-cu-gui" "$D/applications/ps5-cu-unlock.desktop" \
        "$D/icons/hicolor/128x128/apps/ps5-cu-bisect-unlock.png" "$HOME/Desktop/ps5-cu-unlock.desktop"
}

echo "== 1. install from the suite checkout"
bash "$SUITE/apps/compute/packaging/bazzite/install-bisect-gui.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "no sudo used" "! grep -q 'sudo called' $T/log1"
check "app copied, both scripts" "[ -f $B/app/cu_bisect/__main__.py ] && [ -f $B/app/cu_bisect/session.py ] && [ -x $B/app/ps5-cu-bisect.sh ] && [ -x $B/app/ps5-cu-unlock.sh ] && [ -f $B/app/images/ps5-cu-bisect.webp ]"
check "no caches copied" "! find $B -name __pycache__ | grep -q ."
check "one venv" "[ -x $B/venv/bin/python ] && [ ! -e $U ]"
check "launcher passes both scripts" "grep -qF 'exec \"$B/venv/bin/python\" -m cu_bisect --script \"$B/app/ps5-cu-bisect.sh\"' $L && grep -qF -- '--unlock-script \"$B/app/ps5-cu-unlock.sh\"' $L"
check "launcher executable" "[ -x $L ]"
check "menu entry" "grep -qx 'Exec=$L' $D/applications/ps5-cu-bisect.desktop && [ ! -e $D/applications/ps5-cu-unlock.desktop ]"
check "icon by path" "grep -qx 'Icon=$D/icons/hicolor/128x128/apps/ps5-cu-bisect.png' $D/applications/ps5-cu-bisect.desktop"
check "desktop icon, executable" "[ -x $HOME/Desktop/ps5-cu-bisect.desktop ]"

echo "== 2. reinstall without the Desktop icon"
bash "$SUITE/apps/compute/packaging/bazzite/install-bisect-gui.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "desktop icon removed" "[ ! -e $HOME/Desktop/ps5-cu-bisect.desktop ]"
check "menu entry kept" "[ -f $D/applications/ps5-cu-bisect.desktop ]"

echo "== 3. update over the separate unlock window of before"
old_unlock
bash "$SUITE/apps/compute/packaging/bazzite/install-bisect-gui.sh" > "$T/log3" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "says it removes it" "grep -q 'separate unlock window of before' $T/log3"
check "its app, launcher, menu entry, icon and Desktop icon gone" "! ls $U $HOME/.local/bin/ps5-unlock-cu-gui $D/applications/ps5-cu-unlock.desktop $D/icons/hicolor/*/apps/ps5-cu-bisect-unlock.png $HOME/Desktop/ps5-cu-unlock.desktop 2>/dev/null | grep -q ."
check "this app still installed" "[ -x $L ] && [ -f $D/applications/ps5-cu-bisect.desktop ]"

echo "== 4. install a staged release over it"
mkdir -p "$B/app/ps5_bisect_gui"   # a copy installed before the package's rename
rm -rf "$T/stage"; /usr/bin/python3 "$NEXUS/tools/stage_app.py" compute "$T/stage" > /dev/null
check "manual bundled" "[ -f $T/stage/MANUAL.md ]"
check "no separate unlock package or installer" "[ ! -e $T/stage/cu_unlock ] && [ ! -e $T/stage/packaging/bazzite/install-gui.sh ]"
echo "# release marker" >> "$T/stage/ps5-cu-unlock.sh"
bash "$T/stage/packaging/bazzite/install-bisect-gui.sh" > "$T/log4" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "the release's files used" "grep -q 'release marker' $B/app/ps5-cu-unlock.sh"
check "the package before the rename removed" "[ ! -e $B/app/ps5_bisect_gui ]"

echo "== 5. unknown option refused"
bash "$T/stage/packaging/bazzite/install-bisect-gui.sh" --bogus > "$T/log5" 2>&1; rc=$?
check "exit non-zero" "[ $rc -ne 0 ]"
check "says why" "grep -q 'unknown option: --bogus' $T/log5"

echo "== 6. uninstall, keeping the results"
mkdir -p "$D/ps5-cu-bisect" && touch "$D/ps5-cu-bisect/state"
bash "$T/stage/packaging/bazzite/uninstall-bisect-gui.sh" > "$T/log6" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "app and venv gone" "[ ! -e $B ]"
check "launcher, menu entry, icon gone" "! ls $L $D/applications/ps5-cu-*.desktop $D/icons/hicolor/*/apps/ps5-cu-* $HOME/Desktop/ps5-cu-*.desktop 2>/dev/null | grep -q ."
check "bisect results kept" "[ -f $D/ps5-cu-bisect/state ]"

echo "== 7. the app's install.sh: install, refusals, uninstall, --purge"
bash "$T/stage/install.sh" > "$T/log7" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "installed, with the Desktop icon" "[ -x $L ] && [ -x $HOME/Desktop/ps5-cu-bisect.desktop ]"
bash "$T/stage/install.sh" --no-desktop-shortcut > "$T/log7b" 2>&1; rc=$?
check "--no-desktop-shortcut passed on" "[ $rc -eq 0 ] && [ ! -e $HOME/Desktop/ps5-cu-bisect.desktop ] && [ -f $D/applications/ps5-cu-bisect.desktop ]"
bash "$T/stage/install.sh" --unlock-only > "$T/log7c" 2>&1; rc=$?
check "--unlock-only is gone" "[ $rc -ne 0 ] && grep -q 'Unknown option: --unlock-only' $T/log7c"
bash "$T/stage/install.sh" --purge > "$T/log7c" 2>&1; rc=$?
check "--purge alone refused" "[ $rc -ne 0 ] && grep -q 'only goes with --uninstall' $T/log7c"
fakeroot -- bash "$T/stage/install.sh" > "$T/log7c" 2>&1; rc=$?
check "root refused" "[ $rc -ne 0 ] && grep -q 'not with sudo' $T/log7c"
fakeroot -- bash "$T/stage/packaging/bazzite/install-bisect-gui.sh" > "$T/log7c" 2>&1; rc=$?
check "root refused by the app's installer too" "[ $rc -ne 0 ] && grep -q 'not with sudo' $T/log7c"
mkdir -p "$XDG_CONFIG_HOME/ps5-cu-bisect" "$XDG_CONFIG_HOME/autostart"
touch "$XDG_CONFIG_HOME/ps5-cu-bisect/ps5-bisect-gui.conf" "$XDG_CONFIG_HOME/autostart/ps5-cu-bisect-watch.desktop" \
    "$XDG_CONFIG_HOME/autostart/ps5-cu-tools-resume.desktop"
old_unlock
bash "$T/stage/install.sh" --uninstall > "$T/log7d" 2>&1; rc=$?
check "uninstall removes the app, the old unlock window and the resume entry, keeps results and settings" "[ $rc -eq 0 ] && [ ! -e $XDG_CONFIG_HOME/autostart/ps5-cu-tools-resume.desktop ] && [ ! -e $B ] && [ ! -e $U ] && [ ! -e $HOME/.local/bin/ps5-unlock-cu-gui ] && [ -f $D/ps5-cu-bisect/state ] && [ -d $XDG_CONFIG_HOME/ps5-cu-bisect ]"
bash "$T/stage/install.sh" --uninstall --purge > "$T/log7d" 2>&1; rc=$?
check "--purge removes results, settings and the autostart entry" "[ $rc -eq 0 ] && [ ! -e $D/ps5-cu-bisect ] && [ ! -e $XDG_CONFIG_HOME/ps5-cu-bisect ] && [ ! -e $XDG_CONFIG_HOME/autostart/ps5-cu-bisect-watch.desktop ] && [ ! -e $XDG_CONFIG_HOME/autostart/ps5-cu-tools-resume.desktop ]"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 2 3 4 5 6 7 7b 7c 7d; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
