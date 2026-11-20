#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Runs the jobs of the CI workflow (ci.yml) here, as GitHub runs them (Python 3.12,
# each job with only its own requirements), in a container: tools/ci_local.py inside
# tools/ci-local/Containerfile. Before a push or a release, so "passes here, fails in CI" shows up here first.
#
#   tools/ci-local.sh                                      # the workflows this push starts on GitHub (--all: every one)
#   tools/ci-local.sh shell pytest/tools                   # jobs by name
#   tools/ci-local.sh --list                               # the jobs
#
# Needs podman (Bazzite has it) or docker. The image is built the first time and when the Containerfile changes;
# venvs, pip's downloads and the logs stay in ~/.cache/bazzite-console-ci-local. Linux only.
set -euo pipefail
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then
    sed -n '3,12p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)

die() { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }
info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }

ENGINE=$(command -v podman || command -v docker || true)
[ -n "$ENGINE" ] || die "Needs podman or docker."
CONTAINERFILE="$ROOT/tools/ci-local/Containerfile"
IMAGE="localhost/bazzite-console-ci-local:$(sha256sum "$CONTAINERFILE" | cut -c1-12)"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/bazzite-console-ci-local"
# Remote Play's FFmpeg, built in the container like CI's (the host's links its newer libva): its own cache folder.
FFMPEG="$CACHE/remoteplay-ffmpeg"
mkdir -p "$CACHE" "$FFMPEG"

# One run at a time: two runs share the venvs, pip's cache and the logs here, and one broke the other (owner,
# 15-11-2026: a crash in a Qt test and a run that never ended, while a second run went on beside them). A second run
# waits for the first; the lock goes with the container run below (exec keeps it open) and ends with it.
case " $* " in *" --list "*) ;; *)
    exec 9>"$CACHE/run.lock"
    if ! flock -n 9; then
        info "Another ci-local.sh run is going on this computer: waiting until it ends"
        flock 9
    fi
    # What earlier runs and tests left behind goes first (venvs no run uses, old test files in /tmp, which is
    # kept in memory): tools/clean_caches.py. It never stops a run.
    python3 "$ROOT/tools/clean_caches.py" --quiet || true ;;
esac

if ! "$ENGINE" image inspect "$IMAGE" >/dev/null 2>&1; then
    info "Building the CI image (once; a few minutes)"
    "$ENGINE" build -q -t "$IMAGE" -f "$CONTAINERFILE" "$ROOT/tools/ci-local" >/dev/null 2>"$CACHE/image-build.log" ||
        die "Building the image failed: $CACHE/image-build.log"
    # earlier versions of the image: the Containerfile changed since
    "$ENGINE" images --format '{{.Repository}}:{{.Tag}}' | grep '^localhost/bazzite-console-ci-local:' | grep -vx "$IMAGE" |
        xargs -r "$ENGINE" rmi -f >/dev/null 2>&1 || true
fi

# The jobs run as you, as on GitHub (the installers refuse root), in a copy named as the checkout (GitHub's is named
# as the repository: the tests may read the folder's name). FFmpeg's build names its own folder in its pkg-config
# files, so it is always mounted at the same place: ~/.cache/ps5-remoteplay in the container's home.
if [ "${ENGINE##*/}" = podman ]; then as_user=(--userns=keep-id); else as_user=(--user "$(id -u):$(id -g)"); fi
exec "$ENGINE" run --rm --init "${as_user[@]}" \
    --tmpfs "$HOME:rw,mode=1777" -e HOME="$HOME" \
    -v "$ROOT:/src:ro,z" -v "$CACHE:/cache:z" -v "$FFMPEG:$HOME/.cache/ps5-remoteplay:z" \
    -e CI_LOCAL_HOST_LOGS="$CACHE/logs" -e CARGO_HOME=/cache/cargo -e CI_LOCAL_WORK="/tmp/ci-local-work/${ROOT##*/}" \
    "$IMAGE" python3 /src/tools/ci_local.py "$@"
