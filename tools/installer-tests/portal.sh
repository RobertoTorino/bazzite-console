#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise portal/install.sh: from the checkout (through the root install.sh), from a release-shaped tree, the
# portal's own update from its state folder, uninstall and purge.
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NEXUS=$SUITE                        # the repository: the Nexus tools (stage_app.py) and core/
T=/tmp/bazzite-console-portal-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
P=$D/bazzite-console-suite/portal        # the installed portal
S=$D/bazzite-console-suite/state         # what it remembers
logs=()
V=$(cat "$SUITE/portal/VERSION")
NEXT="${V%.*}.$(( ${V##*.} + 1 ))"   # a later portal release, for the update in step 2
BT="ps5-board-v$(tr -d '[:space:]' < "$SUITE/apps/board/VERSION")"   # the bundled release

echo "== 1. install from the suite checkout, with the install.sh at its root"
bash "$SUITE/install.sh" > "$T/log1" 2>&1; rc=$?; logs+=("$T/log1")
check "exit 0" "[ $rc -eq 0 ]"
check "portal installs apps from the checkout" "[ \"\$(cat $P/suite-checkout)\" = \"\$(cd $NEXUS && pwd -P)\" ]"
check "portal in the home folder without the dependency checker catalog" "[ -f $P/bazzite_console_portal/__main__.py ] && [ -f $P/apps.toml ] && [ ! -e $P/dependencies.toml ]"
check "nothing of the portal in /opt" "[ ! -e $T/opt/bazzite-console-suite ] && [ -z \"\$(ls -d $T/opt/bazzite-console-suite-v* 2>/dev/null)\" ]"
check "no staging folder left" "[ ! -e $D/bazzite-console-suite/.portal.new ]"
check "core bundled with portal" "[ -f $P/bazzite_console_core/platform.py ]"
check "no tests in the copy" "[ ! -d $P/tests ]"
check "the sound is in the copy" "[ -s $P/bazzite_console_portal/sounds/bigpicture.wav ] && [ ! -e $P/bazzite_console_portal/sounds/swoosh.wav ]"
check "the controller reader is in the requirements" "grep -q '^pygame-ce' $P/requirements.txt"
check "Board Test installed too" "[ -f $T/opt/ps5-board-test/test-board.sh ] && [ -x $HOME/.local/bin/ps5-board-test ]"
check "Board Test has its manual" "cmp -s $SUITE/docs/apps/board.md $T/opt/ps5-board-test/MANUAL.md"
check "both venv users" "[ -f $D/bazzite-console-suite/venv-users/bazzite-console-suite ] && [ -f $D/bazzite-console-suite/venv-users/ps5-board-test ]"
check "portal launcher" "grep -qF 'm bazzite_console_portal' $HOME/.local/bin/bazzite-console-suite"
check "desktop icons" "[ -x $HOME/Desktop/bazzite-console-suite.desktop ] && [ -x $HOME/Desktop/ps5-board-test.desktop ]"
check "record says local" "grep -q '\"board\": \"local\"' $S/installed.json"
check "portal imports its bundled core" "(cd $P && /usr/bin/python3 -c 'import bazzite_console_core, os, sys; sys.exit(0 if os.path.abspath(bazzite_console_core.__file__).startswith(\"$P\") else 1)')"
check "manifest parses on Linux python" "(cd $P && /usr/bin/python3 -c 'import tomllib; d=tomllib.load(open(\"apps.toml\",\"rb\")); assert list(d[\"apps\"])[0]==\"board\"')"

echo "== 2. release-shaped tree: portal staged + bundled Board Test, no desktop icons"
R="$T/release/ps5-portal-v$NEXT"; rm -rf "$T/release"; mkdir -p "$T/release"
/usr/bin/python3 "$NEXUS/tools/stage_app.py" portal "$R" > /dev/null
/usr/bin/python3 "$NEXUS/tools/stage_app.py" board "$R/bundled/$BT" > /dev/null
sed -i "s/^__version__ = \"$V\"\$/__version__ = \"$NEXT\"/" "$R/bazzite_console_portal/__init__.py"
(cd "$T/release" && tar -czf "ps5-portal-v$NEXT.tar.gz" "ps5-portal-v$NEXT")      # the tarball beside it, as a download leaves it
bash "$R/install.sh" --no-desktop-shortcut > "$T/log2" 2>&1; rc=$?; logs+=("$T/log2")
check "exit 0" "[ $rc -eq 0 ]"
check "the tarball's sha256 is kept beside the program" "[ \"\$(cut -c1-64 $P/build.sha256)\" = \"\$(sha256sum $T/release/ps5-portal-v$NEXT.tar.gz | cut -c1-64)\" ]"
check "the new portal version replaced the old" "grep -q '^__version__ = \"$NEXT\"' $P/bazzite_console_portal/__init__.py"
check "the release has the sound" "[ -s $P/bazzite_console_portal/sounds/bigpicture.wav ]"
check "bundled/ not copied" "[ ! -d $P/bundled ]"
check "portal installs apps from releases" "[ ! -e $P/suite-checkout ]"
check "record has the bundled tag" "grep -q '\"board\": \"$BT\"' $S/installed.json"
check "desktop icons removed" "[ ! -e $HOME/Desktop/bazzite-console-suite.desktop ] && [ ! -e $HOME/Desktop/ps5-board-test.desktop ]"

echo "== 3. the portal's own update: a release unpacked in the state folder, installed from there"
U="$S/portal-update/ps5-portal-v$NEXT"; mkdir -p "$S/portal-update"; cp -r "$R" "$U"
echo picture > "$S/wallpaper.png"
(cd "$U" && ./install.sh --no-desktop-shortcut) > "$T/log2b" 2>&1; rc=$?; logs+=("$T/log2b")
check "exit 0" "[ $rc -eq 0 ]"
check "the portal is installed, the state untouched" "[ -f $P/bazzite_console_portal/__main__.py ] && grep -q '\"board\": \"$BT\"' $S/installed.json && [ -f $S/wallpaper.png ]"
# An earlier portal kept its downloads in what is the portal's own folder now: the copy replaces the folder the
# update runs from, after Board Test is installed from it.
U="$P/portal-update/ps5-portal-v$NEXT"; mkdir -p "$P/portal-update"; cp -r "$R" "$U"
(cd "$U" && ./install.sh --no-desktop-shortcut) > "$T/log2c" 2>&1; rc=$?; logs+=("$T/log2c")
check "from inside the portal's folder: exit 0, the portal installed" "[ $rc -eq 0 ] && [ -f $P/bazzite_console_portal/__main__.py ] && [ ! -e $P/portal-update ] && [ -x $HOME/.local/bin/bazzite-console-suite ]"

echo "== 4. uninstall keeps the venv for another suite app and the wallpaper, drops the state of apps that are gone"
touch "$D/bazzite-console-suite/venv-users/ps5-fan-controller"
mkdir -p "$S/releases/fan-v0.0.1" "$S/releases/local-ssd"
bash "$P/install.sh" --uninstall > "$T/log3" 2>&1; rc=$?; logs+=("$T/log3")
check "exit 0" "[ $rc -eq 0 ]"
check "portal gone, Board Test gone from /opt" "[ ! -e $P ] && [ -z \"\$(ls $T/opt)\" ]"
check "launchers gone" "[ ! -e $HOME/.local/bin/bazzite-console-suite ] && [ ! -e $HOME/.local/bin/ps5-board-test ]"
check "venv kept, only Fan Controller left" "[ -x $D/bazzite-console-suite/venv/bin/python ] && [ \"\$(ls $D/bazzite-console-suite/venv-users)\" = ps5-fan-controller ]"
check "mentions what is left" "grep -q 'Still installed: ps5-fan-controller' $T/log3"
check "the wallpaper kept, the records and releases of the apps that are gone dropped" "[ -f $S/wallpaper.png ] && [ ! -e $S/installed.json ] && [ ! -e $S/releases ]"
rm "$S/wallpaper.png" "$S/portal-update" -r

echo "== 5. reinstall and purge as the last user"
rm "$D/bazzite-console-suite/venv-users/ps5-fan-controller"
mkdir -p "$T/log/ps5-board-test" && touch "$T/log/ps5-board-test/ps5-board-test-results-20260101-000000.log"
bash "$R/install.sh" > "$T/log4" 2>&1 && bash "$P/install.sh" --uninstall --purge >> "$T/log4" 2>&1; rc=$?; logs+=("$T/log4")
check "exit 0" "[ $rc -eq 0 ]"
check "suite data dir gone" "[ ! -e $D/bazzite-console-suite ]"
check "Board Test results gone" "[ ! -e $T/log/ps5-board-test ]"
check "/opt empty" "[ -z \"\$(ls $T/opt)\" ]"

echo "== 6. uninstall asks about each other app: cancel, then skip one and uninstall the others"
# The others: overlay and ssd as the portal installs them from the checkout, and datstation, installed the same
# way. Then ssd and datstation are dropped from the installed portal's manifest, as a newer portal drops an app: ssd
# keeps its record and release folder (the portal's), datstation neither (found by its own installed copy under
# ~/.local/share). Nexus Installer Tests (dev/itests, a Nexus app), installed from the checkout too, is not the
# portal's (no Development tab, owner 27-10-2026): the portal's uninstall leaves it.
bash "$SUITE/install.sh" > "$T/log5" 2>&1; logs+=("$T/log5")
for app in overlay ssd datstation; do
    /usr/bin/python3 "$NEXUS/tools/stage_app.py" "$app" "$S/releases/local-$app" > /dev/null
    (cd "$S/releases/local-$app" && bash install.sh) >> "$T/log5" 2>&1
done
bash "$NEXUS/dev/itests/install.sh" --no-desktop-shortcut >> "$T/log5" 2>&1
rm -rf "$S/releases/local-datstation"
/usr/bin/python3 - "$S/installed.json" "$P/apps.toml" <<'PY'
import json, re, sys
from pathlib import Path
data = json.load(open(sys.argv[1]))
data.update({"overlay": "local", "ssd": "local"})
json.dump(data, open(sys.argv[1], "w"))
manifest = Path(sys.argv[2])
text = manifest.read_text(encoding="utf-8")
for key in ("ssd", "datstation"):                # dropped from this portal's manifest
    text = re.sub(rf"^\[apps\.{key}\]\n(?:(?!^\[).*\n)*", "", text, flags=re.M)
manifest.write_text(text, encoding="utf-8")
PY
installed() { [ -x "$HOME/.local/bin/$1" ]; }
check "the apps are installed" "installed ps5-system-overlay && installed ps5-ssd-check && installed ps5-datstation && installed nexus-installer-tests"
check "two of them dropped from the installed manifest" "! grep -q 'apps.ssd' $P/apps.toml && ! grep -q 'apps.datstation' $P/apps.toml && grep -q 'apps.overlay' $P/apps.toml"
mkdir -p "$S/releases/overlay-v0.0.1"   # an older release it was updated from
printf 'y\nc\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$SUITE/install.sh" --uninstall >> "$T/log5" 2>&1; rc=$?
check "cancel: exit 1" "[ $rc -eq 1 ]"
check "cancel: nothing removed" "installed ps5-system-overlay && installed ps5-ssd-check && installed ps5-datstation && installed nexus-installer-tests && installed bazzite-console-suite && installed ps5-board-test"
check "cancel: says so" "grep -q 'Canceled: nothing was uninstalled.' $T/log5"
printf 'x\ns\ny\ny\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$SUITE/install.sh" --uninstall >> "$T/log5" 2>&1; rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "asked about overlay three times (the cancel run, an unknown answer), SSD Check twice, datstation once, Installer Tests never" "[ \$(grep -o 'Uninstall PS5 System Overlay?' $T/log5 | wc -l) -eq 3 ] && [ \$(grep -o 'Uninstall PS5 SSD Check?' $T/log5 | wc -l) -eq 2 ] && [ \$(grep -o 'Uninstall PS5 DatStation?' $T/log5 | wc -l) -eq 1 ] && ! grep -q 'Uninstall Nexus Installer Tests?' $T/log5"
check "skipped app stays" "installed ps5-system-overlay && [ -d $S/releases/local-overlay ]"
check "chosen app gone" "! installed ps5-ssd-check && [ ! -e $S/releases/local-ssd ]"
check "Installer Tests stays: the checkout's, not the portal's" "installed nexus-installer-tests"
check "dropped app without a record gone" "! installed ps5-datstation && [ ! -e $D/ps5-datstation/app ]"
check "record drops the chosen app" "! grep -q ssd $S/installed.json && grep -q overlay $S/installed.json"
check "record and folder of Board Test gone" "! grep -q board $S/installed.json && [ ! -e $S/releases/local-board ]"
check "older release of the skipped app gone" "[ ! -e $S/releases/overlay-v0.0.1 ]"
check "portal and Board Test gone" "! installed bazzite-console-suite && ! installed ps5-board-test"
check "mentions what is left" "grep -q 'Still installed: ps5-system-overlay' $T/log5"
(cd "$S/releases/local-overlay" && bash install.sh --uninstall) >> "$T/log5" 2>&1
bash "$NEXUS/dev/itests/install.sh" --uninstall >> "$T/log5" 2>&1

echo "== 7. after an uninstall that kept nothing, no suite folder is left"
bash "$SUITE/install.sh" > "$T/log6" 2>&1 && bash "$P/install.sh" --uninstall >> "$T/log6" 2>&1
rc=$?; logs+=("$T/log6")
check "exit 0" "[ $rc -eq 0 ]"
check "suite data dir gone (settings stay in ~/.config)" "[ ! -e $D/bazzite-console-suite ]"

echo "== 8. --uninstall --all: one confirmation for the whole suite, no question per app"
bash "$SUITE/install.sh" > "$T/log7" 2>&1; logs+=("$T/log7")
for app in overlay ssd; do
    rm -rf "$S/releases/local-$app"
    /usr/bin/python3 "$NEXUS/tools/stage_app.py" "$app" "$S/releases/local-$app" > /dev/null
    (cd "$S/releases/local-$app" && bash install.sh) >> "$T/log7" 2>&1
done
mkdir -p "$XDG_CONFIG_HOME/ps5-system-overlay" && echo x > "$XDG_CONFIG_HOME/ps5-system-overlay/settings.ini"
check "both apps installed, overlay has settings" "installed ps5-system-overlay && installed ps5-ssd-check && [ -f $XDG_CONFIG_HOME/ps5-system-overlay/settings.ini ]"
bash "$SUITE/install.sh" --all > "$T/log7a" 2>&1; rc=$?
check "--all without --uninstall refused" "[ $rc -ne 0 ] && grep -q 'only goes with --uninstall' $T/log7a"
bash "$SUITE/install.sh" --uninstall --all < /dev/null >> "$T/log7" 2>&1; rc=$?
check "without a terminal: refused, nothing removed" "[ $rc -ne 0 ] && grep -q 'needs a terminal' $T/log7 && installed ps5-system-overlay && installed bazzite-console-suite"
printf 'n\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$SUITE/install.sh" --uninstall --all >> "$T/log7" 2>&1; rc=$?
check "no: canceled, nothing removed" "[ $rc -eq 1 ] && grep -q 'Canceled: nothing was uninstalled.' $T/log7 && installed ps5-system-overlay && installed ps5-ssd-check && installed bazzite-console-suite"
check "the warning names every app" "grep -q 'WARNING: --all removes the whole suite from this computer: PS5 SSD Check, PS5 System Overlay, with the portal and Board Test.' $T/log7"
check "asks once, not per app" "grep -q 'Are you sure you want to delete everything permanently?' $T/log7 && ! grep -q 'Uninstall PS5 System Overlay?' $T/log7"
printf 'y\n' | BAZZITE_CONSOLE_INTERACTIVE=1 bash "$SUITE/install.sh" --uninstall --all --purge >> "$T/log7" 2>&1; rc=$?
check "yes: exit 0" "[ $rc -eq 0 ]"
check "the warning says the settings go too" "grep -q 'WARNING: --purge removes their settings' $T/log7"
check "everything gone, the apps' settings too" "! installed ps5-system-overlay && ! installed ps5-ssd-check && ! installed bazzite-console-suite && ! installed ps5-board-test && [ ! -e $XDG_CONFIG_HOME/ps5-system-overlay ] && [ ! -e $D/bazzite-console-suite ]"
check "nothing left to mention" "! grep -q 'Still installed' $T/log7"

[ $fail -eq 0 ] && echo "ALL OK" || for l in "${logs[@]}"; do echo "--- $l"; cat "$l"; done
exit $fail
