#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Starts the release front end, Nexus Release Tool (dev/nrt), with the checkout's dev venv.
# It only edits files; committing, tagging and pushing stay with you.
#
#   tools/nrt.sh                              # open it (dev/nrt/run.sh)
#   tools/nrt.sh --list                       # the apps, their tags and what needs a release
#   tools/nrt.sh --install                    # app menu entry and Desktop icon (dev/nrt/install.sh)
#   tools/nrt.sh --install --no-desktop-shortcut
#   tools/nrt.sh --uninstall [--purge]        # remove them again (--purge: and the settings)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
APP="$ROOT/dev/nrt"
case "${1:-}" in
    --install) shift; exec bash "$APP/install.sh" "$@" ;;
    --uninstall) exec bash "$APP/install.sh" "$@" ;;        # --uninstall [--purge]
    -h|--help) sed -n '3,10p' "$0" | sed 's/^# \{0,1\}//' ;;
    *) exec bash "$APP/run.sh" "$@" ;;
esac
