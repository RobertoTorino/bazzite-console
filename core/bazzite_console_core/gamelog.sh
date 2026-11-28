# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# The emulator log of a game manager's run wrapper (owner, 28-11-2026: everything needed for debugging, in one
# place). A wrapper sources this file and ends with gamelog_run. What the emulator prints goes to the app's
# emulator log, which the View logs tab shows beside the app's own, between lines of the wrapper's own: what the
# game ran with before it, how it ended after it. Every line has the time and a level (INFO, WARNING or ERROR), as
# the app's own log, and the home folder written as ~, so no user name is in it. No serial number or MAC address is
# read. The file turns over at 1 MB with three older ones kept, as the app's own log does. The wrapper stays while
# the emulator runs, passes a stop on to it and ends with its exit code, so Steam sees the game end. SIGINT is passed
# on as SIGTERM: a program started in the background ignores SIGINT.
#
# The wrapper sets before gamelog_run:
#   GAMELOG_NAME      the emulator's name, as the log names it (shadPS4)
#   EMULATOR_LOG      the log file, beside the app's own log
#   GAMELOG_BUILD     the folder of the build in use (emulator/current)
#   INPUT_DEVICES     the kernel's list of input devices
#   game              the game started, or empty
# and may set GAMELOG_TITLE (the game's title, ID and version), STARTED_WITH (the arguments as the log shows them)
# and a function gamelog_details, which adds its own lines with note.
#
# The files and programs read can be others in the tests: GAMELOG_SYS (/sys), GAMELOG_MEMINFO, GAMELOG_CPUINFO,
# GAMELOG_HOSTNAME and GAMELOG_WAIT (the wait for the system log after the end, in seconds).

private_lines() {
    # Each line as it comes, the home folder written as ~ (and /home/<user> for /var/home/<user>, Bazzite's link),
    # as core's platform.private() does: only where the next character is not part of a longer name. With "stamp"
    # (what the emulator prints) each line also gets the time and a level: ERROR for a line that starts with error,
    # fatal or critical or tells of a crash, WARNING for one that starts with warning or tells of something that
    # failed, INFO for the rest. Its own "ERROR:" or "WARNING:" in front goes.
    awk -v stamp="${1:-}" 'function swap(text, from,   out, at, after) {
             out = ""
             while ((at = index(text, from)) > 0) {
                 after = substr(text, at + length(from), 1)
                 out = out substr(text, 1, at - 1) (after ~ /[A-Za-z0-9_]/ ? from : "~")
                 text = substr(text, at + length(from))
             }
             return out text
         }
         BEGIN { home = ENVIRON["HOME"]; sub(/\/+$/, "", home)
                 short = home ~ /^\/var\/home\// ? substr(home, 5) : "" }
         { line = length(home) > 1 ? swap($0, home) : $0
           if (short != "") line = swap(line, short)
           if (stamp != "") {
               lower = tolower(line)
               level = "INFO"
               if (lower ~ /^(error|fatal|critical)[: ]/ ||
                   lower ~ /segmentation fault|core dumped|assertion .*failed|abort(ed)?[: ]|terminate called/)
                   level = "ERROR"
               else if (lower ~ /^warn(ing)?[: ]/ || lower ~ /failed|cannot |could not|unable to/)
                   level = "WARNING"
               if (lower ~ /^(error|fatal|critical|warn|warning): */) sub(/^[A-Za-z]+: */, "", line)
               line = strftime("%d-%m-%Y %H:%M:%S") " " level " " line
           }
           print line; fflush() }'
}

note() {
    # One line of the wrapper's own in the emulator log, in the app's form: note INFO|WARNING|ERROR text.
    printf '%(%d-%m-%Y %H:%M:%S)T %s %s\n' -1 "$1" "$2" | private_lines >>"$EMULATOR_LOG"
}

gamelog_memory() {
    # The memory and swap left, from the kernel's count: gamelog_memory "at the start"|"at the end".
    awk -v when="$1" '/^MemTotal:/ { total = $2 } /^MemAvailable:/ { free = $2 }
        /^SwapTotal:/ { swap = $2 } /^SwapFree:/ { swapfree = $2 }
        END { if (total) printf "Memory %s: %d MiB of %d MiB available, swap %d MiB of %d MiB free.\n",
                                when, free / 1024, total / 1024, swapfree / 1024, swap / 1024 }' \
        "${GAMELOG_MEMINFO:-/proc/meminfo}" 2>/dev/null
}

# What the system log says when a game is ended from outside: the out-of-memory killer (the kernel's and
# systemd-oomd), a GPU hang, reset or fault (bc250-bazzite's Board Test signatures, test-board.sh) and a core dump.
GAMELOG_EVENTS="Out of memory: Killed process|invoked oom-killer|systemd-oomd.*Killed|dumped core"
GAMELOG_EVENTS="$GAMELOG_EVENTS|ring [a-z0-9_.]+ timed? ?out|amdgpu_job_timedout|GPU reset begin|GPU reset\("
GAMELOG_EVENTS="$GAMELOG_EVENTS|amdgpu_device_gpu_recover|Waiting for fences timed out|VM_L2_PROTECTION_FAULT"
GAMELOG_EVENTS="$GAMELOG_EVENTS|GPU fault detected|page fault \(src_id|MES failed|Failed to evict|GPU hang"
GAMELOG_EVENTS="$GAMELOG_EVENTS|soft recovery|reset was successful|failed to write reg|SMU: I'm not done"

gamelog_events() {
    # The system log's lines that match GAMELOG_EVENTS between two times (seconds since 1970), at most 30, each a
    # WARNING; an INFO when there are none or the log cannot be read. The host name is left out.
    if ! command -v journalctl >/dev/null 2>&1 || [ -z "$(journalctl -q -n 1 -o cat 2>/dev/null)" ]; then
        note INFO "System log: not read, so out-of-memory kills and GPU resets are not known."
        return
    fi
    local found line
    found=$(journalctl -q --no-pager -o short-iso --since "@$1" --until "@$2" 2>/dev/null |
            grep -E -m 30 "$GAMELOG_EVENTS" | sed -E 's/^([^ ]+) [^ ]+ /\1 /') || true      # none found
    if [ -z "$found" ]; then
        note INFO "System log: no out-of-memory kill, GPU reset, GPU fault or core dump."
        return
    fi
    while IFS= read -r line; do note WARNING "System log: $line"; done <<<"$found"
}

gamelog_monitor() {
    # The EDID's display name descriptor (tag 0xFC) and the maker's three letters; nothing for no EDID. The serial
    # number descriptor (0xFF) is never read.
    od -An -tu1 -v "$1" 2>/dev/null | awk '
        { for (i = 1; i <= NF; i++) byte[n++] = $i }
        END { if (n < 128) exit
              for (d = 54; d <= 108; d += 18)
                  if (byte[d] == 0 && byte[d + 1] == 0 && byte[d + 3] == 252)
                      for (k = d + 5; k < d + 18 && byte[k] != 10; k++) name = name sprintf("%c", byte[k])
              code = byte[8] * 256 + byte[9]
              maker = sprintf("%c%c%c", 64 + int(code / 1024) % 32, 64 + int(code / 32) % 32, 64 + code % 32)
              sub(/ +$/, "", name)
              print (name != "" ? name " " : "") "(" maker ")" }'
}

gamelog_desktop_mode() {
    # The modes the X server shows the game (XWayland on the desktop, gamescope's in Game Mode): one line per
    # output, "DP-1 1920x1080 at 119.93 Hz". Nothing without a display or xrandr.
    [ -n "${DISPLAY:-}" ] && command -v xrandr >/dev/null 2>&1 || return 0
    xrandr --current 2>/dev/null |
        awk '/ connected/ { output = $1 }
             /\*/ && output != "" { for (i = 2; i <= NF; i++) if ($i ~ /\*/) { rate = $i; gsub(/[*+]/, "", rate) }
                                    print output " " $1 " at " rate " Hz"; output = "" }'
}

gamelog_before() {
    # The lines before the game: what it runs on and with.
    local sys="${GAMELOG_SYS:-/sys}" value build cpu host status dir mode name line controllers folder
    note INFO "$GAMELOG_NAME started: ${STARTED_WITH-$*}"
    build=$(readlink "$GAMELOG_BUILD" 2>/dev/null) || build=""
    note INFO "Build: ${build:-not known}."
    # The board by the name it was given (its host name; owner, 27-11-2026),
    # then its firmware's DMI tables (no serial number) and the processor the kernel names.
    host=${GAMELOG_HOSTNAME:-$(cat /proc/sys/kernel/hostname 2>/dev/null || true)}
    dmi() { value=$(cat "$sys/class/dmi/id/$1" 2>/dev/null) || value=""; echo "${value:-not given}"; }
    note INFO "Board: ${host:-no name}, $(dmi board_vendor) $(dmi board_name), BIOS $(dmi bios_version) of $(dmi bios_date)."
    cpu=$(sed -n 's/^model name[[:space:]]*: *//p' "${GAMELOG_CPUINFO:-/proc/cpuinfo}" 2>/dev/null | head -n 1) || cpu=""
    note INFO "Processor: ${cpu:-not given}, $(nproc 2>/dev/null || echo "?") threads, kernel $(uname -r 2>/dev/null || echo "not known")."
    # The game: by its path when it is one that is there (the last argument can be an option or a title ID), else by
    # its title alone.
    if [ -n "${game:-}" ] && [ "${game#-}" = "$game" ] && [ -e "$game" ]; then
        folder=${game%/}
        note INFO "Game: ${GAMELOG_TITLE:-${folder##*/}}, from $game."
    elif [ -n "${GAMELOG_TITLE:-}" ]; then
        note INFO "Game: $GAMELOG_TITLE."
    fi
    # Every controller SDL can see (a joystick to the kernel), by the name and USB IDs it gives; Steam's virtual one
    # named. A connected Bluetooth controller's address is never read.
    controllers=$(awk -v steam="Steam's virtual controller" '
        /^I:/ { vendor = product = ""
                for (i = 1; i <= NF; i++) {
                    if ($i ~ /^Vendor=/) vendor = tolower(substr($i, 8))
                    if ($i ~ /^Product=/) product = tolower(substr($i, 9))
                } }
        /^N:/ { name = $0; sub(/^N: Name="/, "", name); sub(/"$/, "", name) }
        /^H:/ && / js[0-9]/ && name !~ /Motion Sensors$/ {
            print name " (" vendor ":" product ")" (vendor == "28de" ? ", " steam : "") }' \
        "$INPUT_DEVICES" 2>/dev/null) || controllers=""
    if [ -z "$controllers" ]; then
        note WARNING "Controller: none connected."
    else
        while IFS= read -r line; do note INFO "Controller: $line."; done <<<"$controllers"
    fi
    note INFO "Session: ${XDG_SESSION_TYPE:-not given}, desktop ${XDG_CURRENT_DESKTOP:-not given}, SDL video driver ${SDL_VIDEO_DRIVER:-not set}."
    # Every connected display: the name and maker code its EDID gives and its preferred mode, which the kernel lists
    # first; then the desktop's mode.
    for status in "$sys"/class/drm/card*-*/status; do
        [ -r "$status" ] && [ "$(cat "$status" 2>/dev/null)" = connected ] || continue
        dir=${status%/status}
        mode=$(head -n 1 "$dir/modes" 2>/dev/null) || mode=""
        name=$(gamelog_monitor "$dir/edid") || name=""
        note INFO "Display ${dir##*/}: ${name:-no EDID}, preferred mode ${mode:-not given}."
    done
    while IFS= read -r line; do
        [ -z "$line" ] || note INFO "Desktop mode: $line."
    done < <(gamelog_desktop_mode)
    if declare -F gamelog_details >/dev/null; then gamelog_details; fi
    line=$(gamelog_memory "at the start") && [ -n "$line" ] && note INFO "$line"
    return 0
}

gamelog_run() {
    # Runs the program with the arguments given, its output in the log between the lines before and after, and ends
    # the wrapper with its exit code.
    local program=$1 size n started before status signal level ended line running
    shift
    { [ -d "${EMULATOR_LOG%/*}" ] && : >>"$EMULATOR_LOG"; } 2>/dev/null || exec "$program" "$@"
    size=$(stat -c %s "$EMULATOR_LOG" 2>/dev/null) || size=0
    if [ "$size" -ge 1000000 ]; then
        { rm -f "$EMULATOR_LOG.3"
          for n in 2 1; do [ ! -e "$EMULATOR_LOG.$n" ] || mv -f "$EMULATOR_LOG.$n" "$EMULATOR_LOG.$((n + 1))"; done
          mv -f "$EMULATOR_LOG" "$EMULATOR_LOG.1"; } 2>/dev/null || true
    fi
    started=$(printf '%(%s)T' -1)
    # A start whose wrapper was ended with it (the out-of-memory killer can take the whole game): its file is still
    # there, as no end line was written. What the system log has from then to now comes first, unless that build
    # still runs.
    running="${EMULATOR_LOG%/*}/emulator.running"
    if [ -f "$running" ] && ! pgrep -f -- "$(readlink -f "$GAMELOG_BUILD" 2>/dev/null || echo "$GAMELOG_BUILD")/" \
            >/dev/null 2>&1 && ! pgrep -f -- "$GAMELOG_BUILD/" >/dev/null 2>&1; then
        read -r before <"$running" 2>/dev/null || before=""
        if [[ $before =~ ^[0-9]+$ ]]; then
            note WARNING "The start at $(printf '%(%d-%m-%Y %H:%M:%S)T' "$before") has no end line: it was ended from outside."
            gamelog_events "$before" "$started"
        fi
    fi
    echo "$started" >"$running" 2>/dev/null || true
    gamelog_before "$@"
    exec 3> >(private_lines stamp >>"$EMULATOR_LOG")
    local writer=$!
    GAMELOG_PID=""
    trap '[ -z "$GAMELOG_PID" ] || kill -TERM "$GAMELOG_PID" 2>/dev/null || true' TERM INT
    trap '[ -z "$GAMELOG_PID" ] || kill -HUP "$GAMELOG_PID" 2>/dev/null || true' HUP
    "$program" "$@" <&0 >&3 2>&3 &
    GAMELOG_PID=$!
    status=0
    wait "$GAMELOG_PID" || status=$?
    while kill -0 "$GAMELOG_PID" 2>/dev/null; do     # the wait above was cut short by a stop passed on: wait again
        status=0
        wait "$GAMELOG_PID" || status=$?
    done
    exec 3>&-
    wait "$writer" 2>/dev/null || true                 # its last lines written, a last one without a newline ended
    ended=$(printf '%(%s)T' -1)
    # The level says how it ended: INFO for a normal end or a stop (Steam's, Ctrl+C, a closed terminal), ERROR for
    # any other signal (a crash: SIGSEGV, SIGABRT, SIGPIPE, SIGKILL from the out-of-memory killer), WARNING for an
    # exit code that is not 0.
    signal=""
    [ "$status" -gt 128 ] && signal=$(kill -l "$((status - 128))" 2>/dev/null) && signal="SIG$signal"
    case $status:$signal in
        0:|*:SIGTERM|*:SIGINT|*:SIGHUP) level=INFO ;;
        *:SIG*) level=ERROR ;;
        *) level=WARNING ;;
    esac
    note "$level" "$GAMELOG_NAME ended (exit code $status${signal:+, $signal}) after $((ended - started)) s."
    line=$(gamelog_memory "at the end") && [ -n "$line" ] && note INFO "$line"
    sleep "${GAMELOG_WAIT:-1}" 2>/dev/null || true     # the system log takes a moment to have the last lines
    gamelog_events "$started" "$(printf '%(%s)T' -1)"
    rm -f "$running" 2>/dev/null || true
    exit "$status"
}
