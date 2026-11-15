#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Runs every test suite in the repo (core, tools, the development apps in dev/, the portal and each app with a tests/
# folder), offscreen.
# Extra arguments go to pytest, e.g. ./test.sh -k profile  or  ./test.sh -x -vv
#
# System: the portal and the apps are tested on the system they are made for (SYSTEM: bazzite), so on Windows only
# core, tools and dev/ run. NEXUS_SYSTEM=bazzite runs the portal and the apps there too.
#
# Interpreter: $PYTHON if set, else the venv for this OS. A venv only runs on the OS that made it, so a checkout
# used from both Linux and Windows keeps one per OS: .venv-linux/ and .venv-windows/ (a plain .venv/ works too).
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-}
if [[ -z "$PY" ]]; then
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*) candidates=(.venv-windows/Scripts/python.exe .venv/Scripts/python.exe) ;;
        *)                    candidates=(.venv-linux/bin/python .venv/bin/python) ;;
    esac
    for candidate in "${candidates[@]}"; do
        [[ -x "$candidate" ]] && PY="$PWD/$candidate" && break
    done
fi
if [[ -z "$PY" ]]; then
    echo "No venv for this OS. Create one, e.g. on Linux:" >&2
    echo "  python3 -m venv .venv-linux && .venv-linux/bin/python -m pip install -r requirements-dev.txt" >&2
    echo "or on Windows (Git Bash):" >&2
    echo "  py -m venv .venv-windows && .venv-windows/Scripts/python.exe -m pip install -r requirements-dev.txt" >&2
    exit 1
fi

case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) system=${NEXUS_SYSTEM:-windows} ;;
    *)                    system=${NEXUS_SYSTEM:-bazzite} ;;
esac

export QT_QPA_PLATFORM=offscreen
export PYTHONDONTWRITEBYTECODE=1
rc=0
dirs=(core tools dev/*)
suite_system=$(tr -d '[:space:]' < SYSTEM 2>/dev/null || true)
if [[ "$suite_system" == "$system" ]]; then
    dirs+=(portal apps/*)
else
    echo "== portal and apps: made for ${suite_system:-no system}, left out on $system (NEXUS_SYSTEM=${suite_system:-...} ./test.sh runs them)"
fi
for dir in "${dirs[@]}"; do
    [[ -d "$dir/tests" ]] || continue
    echo "== $dir"
    (cd "$dir" && "$PY" -m pytest -q -p no:cacheprovider tests "$@") || rc=1
done
exit $rc
