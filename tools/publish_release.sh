#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Publishes one release of the Bazzite Console Suite from build_release.py's folder: <tag>.tar.gz, SHA256SUMS, the
# title (title.txt) and the notes (notes.md). The release workflow (release.yml) runs it with gh
# signed in (GH_TOKEN, GH_REPO).
#
#   publish_release.sh TAG COMMIT DIR            # published; the tag is made on COMMIT when it is not there yet
#   publish_release.sh TAG COMMIT DIR --draft    # a draft aimed at COMMIT: no tag until it is published
#
# GitHub's "Latest" is the newest portal: a portal published here becomes it, an app release never does, and a draft
# cannot be it (Nexus Release Tool's Publish makes it so). A release that is out already gets the assets again
# (--clobber); a draft is made anew, so a run started again leaves one draft of the newest build, and
# one that is out already is left alone. Each try that fails is tried again, up to five times.
set -euo pipefail
[ $# -ge 3 ] || { sed -n '7,8p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
tag=$1 commit=$2 dir=$3 draft=false
[ "${4:-}" = --draft ] && draft=true
title=$(cat "$dir/title.txt")             # the suite's and the app's names (build_release.py's release_title)
prefix=$(tr -d '[:space:]' < "$(dirname "${BASH_SOURCE[0]}")/../TAG_PREFIX")     # the suite's tags: ps5-...
assets=("$dir/$tag.tar.gz" "$dir/SHA256SUMS")

state() {                                 # draft, published or none
    local is_draft
    if is_draft=$(gh release view "$tag" --json isDraft --jq .isDraft 2>/dev/null); then
        [ "$is_draft" = true ] && echo draft || echo published
    else
        echo none
    fi
}

publish() {
    case "$(state)" in
        published)
            if $draft; then
                echo "$tag is out already: left as it is"
                return 0
            fi
            gh release upload "$tag" "${assets[@]}" --clobber ;;
        draft)
            gh release delete "$tag" --yes                      # a draft has no tag: nothing else goes with it
            create ;;
        none)
            create ;;
    esac
}

create() {
    local latest=false
    [[ "$tag" == "${prefix}portal-v"* ]] && ! $draft && latest=true
    local args=(--title "$title" --notes-file "$dir/notes.md" --target "$commit" "--latest=$latest")
    $draft && args+=(--draft)
    gh release create "$tag" "${assets[@]}" "${args[@]}"
}

for attempt in 1 2 3 4 5; do
    publish && exit 0
    [ "$attempt" = 5 ] && break
    echo "Publishing failed (try $attempt of 5); again in $((attempt * 30)) s" >&2
    sleep $((attempt * 30))
done
echo "Publishing $tag failed five times." >&2
exit 1
