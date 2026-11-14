#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# The portal tests of a release, as Nexus Release Tool's buttons run them, and what they leave on the machine:
#
#   check-release.sh local             # install the portal from this checkout and start it
#   check-release.sh release [TAG]     # download the portal's release (default ps5-portal-v<portal/VERSION>), verify
#                                      # it, install it and start it; while the release is still a draft, the draft
#   check-release.sh draft [TAG]       # the same from the draft the release workflow made (gh, signed in)
#   ... --no-start                     # install only, do not start the portal
#   ... --keep                         # keep what the test installed: it is the machine's own install from then on
#   check-release.sh status            # what of the suite is installed here, and whether a test put it there
#   check-release.sh remove [--purge]  # remove the suite: every app, the portal and Bazzite Test, each with its own
#                                      # uninstaller; --purge also removes their settings and logs
#
# A test on a machine without the suite removes everything again when the portal closes: the portal, Bazzite Test
# and the apps installed during the test. It marks its install (TEST-INSTALL in the portal's folder), which status
# shows. A machine that had the suite installed already keeps it: the test replaces the portal there and removes
# nothing. PS5_RELEASE_URL overrides the download address (tests).
set -euo pipefail
export PATH="$PATH:${HOMEBREW_PREFIX:-/home/linuxbrew/.linuxbrew}/bin"
cd "$(dirname "$0")/.."
REPO=$PWD
URL=${PS5_RELEASE_URL:-https://github.com/RobertoTorino/bazzite-console/releases/download}
GH_REPO_NAME=RobertoTorino/bazzite-console
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/bazzite-console-release-check"
PORTAL="$HOME/.local/bin/bazzite-console-suite"
PORTAL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/bazzite-console-suite/portal"
MARK="$PORTAL_DIR/TEST-INSTALL"        # install.sh empties the folder: an install by hand ends the mark

info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

# The suite's apps as apps.toml lists them, one per line: key, name and launcher, with tabs between.
apps() {
    python3 - "$REPO/portal/apps.toml" <<'EOF'
import os
import sys
import tomllib

with open(sys.argv[1], "rb") as handle:
    for key, app in tomllib.load(handle).get("apps", {}).items():
        print(key, app.get("name", key), os.path.expanduser((app.get("detect") or [""])[0]), sep="\t")
EOF
}

status() {
    local key name launcher version="?" found=0
    if [ -e "$PORTAL" ]; then
        found=1
        [ ! -f "$PORTAL_DIR/VERSION" ] || version=$(tr -d '[:space:]' < "$PORTAL_DIR/VERSION")
        if [ -f "$MARK" ]; then
            echo "Portal $version: a test install ($(head -n 1 "$MARK"))"
        else
            echo "Portal $version: the machine's own install (by hand, or kept from a test)"
        fi
    else
        echo "Portal: not installed"
    fi
    while IFS=$'\t' read -r key name launcher; do
        [ -n "$launcher" ] && [ -e "$launcher" ] || continue
        found=1
        echo "  $name ($key)"
    done < <(apps)
    [ "$found" -eq 1 ] || echo "Nothing of the suite is installed."
}

# Every installed app with its own uninstaller, then the portal, then Bazzite Test (the suite's venv goes with the
# last of them). Arguments: --purge, or none. The list is read on 3, so an uninstaller's sudo keeps the terminal.
remove_suite() {
    local key name launcher failed=0
    while IFS=$'\t' read -r key name launcher <&3; do
        [ "$key" != bazzite ] && [ -n "$launcher" ] && [ -e "$launcher" ] || continue
        info "Removing $name"
        bash "$REPO/apps/$key/install.sh" --uninstall "$@" || { failed=1; echo "$name could not be removed." >&2; }
    done 3< <(apps)
    if [ -e "$PORTAL" ] || [ -d "$PORTAL_DIR" ]; then
        info "Removing the portal"
        bash "$REPO/portal/install.sh" --uninstall "$@" >/dev/null || failed=1
    fi
    if [ -e "$HOME/.local/bin/bazzite-test" ]; then
        info "Removing Bazzite Test (it is in /opt: sudo asks for the password)"
        bash "$REPO/apps/bazzite/install.sh" --uninstall "$@" ||
            { failed=1; echo "Bazzite Test could not be removed." >&2; }
    fi
    rmdir "$(dirname "$PORTAL_DIR")" 2>/dev/null || true
    [ "$failed" -eq 0 ] || die "Not everything could be removed: see above, and check-release.sh status."
    info "The suite is removed."
}

portal_runs() { pgrep -u "$(id -u)" -f 'python.* -m bazzite_console_portal' >/dev/null; }

# After the install ($1: where it came from): mark a test's install, start the portal and remove the test's install
# again when the portal is closed.
finish() {
    if [ "$own" -eq 1 ]; then
        info "The suite was installed here already: this test replaced its portal, and everything stays installed."
    elif [ "$keep" -eq 1 ]; then
        info "Kept (--keep): what this test installed stays, as the machine's own install."
    else
        mkdir -p "$PORTAL_DIR"
        printf '%s, %s\n' "$1" "$(date '+%d-%m-%Y %H:%M')" > "$MARK"
    fi
    if [ "$start" -eq 0 ]; then
        [ ! -f "$MARK" ] || info "A test install: check-release.sh remove takes it away again."
        exit 0
    fi
    if [ ! -f "$MARK" ]; then
        info "Starting the portal. Close it to finish."
        exec "$PORTAL"
    fi
    info "Starting the portal. Close it to finish: the test then removes what it installed."
    "$PORTAL" || true
    sleep 3                             # a portal that starts itself again (its Restart) is back within this
    while portal_runs; do sleep 2; done
    info "The portal is closed: removing the test install"
    remove_suite
}

mode=${1:-}; [ $# -gt 0 ] && shift
tag="" start=1 keep=0 purge=()
for arg in "$@"; do
    case "$arg" in
        --no-start) start=0 ;;
        --keep) keep=1 ;;
        --purge) purge=(--purge) ;;
        ps5-portal-v*) tag=$arg ;;
        *) die "Unknown argument: $arg (see the top of $0)" ;;
    esac
done
[ "$(id -u)" -ne 0 ] || die "Run this as your own user, not with sudo."
[ "${#purge[@]}" -eq 0 ] || [ "$mode" = remove ] || die "--purge only goes with remove."

# The suite is the machine's own when a portal is installed that no test marked.
own=0
[ ! -e "$PORTAL" ] || [ -f "$MARK" ] || own=1

case "$mode" in
    status)
        status
        ;;
    remove)
        status
        remove_suite "${purge[@]}"
        ;;
    local)
        info "Installing the portal from this checkout ($REPO)"
        ./install.sh
        finish "the checkout"
        ;;
    release|draft)
        tag=${tag:-ps5-portal-v$(tr -d '[:space:]' < portal/VERSION)}
        rm -rf "$CACHE"
        mkdir -p "$CACHE"
        cd "$CACHE"
        if [ "$mode" = release ]; then
            info "Downloading $tag"
            if curl -fsSL -o "$tag.tar.gz" "$URL/$tag/$tag.tar.gz"; then
                curl -fsSL -o SHA256SUMS "$URL/$tag/SHA256SUMS" || die "$tag has no SHA256SUMS."
            else
                # A draft has no public address: GitHub answers 404 until the release is published.
                draft=$(gh release view "$tag" --repo "$GH_REPO_NAME" --json isDraft --jq .isDraft 2>/dev/null) || draft=""
                [ "$draft" = true ] ||
                    die "$tag has no $tag.tar.gz yet. Is the tag pushed, and has GitHub finished the release workflow?"
                info "$tag is still a draft on GitHub: testing the draft. Publish it after the test."
                mode=draft
            fi
        fi
        if [ "$mode" = draft ]; then
            info "Downloading the draft of $tag"
            rm -f "$tag.tar.gz" SHA256SUMS
            gh release download "$tag" --pattern "$tag.tar.gz" --pattern SHA256SUMS --dir . --repo "$GH_REPO_NAME" ||
                die "No draft of $tag to download. Has the release workflow built it, and is gh signed in?"
        fi
        info "Verifying the checksum"
        sha256sum --check SHA256SUMS || die "$tag.tar.gz does not match its SHA256SUMS."
        tar -xzf "$tag.tar.gz"
        info "Installing $tag"
        (cd "$tag" && ./install.sh)
        cd "$REPO"
        finish "$mode $tag"
        ;;
    *) die "Usage: check-release.sh local|release|draft [ps5-portal-vX.Y.Z] [--no-start] [--keep] | status | remove [--purge]" ;;
esac
