#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# tools/check-release.sh: a test's install is marked and removed again, the machine's own install is kept.
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
T=/tmp/bazzite-console-release-check-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
CHECK="$SUITE/tools/check-release.sh"
BIN=$HOME/.local/bin
MARK=$XDG_DATA_HOME/bazzite-console-suite/portal/TEST-INSTALL
run() { "$CHECK" "$@" > "$T/out.log" 2>&1; }

echo "== 1. a test on a machine without the suite"
run status
check "nothing is installed" "grep -q 'Nothing of the suite is installed' $T/out.log"
run local --no-start; rc=$?
check "the test installs the portal and Bazzite Test" "[ $rc -eq 0 ] && [ -x $BIN/bazzite-console-suite ] && [ -x $BIN/bazzite-test ]"
check "the install is marked as a test's" "grep -q '^the checkout, ' $MARK"
run status
check "status says it is a test install" "grep -q 'Portal .*: a test install (the checkout, ' $T/out.log"
check "status lists Bazzite Test" "grep -q 'Bazzite Test (bazzite)' $T/out.log"

echo "== 2. remove"
bash "$SUITE/apps/fan/install.sh" --no-desktop-shortcut > "$T/fan.log" 2>&1
check "an app is installed beside it" "[ -x $BIN/ps5-fan-control ]"
run remove; rc=$?
check "remove succeeds" "[ $rc -eq 0 ]"
check "the portal, Bazzite Test and the app are gone" \
    "[ ! -e $BIN/bazzite-console-suite ] && [ ! -e $BIN/bazzite-test ] && [ ! -e $BIN/ps5-fan-control ]"
check "the suite's folder is gone" "[ ! -e $XDG_DATA_HOME/bazzite-console-suite ]"
check "Bazzite Test left /opt" "[ ! -e $T/opt/bazzite-test ]"

echo "== 3. the machine's own install stays"
run local --no-start --keep
check "--keep leaves no mark" "[ -x $BIN/bazzite-console-suite ] && [ ! -e $MARK ]"
run local --no-start
check "a test over the machine's own install leaves no mark" "[ ! -e $MARK ]"
check "and says that it stays" "grep -q 'everything stays installed' $T/out.log"
run status
check "status says it is the machine's own" "grep -q \"the machine's own install\" $T/out.log"

echo "== 4. options"
run local --purge
check "--purge only goes with remove" "grep -q 'only goes with remove' $T/out.log"
run remove --purge; rc=$?
check "remove --purge succeeds" "[ $rc -eq 0 ] && [ ! -e $BIN/bazzite-console-suite ]"

[ $fail -eq 0 ] && echo "ALL OK" || { cat "$T/out.log"; exit 1; }
exit "$fail"
