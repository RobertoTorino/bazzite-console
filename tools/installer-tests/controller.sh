#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/controller/install.sh: install from the checkout (core bundled, shared venv, no sudo, no
# idle-off service), a staged release replacing it, the refusal to run as root, --enable-idle-service (the per-user
# service, enabled), uninstall (the service gone) and --purge.
# Runs with the shims from shims.sh (as CI does).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
REPO=$SUITE
T=/tmp/ps5-controller-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
APP=ps5-controller
A=$D/$APP/app
U=$XDG_CONFIG_HOME/systemd/user
# sudo must never be needed: make it fail loudly.
printf '#!/bin/sh\necho "sudo called: $*" >&2\nexit 1\n' > "$T/shims/sudo"
# systemctl only records what it was asked.
printf '#!/bin/sh\necho "$*" >> "%s"\n' "$T/systemctl.log" > "$T/shims/systemctl"
chmod +x "$T/shims/systemctl"

echo "== 1. install from the suite checkout"
bash "$SUITE/apps/controller/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "app copied" "[ -f $A/controller/__main__.py ] && [ -f $A/images/$APP.webp ] && [ -f $A/images/$APP-128.png ]"
check "core bundled from checkout" "[ -f $A/bazzite_console_core/theme.py ]"
check "no tests or caches copied" "[ ! -d $A/tests ] && ! find $A -name __pycache__ | grep -q ."
check "launcher cds into the app" "grep -qF 'cd \"$A\"' $HOME/.local/bin/$APP"
check "menu entry" "grep -qx 'Exec=$HOME/.local/bin/$APP' $D/applications/$APP.desktop"
check "desktop icon, executable" "[ -x $HOME/Desktop/$APP.desktop ]"
check "shared venv" "[ -x $D/bazzite-console-suite/venv/bin/python ]"
check "venv user marker" "[ -f $D/bazzite-console-suite/venv-users/$APP ]"
check "launcher uses shared venv" "grep -qF 'bazzite-console-suite/venv/bin/python\" -m controller' $HOME/.local/bin/$APP"
check "no sudo used" "! grep -q 'sudo called' $T/log1 && [ -z \"\$(ls -A $T/opt)\" ]"
check "no idle-off service unless asked" "[ ! -e $U/$APP-idle.service ] && grep -q 'enable-idle-service' $T/log1"

echo "== 2. install a staged release (core bundled in the tarball) without the Desktop icon"
rm -rf "$T/stage"; /usr/bin/python3 "$REPO/tools/stage_app.py" controller "$T/stage" > /dev/null
echo "# release marker" >> "$T/stage/bazzite_console_core/__init__.py"
bash "$T/stage/install.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "the release's own core used" "grep -q 'release marker' $A/bazzite_console_core/__init__.py"
check "manual in the staged release" "[ -f $A/MANUAL.md ]"
check "desktop icon removed" "[ ! -e $HOME/Desktop/$APP.desktop ]"

echo "== 3. refuses to run as root, and --purge without --uninstall"
fakeroot -- bash "$T/stage/install.sh" > "$T/log3" 2>&1; rc=$?
check "exit non-zero as root" "[ $rc -ne 0 ] && grep -q 'not with sudo' $T/log3"
bash "$T/stage/install.sh" --purge >> "$T/log3" 2>&1; rc=$?
check "exit non-zero for --purge alone" "[ $rc -ne 0 ]"

echo "== 4. --enable-idle-service"
bash "$T/stage/install.sh" --enable-idle-service > "$T/log4" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "service written" "grep -qx 'ExecStart=$HOME/.local/bin/$APP --idle-watch' $U/$APP-idle.service"
check "service enabled and restarted" "grep -qx -- '--user enable $APP-idle.service' $T/systemctl.log && grep -qx -- '--user restart $APP-idle.service' $T/systemctl.log"
bash "$T/stage/install.sh" >> "$T/log4" 2>&1
check "a later install without the option keeps the service" "[ -f $U/$APP-idle.service ]"

echo "== 5. uninstall while another suite app still uses the venv"
mkdir -p "$D/$APP/firmware" && touch "$D/$APP/firmware/fw.bin"
touch "$D/bazzite-console-suite/venv-users/bazzite-test"
bash "$T/stage/install.sh" --uninstall > "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "service disabled and gone" "grep -qx -- '--user disable --now $APP-idle.service' $T/systemctl.log && [ ! -e $U/$APP-idle.service ]"
check "app gone, firmware kept" "[ ! -e $A ] && [ -f $D/$APP/firmware/fw.bin ]"
check "venv kept, own marker gone" "[ -x $D/bazzite-console-suite/venv/bin/python ] && [ ! -e $D/bazzite-console-suite/venv-users/$APP ]"
check "launcher and menu entry gone" "[ ! -e $HOME/.local/bin/$APP ] && [ ! -e $D/applications/$APP.desktop ]"

echo "== 6. reinstall, then uninstall --purge as the last venv user"
rm "$D/bazzite-console-suite/venv-users/bazzite-test"
mkdir -p "$XDG_CONFIG_HOME/$APP" && touch "$XDG_CONFIG_HOME/$APP/$APP.ini"
bash "$T/stage/install.sh" > "$T/log6" 2>&1 && bash "$T/stage/install.sh" --uninstall --purge >> "$T/log6" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "venv removed" "[ ! -e $D/bazzite-console-suite/venv ] && [ ! -e $D/bazzite-console-suite/venv-users ]"
check "settings, firmware and backups removed" "[ ! -e $XDG_CONFIG_HOME/$APP ] && [ ! -e $D/$APP ]"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 2 3 4 5 6; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
