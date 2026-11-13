#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Build the required app and portal releases, then install the portal tarball with its bundled app.
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
REPO=$SUITE
NEXUS=$(cd "$SUITE/.." && pwd)      # the Nexus checkout the suite is cloned into: the Nexus tools
GIT_ROOT=$(git -C "$SUITE" rev-parse --show-toplevel)
SUITE_REL=$(realpath --relative-to="$GIT_ROOT" "$SUITE")
T=$(mktemp -d "${TMPDIR:-/tmp}/bazzite-console-release-test.XXXXXX")
trap 'rm -rf "$T"' EXIT
MODE=${1:-local}
PORTAL_TAG=${2:-}
if [[ "$MODE" != local && "$MODE" != release ]] || [[ "$MODE" == release && -z "$PORTAL_TAG" ]]; then
    echo "Usage: tools/installer-tests/release.sh [local | release PORTAL-TAG]" >&2
    exit 2
fi
if [[ "$MODE" == release ]]; then
    command -v gh >/dev/null || { echo "GitHub CLI (gh) is required to download a release." >&2; exit 1; }
    mkdir -p "$T/download"
    gh release download "$PORTAL_TAG" --dir "$T/download" \
        --pattern "$PORTAL_TAG.tar.gz" --pattern SHA256SUMS || exit 1
fi
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
if [[ "$MODE" == local ]]; then
    APP="ps5-bazzite-v$(tr -d '[:space:]' < "$SUITE/apps/bazzite/VERSION")"
    PORTAL="ps5-portal-v$(tr -d '[:space:]' < "$SUITE/portal/VERSION")"
    export SOURCE_DATE_EPOCH=1790000000
    # A copy of the Nexus checkout as the tools know it: the Nexus tools at its root, and this suite as git sees it
    # (tracked and new files, nothing ignored) in its folder.
    N=$T/nexus
    S=$N/${SUITE##*/}
    mkdir -p "$S" "$T/build-app" "$N/tools"
    cp "$NEXUS"/tools/*.py "$N/tools/"
    git -C "$GIT_ROOT" ls-files -z --cached --others --exclude-standard -- "$SUITE_REL/" |
        while IFS= read -r -d '' f; do
            f=${f#"$SUITE_REL"/}
            [ -e "$REPO/$f" ] && printf '%s\0' "$f"
        done | tar -C "$REPO" --null -T - -cf - |
        tar -xf - -C "$S"

    echo "== 1. build the app and portal releases"
    /usr/bin/python3 "$N/tools/build_release.py" --suite "${SUITE##*/}" "$APP" "$T/build-app" > "$T/build-app.log" 2>&1 || {
        cat "$T/build-app.log"; exit 1;
    }
    /usr/bin/python3 "$S/tools/pin_app.py" "$APP" \
        --sha256 "$(cut -d' ' -f1 "$T/build-app/SHA256SUMS")" > "$T/pin.log" 2>&1 || {
        cat "$T/pin.log"; exit 1;
    }
    /usr/bin/python3 "$S/tools/check_manifest.py" > "$T/manifest.log" 2>&1 || {
        cat "$T/manifest.log"; exit 1;
    }
    mkdir -p "$T/bundle"
    cp "$T/build-app/$APP.tar.gz" "$T/build-app/SHA256SUMS" "$T/bundle/"
    /usr/bin/python3 "$N/tools/build_release.py" --suite "${SUITE##*/}" "$PORTAL" "$T/build-portal" --bundle "$T/bundle" \
        > "$T/build-portal.log" 2>&1 || { cat "$T/build-portal.log"; exit 1; }
    check "app and portal tarballs built with valid checksums" \
        "[ -f $T/build-app/$APP.tar.gz ] && [ -f $T/build-portal/$PORTAL.tar.gz ] && \
         (cd $T/build-app && sha256sum --check --quiet SHA256SUMS) && \
         (cd $T/build-portal && sha256sum --check --quiet SHA256SUMS)"
    mkdir -p "$T/unpacked"
    tar -xzf "$T/build-portal/$PORTAL.tar.gz" -C "$T/unpacked"
    PORTAL_DIR="$T/unpacked/$PORTAL"
else
    PORTAL=$PORTAL_TAG
    (cd "$T/download" && sha256sum --check --quiet SHA256SUMS) || {
        echo "The published portal release failed its SHA256SUMS check." >&2; exit 1;
    }
    mkdir -p "$T/unpacked"
    tar -xzf "$T/download/$PORTAL.tar.gz" -C "$T/unpacked"
    PORTAL_DIR="$T/unpacked/$PORTAL"
    APP=$(find "$PORTAL_DIR/bundled" -mindepth 1 -maxdepth 1 -type d -name 'ps5-bazzite-v*' -printf '%f\n' | head -n 1)
    [[ -n "$APP" ]] || { echo "$PORTAL has no bundled Bazzite Test release." >&2; exit 1; }
fi

check "portal and bundled app installers are executable" \
    "[ -x $PORTAL_DIR/install.sh ] && [ -x $PORTAL_DIR/bundled/$APP/install.sh ]"
(cd /tmp && "$PORTAL_DIR/install.sh" > "$T/install.log" 2>&1); rc=$?
check "portal install succeeds" "[ $rc -eq 0 ]"
check "required app was installed" "[ -f $T/opt/bazzite-test/bazzite_test/main_window.py ]"
check "portal launcher was installed" "[ -x $HOME/.local/bin/bazzite-console-suite ]"

[ $fail -eq 0 ] && echo "ALL OK" || { cat "$T/install.log"; exit 1; }
exit "$fail"
