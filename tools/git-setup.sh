#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Register the CHANGELOG merge driver for this checkout.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
PYTHON=${PYTHON:-python3}
command -v "$PYTHON" >/dev/null 2>&1 || {
    printf 'git-setup: Python not found: %s\n' "$PYTHON" >&2
    exit 1
}

printf -v DRIVER '%q %q %%O %%A %%B' "$PYTHON" "$ROOT/tools/merge_changelog.py"
set_config() {
    local key=$1 value=$2
    if [[ $(git config --local --get "$key" || true) != "$value" ]]; then
        git config --local "$key" "$value"
        printf 'git-setup: %s configured\n' "$key"
    fi
}

set_config merge.changelog.name "CHANGELOG entries"
set_config merge.changelog.driver "$DRIVER"
