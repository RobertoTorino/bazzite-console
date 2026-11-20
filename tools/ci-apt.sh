#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Packages from Ubuntu's mirror for a CI job, downloaded once and not per job (owner, 20-11-2026: "every test has to
# download that same font over and over"): apt keeps what it downloads in a folder that GitHub's cache holds
# (.github/actions/runner-packages), and takes from that folder what is there already. ci.yml's plan job fills the
# folder before the other jobs start, so they install without the mirror. Some runners reach the mirror at about
# 45 kB/s: 40 jobs each downloaded the same 13 MB font and ten libraries, and the slow ones failed at the step's 5
# minutes before a test ran.
#
# Read by tools/ci-qt-libs.sh and tools/ci-font.sh (source), never run by itself:
#
#   kept_packages install <package> ...   # download what the folder lacks, then install
#   kept_packages fetch <package> ...     # only fill the folder
#
# The folder is CI_APT_DIR, ~/.cache/ci-apt without it.

# The runner's mirror list names Azure's mirror first and Ubuntu's own after it: without the first line apt takes
# the next, when the first is the slow one.
other_mirror() {
    local list=/etc/apt/apt-mirrors.txt
    if [ -f "$list" ] && grep -q 'azure\.archive' "$list" && grep -qv 'azure\.archive' "$list"; then
        echo "Taking Azure's mirror out of $list: the next one in it serves the packages"
        sudo sed -i '/azure\.archive/d' "$list"
    fi
}

kept_packages() {
    local mode=$1 kept="${CI_APT_DIR:-$HOME/.cache/ci-apt}" attempt limit=20
    shift
    mkdir -p "$kept/partial"
    local apt=(-o Dir::Cache::archives="$kept" -o APT::Keep-Downloaded-Packages=true -o Acquire::Retries=3
               -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30)
    # apt runs as root and leaves its lock and its partial downloads in the folder: ours again when the script
    # ends, however it ends, so the cache can read and write it.
    # shellcheck disable=SC2064  # the folder as it is now
    trap "sudo chown -R '$(id -u):$(id -g)' '$kept'; rm -rf '$kept/partial' '$kept/lock'" EXIT
    # The first try is cut off after 20 seconds, as apt's own timeouts do not end a download that only slows down:
    # all of it is 18 MB, a second or two from a mirror at its usual speed, and where Azure's mirror gave 109 kB/s
    # the next one gave 26 MB/s (20-11-2026). The next try goes on where the first stopped (the partial download
    # stays), from that other mirror and with its package lists, and has 90 seconds.
    # The runner's own lists usually name the packages' versions still, so the first try asks for no lists.
    for attempt in 1 2 3; do
        if sudo timeout -k 5 "$limit" apt-get "${apt[@]}" install -y -q --download-only "$@"; then
            break
        fi
        [ "$attempt" -lt 3 ] || { echo "Ubuntu's mirrors did not deliver $* in three tries" >&2; return 1; }
        echo "Try $attempt failed or was too slow: once more"
        other_mirror
        sudo timeout -k 5 40 apt-get "${apt[@]}" update -q || true
        limit=90
    done
    [ "$mode" = fetch ] || sudo apt-get "${apt[@]}" install -y -q --no-download "$@"
}
