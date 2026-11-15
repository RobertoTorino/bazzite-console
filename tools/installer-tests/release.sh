#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# End to end from release tarballs: build the Board Test, SSD Check and portal releases with build_release.py,
# install the portal from its tarball (which installs the bundled Board Test release build), and let the
# portal's release code fetch and verify the SSD Check release the way it would from GitHub. Last, the suite's
# check-release.sh installs that portal tarball as if downloaded from GitHub, and the portal from the checkout copy.
# It works on a copy of the checkout in which apps.toml pins Board Test and SSD Check to these local builds: the
# checksums pinned in the repository are those of the real releases, which a local build never matches.
# Runs with the shims from shims.sh (CI).
#
#   release.sh                 # the local builds, as above
#   release.sh release TAG     # a published portal release instead: downloaded with gh, verified and installed
set -u
SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NEXUS=$SUITE                        # the repository: the Nexus tools (build_release.py) and core/
T=/tmp/bazzite-console-release-test
# shellcheck source=tools/installer-tests/shims.sh
source "$(dirname "${BASH_SOURCE[0]}")/shims.sh" "$T"; set +e
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
D=$XDG_DATA_HOME
ver() { tr -d '[:space:]' < "$SUITE/$1/VERSION"; }
BT="ps5-board-v$(ver apps/board)"; GOV="ps5-ssd-v$(ver apps/ssd)"; PORTAL="ps5-portal-v$(ver portal)"
export SOURCE_DATE_EPOCH=1790000000

if [ "${1:-}" = release ]; then
    TAG=${2:?"Usage: tools/installer-tests/release.sh [release PORTAL-TAG]"}
    command -v gh >/dev/null || { echo "GitHub CLI (gh) is required to download a release." >&2; exit 1; }
    mkdir -p "$T/download" "$T/unpacked"
    gh release download "$TAG" --dir "$T/download" --pattern "$TAG.tar.gz" --pattern SHA256SUMS || exit 1
    echo "== the published release $TAG"
    check "it matches its SHA256SUMS" "(cd $T/download && sha256sum --check --quiet SHA256SUMS)"
    tar -xzf "$T/download/$TAG.tar.gz" -C "$T/unpacked"
    (cd /tmp && "$T/unpacked/$TAG/install.sh" > "$T/install.log" 2>&1); rc=$?
    check "the portal installs, with its bundled Board Test" "[ $rc -eq 0 ] && [ -f $T/opt/ps5-board-test/board_test/main_window.py ] && [ -x $HOME/.local/bin/bazzite-console-suite ]"
    [ $fail -eq 0 ] && echo "ALL OK" || cat "$T/install.log"
    exit $fail
fi

echo "== 1. build the releases"
mkdir -p "$T/dist" "$T/suite"
# The checkout (the whole repository: the suite's folder, core and the Nexus tools) as git sees it (tracked and new
# files, nothing ignored, not what is deleted but not committed yet), without .git.
(cd "$NEXUS" && git ls-files -z --cached --others --exclude-standard |
    while IFS= read -r -d '' f; do [ -e "$f" ] && printf '%s\0' "$f"; done | tar --null -T - -cf -) | tar -xf - -C "$T/suite"
S=$T/suite                          # the copy of the repository
for tag in "$BT" "$GOV"; do
    /usr/bin/python3 "$S/tools/build_release.py" "$tag" "$T/build-$tag" > "$T/build.log" 2>&1 || { cat "$T/build.log"; fail=1; }
    cp "$T/build-$tag/$tag.tar.gz" "$T/dist/"
    /usr/bin/python3 "$S/tools/pin_app.py" "$tag" --sha256 "$(cut -d' ' -f1 "$T/build-$tag/SHA256SUMS")" >> "$T/build.log" 2>&1 || fail=1
done
/usr/bin/python3 "$S/tools/build_release.py" "$PORTAL" "$T/build-portal" --bundle "$T/build-$BT" > "$T/build.log" 2>&1 || { cat "$T/build.log"; fail=1; }
cat "$T/build-$BT/SHA256SUMS" "$T/build-$GOV/SHA256SUMS" > "$T/dist/SHA256SUMS"
check "three tarballs" "[ -f $T/dist/$BT.tar.gz ] && [ -f $T/dist/$GOV.tar.gz ] && [ -f $T/build-portal/$PORTAL.tar.gz ]"
check "sums verify" "(cd $T/dist && sha256sum --check --quiet SHA256SUMS) && (cd $T/build-portal && sha256sum --check --quiet SHA256SUMS)"

echo "== 2. install the portal from its tarball"
mkdir -p "$T/dl" && tar -xzf "$T/build-portal/$PORTAL.tar.gz" -C "$T/dl"
check "install.sh executable in the tarball" "[ -x $T/dl/$PORTAL/install.sh ] && [ -x $T/dl/$PORTAL/bundled/$BT/install.sh ]"
(cd /tmp && "$T/dl/$PORTAL/install.sh" > "$T/install.log" 2>&1); rc=$?
check "exit 0" "[ $rc -eq 0 ]"
check "Board Test is a release build" "[ -f $T/opt/ps5-board-test/board_test/_build_info.py ]"
check "its engine hash matches" "grep -q \"\$(sha256sum < $T/opt/ps5-board-test/test-board.sh | cut -d' ' -f1)\" $T/opt/ps5-board-test/board_test/_build_info.py"
check "no 'not a release build' note" "! grep -q 'not a release build' $T/install.log"
check "record has the bundled tag" "grep -q \"\\\"board\\\": \\\"$BT\\\"\" $D/bazzite-console-suite/state/installed.json"
check "portal from the release" "[ -f $D/bazzite-console-suite/portal/bazzite_console_core/__init__.py ] && [ ! -d $D/bazzite-console-suite/portal/bundled ]"

echo "== 3. the installed portal fetches and verifies the SSD Check release"
cat > "$T/fetch.py" <<'PY'
import shutil, sys
from pathlib import Path
from bazzite_console_portal import MANIFEST
from bazzite_console_portal.manifest import load
from bazzite_console_portal.sources import Sources, SourceError
dist = Path(sys.argv[1])
def download(url, dest):                     # serve the "GitHub release" from the dist folder
    shutil.copy(dist / url.rsplit("/", 1)[1], dest)
entry = next(e for e in load(MANIFEST) if e.key == "ssd")
folder = Sources(Path(sys.argv[2]), download=download).prepare(entry)
print(folder)
assert (folder / "install.sh").is_file() and (folder / "ssd_check" / "__main__.py").is_file()
data = bytearray((dist / entry.asset).read_bytes())
data[len(data) // 2] ^= 0xFF                                                       # tamper
(dist / entry.asset).write_bytes(bytes(data))
try:
    Sources(Path(sys.argv[2]) / "again", download=download).prepare(entry)
except SourceError as exc:
    print("refused:", exc)
else:
    sys.exit("a tampered tarball was accepted")
PY
PYTHONPATH="$D/bazzite-console-suite/portal" /usr/bin/python3 "$T/fetch.py" "$T/dist" "$T/work" > "$T/fetch.log" 2>&1; rc=$?
check "fetched, verified, unpacked; tampered copy refused" "[ $rc -eq 0 ] && grep -q 'refused:' $T/fetch.log"
check "SSD Check's installer runs from the fetched folder" "(cd $T/work/$GOV && bash install.sh --help >/dev/null 2>&1)"

echo "== 4. check-release.sh: the local check, then back to the release"
R=$D/bazzite-console-suite/state/installed.json
bash "$S/tools/check-release.sh" local --no-start > "$T/check-local.log" 2>&1; rc=$?
check "local: installs the portal from the checkout" "[ $rc -eq 0 ] && grep -q '\"board\": \"local\"' $R"
mkdir -p "$T/gh/$PORTAL" && cp "$T/build-portal/$PORTAL.tar.gz" "$T/build-portal/SHA256SUMS" "$T/gh/$PORTAL/"
PS5_RELEASE_URL="file://$T/gh" bash "$S/tools/check-release.sh" release --no-start > "$T/check-release.log" 2>&1; rc=$?
check "release: downloads and verifies portal/VERSION's tag" "[ $rc -eq 0 ] && grep -q '$PORTAL.tar.gz: OK' $T/check-release.log"
check "release: installed it, bundled Board Test included" "grep -q \"\\\"board\\\": \\\"$BT\\\"\" $R && [ -f $D/bazzite-console-suite/portal/bazzite_console_core/__init__.py ]"
PS5_RELEASE_URL="file://$T/gh" bash "$S/tools/check-release.sh" release ps5-portal-v9.9.9 --no-start > "$T/check-missing.log" 2>&1; rc=$?
check "release: a tag GitHub has not built yet is reported" "[ $rc -ne 0 ] && grep -q 'finished the release workflow' $T/check-missing.log"
# The device test of a release (check-release.sh draft): the draft's assets come through gh, stood in for
# here by a script that copies them from the "GitHub" folder, as before.
cat > "$T/shims/gh" <<'X'
#!/bin/sh
# gh release download TAG --pattern A --pattern B --dir DIR --repo R: the draft's files from the test's folder
[ "$1 $2" = "release download" ] || { echo "unexpected gh $*" >&2; exit 2; }
tag=$3; dir=.
while [ $# -gt 0 ]; do [ "$1" = --dir ] && dir=$2; shift; done
[ -d "$GH_DRAFTS/$tag" ] || { echo "release not found" >&2; exit 1; }
cp "$GH_DRAFTS/$tag"/* "$dir/"
X
chmod +x "$T/shims/gh"
bash "$S/tools/check-release.sh" local --no-start > /dev/null 2>&1
GH_DRAFTS="$T/gh" bash "$S/tools/check-release.sh" draft --no-start > "$T/check-draft.log" 2>&1; rc=$?
check "draft: downloads portal/VERSION's draft with gh, verifies and installs it" "[ $rc -eq 0 ] && grep -q 'draft of $PORTAL' $T/check-draft.log && grep -q '$PORTAL.tar.gz: OK' $T/check-draft.log && grep -q \"\\\"board\\\": \\\"$BT\\\"\" $R"
GH_DRAFTS="$T/gh" bash "$S/tools/check-release.sh" draft ps5-portal-v9.9.9 --no-start > "$T/check-nodraft.log" 2>&1; rc=$?
check "draft: no draft to download is reported" "[ $rc -ne 0 ] && grep -q 'No draft of ps5-portal-v9.9.9' $T/check-nodraft.log"
bash "$S/tools/check-release.sh" nonsense > "$T/check-usage.log" 2>&1; rc=$?
check "unknown mode refused" "[ $rc -ne 0 ] && grep -q 'Usage' $T/check-usage.log"

[ $fail -eq 0 ] && echo "ALL OK" || for l in "$T"/*.log; do echo "--- $l"; cat "$l"; done
exit $fail
