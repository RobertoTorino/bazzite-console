#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise apps/bazzite/install.sh: from the checkout, from a staged release, uninstall with and without
# other venv users. Runs with the shims from shims.sh (CI, or WSL on Windows).
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NEXUS=$(cd "$SUITE/.." && pwd)      # the Nexus checkout the suite is cloned into: the Nexus tools (stage_app.py)
T=/tmp/bazzite-test-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
V=$(tr -d '[:space:]' < "$SUITE/apps/bazzite/VERSION")   # the version in the checkout
NEXT="${V%.*}.$(( ${V##*.} + 1 ))"                             # a later release, for the update in step 2

echo "== 1. install from the suite checkout"
mkdir -p "$D/bazzite-test/venv/bin"                     # a pre-suite venv that should go
bash "$SUITE/apps/bazzite/install.sh" --no-desktop-shortcut > "$T/log1" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "versioned /opt copy" "[ -f $T/opt/bazzite-test-v$V/test-bazzite.sh ]"
check "symlink" "[ \"\$(readlink $T/opt/bazzite-test)\" = bazzite-test-v$V ]"
check "core bundled from checkout" "[ -f $T/opt/bazzite-test/bazzite_console_core/widgets.py ]"
check "no tests or caches copied" "[ ! -d $T/opt/bazzite-test/bazzite_console_core/__pycache__ ]"
check "shared venv" "[ -x $D/bazzite-console-suite/venv/bin/python ]"
check "venv user marker" "[ -f $D/bazzite-console-suite/venv-users/bazzite-test ]"
check "old own venv removed" "[ ! -d $D/bazzite-test/venv ]"
check "launcher uses shared venv" "grep -qF 'bazzite-console-suite/venv/bin/python\" -m bazzite_test' $HOME/.local/bin/bazzite-test"
check "launcher cds into /opt link" "grep -q \"cd \\\"$T/opt/bazzite-test\\\"\" $HOME/.local/bin/bazzite-test"
check "menu entry" "[ -f $D/applications/bazzite-test.desktop ]"
check "no desktop icon" "[ ! -e $HOME/Desktop/bazzite-test.desktop ]"
check "core imports from the /opt copy" "(cd $T/opt/bazzite-test && python3 -c 'import bazzite_console_core, sys; sys.exit(0 if bazzite_console_core.__file__.startswith(\"$T/opt\") else 1)' 2>/dev/null || (cd $T/opt/bazzite-test && /usr/bin/python3 -c 'import importlib.util as u, sys; s=u.find_spec(\"bazzite_console_core\"); sys.exit(0 if s and s.origin.startswith(\"$T/opt\") else 1)'))"

echo "== 2. install a staged release (core bundled in the tarball), new version replaces the old"
rm -rf "$T/stage"; /usr/bin/python3 "$NEXUS/tools/stage_app.py" --suite "${SUITE##*/}" bazzite "$T/stage" > /dev/null
sed -i "s/^__version__ = \"$V\"\$/__version__ = \"$NEXT\"/" "$T/stage/bazzite_test/__init__.py"
echo "# release marker" >> "$T/stage/bazzite_console_core/__init__.py"
bash "$T/stage/install.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "new version linked" "[ \"\$(readlink $T/opt/bazzite-test)\" = bazzite-test-v$NEXT ]"
check "old version removed" "[ ! -d $T/opt/bazzite-test-v$V ]"
check "the release's own core used" "grep -q 'release marker' $T/opt/bazzite-test/bazzite_console_core/__init__.py"
check "no tests in staged tree" "[ ! -d $T/stage/tests ] && [ ! -e $T/stage/requirements-dev.txt ]"

echo "== 3. uninstall while another suite app still uses the venv"
touch "$D/bazzite-console-suite/venv-users/ps5-rpcs3-manager"
bash "$T/stage/install.sh" --uninstall > "$T/log3" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "/opt copy gone" "[ ! -e $T/opt/bazzite-test ] && ! ls -d $T/opt/bazzite-test-v* >/dev/null 2>&1"
check "venv kept" "[ -x $D/bazzite-console-suite/venv/bin/python ]"
check "own marker gone" "[ ! -e $D/bazzite-console-suite/venv-users/bazzite-test ]"
check "launcher gone" "[ ! -e $HOME/.local/bin/bazzite-test ]"

echo "== 4. reinstall, then uninstall as the last user"
rm "$D/bazzite-console-suite/venv-users/ps5-rpcs3-manager"
bash "$T/stage/install.sh" > "$T/log4" 2>&1 && bash "$T/stage/install.sh" --uninstall >> "$T/log4" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "venv removed" "[ ! -e $D/bazzite-console-suite/venv ]"
check "markers dir removed" "[ ! -e $D/bazzite-console-suite/venv-users ]"
check "desktop icon removed" "[ ! -e $HOME/Desktop/bazzite-test.desktop ]"

[ $fail -eq 0 ] && echo "ALL OK" || { echo "--- log1"; cat "$T/log1"; echo "--- log2"; cat "$T/log2"; echo "--- log3"; cat "$T/log3"; echo "--- log4"; cat "$T/log4"; }
exit $fail
