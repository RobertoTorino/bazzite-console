#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Check the portal installer options without installing or changing the host.
set -euo pipefail
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
T=/tmp/bazzite-console-portal-test
mkdir -p "$T/home"
export HOME="$T/home" XDG_DATA_HOME="$T/home/.local/share" XDG_CONFIG_HOME="$T/home/.config"
if [ "$(id -u)" -eq 0 ]; then
    if bash "$SUITE/portal/install.sh" --help >/dev/null 2>&1; then
        echo "The installer accepted root." >&2
        exit 1
    fi
else
    bash "$SUITE/portal/install.sh" --help >/dev/null
fi
if bash "$SUITE/portal/install.sh" --purge >/dev/null 2>&1; then
    echo "The installer accepted --purge without --uninstall." >&2
    exit 1
fi
echo "Portal installer options passed."
[ "$(id -u)" -ne 0 ] || exit 0

# An install, and the portal's own update: a release unpacked inside the installed portal's folder (where portals up
# to 1.0.0 put it) replaces that portal and keeps what it remembered. Board Test's installer is a stub here; its
# own test is board.sh. Runs with the shims from shims.sh (as CI does).
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME/bazzite-console-suite
release() {                                         # a portal release in folder $1, saying it is version $2
    mkdir -p "$1/bundled/ps5-board-v0.0.0"
    (cd "$SUITE/portal" && tar --exclude='./tests' --exclude='__pycache__' -cf - .) | tar -xf - -C "$1"
    cp -r "$SUITE/core/bazzite_console_core" "$1/"
    printf '#!/bin/sh\nexit 0\n' > "$1/bundled/ps5-board-v0.0.0/install.sh"
    echo 0.0.0 > "$1/bundled/ps5-board-v0.0.0/VERSION"
    echo "$2" > "$1/VERSION"
}

echo "== 1. install a release"
release "$T/first" 9.9.1
bash "$T/first/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "portal copied" "[ -f $D/portal/bazzite_console_portal/__main__.py ] && [ \"\$(cat $D/portal/VERSION)\" = 9.9.1 ]"
check "core bundled" "[ -f $D/portal/bazzite_console_core/theme.py ]"
check "launcher" "grep -qF 'venv/bin/python\" -m bazzite_console_portal' $HOME/.local/bin/bazzite-console-suite"
check "nothing left of the staging folder" "[ ! -e $D/.portal.new ]"

echo "== 2. the portal's own update, from inside the installed portal, with state of a portal up to 1.0.0"
echo '{"fan": "ps5-fan-v1.0.0"}' > "$D/portal/installed.json"
echo picture > "$D/portal/wallpaper.png"
echo '{"saved": []}' > "$D/portal/wallpapers.json"
mkdir -p "$D/portal/releases/ps5-fan-v1.0.0" "$D/portal/portal-update"
release "$D/portal/portal-update/ps5-portal-v9.9.2" 9.9.2
(cd "$D/portal/portal-update/ps5-portal-v9.9.2" && ./install.sh) > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "the new portal is installed" "[ \"\$(cat $D/portal/VERSION)\" = 9.9.2 ] && [ -f $D/portal/bazzite_console_portal/__main__.py ]"
check "what it installed is remembered" "grep -q ps5-fan-v1.0.0 $D/state/installed.json"
check "the wallpaper and its history are kept" "[ -f $D/state/wallpaper.png ] && [ -f $D/state/wallpapers.json ]"
check "the apps' releases are kept" "[ -d $D/state/releases/ps5-fan-v1.0.0 ]"
check "no state left in the program folder" "[ ! -e $D/portal/installed.json ] && [ ! -e $D/portal/portal-update ]"

echo "== 3. an update from the state folder (portals after 1.0.0) keeps the state"
release "$D/state/portal-update/ps5-portal-v9.9.3" 9.9.3
(cd "$D/state/portal-update/ps5-portal-v9.9.3" && ./install.sh) > "$T/log3" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "the new portal is installed" "[ \"\$(cat $D/portal/VERSION)\" = 9.9.3 ]"
check "the state is untouched" "grep -q ps5-fan-v1.0.0 $D/state/installed.json && [ -f $D/state/wallpaper.png ]"

echo "== 4. uninstall keeps the wallpaper, drops the state of apps that are gone; --purge removes the rest"
bash "$D/portal/install.sh" --uninstall > "$T/log4" 2>&1; rc=$?
check "exit 0, portal gone" "[ $rc -eq 0 ] && [ ! -e $D/portal ] && [ ! -e $HOME/.local/bin/bazzite-console-suite ]"
check "wallpaper kept" "[ -f $D/state/wallpaper.png ]"
check "record and release of the app that is gone dropped" "[ ! -e $D/state/installed.json ] && [ ! -e $D/state/releases ]"
bash "$T/first/install.sh" --uninstall --purge > "$T/log5" 2>&1; rc=$?
check "--purge removes the state" "[ $rc -eq 0 ] && [ ! -e $D/state ] && [ ! -e $D ]"

echo "== 5. uninstall asks about each other app: cancel, then skip one and uninstall the other, and Board Test"
# Two apps as the portal installs them from the checkout, and Board Test as a stub that notes its options.
bash "$T/first/install.sh" > "$T/log6" 2>&1
for app in overlay ssd; do
    /usr/bin/python3 "$SUITE/tools/stage_app.py" "$app" "$D/state/releases/local-$app" > /dev/null
    (cd "$D/state/releases/local-$app" && bash install.sh --no-desktop-shortcut) >> "$T/log6" 2>&1
done
echo '{"overlay": "local", "ssd": "local"}' > "$D/state/installed.json"
mkdir -p "$T/opt/ps5-board-test"
printf '#!/bin/sh\necho "$*" > %s/bt-args\n' "$T" > "$T/opt/ps5-board-test/install.sh"
installed() { [ -x "$HOME/.local/bin/$1" ]; }
check "the apps are installed" "installed ps5-system-overlay && installed ps5-ssd-check"
printf 'y\nc\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$D/portal/install.sh" --uninstall >> "$T/log6" 2>&1; rc=$?
check "cancel: exit 1, nothing removed" "[ $rc -eq 1 ] && installed ps5-system-overlay && installed ps5-ssd-check && installed bazzite-console-suite && [ ! -e $T/bt-args ]"
check "cancel: says so" "grep -q 'Canceled: nothing was uninstalled.' $T/log6"
printf 'x\ns\ny\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$D/portal/install.sh" --uninstall >> "$T/log6" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "asked about each app, in the manifest's order" "[ \$(grep -o 'Uninstall PS5 SSD Check?' $T/log6 | wc -l) -eq 3 ] && [ \$(grep -o 'Uninstall PS5 System Overlay?' $T/log6 | wc -l) -eq 2 ]"
check "skipped app stays, with its record and release" "installed ps5-ssd-check && [ -d $D/state/releases/local-ssd ] && grep -q ssd $D/state/installed.json"
check "chosen app gone, with its record and release" "! installed ps5-system-overlay && [ ! -e $D/state/releases/local-overlay ] && ! grep -q overlay $D/state/installed.json"
check "Board Test uninstalled with its own installer" "[ \"\$(cat $T/bt-args)\" = --uninstall ]"
check "portal gone" "! installed bazzite-console-suite && [ ! -e $D/portal ]"
check "mentions what is left" "grep -q 'Still installed: ps5-ssd-check' $T/log6"

echo "== 6. --uninstall --all --purge: one confirmation for the whole suite"
bash "$T/first/install.sh" > "$T/log7" 2>&1
bash "$T/first/install.sh" --uninstall --all < /dev/null >> "$T/log7" 2>&1; rc=$?
check "without a terminal: refused, nothing removed" "[ $rc -ne 0 ] && grep -q 'needs a terminal' $T/log7 && installed ps5-ssd-check && installed bazzite-console-suite"
printf 'n\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$T/first/install.sh" --uninstall --all >> "$T/log7" 2>&1; rc=$?
check "no: canceled, nothing removed" "[ $rc -eq 1 ] && installed ps5-ssd-check && installed bazzite-console-suite"
check "the warning names the app" "grep -q 'WARNING: --all removes the whole suite from this computer: PS5 SSD Check, with the portal and Board Test.' $T/log7"
printf 'y\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$T/first/install.sh" --uninstall --all --purge >> "$T/log7" 2>&1; rc=$?
check "yes: exit 0, asked once" "[ $rc -eq 0 ] && ! grep -q 'Uninstall PS5 SSD Check?' $T/log7"
check "everything gone" "! installed ps5-ssd-check && ! installed bazzite-console-suite && [ ! -e $D ]"
check "Board Test purged" "[ \"\$(cat $T/bt-args)\" = '--uninstall --purge' ]"
rm -f "$T/opt/ps5-board-test/install.sh"; rmdir "$T/opt/ps5-board-test"

echo "== 7. nothing installed: says so and removes nothing"
bash "$T/first/install.sh" --uninstall --purge > "$T/log8" 2>&1; rc=$?
check "exit 0, says so" "[ $rc -eq 0 ] && grep -q 'Bazzite Console Suite is not installed: nothing to remove.' $T/log8 && [ \$(wc -l < $T/log8) -eq 1 ]"

[ $fail -eq 0 ] && echo "Portal installer passed." || { echo "Portal installer FAILED (logs in $T)"; exit 1; }
