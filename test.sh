#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Runs every test suite in the repo (core, tools, the development apps in dev/, the portal and each app with a tests/
# folder), offscreen.
# Extra arguments go to pytest, e.g. ./test.sh -k profile  or  ./test.sh -x -vv
#
# Interpreter: $PYTHON if set, else the checkout's venv: .venv-linux/ (a plain .venv/ works too).
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-}
if [[ -z "$PY" ]]; then
    for candidate in .venv-linux/bin/python .venv/bin/python; do
        [[ -x "$candidate" ]] && PY="$PWD/$candidate" && break
    done
fi
if [[ -z "$PY" ]]; then
    echo "No venv in the checkout. Create one:" >&2
    echo "  python3 -m venv .venv-linux && .venv-linux/bin/python -m pip install -r requirements-dev.txt" >&2
    exit 1
fi

export QT_QPA_PLATFORM=offscreen
export PYTHONDONTWRITEBYTECODE=1
# A test that hangs (a dialog waiting for a click, owner 20-11-2026: one ran for 15 minutes without a word) prints where
# it is stuck after 2 minutes and ends the run, failed. The slowest test takes seconds.
HANG_LIMIT=(-o faulthandler_timeout=120 -o faulthandler_exit_on_timeout=true)
rc=0
for dir in core tools dev/* portal apps/*; do
    [[ -d "$dir/tests" ]] || continue
    echo "== $dir"
    (cd "$dir" && "$PY" -m pytest -q -p no:cacheprovider "${HANG_LIMIT[@]}" tests "$@") || rc=1
done
exit $rc
