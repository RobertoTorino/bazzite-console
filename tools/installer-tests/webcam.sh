#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/webcam/install.sh: install from the checkout (core bundled, shared venv, the load service, no
# sudo), a staged release replacing it, the refusal to run as root, uninstall (the load service gone, the udev rule
# removed with sudo, the firmware kept) and --purge.
# Runs with the shims from shims.sh (as CI does).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
REPO=$SUITE
T=/tmp/ps5-webcam-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
APP=ps5-webcam
A=$D/$APP/app
export WEBCAM_SYSTEM_ROOT=$T/system                # the udev rule's /etc
RULE=$WEBCAM_SYSTEM_ROOT/etc/udev/rules.d/70-$APP.rules
U=$XDG_CONFIG_HOME/systemd/user
# sudo is only for removing the udev rule: until then make it fail loudly.
cp "$T/shims/sudo" "$T/sudo-fakeroot"
printf '#!/bin/sh\necho "sudo called: $*" >&2\nexit 1\n' > "$T/shims/sudo"
# systemctl only records what it was asked.
printf '#!/bin/sh\necho "$*" >> "%s"\n' "$T/systemctl.log" > "$T/shims/systemctl"
chmod +x "$T/shims/systemctl"
printf '#!/bin/sh\nexit 0\n' > "$T/shims/udevadm"; chmod +x "$T/shims/udevadm"

echo "== 1. install from the suite checkout"
bash "$SUITE/apps/webcam/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "app copied" "[ -f $A/webcam/__main__.py ] && [ -f $A/images/$APP.webp ] && [ -f $A/images/$APP-128.png ]"
check "core bundled from checkout" "[ -f $A/bazzite_console_core/theme.py ]"
check "no tests or caches copied" "[ ! -d $A/tests ] && ! find $A -name __pycache__ | grep -q ."
check "launcher cds into the app" "grep -qF 'cd \"$A\"' $HOME/.local/bin/$APP"
check "menu entry" "grep -qx 'Exec=$HOME/.local/bin/$APP' $D/applications/$APP.desktop"
check "desktop icon, executable" "[ -x $HOME/Desktop/$APP.desktop ]"
check "shared venv" "[ -x $D/bazzite-console-suite/venv/bin/python ]"
check "venv user marker" "[ -f $D/bazzite-console-suite/venv-users/$APP ]"
check "launcher uses shared venv" "grep -qF 'bazzite-console-suite/venv/bin/python\" -m webcam' $HOME/.local/bin/$APP"
check "no sudo used, no udev rule written" "! grep -q 'sudo called' $T/log1 && [ ! -e $RULE ]"
check "load service written and enabled" "grep -qF 'ExecStart=\"$HOME/.local/bin/$APP\" --load --auto' $U/$APP-load.service && [ -L $U/default.target.wants/$APP-load.service ]"
check "says the app asks for access" "grep -q 'Allow access' $T/log1"

echo "== 2. install a staged release (core bundled in the tarball) without the Desktop icon"
rm -rf "$T/stage"; /usr/bin/python3 "$REPO/tools/stage_app.py" webcam "$T/stage" > /dev/null
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

echo "== 4. uninstall with the udev rule in place and another suite app using the venv"
mkdir -p "$(dirname "$RULE")" && echo rule > "$RULE"
mkdir -p "$D/$APP/firmware" && touch "$D/$APP/firmware/camera.bin"
touch "$D/bazzite-console-suite/venv-users/bazzite-test"
cp "$T/sudo-fakeroot" "$T/shims/sudo"
bash "$T/stage/install.sh" --uninstall > "$T/log4" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "udev rule removed" "[ ! -e $RULE ]"
check "load service gone" "[ ! -e $U/$APP-load.service ] && [ ! -e $U/default.target.wants/$APP-load.service ]"
check "app gone, firmware kept" "[ ! -e $A ] && [ -f $D/$APP/firmware/camera.bin ]"
check "venv kept, own marker gone" "[ -x $D/bazzite-console-suite/venv/bin/python ] && [ ! -e $D/bazzite-console-suite/venv-users/$APP ]"
check "launcher and menu entry gone" "[ ! -e $HOME/.local/bin/$APP ] && [ ! -e $D/applications/$APP.desktop ]"

echo "== 5. reinstall, then uninstall --purge as the last venv user"
rm "$D/bazzite-console-suite/venv-users/bazzite-test"
mkdir -p "$XDG_CONFIG_HOME/$APP" && touch "$XDG_CONFIG_HOME/$APP/$APP.ini"
bash "$T/stage/install.sh" > "$T/log5" 2>&1 && bash "$T/stage/install.sh" --uninstall --purge >> "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "venv removed" "[ ! -e $D/bazzite-console-suite/venv ] && [ ! -e $D/bazzite-console-suite/venv-users ]"
check "settings and firmware removed" "[ ! -e $XDG_CONFIG_HOME/$APP ] && [ ! -e $D/$APP ]"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 2 3 4 5; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
