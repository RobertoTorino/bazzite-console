#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/cec/install.sh: install from the checkout (core bundled, shared venv, no sudo), a staged release
# replacing it (and restarting the watcher service when it is there), uninstall with and without other venv users
# (the CEC daemon settings kept, the watcher service removed), --purge (removed), and the refusal to run as root.
# Runs with the shims from shims.sh (CI).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
REPO=$SUITE
T=/tmp/ps5-hdmi-cec-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
APP=ps5-hdmi-cec
A=$D/$APP/app
FRAGMENT=$XDG_CONFIG_HOME/cecd/config.d/99-ps5-hdmi-cec.toml
WATCH=$XDG_CONFIG_HOME/systemd/user/ps5-hdmi-cec-watch.service
export PS5_SYSTEM_ROOT=$T/system                  # nothing of the app is in /etc: it must stay empty
# Nothing here needs sudo: make it fail loudly. systemctl and udevadm only record
# what they were asked.
cp "$T/shims/sudo" "$T/sudo-fakeroot"
printf '#!/bin/sh\necho "sudo called: $*" >&2\nexit 1\n' > "$T/shims/sudo"
printf '#!/bin/sh\necho "$*" >> "%s"\n' "$T/systemctl.log" > "$T/shims/systemctl"
printf '#!/bin/sh\necho "$*" >> "%s"\n' "$T/udevadm.log" > "$T/shims/udevadm"
chmod +x "$T/shims/systemctl" "$T/shims/udevadm"

echo "== 1. install from the suite checkout"
bash "$SUITE/apps/cec/install.sh" > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "no sudo used" "! grep -q 'sudo called' $T/log1 && [ -z \"\$(ls -A $T/opt)\" ]"
check "app copied" "[ -f $A/hdmi_cec/main_window.py ] && [ -f $A/images/$APP.webp ] && [ -f $A/images/$APP-128.png ]"
check "core bundled from checkout" "[ -f $A/bazzite_console_core/theme.py ]"
check "no tests or caches copied" "[ ! -d $A/tests ] && ! find $A -name __pycache__ | grep -q ."
check "shared venv" "[ -x $D/bazzite-console-suite/venv/bin/python ]"
check "venv user marker" "[ -f $D/bazzite-console-suite/venv-users/$APP ]"
check "launcher uses shared venv" "grep -qF 'bazzite-console-suite/venv/bin/python\" -m hdmi_cec' $HOME/.local/bin/$APP"
check "launcher cds into the app" "grep -qF 'cd \"$A\"' $HOME/.local/bin/$APP"
check "menu entry" "grep -qx 'Exec=$HOME/.local/bin/$APP' $D/applications/$APP.desktop"
check "desktop icon, executable" "[ -x $HOME/Desktop/$APP.desktop ]"
check "core imports from the app copy" "(cd $A && /usr/bin/python3 -c 'import importlib.util as u, sys; s=u.find_spec(\"bazzite_console_core\"); sys.exit(0 if s and s.origin.startswith(\"$A\") else 1)')"

check "no watcher service: systemctl not asked" "[ ! -s $T/systemctl.log ]"

echo "== 2. install a staged release (core bundled in the tarball) without the Desktop icon; the watcher restarts"
rm -rf "$T/stage"; /usr/bin/python3 "$REPO/tools/stage_app.py" cec "$T/stage" > /dev/null
echo "# release marker" >> "$T/stage/bazzite_console_core/__init__.py"
mkdir -p "$(dirname "$WATCH")" && printf '[Service]\nExecStart=/venv/bin/python -m hdmi_cec.watcher --pause-media\n' > "$WATCH"
bash "$T/stage/install.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "the release's own core used" "grep -q 'release marker' $A/bazzite_console_core/__init__.py"
check "manual bundled" "[ -f $A/MANUAL.md ]"
check "desktop icon removed" "[ ! -e $HOME/Desktop/$APP.desktop ]"
check "watcher restarted" "grep -qx -- '--user try-restart ps5-hdmi-cec-watch.service' $T/systemctl.log"
bash "$T/stage/install.sh" --no-desktop-shortcut > "$T/log2b" 2>&1
check "the same version is not reported" "! grep -q 'boot service' $T/log2b"

echo "== 3. refuses to run as root"
fakeroot -- bash "$T/stage/install.sh" > "$T/log3" 2>&1; rc=$?
check "exit non-zero" "[ $rc -ne 0 ] && grep -q 'not with sudo' $T/log3"

echo "== 4. uninstall while another suite app still uses the venv; the CEC daemon settings are kept"
touch "$D/bazzite-console-suite/venv-users/bazzite-test"
mkdir -p "$(dirname "$FRAGMENT")" && echo "wake_tv = true" > "$FRAGMENT"
cp "$T/shims/sudo" "$T/sudo-failing" && cp "$T/sudo-fakeroot" "$T/shims/sudo"
bash "$T/stage/install.sh" --uninstall > "$T/log4" 2>&1; rc=$?
cp "$T/sudo-failing" "$T/shims/sudo"
check "exit 0" "[ $rc -eq 0 ]"
check "app gone, CEC daemon settings kept" "[ ! -e $A ] && [ -f $FRAGMENT ]"
check "watcher stopped and removed" "[ ! -e $WATCH ] && grep -qx -- '--user disable --now ps5-hdmi-cec-watch.service' $T/systemctl.log"
check "venv kept" "[ -x $D/bazzite-console-suite/venv/bin/python ]"
check "own marker gone" "[ ! -e $D/bazzite-console-suite/venv-users/$APP ]"
check "launcher and menu entry gone" "[ ! -e $HOME/.local/bin/$APP ] && [ ! -e $D/applications/$APP.desktop ]"

echo "== 5. reinstall, then uninstall --purge as the last venv user"
rm "$D/bazzite-console-suite/venv-users/bazzite-test"
mkdir -p "$XDG_CONFIG_HOME/$APP" && touch "$XDG_CONFIG_HOME/$APP/$APP.ini"
echo "keep = true" > "$(dirname "$FRAGMENT")/98-bazzite-cec-mode.toml"
bash "$T/stage/install.sh" > "$T/log5" 2>&1 && bash "$T/stage/install.sh" --uninstall --purge >> "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "no sudo without a boot service" "! grep -q 'sudo called' $T/log5"
check "venv removed" "[ ! -e $D/bazzite-console-suite/venv ] && [ ! -e $D/bazzite-console-suite/venv-users ]"
check "settings and CEC daemon settings removed" "[ ! -e $XDG_CONFIG_HOME/$APP ] && [ ! -e $FRAGMENT ] && [ ! -e $D/$APP ]"
check "Bazzite's own cecd file untouched" "[ -f $(dirname "$FRAGMENT")/98-bazzite-cec-mode.toml ]"

[ $fail -eq 0 ] && echo "ALL OK" || for n in 1 2 2b 3 4 5; do echo "--- log$n"; cat "$T/log$n"; done
exit $fail
