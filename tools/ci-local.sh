#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# The checks of ci.yml, here, in the checkout's venv, so "passes here, fails in CI" shows up before the push (Nexus
# Release Tool's Push runs it first): the versions, the manifest and the icons' copies, every folder's tests, the
# shell scripts' syntax, the installer tests (fakeroot) and the wiki (mkdocs build --strict). Each job's line says
# ok or FAIL as it ends; a failed job's output follows at the end, its whole log in
# ~/.cache/bazzite-console-ci-local/logs. One run at a time: a second one waits.
#
#   tools/ci-local.sh            # every job
#   tools/ci-local.sh docs tools # some jobs, by name (versions, manifest, shell, installers, docs, a test folder)
set -uo pipefail

SUITE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$SUITE" || exit 1
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
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/bazzite-console-ci-local"
LOGS="$CACHE/logs"
mkdir -p "$LOGS"

# One run at a time (owner, 15-11-2026: two runs at once broke each other): a second run waits for the first.
exec 9>"$CACHE/run.lock"
if ! flock -n 9; then
    printf '\033[1;35m==>\033[0m %s\n' "Another ci-local.sh run is going on this computer: waiting until it ends"
    flock 9
fi

export QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1

job_versions() { "$PY" tools/check_versions.py; }
job_manifest() { "$PY" tools/check_manifest.py && "$PY" tools/sync_icons.py --check; }
job_shell() { find apps portal tools test.sh -name '*.sh' -print0 | xargs -0 -n1 bash -n; }
job_installers() {
    command -v fakeroot >/dev/null || { echo "The installer tests need fakeroot: brew install fakeroot"; return 1; }
    local t failed=()
    for t in tools/installer-tests/*.sh; do
        [ "${t##*/}" = shims.sh ] && continue
        echo "== ${t##*/}"
        bash "$t" || failed+=("${t##*/}")
    done
    [ ${#failed[@]} -eq 0 ] || { echo "Failed: ${failed[*]}"; return 1; }
}
job_docs() {
    local site rc
    site=$(mktemp -d)
    "$PY" -m mkdocs build --strict -d "$site"
    rc=$?
    rm -rf "$site"
    return $rc
}
# As ci.yml runs them; the development apps of dev/ but the dashboard as the suite's tests have always run here.
job_tests() {
    local mode=()
    case "$1" in dev/dash) ;; dev/*) mode=(--import-mode=importlib) ;; esac
    (cd "$1" && "$PY" -X faulthandler -m pytest -q ${mode[@]+"${mode[@]}"} tests)
}

# The jobs, in ci.yml's order: the checks, then every folder with tests (tools, dev/, the portal, each app).
jobs=(versions manifest shell)
for dir in tools dev/* portal apps/*; do
    [ -d "$dir/tests" ] && jobs+=("$dir")
done
jobs+=(installers docs)
if [ $# -gt 0 ]; then
    wanted=()
    for name in "$@"; do
        printf '%s\n' "${jobs[@]}" | grep -qx -- "$name" || { echo "No job $name. The jobs: ${jobs[*]}" >&2; exit 2; }
        wanted+=("$name")
    done
    jobs=("${wanted[@]}")
fi

echo "${#jobs[@]} jobs from ci.yml, one at a time, in $("$PY" -c 'import sys; print("Python %d.%d.%d" % sys.version_info[:3])')"
failed=()
for name in "${jobs[@]}"; do
    log="$LOGS/${name//\//_}.log"
    start=$(date +%s.%N)
    case "$name" in
        versions|manifest|shell|installers|docs) "job_$name" > "$log" 2>&1 ;;
        *) job_tests "$name" > "$log" 2>&1 ;;
    esac
    rc=$?
    took=$(awk -v a="$start" -v b="$(date +%s.%N)" 'BEGIN { printf "%.1f", b - a }')
    if [ $rc -eq 0 ]; then
        printf '  ok   %-45s %6s s\n' "$name" "$took"
    else
        printf '  FAIL %-45s %6s s\n' "$name" "$took"
        failed+=("$name")
    fi
done
for name in ${failed[@]+"${failed[@]}"}; do
    printf '\n===== %s\n' "$name"
    tail -n 40 "$LOGS/${name//\//_}.log"
done
echo
echo "$(( ${#jobs[@]} - ${#failed[@]} )) of ${#jobs[@]} jobs passed; logs in $LOGS"
[ ${#failed[@]} -eq 0 ]
