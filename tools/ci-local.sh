#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
PY=${PYTHON:-}
if [[ -z "$PY" ]]; then
    for candidate in "$SUITE/.venv-linux/bin/python" python3; do
        if command -v "$candidate" >/dev/null 2>&1 || [[ -x "$candidate" ]]; then
            PY=$candidate
            break
        fi
    done
fi
[[ -n "$PY" ]] || { echo "No Python interpreter found." >&2; exit 1; }

export QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-offscreen}
"$PY" "$SUITE/tools/check_versions.py"
"$PY" "$SUITE/tools/check_manifest.py"
"$PY" -m pytest -q "$SUITE/tools/tests"
"$PY" -m pytest -q "$SUITE/dev/dash/tests"
for app in demo itests nrt sounds deps; do
    "$PY" -m pytest -q --import-mode=importlib "$SUITE/dev/$app/tests"
done
