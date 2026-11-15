#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Every app's installer and the portal's, with --uninstall and with --uninstall --purge, on a computer where nothing
# of them is installed: each says so in one line, exits 0, removes nothing and asks for no sudo password.
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
T=/tmp/bazzite-console-not-installed-test
rm -rf "${T:?}"; mkdir -p "$T/home/Desktop" "$T/opt" "$T/log" "$T/system" "$T/shims"
printf '#!/bin/sh\necho "sudo $*" >> %s/sudo-calls\nexit 1\n' "$T" > "$T/shims/sudo"
chmod +x "$T/shims/sudo"
export PATH="$T/shims:$PATH" HOME="$T/home" XDG_DATA_HOME="$T/home/.local/share" XDG_CONFIG_HOME="$T/home/.config" \
       PS5_BOARD_TEST_OPT_DIR="$T/opt" PS5_BOARD_TEST_LOG_DIR="$T/log" PS5_SYSTEM_ROOT="$T/system" \
       WEBCAM_SYSTEM_ROOT="$T/system"
fail=0
for installer in "$SUITE"/apps/*/install.sh "$SUITE/portal/install.sh"; do
    name=${installer#"$SUITE"/}
    for options in "--uninstall" "--uninstall --purge"; do
        # shellcheck disable=SC2086  # the options are two words
        out=$(bash "$installer" $options < /dev/null 2>&1); rc=$?
        if [ $rc -eq 0 ] && [ "$(wc -l <<<"$out")" -eq 1 ] && grep -q 'is not installed: nothing to remove\.$' <<<"$out"; then
            echo "  ok   $name $options"
        else
            echo "  FAIL $name $options (exit $rc):"; echo "$out" | sed 's/^/       /'; fail=1
        fi
    done
done
[ ! -e "$T/sudo-calls" ] && echo "  ok   no sudo asked" || { echo "  FAIL sudo asked:"; cat "$T/sudo-calls"; fail=1; }
left=$(cd "$T/home" && find . -mindepth 1 ! -path ./Desktop)
[ -z "$left" ] && echo "  ok   nothing written" || { echo "  FAIL written in the home folder:"; echo "$left"; fail=1; }
[ $fail -eq 0 ] && echo "ALL OK"
exit $fail
