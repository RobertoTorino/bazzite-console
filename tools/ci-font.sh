#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Bazzite's font (Noto Sans) on a GitHub runner, for the tests that measure a window and for the picture of the
# portal: the runner's own font is wider and lower. Its package is downloaded once for all jobs, not per job:
# tools/ci-apt.sh keeps it in GitHub's cache. Where the font is installed already (tools/ci-local.sh's image)
# nothing happens.
#
#   tools/ci-font.sh           # install the font
#   tools/ci-font.sh --fetch   # only fill the kept folder (the plan job: it measures no window)
set -euo pipefail
# shellcheck source=tools/ci-apt.sh
source "$(dirname "${BASH_SOURCE[0]}")/ci-apt.sh"

if [ -f /usr/share/fonts/truetype/noto/NotoSans-Regular.ttf ]; then
    echo "Noto Sans is installed already"
    exit 0
fi
if [ "${1:-}" = --fetch ]; then
    kept_packages fetch fonts-noto-core
    exit 0
fi
kept_packages install fonts-noto-core
fc-match sans | grep -F "Noto Sans"
