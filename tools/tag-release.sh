#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Tags release commits and pushes the tags, but only when they can be built: HEAD must hold each tag's version
# (the bump is committed), have no uncommitted changes in that folder, be pushed to origin/main, and have passed CI
# on GitHub (tools/ci_state.py; it waits while CI still runs, up to an hour): ci.yml, which checks the suite, core,
# the tools and the repository's rules. A portal tag also needs every app release HEAD's apps.toml pins: tagged on
# origin and pinned with its sha256. A plain `git tag` tags whatever HEAD is, also a commit from before the bump or
# one CI failed, which release.yml then refuses. release.yml builds and publishes each tag pushed.
#
#   tools/tag-release.sh ps5-portal-v0.9.5
#   tools/tag-release.sh ps5-fan-v2.0.1 ps5-upscaler-v0.1.2
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

die() { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }
info() { printf '\033[1;35m==>\033[0m %s\n' "$1"; }

if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then
    sed -n '3,11p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi
prefix=$(tr -d '[:space:]' < TAG_PREFIX)
[ $# -gt 0 ] || die "Usage: $0 ${prefix}<name>-v<x.y.z> [...], for example $0 ${prefix}portal-v0.9.5"
command -v python3 >/dev/null || die "No python3 found."

tags=()
for tag in "$@"; do
    read -r name version < <(python3 tools/suites.py --tag "$tag") ||
        die "$tag is not ${prefix}<name>-v<x.y.z> (tools/suites.py --tag)."
    if [ "$name" = portal ]; then dir=portal; else dir=apps/$name; fi
    [ -f "$dir/VERSION" ] || die "$tag: there is no $dir/VERSION."
    # A new app is not in HEAD yet: git show fails, which pipefail would turn into a silent exit 128.
    committed=$(git show "HEAD:$dir/VERSION" 2>/dev/null | tr -d '[:space:]') || committed=""
    if [ "$committed" != "$version" ]; then
        if [ "$(tr -d '[:space:]' <"$dir/VERSION")" = "$version" ]; then
            die "$tag: the bump to $version is not committed yet (HEAD has $dir/VERSION ${committed:-not at all}). Commit it, push, then run this again."
        fi
        die "$tag: HEAD has $dir/VERSION ${committed:-not at all}, not $version."
    fi
    git diff --quiet HEAD -- "$dir" ||
        die "$tag: $dir has changes that are not committed (git status $dir). Commit them first: the tag gets only what is committed."
    git rev-parse -q --verify "refs/tags/$tag" >/dev/null &&
        die "$tag exists already. To move it: git tag -d $tag && git push origin :refs/tags/$tag (as a repository admin: the release-tag ruleset lets only admins delete a tag)"
    if [ "$name" = portal ] && git cat-file -e "HEAD:portal/apps.toml" 2>/dev/null; then
        # release.yml builds a portal only on app releases that exist, pinned with their checksum.
        pins=$(git show "HEAD:portal/apps.toml" 2>/dev/null | python3 -c '
import sys, tomllib
for key, app in tomllib.loads(sys.stdin.read()).get("apps", {}).items():
    print(app.get("tag", ""), app.get("sha256", "") or "-")') ||
            die "$tag: could not read portal/apps.toml at HEAD."
        remote=$(git ls-remote --tags origin) || die "Could not reach origin to check the pinned app releases."
        while read -r pin sha; do
            [ -n "$pin" ] || continue
            awk -v ref="refs/tags/$pin" '$2 == ref { found = 1 } END { exit !found }' <<<"$remote" ||
                die "$tag: apps.toml pins $pin, which is not tagged yet. Tag the apps first ($0 $pin), then pin their releases and commit, push and tag the portal."
            [ "$sha" != - ] ||
                die "$tag: apps.toml pins $pin without its sha256. Pin it when GitHub has built it (tools/pin_app.py), commit, push, then tag the portal."
        done <<<"$pins"
    fi
    tags+=("$tag")
done

git fetch -q origin main || die "Could not reach origin to check that HEAD is pushed."
git merge-base --is-ancestor HEAD origin/main ||
    die "HEAD ($(git rev-parse --short HEAD)) is not on origin/main yet: git push first, then run this again."
head=$(git rev-parse HEAD)
info "Checking that CI (ci.yml) passed on ${head:0:7} (waits while it runs, up to an hour)"
python3 tools/ci_state.py --wait 60 "$head" ||
    die "CI has not passed on HEAD (${head:0:7}), so it gets no tag: fix what failed, commit and push, then run this again."

for tag in "${tags[@]}"; do
    git tag "$tag"
    git push -q origin "$tag"
    info "Tagged ${head:0:7} as $tag and pushed it: release.yml builds and publishes it now."
done
