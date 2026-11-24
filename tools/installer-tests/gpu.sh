#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/gpu/install.sh: install from the checkout, Desktop icon on and off, the removal of PS5 GPU OC
# Bisect, a staged release, an unknown option, and uninstall. Runs with the shims from shims.sh (CI). The governor
# service and its config.toml are not the installer's: they are left alone.
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NEXUS=$SUITE                        # the repository: the Nexus tools (stage_app.py) and core/
T=/tmp/ps5-governor-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
APP=ps5-governor-manager
A=$D/$APP
printf '#!/bin/sh\necho "sudo called: $*" >&2\nexit 1\n' > "$T/shims/sudo"

echo "== 1. install from the suite checkout"
bash "$SUITE/apps/gpu/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "no sudo used" "! grep -q 'sudo called' $T/log1"
check "app copied" "[ -f $A/gpu_governor/__main__.py ] && [ -f $A/images/$APP.webp ] && [ -f $A/images/$APP-128.png ] && [ -f $A/requirements.txt ]"
check "the GPU sweep and its script" "[ -f $A/gpu_governor/sweep/app.py ] && [ -x $A/ps5-gpu-sweep.sh ]"
check "no caches copied" "! find $A -name __pycache__ | grep -q ."
check "own venv" "[ -x $A/venv/bin/python ]"
check "launcher" "grep -qF 'cd \"$A\" && exec \"$A/venv/bin/python\" -m gpu_governor' $HOME/.local/bin/$APP"
check "launcher executable" "[ -x $HOME/.local/bin/$APP ]"
check "menu entry" "grep -qx 'Exec=$HOME/.local/bin/$APP' $D/applications/$APP.desktop"
check "icon" "[ -f $D/icons/hicolor/128x128/apps/$APP.png ]"
check "desktop icon, executable" "[ -x $HOME/Desktop/$APP.desktop ]"

echo "== 2. reinstall without the Desktop icon"
bash "$SUITE/apps/gpu/install.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "desktop icon removed" "[ ! -e $HOME/Desktop/$APP.desktop ]"
check "menu entry kept" "[ -f $D/applications/$APP.desktop ]"

echo "== 2b. PS5 GPU OC Bisect goes, with its results"
OLD=ps5-gpu-oc-bisect
OPT=$T/opt
mkdir -p "$OPT/$OLD-v0.5.1" "$D/$OLD-app/venv" "$D/$OLD/logs" "$XDG_CONFIG_HOME/$OLD" "$HOME/.local/bin"
ln -sfn "$OLD-v0.5.1" "$OPT/$OLD"
touch "$HOME/.local/bin/$OLD-gui" "$D/applications/$OLD-gui.desktop" "$HOME/Desktop/$OLD-gui.desktop" "$D/$OLD/runs.tsv"
printf '#!/bin/sh\n"$@"\n' > "$T/shims/sudo"
PS5_OPT_DIR=$OPT bash "$SUITE/apps/gpu/install.sh" > "$T/log2b" 2>&1; rc=$?
printf '#!/bin/sh\necho "sudo called: $*" >&2\nexit 1\n' > "$T/shims/sudo"
check "exit 0" "[ $rc -eq 0 ]"
check "its copy in /opt gone" "[ ! -e $OPT/$OLD ] && [ ! -e $OPT/$OLD-v0.5.1 ]"
check "its launcher, menu entry and Desktop icon gone" "[ ! -e $HOME/.local/bin/$OLD-gui ] && [ ! -e $D/applications/$OLD-gui.desktop ] && [ ! -e $HOME/Desktop/$OLD-gui.desktop ]"
check "its venv, results and settings gone" "[ ! -e $D/$OLD-app ] && [ ! -e $D/$OLD ] && [ ! -e $XDG_CONFIG_HOME/$OLD ]"
PS5_OPT_DIR=$OPT bash "$SUITE/apps/gpu/install.sh" > "$T/log2c" 2>&1
check "without it, no sudo" "! grep -q 'sudo called' $T/log2c && ! grep -q 'OC Bisect' $T/log2c"

echo "== 3. install a staged release over it"
mkdir -p "$A/ps5_governor"   # a copy installed before the package's rename
rm -rf "$T/stage"; /usr/bin/python3 "$NEXUS/tools/stage_app.py" gpu "$T/stage" > /dev/null
check "manual bundled" "[ -f $T/stage/MANUAL.md ]"
echo "# release marker" >> "$T/stage/gpu_governor/__init__.py"
bash "$T/stage/install.sh" > "$T/log3" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "the release's files used" "grep -q 'release marker' $A/gpu_governor/__init__.py"
check "the package before the rename removed" "[ ! -e $A/ps5_governor ]"
check "venv kept" "[ -x $A/venv/bin/python ]"

echo "== 4. unknown option refused"
bash "$T/stage/install.sh" --bogus > "$T/log4" 2>&1; rc=$?
check "exit non-zero" "[ $rc -ne 0 ]"
check "says why" "grep -q 'unknown option: --bogus' $T/log4"

echo "== 5. uninstall"
bash "$T/stage/install.sh" --uninstall > "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "app and venv gone" "[ ! -e $A ]"
check "launcher, menu entry, icons gone" "[ ! -e $HOME/.local/bin/$APP ] && [ ! -e $D/applications/$APP.desktop ] && [ ! -e $D/icons/hicolor/128x128/apps/$APP.png ] && [ ! -e $HOME/Desktop/$APP.desktop ]"
check "governor config left alone" "grep -q 'config.toml and backups were left untouched' $T/log5"

echo "== 6. refusals, and uninstall --purge"
bash "$T/stage/install.sh" --purge > "$T/log6" 2>&1; rc=$?
check "--purge alone refused" "[ $rc -ne 0 ] && grep -q 'only goes with --uninstall' $T/log6"
fakeroot -- bash "$T/stage/install.sh" > "$T/log6" 2>&1; rc=$?
check "root refused" "[ $rc -ne 0 ] && grep -q 'not with sudo' $T/log6"
bash "$T/stage/install.sh" > "$T/log6" 2>&1
mkdir -p "$XDG_CONFIG_HOME/$APP" "$XDG_CONFIG_HOME/autostart" "$D/ps5-gpu-sweep" "$XDG_CONFIG_HOME/ps5-gpu-sweep"
touch "$XDG_CONFIG_HOME/$APP/profiles.json" "$XDG_CONFIG_HOME/autostart/$APP.desktop" "$D/ps5-gpu-sweep/runs.tsv" \
    "$XDG_CONFIG_HOME/autostart/ps5-gpu-sweep-resume.desktop"
bash "$T/stage/install.sh" --uninstall > "$T/log6" 2>&1
check "plain uninstall keeps settings, profiles and the sweep's results" "[ -f $XDG_CONFIG_HOME/$APP/profiles.json ] && [ -f $D/ps5-gpu-sweep/runs.tsv ]"
check "the sweep's resume entry goes" "[ ! -e $XDG_CONFIG_HOME/autostart/ps5-gpu-sweep-resume.desktop ]"
bash "$T/stage/install.sh" --uninstall --purge > "$T/log6" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "settings, profiles and start-at-login entry gone" "[ ! -e $XDG_CONFIG_HOME/$APP ] && [ ! -e $XDG_CONFIG_HOME/autostart/$APP.desktop ]"
check "the sweep's results and settings gone" "[ ! -e $D/ps5-gpu-sweep ] && [ ! -e $XDG_CONFIG_HOME/ps5-gpu-sweep ]"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 2 2b 2c 3 4 5 6; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
