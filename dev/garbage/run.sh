#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Starts Nexus Garbage Remover with the checkout's dev venv, on the checkout it lives in.
#
#   dev/garbage/run.sh            # open the window; --remind is the hourly check
#   dev/garbage/install.sh        # app menu entry, Desktop icon and the hourly reminder for this checkout
set -euo pipefail
APP=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd "$APP/../.." && pwd -P)          # the repository: the venv and core/

die() { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

case "${1:-}" in
    -h|--help) sed -n '3,6p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
esac

PY=${PYTHON:-}
if [[ -z "$PY" ]]; then
    candidates=(.venv-linux/bin/python .venv/bin/python)
    for candidate in "${candidates[@]}"; do
        [[ -x "$REPO/$candidate" ]] && PY="$REPO/$candidate" && break
    done
fi
[[ -n "$PY" ]] || die "No venv in $REPO. See CLAUDE.md or ./test.sh for how to create one."
cd "$APP"
PYTHONPATH="$REPO/core${PYTHONPATH:+:$PYTHONPATH}" exec "$PY" -m nexus_garbage_remover "$@"
