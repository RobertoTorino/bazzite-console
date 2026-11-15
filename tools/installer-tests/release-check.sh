#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# tools/check-release.sh: a test's install is marked and removed again, the machine's own install is kept; status and
# remove, with and without --purge.
# Runs with the shims from shims.sh (CI).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
T=/tmp/bazzite-console-release-check-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
CHECK="$SUITE/tools/check-release.sh"
BIN=$HOME/.local/bin
MARK=$XDG_DATA_HOME/bazzite-console-suite/TEST-INSTALL
STATE=$XDG_DATA_HOME/bazzite-console-suite/state
run() { "$CHECK" "$@" > "$T/out.log" 2>&1; }

echo "== 1. a test on a machine without the suite"
run status
check "nothing is installed" "grep -q 'Nothing of the suite is installed' $T/out.log"
run local --no-start; rc=$?
check "the test installs the portal and Board Test" "[ $rc -eq 0 ] && [ -x $BIN/bazzite-console-suite ] && [ -x $BIN/ps5-board-test ]"
check "the install is marked as a test's" "grep -q '^the checkout, ' $MARK"
run status
check "status says it is a test install" "grep -q 'Portal [0-9.]*: a test install (the checkout, ' $T/out.log"
check "status lists Board Test" "grep -q 'PS5 Board Test (board)' $T/out.log"

echo "== 2. remove"
bash "$SUITE/apps/ssd/install.sh" --no-desktop-shortcut > "$T/ssd.log" 2>&1
check "an app is installed beside it" "[ -x $BIN/ps5-ssd-check ]"
mkdir -p "$STATE" && echo '{}' > "$STATE/installed.json"     # what a portal that was opened remembers
run remove; rc=$?
check "remove succeeds" "[ $rc -eq 0 ]"
check "the portal, Board Test and the app are gone" \
    "[ ! -e $BIN/bazzite-console-suite ] && [ ! -e $BIN/ps5-board-test ] && [ ! -e $BIN/ps5-ssd-check ]"
check "the suite's folder is gone, with what the test's portal remembered" "[ ! -e $XDG_DATA_HOME/bazzite-console-suite ]"
check "Board Test left /opt" "[ ! -e $T/opt/ps5-board-test ]"

echo "== 3. the test removes itself when the portal closes"
run local; rc=$?                         # the shims' portal starts and closes at once
check "the test ends well" "[ $rc -eq 0 ] && grep -q 'The portal is closed: removing the test install' $T/out.log"
check "nothing of the suite is left" \
    "[ ! -e $BIN/bazzite-console-suite ] && [ ! -e $BIN/ps5-board-test ] && [ ! -e $XDG_DATA_HOME/bazzite-console-suite ]"

echo "== 4. the machine's own install stays"
run local --no-start --keep
check "--keep leaves no mark" "[ -x $BIN/bazzite-console-suite ] && [ ! -e $MARK ]"
run local --no-start
check "a test over the machine's own install leaves no mark" "[ ! -e $MARK ]"
check "and says that it stays" "grep -q 'everything stays installed' $T/out.log"
run status
check "status says it is the machine's own" "grep -q \"the machine's own install\" $T/out.log"
rm -f "$MARK"; run local --no-start --keep; run status
echo "the checkout, 01-01-2026 00:00" > "$MARK"; echo 1 >> "$MARK"   # a mark an install by hand made stale
run status
check "a mark that no longer names the launcher is no test install" "grep -q \"the machine's own install\" $T/out.log"

run local; rc=$?
check "a test over it starts the portal and keeps everything" "[ $rc -eq 0 ] && [ -x $BIN/bazzite-console-suite ] &&
    ! grep -q 'removing the test install' $T/out.log"

echo "== 5. options"
run local --purge
check "--purge only goes with remove" "grep -q 'only goes with remove' $T/out.log"
mkdir -p "$HOME/.config/bazzite-console-suite" && echo x > "$HOME/.config/bazzite-console-suite/settings.ini"
run remove; rc=$?
check "remove keeps the portal's settings" \
    "[ $rc -eq 0 ] && [ ! -e $BIN/bazzite-console-suite ] && [ -f $HOME/.config/bazzite-console-suite/settings.ini ]"
run local --no-start --keep
bash "$SUITE/apps/ssd/install.sh" --no-desktop-shortcut > "$T/ssd.log" 2>&1
mkdir -p "$HOME/.config/ps5-ssd-check" && echo x > "$HOME/.config/ps5-ssd-check/settings.ini"
run remove --purge; rc=$?
check "remove --purge succeeds" "[ $rc -eq 0 ] && [ ! -e $BIN/bazzite-console-suite ] && [ ! -e $BIN/ps5-ssd-check ]"
check "and removes the settings and the suite's folder" "[ ! -e $HOME/.config/ps5-ssd-check ] &&
    [ ! -e $HOME/.config/bazzite-console-suite ] && [ ! -e $XDG_DATA_HOME/bazzite-console-suite ]"

[ $fail -eq 0 ] && echo "ALL OK" || { cat "$T/out.log"; exit 1; }
exit "$fail"
