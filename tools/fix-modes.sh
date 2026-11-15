#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Marks every shell script in the git index as executable (mode 100755).
#
# A checkout with core.fileMode=false (Git for Windows, a file system without exec bits) records a new script as
# 100644, and a Linux checkout (or a release tarball) then gets a script that `./install.sh` cannot run. This sets
# the bit in the index itself. Run it after `git add`, before committing; CI fails when a script is missing the bit.
# Only the index changes: nothing is committed.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

missing=$(git ls-files -s -- '*.sh' | awk '$1 != "100755" { print $4 }')
if [[ -z "$missing" ]]; then
    echo "All tracked .sh files are already executable."
    exit 0
fi
printf '%s\n' "$missing" | tr '\n' '\0' | xargs -0 git update-index --chmod=+x --
printf 'Marked executable:\n%s\n' "$missing"
