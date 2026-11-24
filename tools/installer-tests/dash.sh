#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise dev/dash/install.sh, Nexus Dashboard for PS5's installer: the launcher, menu entry and Desktop icon point at
# this checkout, --no-desktop-shortcut drops the icon, root and unknown options are refused, uninstall leaves the
# checkout alone and keeps the settings, --purge removes them. Runs with the shims from shims.sh (CI).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
NEXUS=$SUITE                        # the repository: dev/ and core/
A=$NEXUS/dev/dash
T=/tmp/bazzite-console-nexus-dashboard-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
APP=nexus-dashboard-ps5
OLD=nexus-dashboard                  # the name both suites shared until 24-11-2026
L=$HOME/.local/bin/$APP
M=$XDG_DATA_HOME/applications/$APP.desktop
I=$HOME/Desktop/$APP.desktop

echo "== 1. install"
mkdir -p "$HOME/.local/bin" "$XDG_DATA_HOME/applications" "$HOME/Desktop"
bash "$A/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "launcher runs this checkout's run.sh" "[ -x $L ] && grep -qF 'exec \"$A/run.sh\"' $L"
check "menu entry" "grep -qx 'Exec=$L' $M && grep -qx 'Icon=$A/images/nexus-dashboard-128.png' $M && grep -qx 'StartupWMClass=$APP' $M"
check "the icon exists" "[ -f $A/images/nexus-dashboard.webp ] && [ -f $A/images/nexus-dashboard-128.png ]"
check "desktop icon, executable" "[ -x $I ]"
check "launcher passes its arguments" "$L --help | grep -q -- 'install.sh'"

echo "== 1b. the old shared name goes when it starts this checkout, and stays when it starts another"
printf '#!/usr/bin/env bash\nexec "%s/run.sh" "$@"\n' "$A" > "$HOME/.local/bin/$OLD"
touch "$XDG_DATA_HOME/applications/$OLD.desktop" "$HOME/Desktop/$OLD.desktop"
bash "$A/install.sh" > "$T/log1b" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "this checkout's old launcher, menu entry and icon gone" "[ ! -e $HOME/.local/bin/$OLD ] && [ ! -e $XDG_DATA_HOME/applications/$OLD.desktop ] && [ ! -e $HOME/Desktop/$OLD.desktop ]"
printf '#!/usr/bin/env bash\nexec "/elsewhere/dev/dash/run.sh" "$@"\n' > "$HOME/.local/bin/$OLD"
touch "$XDG_DATA_HOME/applications/$OLD.desktop"
bash "$A/install.sh" > "$T/log1c" 2>&1
check "another checkout's old entry stays" "[ -f $HOME/.local/bin/$OLD ] && [ -f $XDG_DATA_HOME/applications/$OLD.desktop ]"
rm -f "$HOME/.local/bin/$OLD" "$XDG_DATA_HOME/applications/$OLD.desktop"

echo "== 2. again without the Desktop icon"
bash "$A/install.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "desktop icon removed, menu entry kept" "[ ! -e $I ] && [ -f $M ]"

echo "== 3. refusals"
fakeroot -- bash "$A/install.sh" > "$T/log3" 2>&1; rc=$?
check "root refused" "[ $rc -ne 0 ] && grep -q 'not with sudo' $T/log3"
bash "$A/install.sh" --bogus > "$T/log3b" 2>&1; rc=$?
check "unknown option refused" "[ $rc -ne 0 ] && grep -q 'Unknown option: --bogus' $T/log3b"

echo "== 4. uninstall"
bash "$A/install.sh" --uninstall > "$T/log4" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "launcher, menu entry and icon gone" "[ ! -e $L ] && [ ! -e $M ] && [ ! -e $I ]"
check "checkout untouched" "[ -x $A/run.sh ] && [ -f $A/install.sh ]"

echo "== 5. --purge"
bash "$A/install.sh" --purge > "$T/log5" 2>&1; rc=$?
check "--purge alone refused" "[ $rc -ne 0 ] && grep -q 'only goes with --uninstall' $T/log5"
bash "$A/install.sh" > "$T/log5" 2>&1
mkdir -p "$XDG_CONFIG_HOME/$APP" && touch "$XDG_CONFIG_HOME/$APP/$APP.ini"
bash "$A/install.sh" --uninstall > "$T/log5" 2>&1
check "plain uninstall keeps the settings" "[ -f $XDG_CONFIG_HOME/$APP/$APP.ini ]"
bash "$A/install.sh" --uninstall --purge > "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "settings gone, checkout untouched" "[ ! -e $XDG_CONFIG_HOME/$APP ] && [ -x $A/run.sh ]"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 1b 1c 2 3 3b 4 5; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
