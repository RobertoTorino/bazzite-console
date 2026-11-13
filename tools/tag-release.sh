#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Build and publish already-committed Bazzite Console releases with gh. This does not commit or push source.
set -euo pipefail

SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then
    echo "Usage: tools/tag-release.sh ps5-<app>-v<x.y.z> [...]"
    echo "Builds releases from the pushed HEAD and publishes their assets with gh."
    echo "A portal release downloads its required app release as the bundle."
    echo "Remote Play also builds its native decoder wheel (maturin and a C toolchain required)."
    exit 0
fi
[[ $# -ge 1 ]] || { echo "Usage: tools/tag-release.sh ps5-<app>-v<x.y.z> [...]" >&2; exit 2; }
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
command -v gh >/dev/null || { echo "GitHub CLI (gh) is required to publish a release." >&2; exit 1; }

GIT_ROOT=$(git -C "$SUITE" rev-parse --show-toplevel)
SUITE_REL=$(realpath --relative-to="$GIT_ROOT" "$SUITE")
git -C "$GIT_ROOT" fetch -q origin main
git -C "$GIT_ROOT" merge-base --is-ancestor HEAD origin/main || {
    echo "HEAD is not on origin/main; push the release commit before publishing." >&2
    exit 1
}

WORK=
cleanup() {
    [[ -z "$WORK" ]] || rm -rf "$WORK"
}
trap cleanup EXIT

for TAG in "$@"; do
    parsed=$("$PY" "$SUITE/tools/suites.py" --tag "$TAG") || exit 1
    read -r suite app version <<<"$parsed"
    [[ "$suite" == "." ]] || { echo "$TAG does not belong to this Bazzite Console checkout." >&2; exit 1; }
    if [[ "$app" == portal ]]; then
        source_dir=portal
    else
        source_dir="apps/$app"
    fi
    [[ -f "$SUITE/$source_dir/VERSION" ]] || { echo "$TAG has no $source_dir/VERSION." >&2; exit 1; }
    actual=$("$PY" - "$SUITE/$source_dir/VERSION" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).read_text(encoding="utf-8").strip())
PY
    )
    [[ "$actual" == "$version" ]] || {
        echo "$TAG expects version $version, but $source_dir/VERSION is $actual." >&2
        exit 1
    }

    REPO_PATH="$SUITE_REL/$source_dir"
    git -C "$GIT_ROOT" diff --quiet HEAD -- "$REPO_PATH" || {
        echo "$REPO_PATH has uncommitted changes; commit and push them before publishing." >&2
        exit 1
    }
    [[ -z "$(git -C "$GIT_ROOT" status --porcelain -- "$REPO_PATH")" ]] || {
        echo "$REPO_PATH has untracked changes; commit and push them before publishing." >&2
        exit 1
    }

    WORK=$(mktemp -d "${TMPDIR:-/tmp}/bazzite-release.XXXXXX")
    args=("$TAG" "$WORK/build")
    if [[ "$app" == portal ]]; then
        bundle_tag=$("$PY" - "$SUITE/portal/apps.toml" <<'PY'
import sys
import tomllib
from pathlib import Path

manifest = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = next((entry for entry in manifest.get("apps", {}).values() if entry.get("required")), None)
if required is None or not required.get("tag"):
    raise SystemExit("portal/apps.toml has no pinned required app release")
print(required["tag"])
PY
        )
        mkdir "$WORK/bundle"
        gh release download "$bundle_tag" --dir "$WORK/bundle" \
            --pattern "$bundle_tag.tar.gz" --pattern SHA256SUMS
        args+=(--bundle "$WORK/bundle")
    fi
    if [[ "$app" == remoteplay ]]; then
        command -v maturin >/dev/null || {
            echo "maturin is required to build the Remote Play release wheel." >&2
            exit 1
        }
        ffmpeg_dir=${PS5_FFMPEG_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/ps5-remoteplay/ffmpeg-7.1.2}
        if [[ ! -f "$ffmpeg_dir/lib/pkgconfig/libavcodec.pc" ]]; then
            "$SUITE/apps/remoteplay/native/ffmpeg/build.sh" "$ffmpeg_dir"
        fi
        mkdir "$WORK/wheel"
        (
            cd "$SUITE/apps/remoteplay/native"
            PS5_FFMPEG_DIR="$ffmpeg_dir" maturin build --release --features decoder --out "$WORK/wheel"
        )
        PS5_NATIVE_WHEEL_DIR="$WORK/wheel" "$PY" "$SUITE/tools/build_release.py" "${args[@]}"
    else
        "$PY" "$SUITE/tools/build_release.py" "${args[@]}"
    fi
    commit=$(git -C "$GIT_ROOT" rev-parse HEAD)
    "$SUITE/tools/publish_release.sh" "$TAG" "$commit" "$WORK/build"
    cleanup
    WORK=
done
