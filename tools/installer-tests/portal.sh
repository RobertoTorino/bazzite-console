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
# to 1.0.0 put it) replaces that portal and keeps what it remembered. Bazzite Test's installer is a stub here; its
# own test is bazzite.sh. Runs with the shims from shims.sh (as CI does).
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME/bazzite-console-suite
release() {                                         # a portal release in folder $1, saying it is version $2
    mkdir -p "$1/bundled/ps5-bazzite-v0.0.0"
    (cd "$SUITE/portal" && tar --exclude='./tests' --exclude='__pycache__' -cf - .) | tar -xf - -C "$1"
    cp -r "$SUITE/core/bazzite_console_core" "$1/"
    printf '#!/bin/sh\nexit 0\n' > "$1/bundled/ps5-bazzite-v0.0.0/install.sh"
    echo 0.0.0 > "$1/bundled/ps5-bazzite-v0.0.0/VERSION"
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

echo "== 4. uninstall keeps the state, --purge removes it"
bash "$D/portal/install.sh" --uninstall > "$T/log4" 2>&1; rc=$?
check "exit 0, portal gone" "[ $rc -eq 0 ] && [ ! -e $D/portal ] && [ ! -e $HOME/.local/bin/bazzite-console-suite ]"
check "state kept" "[ -f $D/state/installed.json ]"
bash "$T/first/install.sh" --uninstall --purge > "$T/log5" 2>&1; rc=$?
check "--purge removes the state" "[ $rc -eq 0 ] && [ ! -e $D/state ]"

[ $fail -eq 0 ] && echo "Portal installer passed." || { echo "Portal installer FAILED (logs in $T)"; exit 1; }
