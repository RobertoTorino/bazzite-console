#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/kytyps5/install.sh: install from the checkout (core bundled, shared venv, the run wrapper,
# no sudo), a staged release replacing it, the refusals, uninstall with another venv user (the installed
# KytyPS5-Native removed; its own folders, the games and the settings kept) and --purge as the last venv user (the
# settings removed).
# Runs with the shims from shims.sh (CI).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NEXUS=$SUITE                        # the repository: the Nexus tools (stage_app.py) and core/
T=/tmp/ps5-kytyps5-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
APP=ps5-kytyps5
A=$D/$APP/app
RUN=$HOME/.local/bin/ps5-kytyps5-run
# sudo must never be needed: make it fail loudly.
printf '#!/bin/sh\necho "sudo called: $*" >&2\nexit 1\n' > "$T/shims/sudo"

echo "== 1. install from the suite checkout"
bash "$SUITE/apps/kytyps5/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "no sudo used" "! grep -q 'sudo called' $T/log1 && [ -z \"\$(ls -A $T/opt)\" ]"
check "app copied" "[ -f $A/kytyps5_manager/main_window.py ] && [ -f $A/images/$APP.webp ] && [ -f $A/images/$APP-128.png ]"
check "core bundled from checkout" "[ -f $A/bazzite_console_core/steam.py ]"
check "no tests or caches copied" "[ ! -d $A/tests ] && ! find $A -name __pycache__ | grep -q ."
check "shared venv and its user marker" "[ -x $D/bazzite-console-suite/venv/bin/python ] && [ -f $D/bazzite-console-suite/venv-users/$APP ]"
check "launcher uses shared venv" "grep -qF 'bazzite-console-suite/venv/bin/python\" -m kytyps5_manager' $HOME/.local/bin/$APP"
check "launcher cds into the app" "grep -qF 'cd \"$A\"' $HOME/.local/bin/$APP"
check "run wrapper installed, executable" "[ -x $RUN ] && cmp -s $RUN $SUITE/apps/kytyps5/ps5-kytyps5-run"
check "menu entry" "grep -qx 'Exec=$HOME/.local/bin/$APP' $D/applications/$APP.desktop"
check "desktop icon, executable" "[ -x $HOME/Desktop/$APP.desktop ]"
check "core imports from the app copy" "(cd $A && /usr/bin/python3 -c 'import importlib.util as u, sys; s=u.find_spec(\"bazzite_console_core\"); sys.exit(0 if s and s.origin.startswith(\"$A\") else 1)')"

echo "== 2. the run wrapper"
bash "$RUN" --game /games/x > "$T/run.log" 2>&1; rc=$?
check "without KytyPS5-Native it says so" "[ $rc -eq 1 ] && grep -q 'KytyPS5-Native is not installed' $T/run.log"
mkdir -p "$D/$APP/emulator/2026-11-27-8278d03"
printf '#!/bin/sh\necho "args: $*"\necho "from: $(pwd)"\n' > "$D/$APP/emulator/2026-11-27-8278d03/kyty_emulator"
printf '#!/bin/sh\necho "launcher: $*"\n' > "$D/$APP/emulator/2026-11-27-8278d03/kyty_launcher"
chmod +x "$D/$APP/emulator/2026-11-27-8278d03/kyty_emulator" "$D/$APP/emulator/2026-11-27-8278d03/kyty_launcher"
ln -sfn 2026-11-27-8278d03 "$D/$APP/emulator/current"
mkdir -p "$T/games/My Game"                                                # a game that is there (the wrapper's gone check)
bash "$RUN" --fullscreen --game "$T/games/My Game" > "$T/run.log" 2>&1; rc=$?
check "starts the current KytyPS5-Native with the arguments as given" "[ $rc -eq 0 ] && grep -qxF 'args: --fullscreen --game $T/games/My Game' $T/run.log $D/$APP/emulator.log"
check "from the emulator's own data folder, the home folder written as ~" "grep -qxF 'from: ~/.local/share/KytyPS5-Native/data' $D/$APP/emulator.log"
bash "$RUN" --launcher > "$T/run.log" 2>&1; rc=$?
check "--launcher starts its own window" "[ $rc -eq 0 ] && grep -qxF 'launcher: ' $T/run.log"

echo "== 3. install a staged release (core bundled in the tarball) without the Desktop icon"
rm -rf "$T/stage"; /usr/bin/python3 "$NEXUS/tools/stage_app.py" kytyps5 "$T/stage" > /dev/null
echo "# release marker" >> "$T/stage/bazzite_console_core/__init__.py"
bash "$T/stage/install.sh" --no-desktop-shortcut > "$T/log3" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "the release's own core used" "grep -q 'release marker' $A/bazzite_console_core/__init__.py"
check "manual bundled" "[ -f $A/MANUAL.md ]"
check "desktop icon removed" "[ ! -e $HOME/Desktop/$APP.desktop ]"
check "the installed KytyPS5-Native kept across an update" "[ -x $D/$APP/emulator/current/kyty_emulator ]"

echo "== 4. refusals"
fakeroot -- bash "$T/stage/install.sh" > "$T/log4" 2>&1; rc=$?
check "root refused" "[ $rc -ne 0 ] && grep -q 'not with sudo' $T/log4"
bash "$T/stage/install.sh" --purge > "$T/log4" 2>&1; rc=$?
check "--purge alone refused" "[ $rc -ne 0 ] && grep -q 'only goes with --uninstall' $T/log4"
bash "$T/stage/install.sh" --bogus > "$T/log4" 2>&1; rc=$?
check "unknown option refused" "[ $rc -ne 0 ] && grep -q 'Unknown option: --bogus' $T/log4"

echo "== 5. uninstall while another suite app uses the venv: KytyPS5-Native's own folders and the settings kept"
touch "$D/bazzite-console-suite/venv-users/ps5-board-test"
mkdir -p "$XDG_CONFIG_HOME/Kyty" "$XDG_CONFIG_HOME/$APP" && touch "$XDG_CONFIG_HOME/Kyty/Kyty.ini" "$D/KytyPS5-Native/data/save" "$XDG_CONFIG_HOME/$APP/$APP.ini"
bash "$T/stage/install.sh" --uninstall > "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "app and installed KytyPS5-Native gone" "[ ! -e $A ] && [ ! -e $D/$APP/emulator ]"
check "launchers and menu entry gone" "[ ! -e $HOME/.local/bin/$APP ] && [ ! -e $RUN ] && [ ! -e $D/applications/$APP.desktop ]"
check "KytyPS5-Native's own folders and the settings kept" "[ -f $XDG_CONFIG_HOME/Kyty/Kyty.ini ] && [ -f $D/KytyPS5-Native/data/save ] && [ -f $XDG_CONFIG_HOME/$APP/$APP.ini ]"
check "venv kept, own marker gone" "[ -x $D/bazzite-console-suite/venv/bin/python ] && [ ! -e $D/bazzite-console-suite/venv-users/$APP ]"

echo "== 6. reinstall, then uninstall --purge as the last venv user"
rm "$D/bazzite-console-suite/venv-users/ps5-board-test"
mkdir -p "$D/$APP/covers" && touch "$D/$APP/covers/PPSA00001p.png"       # covers found on SteamGridDB
bash "$T/stage/install.sh" > "$T/log6" 2>&1 && bash "$T/stage/install.sh" --uninstall --purge >> "$T/log6" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "venv removed" "[ ! -e $D/bazzite-console-suite/venv ] && [ ! -e $D/bazzite-console-suite/venv-users ]"
check "settings and covers removed" "[ ! -e $XDG_CONFIG_HOME/$APP ] && [ ! -e $D/$APP ]"
check "KytyPS5-Native's own folders still there" "[ -f $XDG_CONFIG_HOME/Kyty/Kyty.ini ] && [ -f $D/KytyPS5-Native/data/save ]"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 3 4 5 6; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
