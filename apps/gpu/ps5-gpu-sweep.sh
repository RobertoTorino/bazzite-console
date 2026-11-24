#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

# ps5-gpu-sweep.sh - finds your PS5's safe GPU overclock and undervolt, one step at a time.
#
# The cyan-skillfish governor (smu or tt) scales the PS5 GPU along a frequency/voltage curve defined by
# the [[safe-points]] in its config.toml. There is no formula for the right values: the stable ceiling
# depends on your specific die, cooling and PSU rail. This script finds it empirically:
#
#   control   the governor's current top safe-point, unchanged. If the control fails, power,
#             heat or the load tool is at fault and no step verdict can be trusted.
#   OC step   top frequency raised one step at a time (default +50 MHz) at a fixed voltage.
#   UV step   top voltage lowered one step at a time (default -25 mV) at the stock top frequency.
#
# For every step the script swaps in a temporary governor config whose top safe-point is the step
# under test, restarts the governor, runs a verified GPU load (memtest_vulkan finds wrong results,
# not only crashes), watches temperature/clock/busy, then restores your own config. Every step runs
# several rounds. Results are crash-safe: after a freeze, cold boot and run the script again - it
# restores your config first, records the crash and resumes.
#
# Verdict per step: "fails every time" = past your die's limit. "Random" = power or heat. Steps
# above/below a consistently failing step are skipped. --install writes the best step that passed
# every round, one step back as the margin. It keeps the curve's lower safe-points and drops those
# whose voltage is above the new top's. It backs up the config as config.toml.bak-<stamp> first,
# which PS5 GPU Manager's Backups page restores.
#
# PS5 GPU Manager's GPU sweep window runs this script step by step. Run it as your desktop user;
# sudo is used for the governor config, systemctl and the kernel log.
#
# Usage: ./ps5-gpu-sweep.sh [options]
#   -t, --time SECS      GPU load per attempt (default 180, minimum 60)
#   -r, --rounds N       attempts per step (default 3, 2-9)
#       --oc             sweep frequency up (default when neither --oc nor --uv is given: both)
#       --uv             sweep voltage down
#       --max-freq MHZ   highest frequency to try (default 2200, hard ceiling 2500)
#       --min-volt MV    lowest voltage to try (default 850, hard floor 700)
#       --oc-volt MV     voltage used for the OC ladder (default: your config's top voltage;
#                        hard ceiling 1100)
#       --freq-step MHZ  OC ladder step (default 50, minimum 25)
#       --volt-step MV   UV ladder step (default 25, minimum 5)
#       --per-boot       one attempt per boot for strict isolation (default: same boot, with a
#                        cooldown between attempts; the governor restart resets its state)
#       --only PART      run only the attempts of one part: control, oc or uv. The window runs
#                        the steps this way. oc and uv wait until every control round passed.
#       --scan           read the GPU, the governor, its config and the load tool, then exit.
#                        It writes nothing and needs no password.
#       --install        write the recommended margin step into the governor config and exit
#       --status         show the results so far and write the report, then exit
#       --reset          delete the results and start over
#   -V, --version        show the version
#   -h, --help           show this help
#
# https://github.com/RobertoTorino/bazzite-console/tree/main/apps/gpu

set -u
if (( BASH_VERSINFO[0] < 4 )); then echo "This script needs bash 4 or newer." >&2; exit 1; fi

VERSION="0.1.0"
STRESS_SECS="" ROUNDS_OPT="" MODE=run SWEEP="" PER_BOOT=0 ONLY=""
MAX_FREQ_OPT="" MIN_VOLT_OPT="" OC_VOLT_OPT="" FREQ_STEP_OPT="" VOLT_STEP_OPT=""

# Hard rails. The community record of hard-locks above ~1850-2000 MHz and the bricked-board report
# from CPU overvolting are the reason these are not options.
HARD_MAX_FREQ=2500 HARD_MAX_VOLT=1100 HARD_MIN_VOLT=700 TEMP_ABORT=97

say()  { printf '%s\n' "$*"; }
hdr()  { printf '\n=== %s ===\n' "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
ev()   { [[ -z ${PS5_GUI:-} ]] || printf '@@ %s\n' "$*"; }   # a line for GPU Manager's sweep window (PS5_GUI=1), not for people
ask()  { # prompt [name for the window]; only the answer goes to stdout (callers capture it)
  if [[ -n ${PS5_GUI:-} ]]; then say "$1" >&2; ev ask "${2:-question}" >&2; local a; read -r a; printf '%s' "$a"; return 0; fi
  local a; read -rp "$1 " a; printf '%s' "$a"
}
usage() { sed -n '4,/^$/{s/^# \{0,1\}//;p;}' "$0"; }   # the header comment, after the SPDX line and the blank

while (( $# )); do
  case $1 in
    -t|--time)    STRESS_SECS=${2:-}; shift ;;
    -r|--rounds)  ROUNDS_OPT=${2:-}; shift ;;
    --oc)         SWEEP="${SWEEP}oc," ;;
    --uv)         SWEEP="${SWEEP}uv," ;;
    --max-freq)   MAX_FREQ_OPT=${2:-}; shift ;;
    --min-volt)   MIN_VOLT_OPT=${2:-}; shift ;;
    --oc-volt)    OC_VOLT_OPT=${2:-}; shift ;;
    --freq-step)  FREQ_STEP_OPT=${2:-}; shift ;;
    --volt-step)  VOLT_STEP_OPT=${2:-}; shift ;;
    --per-boot)   PER_BOOT=1 ;;
    --only)       ONLY=${2:-}; shift ;;
    --scan)       MODE=scan ;;
    --install)    MODE=install ;;
    --status)     MODE=status ;;
    --reset)      MODE=reset ;;
    -V|--version) echo "ps5-gpu-sweep $VERSION"; exit 0 ;;
    -h|--help)    usage; exit 0 ;;
    *)            usage; die "unknown option: $1" ;;
  esac
  shift
done
[[ -z $STRESS_SECS ]] || { [[ $STRESS_SECS =~ ^[0-9]+$ ]] && (( STRESS_SECS >= 60 )); } || die "--time needs 60 seconds or more."
[[ -z $ROUNDS_OPT || $ROUNDS_OPT =~ ^[2-9]$ ]] || die "--rounds needs a number from 2 to 9."
[[ -z $MAX_FREQ_OPT ]] || { [[ $MAX_FREQ_OPT =~ ^[0-9]+$ ]] && (( MAX_FREQ_OPT <= HARD_MAX_FREQ )); } || die "--max-freq must be a number up to $HARD_MAX_FREQ MHz."
[[ -z $MIN_VOLT_OPT ]] || { [[ $MIN_VOLT_OPT =~ ^[0-9]+$ ]] && (( MIN_VOLT_OPT >= HARD_MIN_VOLT )); } || die "--min-volt must be $HARD_MIN_VOLT mV or more."
[[ -z $OC_VOLT_OPT ]] || { [[ $OC_VOLT_OPT =~ ^[0-9]+$ ]] && (( OC_VOLT_OPT <= HARD_MAX_VOLT )); } || die "--oc-volt must be a number up to $HARD_MAX_VOLT mV. The wiki explains this hard ceiling."
[[ -z $FREQ_STEP_OPT ]] || { [[ $FREQ_STEP_OPT =~ ^[0-9]+$ ]] && (( FREQ_STEP_OPT >= 25 )); } || die "--freq-step must be 25 MHz or more."
[[ -z $VOLT_STEP_OPT ]] || { [[ $VOLT_STEP_OPT =~ ^[0-9]+$ ]] && (( VOLT_STEP_OPT >= 5 )); } || die "--volt-step must be 5 mV or more."
[[ -z $ONLY || $ONLY =~ ^(control|oc|uv)$ ]] || die "--only takes control, oc or uv."
SWEEP_OPT=$SWEEP
[[ -n $SWEEP ]] || SWEEP="oc,uv,"

STATE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ps5-gpu-sweep"
CONFIG="$STATE_DIR/config"
RUNS="$STATE_DIR/runs.tsv"
PENDING="$STATE_DIR/pending"
ORIG_CONF="$STATE_DIR/governor-config.orig"
TEST_MARKER="$STATE_DIR/test-config-active"
LOGS="$STATE_DIR/logs"
BOOT_ID=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)
FAULT_RE='ring .* timeout|GPU reset|amdgpu.*(fault|hang)|gfxhub|VM_L2|page fault|soft lockup|hard lockup|Oops|BUG:|general protection fault'
FAIL_RE='^(CRASH-LOAD|FAULT|ERRORS|LOAD-FAIL|NO-REACH|GOV-FAIL)$'

# ------------------------------------------------------------------ helpers --
cfg_get() { sed -n "s/^$1=//p" "$CONFIG" 2>/dev/null | head -1; }
cfg_set() {
  local tmp="$CONFIG.tmp"
  { grep -v "^$1=" "$CONFIG" 2>/dev/null; printf '%s=%s\n' "$1" "$2"; } >"$tmp" && mv "$tmp" "$CONFIG"
}

# The governor: cyan-skillfish-governor-smu or -tt. The one whose service runs, else the one whose config is
# there. A run keeps the governor it started with.
GOV="" GOV_SVC="" GOV_CONF=""
ETC_DIR="${PS5_SWEEP_ETC:-/etc}"           # override only for testing
find_governor() {
  local g found=()
  for g in smu tt; do
    [[ -r $ETC_DIR/cyan-skillfish-governor-$g/config.toml ]] && found+=("$g")
  done
  for g in "${found[@]}"; do
    systemctl is-active --quiet "cyan-skillfish-governor-$g" && { GOV=$g; break; }
  done
  [[ -n $GOV || ${#found[@]} -ne 1 ]] || GOV=${found[0]}
  if [[ -n $GOV ]]; then
    GOV_SVC="cyan-skillfish-governor-$GOV"
    GOV_CONF="$ETC_DIR/$GOV_SVC/config.toml"
  fi
}

# The governor config without its [[safe-points]] blocks (everything else is kept as-is).
strip_safepoints() {
  awk '
    /^\[\[safe-points\]\]/ { skip = 1; next }
    /^\[/ && !/^\[\[safe-points\]\]/ { skip = 0 }
    !skip { print }
  ' "$1"
}
# "frequency voltage" of every safe-point in a config file, one per line, lowest frequency first.
all_safepoints() {
  awk '
    /^\[\[safe-points\]\]/ { inpt = 1; f = ""; v = ""; next }
    /^\[/ { inpt = 0 }
    inpt && /^[[:space:]]*frequency[[:space:]]*=/ { sub(/#.*/, ""); gsub(/[^0-9]/, "", $0); f = $0 }
    inpt && /^[[:space:]]*voltage[[:space:]]*=/   { sub(/#.*/, ""); gsub(/[^0-9]/, "", $0); v = $0 }
    inpt && f != "" && v != "" { print f, v; f = ""; v = "" }
  ' "$1" | sort -n
}
# "frequency voltage" of the highest-frequency safe-point in a config file.
top_safepoint() { all_safepoints "$1" | tail -1; }
# "frequency voltage" of the lowest-frequency safe-point (kept in every test config so the
# governor still has a safe idle point).
low_safepoint() { all_safepoints "$1" | head -1; }

gov_restart() { sudo -n systemctl restart "$GOV_SVC" 2>/dev/null; }
gov_active()  { systemctl is-active --quiet "$GOV_SVC"; }

safepoint_block() { # freq volt [note]
  printf '\n[[safe-points]]\nfrequency = %s # MHz%s\nvoltage = %s # mV\n' "$1" "${3:+  ($3)}" "$2"
}
# Swap in a config whose top safe-point is "freq volt"; keep everything else from the original.
write_test_config() { # freq volt
  local tmp; tmp=$(mktemp) || return 1
  {
    strip_safepoints "$ORIG_CONF"
    safepoint_block "$LOW_F" "$LOW_V"
    safepoint_block "$1" "$2" "ps5-gpu-sweep test point"
  } >"$tmp" || { rm -f "$tmp"; return 1; }
  sudo -n cp "$tmp" "$GOV_CONF" && rm -f "$tmp" && touch "$TEST_MARKER"
}
restore_config() {
  [[ -f $TEST_MARKER ]] || return 0
  sudo -n cp "$ORIG_CONF" "$GOV_CONF" && rm -f "$TEST_MARKER" && gov_restart
}

record() { # round item freq volt outcome errors faults maxtemp maxsclk maxbusy note
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "${BOOT_ID:0:8}" "$@" >>"$RUNS"
  sync "$RUNS" 2>/dev/null
  ev result "$1" "$2" "$5" >&2           # stderr: next_attempt records skipped steps inside $(...)
}
attempt_done() { awk -F'\t' -v r="$1" -v i="$2" '$3==r && $4==i && $7!="ABORTED"{f=1} END{exit !f}' "$RUNS"; }
item_verdict() { # item -> none|good|bad|failing|random
  local outs fails=0 tries=0 o
  outs=$(awk -F'\t' -v i="$1" '$4==i && $7!="ABORTED" && $7!="SKIPPED"{print $7}' "$RUNS")
  for o in $outs; do (( tries++ )); [[ $o =~ $FAIL_RE ]] && (( fails++ )); done
  if (( tries == 0 )); then echo none
  elif (( fails == 0 )); then echo good
  elif (( fails == tries && tries >= 2 )); then echo bad
  elif (( fails == tries )); then echo failing
  else echo random
  fi
}
# A ladder step is pruned when an easier step in the same ladder already fails every time.
item_pruned() { # item
  local it=$1 lad=${1%%:*} prev
  for prev in "${ITEMS[@]}"; do
    [[ $prev == "$it" ]] && return 1
    [[ ${prev%%:*} == "$lad" && $lad != control ]] || continue
    [[ $(item_verdict "$prev") == bad ]] && return 0
  done
  return 1
}
in_part() { [[ -z $ONLY || ${1%%:*} == "$ONLY" ]]; }   # item: in the part --only names
next_attempt() { # prints "round item" of the first attempt without a result
  # Ladder order is depth-first: every round of a step runs before the next step is attempted,
  # so the sweep never drives past a step that is still failing.
  local r it
  for it in "${ITEMS[@]}"; do
    in_part "$it" || continue
    for (( r = 1; r <= ROUNDS; r++ )); do
      attempt_done "$r" "$it" && continue
      if item_pruned "$it"; then
        record "$r" "$it" "${ITEM_F[$it]}" "${ITEM_V[$it]}" SKIPPED - - - - - "an easier step already fails every time"
        continue
      fi
      echo "$r $it"; return 0
    done
  done
  return 1
}

# ---------------------------------------------------------------- plan ----
# Items: control (the current top safe-point), then "oc:FREQ" and/or "uv:VOLT" ladder steps.
build_plan() {
  local f v
  ITEMS=(control)
  declare -gA ITEM_F=([control]=$TOP_F) ITEM_V=([control]=$TOP_V)
  if [[ $SWEEP == *oc,* ]]; then
    for (( f = TOP_F + FREQ_STEP; f <= MAX_FREQ; f += FREQ_STEP )); do
      ITEMS+=("oc:$f"); ITEM_F[oc:$f]=$f; ITEM_V[oc:$f]=$OC_VOLT
    done
  fi
  if [[ $SWEEP == *uv,* ]]; then
    for (( v = TOP_V - VOLT_STEP; v >= MIN_VOLT; v -= VOLT_STEP )); do
      ITEMS+=("uv:$v"); ITEM_F[uv:$v]=$TOP_F; ITEM_V[uv:$v]=$v
    done
  fi
}

# The step to install: the best GOOD step of each ladder, one step back as the margin where an earlier
# passing step exists. Sets BEST_F BEST_V.
best_point() {
  local it prev_f="" prev_v=""
  BEST_F=$TOP_F BEST_V=$TOP_V
  for it in "${ITEMS[@]}"; do
    [[ $it == control ]] && continue
    [[ $(item_verdict "$it") == good ]] || continue
    case $it in
      oc:*) prev_f=$BEST_F; BEST_F=${ITEM_F[$it]}; BEST_V=${ITEM_V[$it]} ;;
      uv:*) prev_v=$BEST_V; BEST_V=${ITEM_V[$it]} ;;
    esac
  done
  [[ -n $prev_f ]] && BEST_F=$prev_f
  [[ -n $prev_v ]] && BEST_V=$prev_v
  return 0
}

# ---------------------------------------------------------------- summary --
summary() {
  local it verdict total=0 done_n=0 ctrl_fail=0 best_oc="" best_uv="" oc_margin="" uv_margin="" prev_oc="" prev_uv=""
  hdr "Results"
  say "Governor $GOV_SVC. Stock top point ${TOP_F} MHz @ ${TOP_V} mV, $ROUNDS rounds, ${STRESS_SECS}s load per attempt."
  printf '%-10s %-18s %-6s %s\n' "Step" "Point" "Tries" "Verdict and outcomes"
  for it in "${ITEMS[@]}"; do
    local outs fails=0 tries=0 o skipped=0
    outs=$(awk -F'\t' -v i="$it" '$4==i && $7!="ABORTED" && $7!="SKIPPED"{print $7}' "$RUNS")
    awk -F'\t' -v i="$it" '$4==i && $7=="SKIPPED"{f=1} END{exit !f}' "$RUNS" && skipped=1
    for o in $outs; do (( tries++ )); [[ $o =~ $FAIL_RE ]] && (( fails++ )); done
    # Skipped steps are complete by definition; they add nothing to the remaining work.
    (( skipped && tries == 0 )) || (( total += ROUNDS, done_n += tries ))
    if (( tries == 0 )); then verdict=$([[ $skipped == 1 ]] && echo "skipped" || echo "not tested yet")
    elif (( fails == 0 )); then
      verdict="GOOD"
      case $it in
        oc:*) oc_margin=$prev_oc; best_oc=$it; prev_oc=$it ;;
        uv:*) uv_margin=$prev_uv; best_uv=$it; prev_uv=$it ;;
      esac
    elif (( fails == tries && tries >= 2 )); then verdict="FAILS EVERY TIME"
    elif (( fails == tries )); then verdict="failed its 1 try so far"
    else verdict="RANDOM ($fails of $tries failed)"
    fi
    [[ $it == control ]] && (( fails )) && ctrl_fail=1
    printf '%-10s %4s MHz @ %4s mV  %d/%-4d %s   %s\n' "$it" "${ITEM_F[$it]}" "${ITEM_V[$it]}" "$tries" "$ROUNDS" "$verdict" "$(echo $outs)"
  done
  say ""
  say "What this means:"
  if (( ctrl_fail )); then
    say "- The CONTROL failed. The control changes nothing. It only restarts the governor with your"
    say "  own top point. So power, heat or the load tool is at fault. You cannot trust any step verdict."
  fi
  if (( done_n < total )); then
    say "- $done_n of $total attempts done (skipped steps excluded). Run the script again to continue."
  elif (( ! ctrl_fail )); then
    if [[ -n $best_oc ]]; then
      say "- Best overclock that passed every round: ${ITEM_F[$best_oc]} MHz @ ${ITEM_V[$best_oc]} mV."
      [[ -n $oc_margin ]] && say "  With a margin step back: ${ITEM_F[$oc_margin]} MHz (recommended for daily use)."
    elif [[ $SWEEP == *oc,* ]]; then
      say "- No OC step passed every round. Your board's stable ceiling is the stock ${TOP_F} MHz."
    fi
    if [[ -n $best_uv ]]; then
      say "- Lowest voltage that passed every round at ${TOP_F} MHz: ${ITEM_V[$best_uv]} mV."
      [[ -n $uv_margin ]] && say "  With a margin step back: ${ITEM_V[$uv_margin]} mV (recommended for daily use)."
    elif [[ $SWEEP == *uv,* ]]; then
      say "- No UV step passed every round. Keep the stock ${TOP_V} mV."
    fi
    say "- A step that passed here can still fail under other conditions (heat, a long game)."
    say "  Pick the margin step, then make it permanent:  $0 --install"
    say "  Undo it on PS5 GPU Manager's Backups page, which restores the config.toml.bak-<stamp> it makes."
  fi
}

write_report() {
  local d; d=$(xdg-user-dir DESKTOP 2>/dev/null)
  [[ -z $d || ! -d $d ]] && d="$HOME/Desktop"
  [[ -d $d ]] || return 0
  local f
  f="$d/ps5-gpu-sweep-results-$(date '+%Y%m%d-%H%M%S').txt"
  {
    echo "PS5 GPU sweep $VERSION results ($(date '+%F %T'))"
    summary
    echo ""
    echo "All attempts (time, boot, round, step, MHz, mV, outcome, memtest errors, kernel faults,"
    echo "max temp C, max sclk MHz, max GPU busy %, note):"
    cat "$RUNS"
  } >"$f" && say "" && say "Report written to $f"
}

find_gpu() {
  GPU_DEV=""
  local d
  for d in "${PS5_SWEEP_DRM:-/sys/class/drm}"/card*/device; do      # the override only for testing
    [[ $(cat "$d/vendor" 2>/dev/null) == 0x1002 && $(cat "$d/device" 2>/dev/null) == 0x13fe ]] && { GPU_DEV=$d; break; }
  done
}
find_load() {
  LOAD="" LOAD_BIN=""
  local t p
  for t in memtest_vulkan vkpeak vkmark glmark2; do
    for p in "$(command -v "$t" 2>/dev/null)" "$HOME/.local/bin/$t" "/home/linuxbrew/.linuxbrew/bin/$t"; do
      [[ -n $p && -x $p && -f $p ]] && { LOAD=$t LOAD_BIN=$p; break 2; }
    done
  done
}

# ---------------------------------------------------------------- modes ----
if [[ $MODE == reset ]]; then
  [[ $(ask "Delete all results in $STATE_DIR and start over? [y/N]" reset) =~ ^[Yy]$ ]] || exit 0
  rm -f "$CONFIG" "$RUNS" "$PENDING" "$ORIG_CONF" "$TEST_MARKER"; rm -rf "$LOGS"
  say "Results deleted."; exit 0
fi

(( EUID != 0 )) || die "run this as your normal desktop user, not as root. The script uses sudo where it needs root."
find_governor

# The scan reads what a run needs and writes nothing: the window shows it before step 2.
if [[ $MODE == scan ]]; then
  find_gpu; find_load
  hdr "Scan"
  ev scan gpu "${GPU_DEV:--}"
  ev scan governor "${GOV:--}"
  ev scan service "$([[ -n $GOV ]] && systemctl is-active "$GOV_SVC" 2>/dev/null || echo -)"
  ev scan config "${GOV_CONF:--}"
  ev scan load "${LOAD:--}"
  say "GPU: ${GPU_DEV:-no PS5 GPU (1002:13fe) found}"
  say "Governor: ${GOV_SVC:-none found, or both installed and neither running}"
  say "Load tool: ${LOAD:-none found}"
  if [[ -n $GOV_CONF ]]; then
    read -r F V < <(top_safepoint "$GOV_CONF")
    ev scan top "${F:--}" "${V:--}"
    ev scan points "$(all_safepoints "$GOV_CONF" | grep -c .)"
    say "Top safe-point: ${F:-?} MHz @ ${V:-?} mV"
    if [[ -f $ORIG_CONF ]]; then
      cmp -s "$GOV_CONF" "$ORIG_CONF" && ev scan snapshot same || ev scan snapshot changed
    else
      ev scan snapshot none
    fi
    ev scan saved-governor "$(cfg_get GOVERNOR)"
  fi
  exit 0
fi

[[ -n $GOV ]] || die "no cyan-skillfish governor config found, or both are installed and neither runs. Start the one you use first."
[[ -n $(cfg_get GOVERNOR) && $(cfg_get GOVERNOR) != "$GOV" ]] && die "the results are for cyan-skillfish-governor-$(cfg_get GOVERNOR), but $GOV_SVC is in use now. Reset first to sweep this governor."
lspci -nn 2>/dev/null | grep -qi '1002:13fe' || die "no PS5 GPU (1002:13fe) found."

say "The governor config and service need root. sudo may ask for your password once."
sudo -n true 2>/dev/null || sudo -v || die "sudo failed."
( while kill -0 $$ 2>/dev/null; do sudo -n true 2>/dev/null; sleep 50; done ) &
KEEPALIVE=$!
trap 'kill "$KEEPALIVE" 2>/dev/null' EXIT
mkdir -p "$LOGS" && chmod 700 "$STATE_DIR" "$LOGS" 2>/dev/null
touch "$RUNS"

# A crash can leave the test config installed; put the user's own config back before anything else.
if [[ -f $TEST_MARKER && -f $ORIG_CONF ]]; then
  say "A test config from an interrupted attempt is still installed. Restoring your own config."
  restore_config || die "could not restore $GOV_CONF from $ORIG_CONF. Do it by hand, then rerun."
fi

# The settings of a run: an option given now, else the one the run saved, else the default. Results exist for
# the saved ladder, so a different ladder needs --reset first. It runs in $(...), so each caller exits on its error.
setting() { # name option default
  local saved; saved=$(cfg_get "$1")
  if [[ -n $2 && -n $saved && $2 != "$saved" && -s $RUNS ]]; then
    die "results exist with $1=$saved. Reset first to change it."
  fi
  printf '%s' "${2:-${saved:-$3}}"
}

if [[ $MODE == install ]]; then
  [[ -s $RUNS && -f $ORIG_CONF ]] || die "no finished results. Run the sweep first."
  cmp -s "$GOV_CONF" "$ORIG_CONF" || die "the governor config changed since this run started. Reset first."
  read -r TOP_F TOP_V < <(top_safepoint "$ORIG_CONF")
  read -r LOW_F LOW_V < <(low_safepoint "$ORIG_CONF")
  OC_VOLT=$(setting OC_VOLT "$OC_VOLT_OPT" "$TOP_V") || exit 1; MAX_FREQ=$(setting MAX_FREQ "$MAX_FREQ_OPT" 2200) || exit 1
  MIN_VOLT=$(setting MIN_VOLT "$MIN_VOLT_OPT" 850) || exit 1; FREQ_STEP=$(setting FREQ_STEP "$FREQ_STEP_OPT" 50) || exit 1
  VOLT_STEP=$(setting VOLT_STEP "$VOLT_STEP_OPT" 25) || exit 1
  ROUNDS=$(cfg_get ROUNDS); ROUNDS=${ROUNDS:-3}; STRESS_SECS=$(cfg_get TIME); STRESS_SECS=${STRESS_SECS:-180}
  SWEEP=$(cfg_get SWEEP); SWEEP=${SWEEP:-oc,uv,}
  build_plan
  next_attempt >/dev/null && die "the sweep is not finished yet. Run the script again first."
  [[ $(item_verdict control) == good ]] || die "the control did not pass every round. The script installs nothing."
  best_point
  [[ $BEST_F == "$TOP_F" && $BEST_V == "$TOP_V" ]] && die "nothing better than stock passed. The script has nothing to install."
  # The curve's lower safe-points stay, except those whose voltage is above the new top's (owner, 24-11-2026):
  # the governor wants a voltage that never drops as the frequency rises, and no untested voltage is written.
  KEEP=$(all_safepoints "$ORIG_CONF" | awk -v f="$BEST_F" -v v="$BEST_V" '$1 < f && $2 <= v')
  DROP=$(all_safepoints "$ORIG_CONF" | awk -v f="$BEST_F" -v v="$BEST_V" '$1 < f && $2 > v')
  [[ -n $KEEP ]] || die "every lower safe-point has a voltage above ${BEST_V} mV, so only one point would be left. The script installs nothing."
  say "Installing top safe-point ${BEST_F} MHz @ ${BEST_V} mV (margin pick) into $GOV_CONF."
  say "Kept below it: $(awk '{printf "%s%s MHz @ %s mV", (NR > 1 ? ", " : ""), $1, $2}' <<<"$KEEP")."
  [[ -n $DROP ]] && say "Dropped, as their voltage is above ${BEST_V} mV: $(awk '{printf "%s%s MHz @ %s mV", (NR > 1 ? ", " : ""), $1, $2}' <<<"$DROP")."
  [[ $(ask "Continue? [y/N]" install) =~ ^[Yy]$ ]] || exit 0
  BACKUP="$GOV_CONF.bak-$(date '+%Y%m%d-%H%M%S')"
  sudo -n cp -p "$GOV_CONF" "$BACKUP" || die "could not back up $GOV_CONF."
  tmp=$(mktemp) || die "could not write a temporary file."
  {
    strip_safepoints "$ORIG_CONF"
    while read -r f v; do safepoint_block "$f" "$v"; done <<<"$KEEP"
    safepoint_block "$BEST_F" "$BEST_V" "ps5-gpu-sweep"
  } >"$tmp" && sudo -n cp "$tmp" "$GOV_CONF" || { rm -f "$tmp"; die "could not write $GOV_CONF."; }
  rm -f "$tmp"
  gov_restart || die "governor restart failed. Restore $BACKUP on PS5 GPU Manager's Backups page."
  cfg_set INSTALLED "$BEST_F $BEST_V $BACKUP"
  ev installed "$BEST_F" "$BEST_V" "$BACKUP"
  say "Done. Backup of your previous config: $BACKUP. Undo it on PS5 GPU Manager's Backups page."
  exit 0
fi

# ------------------------------------------------------------ run / status --
# Baseline: snapshot the user's config on the first run; every later run must use the same one.
if [[ ! -f $ORIG_CONF ]]; then
  [[ $MODE == status ]] && die "no results yet."
  cp "$GOV_CONF" "$ORIG_CONF" || die "could not take a snapshot of $GOV_CONF."
  cfg_set CREATED "$(date '+%F %T')"
  cfg_set GOVERNOR "$GOV"
elif ! cmp -s "$GOV_CONF" "$ORIG_CONF"; then
  die "the governor config changed since this run started. Finish or --reset before editing it."
fi
read -r TOP_F TOP_V < <(top_safepoint "$ORIG_CONF")
read -r LOW_F LOW_V < <(low_safepoint "$ORIG_CONF")
[[ -n ${TOP_F:-} && -n ${TOP_V:-} ]] || die "no [[safe-points]] found in $GOV_CONF."
(( TOP_V <= HARD_MAX_VOLT )) || die "your config's top voltage of ${TOP_V} mV is already above the ${HARD_MAX_VOLT} mV rail. The script leaves it alone."

ROUNDS=${ROUNDS_OPT:-$(cfg_get ROUNDS)}; ROUNDS=${ROUNDS:-3}
STRESS_SECS=${STRESS_SECS:-$(cfg_get TIME)}; STRESS_SECS=${STRESS_SECS:-180}
OC_VOLT=$(setting OC_VOLT "$OC_VOLT_OPT" "$TOP_V") || exit 1
MAX_FREQ=$(setting MAX_FREQ "$MAX_FREQ_OPT" 2200) || exit 1
MIN_VOLT=$(setting MIN_VOLT "$MIN_VOLT_OPT" 850) || exit 1
FREQ_STEP=$(setting FREQ_STEP "$FREQ_STEP_OPT" 50) || exit 1
VOLT_STEP=$(setting VOLT_STEP "$VOLT_STEP_OPT" 25) || exit 1
SWEEP_SAVED=$(cfg_get SWEEP)
if [[ -n $SWEEP_SAVED ]]; then
  [[ -n $SWEEP_OPT && $SWEEP_OPT != "$SWEEP_SAVED" ]] && die "results exist for sweep '$SWEEP_SAVED'. Run with --reset first to change the sweep."
  SWEEP=$SWEEP_SAVED
fi
[[ $STRESS_SECS =~ ^[0-9]+$ ]] && (( STRESS_SECS >= 60 )) || die "load time must be 60 seconds or more."
[[ $ROUNDS =~ ^[2-9]$ ]] || die "rounds must be a number from 2 to 9."
(( OC_VOLT <= HARD_MAX_VOLT )) || die "OC voltage ${OC_VOLT} mV is above the ${HARD_MAX_VOLT} mV rail."
cfg_set ROUNDS "$ROUNDS"; cfg_set TIME "$STRESS_SECS"; cfg_set OC_VOLT "$OC_VOLT"; cfg_set SWEEP "$SWEEP"
cfg_set MAX_FREQ "$MAX_FREQ"; cfg_set MIN_VOLT "$MIN_VOLT"; cfg_set FREQ_STEP "$FREQ_STEP"; cfg_set VOLT_STEP "$VOLT_STEP"
build_plan
ev plan "$TOP_F" "$TOP_V" "${ITEMS[*]}"

if [[ $MODE == status ]]; then summary; write_report; exit 0; fi

if [[ $ONLY == oc || $ONLY == uv ]]; then
  ONLY_SAVED=$ONLY; ONLY=control
  next_attempt >/dev/null && die "the control has rounds left. Run them first (--only control)."
  ONLY=$ONLY_SAVED
  [[ $(item_verdict control) == good ]] || die "the control did not pass every round, so no step verdict can be trusted."
fi

find_gpu
find_load
[[ -n $LOAD ]] || die "no GPU load tool found. Put memtest_vulkan (github.com/GpuZelenograd/memtest_vulkan) in ~/.local/bin."

gov_active || die "$GOV_SVC is not running. Start it first: sudo systemctl enable --now $GOV_SVC"

gpu_busy() { cat "$GPU_DEV/gpu_busy_percent" 2>/dev/null || echo 0; }
gpu_temp() { local f; for f in "$GPU_DEV"/hwmon/hwmon*/temp1_input; do [[ -r $f ]] && { echo $(( $(cat "$f") / 1000 )); return; }; done; echo 0; }
gpu_sclk() {
  local f; for f in "$GPU_DEV"/hwmon/hwmon*/freq1_input; do [[ -r $f ]] && { echo $(( $(cat "$f") / 1000000 )); return; }; done
  sed -n 's/.*: *\([0-9]*\)[Mm][Hh]z *\*.*/\1/p' "$GPU_DEV/pp_dpm_sclk" 2>/dev/null | head -1 || echo 0
}
faults_since() { sudo -n journalctl -k --since "$1" --no-pager 2>/dev/null | grep -E "$FAULT_RE"; }

# -------------------------------------------------- crash from last boot ----
if [[ -s $PENDING ]]; then
  read -r P_ROUND P_ITEM P_F P_V P_BOOT <"$PENDING"
  if [[ $P_BOOT != "$BOOT_ID" ]]; then
    hdr "The last attempt did not finish"
    say "The system went down during the load of round $P_ROUND, $P_ITEM at ${P_F} MHz @ ${P_V} mV."
    PREV=$(sudo -n journalctl -k -b -1 --no-pager 2>/dev/null | grep -E "$FAULT_RE" | tail -5)
    [[ -n $PREV ]] && { say "Kernel faults in the previous boot:"; say "$PREV"; }
    if [[ $(ask "Did the system freeze, crash or reboot by itself? [Y/n]" crash) =~ ^[Nn]$ ]]; then
      record "$P_ROUND" "$P_ITEM" "$P_F" "$P_V" ABORTED - - - - - "rebooted by hand during the attempt"
      say "Recorded as interrupted. This attempt will run again."
    else
      record "$P_ROUND" "$P_ITEM" "$P_F" "$P_V" CRASH-LOAD - "$(grep -c . <<<"$PREV")" - - - "system went down"
      say "Recorded as CRASH-LOAD."
    fi
  else
    record "$P_ROUND" "$P_ITEM" "$P_F" "$P_V" ABORTED - - - - - "script stopped"
  fi
  rm -f "$PENDING"
fi

hdr "PS5 GPU sweep $VERSION"
say "Governor: $GOV_SVC   Stock top point: ${TOP_F} MHz @ ${TOP_V} mV   OC ladder voltage: ${OC_VOLT} mV"
say "Steps: ${#ITEMS[@]} (control + ladders)   Rounds: $ROUNDS   Load: $LOAD, ${STRESS_SECS}s"
say "Mode: $([[ $PER_BOOT == 1 ]] && echo 'one attempt per boot' || echo 'same boot, cooldown between attempts')"

if ! NEXT=$(next_attempt); then summary; write_report; exit 0; fi

say ""
say "WARNING: this drives the GPU past its validated point. A too-high step can freeze the"
say "system mid-load. Save your work. After a freeze: cold boot and run the script again -"
say "it restores your own governor config first, records the crash and resumes."
[[ $(ask "Continue? [y/N]" start) =~ ^[Yy]$ ]] || exit 0

# ---------------------------------------------------------------- attempt --
LOAD_PID=""
on_exit() {
  [[ -n $LOAD_PID ]] && kill "$LOAD_PID" 2>/dev/null
  if [[ -s $PENDING ]]; then
    read -r P_ROUND P_ITEM P_F P_V _ <"$PENDING"
    record "$P_ROUND" "$P_ITEM" "$P_F" "$P_V" ABORTED - - - - - "stopped (Ctrl+C)"
    rm -f "$PENDING"
  fi
  restore_config
  kill "$KEEPALIVE" 2>/dev/null
}
trap on_exit EXIT
trap 'exit 130' INT TERM

set_pending() { printf '%s %s %s %s %s\n' "$1" "$2" "$3" "$4" "$BOOT_ID" >"$PENDING"; sync "$PENDING" 2>/dev/null; }

wait_idle() {
  [[ -n $GPU_DEV ]] || return 0
  local calm=0 t=0
  say "Waiting for the GPU to be idle (close games and video)..."
  while (( calm < 3 )); do
    if (( $(gpu_busy) <= 15 )); then (( calm += 1 )); else calm=0; fi
    sleep 1; (( t++ ))
    (( t == 60 )) && { say "The GPU stayed busy. Skipping this attempt."; return 1; }
  done
}

memtest_bytes() {
  local avail vram mib
  avail=$(( $(awk '/^MemAvailable:/ {print $2}' /proc/meminfo) / 1024 ))
  vram=$(( $(cat "$GPU_DEV/mem_info_vram_total" 2>/dev/null || echo 0) / 1048576 ))
  mib=$(( vram * 3 / 4 )); (( mib <= 0 || mib > avail / 2 )) && mib=$(( avail / 2 ))
  echo $(( mib * 1048576 ))
}

run_attempt() { # round item
  local r=$1 it=$2 f=${ITEM_F[$2]} v=${ITEM_V[$2]} t0 faults errs=0 rc note="" o
  local maxt=0 maxf=0 maxb=0 log
  log="$LOGS/$(date '+%Y%m%d-%H%M%S')-r$1-${2//:/-}.log"
  hdr "Round $r/$ROUNDS, $it, ${f} MHz @ ${v} mV"
  ev attempt "$r" "$it" "$f" "$v"
  ev phase idle
  wait_idle || { record "$r" "$it" "$f" "$v" ABORTED - - - - - "GPU not idle"; return 1; }
  t0=$(date '+%F %T')
  set_pending "$r" "$it" "$f" "$v"
  say "Installing the test point and restarting the governor..."
  ev phase governor
  if ! write_test_config "$f" "$v" || ! gov_restart || { sleep 3; ! gov_active; }; then
    record "$r" "$it" "$f" "$v" GOV-FAIL - - - - - "governor did not come up with the test point"
    rm -f "$PENDING"; restore_config; return 0
  fi

  say "Running $LOAD for ${STRESS_SECS}s..."
  ev phase load
  case $LOAD in
    # memtest_vulkan writes its own memtest_vulkan.log into the current folder, so it runs in the logs folder.
    memtest_vulkan) (cd "$LOGS" && exec timeout -k 10 "$STRESS_SECS" "$LOAD_BIN" 0 "$(memtest_bytes)") </dev/null >"$log" 2>&1 & ;;
    vkpeak)  timeout -k 10 "$STRESS_SECS" bash -c 'while :; do "$0" 0 || exit $?; done' "$LOAD_BIN" </dev/null >"$log" 2>&1 & ;;
    vkmark)  timeout -k 10 "$STRESS_SECS" "$LOAD_BIN" --run-forever -s 2560x1440 -b effect2d:kernel=blur </dev/null >"$log" 2>&1 & ;;
    glmark2) timeout -k 10 "$STRESS_SECS" "$LOAD_BIN" --run-forever -s 2560x1440 </dev/null >"$log" 2>&1 & ;;
  esac
  LOAD_PID=$!
  local start=$SECONDS vv
  while kill -0 "$LOAD_PID" 2>/dev/null; do
    sleep 5
    if [[ -n $GPU_DEV ]]; then
      vv=$(gpu_temp); (( vv > maxt )) && maxt=$vv
      vv=$(gpu_sclk); (( ${vv:-0} > maxf )) && maxf=$vv
      vv=$(gpu_busy); (( vv > maxb )) && maxb=$vv
      if (( maxt >= TEMP_ABORT )); then
        kill "$LOAD_PID" 2>/dev/null; wait "$LOAD_PID" 2>/dev/null; LOAD_PID=""
        record "$r" "$it" "$f" "$v" ABORTED - - "$maxt" "$maxf" "$maxb" "aborted at ${maxt}C - fix cooling first"
        rm -f "$PENDING"; restore_config
        die "the GPU reached ${maxt}C, so the run stops. Improve the cooling, then run the script again to continue."
      fi
    fi
    if [[ -n ${PS5_GUI:-} ]]; then ev load "$(( SECONDS - start ))" "$STRESS_SECS" "$maxt" "$maxf" "$maxb"
    else printf '\r  %3ds  %s C  %s MHz  busy %s%%   ' "$(( SECONDS - start ))" "$maxt" "$maxf" "$maxb"; fi
  done
  wait "$LOAD_PID"; rc=$?; LOAD_PID=""; [[ -n ${PS5_GUI:-} ]] || echo
  faults=$(faults_since "$t0")
  [[ $LOAD == memtest_vulkan ]] && errs=$(grep -c 'Error found' "$log" 2>/dev/null); errs=${errs:-0}
  [[ -n $faults ]] && say "$faults"

  if [[ -n $faults ]]; then o=FAULT
  elif (( errs > 0 )); then o=ERRORS; note="memtest_vulkan error reports: $errs"
  elif (( rc != 124 && rc != 0 )); then o="LOAD-FAIL"; note="$LOAD exit $rc: $(tail -1 "$log" | tr '\t' ' ' | cut -c1-80)"
  elif [[ -n $GPU_DEV ]] && (( maxf < f - 75 )); then o=NO-REACH; note="clock only reached ${maxf} MHz of ${f}"
  else o=PASS; fi
  [[ -n $GPU_DEV ]] && (( maxb < 50 )) && note="${note:+$note; }GPU load only reached ${maxb}%"
  record "$r" "$it" "$f" "$v" "$o" "$errs" "$(grep -c . <<<"$faults")" "$maxt" "$maxf" "$maxb" "${note:--}"
  rm -f "$PENDING"
  restore_config
  say "Result: $o${note:+ ($note)}"
}

if (( PER_BOOT )); then
  run_attempt ${NEXT% *} "${NEXT#* }"
  summary
  if NEXT=$(next_attempt); then
    say ""
    say "Next: round ${NEXT% *}, ${NEXT#* }. Reboot, then run the script again (--per-boot)."
    ev restart-first
  else
    write_report
  fi
else
  while NEXT=$(next_attempt); do
    run_attempt ${NEXT% *} "${NEXT#* }" || break
    say "Cooling down 30 s..."; ev phase cooldown; sleep 30
  done
  summary; next_attempt >/dev/null || write_report
fi
