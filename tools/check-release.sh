#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# The portal checks of a release of the Bazzite Console Suite, as the Nexus Release Tool's buttons run them (Linux),
# and what they leave on the machine:
#
#   check-release.sh local             # before the push: install the portal from this checkout and start it
#                                      # with the apps from the pinned GitHub releases (--source release)
#   check-release.sh release [TAG]     # after release.yml built the portal: download the published portal
#                                      # release (default ps5-portal-v<portal/VERSION>), verify it, install it
#                                      # and start it; while the release is still a draft, the draft
#   check-release.sh draft [TAG]       # the device test of a release: the portal's draft release the
#                                      # release workflow made, downloaded with gh (a draft needs the sign-in)
#   ... --no-start                     # install only, do not start the portal
#   ... --keep                         # keep what the test installed: it is the machine's own install from then on
#   check-release.sh status            # what of the suite is installed here, and whether a test put it there
#   check-release.sh remove [--purge]  # remove the suite: every app, the portal and Board Test, each with its own
#                                      # uninstaller; --purge also removes their settings, history and results
#
# A test on a machine without the suite removes everything again when the portal closes: the portal, Board Test
# and the apps installed during the test. It marks its install (TEST-INSTALL in the suite's folder, with the time
# of the portal's launcher, which every install writes anew: an install by hand ends the mark), which status
# shows. A machine that had the suite installed already keeps it: the test replaces the portal there and removes
# nothing. The release is downloaded into ~/.cache/bazzite-console-release-check/, emptied first; run ./install.sh in the
# checkout to go back to the portal from the checkout. PS5_RELEASE_URL overrides the download address (tests).
set -euo pipefail
# Homebrew's own folder (gh), which the terminal NRT opens lacks: a login shell does not read .bashrc, where brew
# shellenv adds it. HOMEBREW_PREFIX names another.
export PATH="$PATH:${HOMEBREW_PREFIX:-/home/linuxbrew/.linuxbrew}/bin"
cd "$(dirname "$0")/.."                 # the suite's folder: its install.sh and portal/VERSION
REPO=$PWD
URL=${PS5_RELEASE_URL:-https://github.com/RobertoTorino/bazzite-console/releases/download}
GH_REPO_NAME=RobertoTorino/bazzite-console
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/bazzite-console-release-check"
PORTAL="$HOME/.local/bin/bazzite-console-suite"
SUITE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/bazzite-console-suite"
PORTAL_DIR="$SUITE_DIR/portal"          # the installed portal (portal/install.sh)
STATE_DIR="$SUITE_DIR/state"            # what the portal remembers
MARK="$SUITE_DIR/TEST-INSTALL"          # where the test came from, and the time of the launcher it installed

info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }
die()  { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

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

launcher_time() { stat -c %.9Y "$PORTAL" 2>/dev/null || echo none; }

# Whether the portal installed is a test's: the mark is there and names the launcher as it is (an install by hand
# writes the launcher anew, which ends the mark).
test_install() { [ -f "$MARK" ] && [ -e "$PORTAL" ] && [ "$(sed -n 2p "$MARK")" = "$(launcher_time)" ]; }

status() {
    local key name launcher version="" found=0
    if [ -e "$PORTAL" ]; then
        found=1
        [ ! -f "$PORTAL_DIR/VERSION" ] || version=$(tr -d '[:space:]' < "$PORTAL_DIR/VERSION")
        if test_install; then
            echo "Portal ${version:-?}: a test install ($(head -n 1 "$MARK"))"
        else
            echo "Portal ${version:-?}: the machine's own install (by hand, or kept from a test)"
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

# Every installed app with its own uninstaller, then the portal, then Board Test when the portal's uninstaller left
# it (the suite's venv goes with the last of them). Arguments: --purge, or none. The list is read on 3, so an
# uninstaller's sudo keeps the terminal. A test's install leaves nothing: what its portal remembered (the state
# folder, which the portal's uninstaller keeps without --purge) goes too. The mark is read first: it goes with the
# portal.
remove_suite() {
    local key name launcher failed=0 was_test=0
    ! test_install || was_test=1
    while IFS=$'\t' read -r key name launcher <&3; do
        [ "$key" != board ] && [ -n "$launcher" ] && [ -e "$launcher" ] || continue
        info "Removing $name"
        bash "$REPO/apps/$key/install.sh" --uninstall "$@" < /dev/null ||
            { failed=1; echo "$name could not be removed." >&2; }
    done 3< <(apps)
    if [ -e "$PORTAL" ] || [ -d "$PORTAL_DIR" ]; then
        info "Removing the portal and Board Test (Board Test is in /opt: sudo asks for the password)"
        bash "$REPO/portal/install.sh" --uninstall "$@" < /dev/null || failed=1
    fi
    if [ -e "$HOME/.local/bin/ps5-board-test" ]; then
        info "Removing Board Test (it is in /opt: sudo asks for the password)"
        bash "$REPO/apps/board/install.sh" --uninstall "$@" < /dev/null ||
            { failed=1; echo "Board Test could not be removed." >&2; }
    fi
    rm -f "$MARK"
    [ "$was_test" -eq 0 ] || rm -rf "${STATE_DIR:?}"
    rmdir "$SUITE_DIR" 2>/dev/null || true
    [ "$failed" -eq 0 ] || die "Not everything could be removed: see above, and check-release.sh status."
    info "The suite is removed."
}

portal_runs() { pgrep -u "$(id -u)" -f 'python.* -m bazzite_console_portal' >/dev/null; }

# After the install ($1: where it came from; the rest: the portal's arguments): mark a test's install, start the
# portal and remove the test's install again when the portal is closed.
finish() {
    local where=$1; shift
    if [ "$own" -eq 1 ]; then
        info "The suite was installed here already: this test replaced its portal, and everything stays installed."
    elif [ "$keep" -eq 1 ]; then
        info "Kept (--keep): what this test installed stays, as the machine's own install."
    else
        mkdir -p "$SUITE_DIR"
        printf '%s, %s\n%s\n' "$where" "$(date '+%d-%m-%Y %H:%M')" "$(launcher_time)" > "$MARK"
    fi
    if [ "$start" -eq 0 ]; then
        ! test_install || info "A test install: check-release.sh remove takes it away again."
        exit 0
    fi
    if ! test_install; then
        info "Starting the portal. Close it to finish."
        exec "$PORTAL" "$@"
    fi
    info "Starting the portal. Close it to finish: the test then removes what it installed."
    "$PORTAL" "$@" || true
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
        ps5-portal-v*)  tag=$arg ;;
        *) die "Unknown argument: $arg (see the top of $0)" ;;
    esac
done
[ "$(id -u)" -ne 0 ] || die "Run this as your own user, not with sudo."
[ "${#purge[@]}" -eq 0 ] || [ "$mode" = remove ] || die "--purge only goes with remove."

# The suite is the machine's own when a portal is installed that no test marked.
own=0
[ ! -e "$PORTAL" ] || test_install || own=1

case "$mode" in
    status)
        status
        ;;
    remove)
        status
        remove_suite ${purge[@]+"${purge[@]}"}
        ;;
    local)
        info "Installing the portal from this checkout ($REPO)"
        ./install.sh
        info "The portal starts with the apps from the pinned GitHub releases (--source release)."
        finish "the checkout" --source release
        ;;
    release|draft)
        tag=${tag:-ps5-portal-v$(tr -d '[:space:]' < portal/VERSION)}
        rm -rf "$CACHE"; mkdir -p "$CACHE"; cd "$CACHE"
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
                die "No draft of $tag to download (gh ended with $?). Has the release workflow built it, and is gh signed in?"
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
