#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# The system libraries Qt needs on a GitHub runner, for the CI workflows' tests and ci.yml's picture of the portal.
# Libraries are looked up by file (ldconfig), not by package: Ubuntu 24.04 renamed some packages (libglib2.0-0t64).
# The mirror is asked only when one is missing (apt-get update, run in every job, hung a CI job for 20 minutes on
# 23-10-2026), and then once for all jobs: tools/ci-apt.sh keeps the packages in GitHub's cache. Ubuntu 26.04's
# runner lacks libEGL and libpulse, so every job downloaded ten packages.
#
#   tools/ci-qt-libs.sh           # Qt's libraries
#   tools/ci-qt-libs.sh --pulse   # and libpulse0, for Qt Multimedia in the apps' tests
#   tools/ci-qt-libs.sh --fetch   # only fill the kept folder (the plan job), with or without --pulse
set -euo pipefail
# shellcheck source=tools/ci-apt.sh
source "$(dirname "${BASH_SOURCE[0]}")/ci-apt.sh"

libs=(libEGL.so.1 libGL.so.1 libxkbcommon.so.0 libdbus-1.so.3 libfontconfig.so.1 libglib-2.0.so.0)
packages=(libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0)
mode=install
for option in "$@"; do
    case "$option" in
        --pulse) libs+=(libpulse.so.0); packages+=(libpulse0) ;;
        --fetch) mode=fetch ;;
        *) echo "unknown option: $option" >&2; exit 2 ;;
    esac
done

known=$(ldconfig -p)
missing=()
for lib in "${libs[@]}"; do
    grep -qF -- "$lib (" <<<"$known" || missing+=("$lib")
done
if [ ${#missing[@]} -eq 0 ]; then
    echo "All on the runner already: ${libs[*]}"
    exit 0
fi

echo "Missing: ${missing[*]}"
kept_packages "$mode" "${packages[@]}"
