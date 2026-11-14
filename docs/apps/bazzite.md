<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Bazzite Test](../assets/bazzite/bazzite-test.webp){ .app-logo }

# Bazzite Test

Read-only diagnostics, a stress test and benchmarks for a **PlayStation 5** running **Bazzite** on the ps5-linux
kernel: about sixty tests in twelve groups, from the platform, the GPU and the sensors to the network, the disks,
the logs and crash forensics. Each test reports SUCCESS, INFO, NOTE, WARNING or ERROR lines, with a hint where
something can be done.

Nothing is installed, enabled, disabled or reconfigured. The only exceptions are the opt-in stress test, which
deliberately puts the console under load, and the optional write part of the disk speed test, which writes one
temporary file and removes it.

---

## Install

Bazzite Test is always installed with the portal (see [Install](../install.md)); it is the first tile on the
**Sustainable** tab. It can also be installed from a checkout of the repository:

```bash
apps/bazzite/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/bazzite/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/bazzite/install.sh --uninstall             # remove it; --purge removes its settings too
```

Run the installer as your own user, not with `sudo`: it asks for the password only to copy the app to `/opt`.
Start *Bazzite Test* from the portal, the app menu or the icon on your Desktop, or run `bazzite-test` in a terminal.

What `install.sh` does:

* copies the app, with the shared code it was released with, to `/opt/bazzite-test-v<version>` (root-owned),
  points `/opt/bazzite-test` at it and removes older versions;
* uses the suite's shared Python environment `~/.local/share/bazzite-console-suite/venv` with PyQt6 (created on
  first use; the wheels bundle Qt, nothing else is needed; about 100 MB of download the first time). The
  environment is removed with the last suite app that uses it;
* adds the launcher `~/.local/bin/bazzite-test`, an app menu entry and a Desktop icon.

Nothing is layered with `rpm-ostree` for the app itself.

**Optional tools** some tests use (stress-ng, vkpeak, memtest_vulkan, fio, speedtest and others) can be installed
with `/opt/bazzite-test/development/tools/install-requirements.sh`: it says what each group is for and asks per
group. See [Requirements](#requirements).

> **Why `/opt`?** The test engine runs as root through sudo. A release build therefore refuses to run
> `test-bazzite.sh` unless the file and every folder above it are owned by root and writable by root only, and the
> file matches the SHA-256 recorded when the release was built. A copy in your home directory fails that check on
> purpose. An install from a checkout has no recorded checksum: the app then shows an orange *Development mode*
> bar and runs the tests anyway.

**Update:** from the portal, or run the new version's `install.sh` again. It replaces the old version; your
settings and the history are kept, as they live in your home directory.

**Uninstall:** Bazzite Test has no Uninstall in the portal, and stays when the portal is removed. Remove it with
its own installer:

```bash
/opt/bazzite-test/install.sh --uninstall           # keeps settings, history and reports
/opt/bazzite-test/install.sh --uninstall --purge   # removes those too
```

## Reporting problems

Open an [issue](https://github.com/RobertoTorino/bazzite-console/issues) and add the app version
(*Settings › About*) and the full report of the run (*Show Logs*). The report contains details about your system:
read it before you post it. Security problems: see [Security](../SECURITY.md).

---

## Using the app

* **Run all tests** runs the passive diagnostics, plus the stress test when *Include stress test (41) in run* is
  ticked. Or open a category on the left and run one test, or all tests of that category.
* A test button turns **yellow** while it runs, then **green** (passed), **orange** (warning), **red** (failure)
  or **blue** (information only).
* The output appears in the terminal of the page, fix suggestions in the **Hints** panel next to it.
* The boxes at the top count the latest result of every test and give a **health score**. Click *Warnings*,
  *Failures* or *Info / hints* to see what is behind the number.
* Most checks need administrator rights. When a password is needed, a masked prompt appears; the password is
  never shown, saved or logged.
* **History** lists every run by date (pick a date range). Select a run to see its results and measurements;
  select two (Ctrl-click) to compare them side by side, for example before and after a kernel update: what got
  better or worse, and by how much.
* The run button shows the progress, and the time left during the stress test. Closing the window during a run
  asks first and stops the tests cleanly. A run of a minute or more that finishes while you're in another window
  gives a desktop notification (*Settings › General*).
* The app remembers its window size, the last page, the panel sizes and the stress settings.
* **Show Logs** lists earlier runs, colored like the live output; **Settings** has privacy options, a system
  overview, log cleanup, version information and **Print results**: it shows the header boxes as a compact
  "PS5 Bazzite Test Results" card, easy to compare with other users. Under the card: **Save…** saves it as a PNG
  where you choose (`results.png` in Downloads at first) and opens it; **Copy** puts it on the clipboard, to paste
  in a chat or a forum post; **Share** sends it to a phone paired with KDE Connect (one entry per phone in reach),
  opens your mail app with it attached (**Email…**), or shows it in the file manager (**Show in file manager**),
  where a right-click and **Share** offers the rest. Share writes the card to `results-card.png` in
  `~/Desktop/bazzite-test/` first, overwritten each time.
* **Game details** records a game while you play: copy its launch line into the game's
  *Properties → Launch options* in Steam. Every session becomes a graph, and when the game ends the page shows
  **Checks for the last session**. See [Game details](#game-details).
* The benchmark (42), the disk speed test (43) and the internet speed test (44) are never part of *Run all
  tests*: start them from their own buttons, on an idle system.

## The window in detail

**The left pane:** the Overview, one page per test category, History, Game details, Help (this chapter) and
Settings.

**The boxes at the top** count the latest result of every test over all runs, also after a restart: *Tests*
available, *Finished* (tests with a result in the history), *Passed*, *Warnings*, *Failures* and *Info / hints*.
The test buttons show that result too; their tooltip has its date. Behind *Warnings*, *Failures* and
*Info / hints* are, per test, the WARNING, ERROR or INFO lines and the hints from the log of that result: click a
test name to open its page, or *Show in log* to open the run log at that test.

* **Health score:** passed and info tests count 100%, warnings 50% and failures 0%, averaged over the tests that
  ran. Green from 90%, orange from 70%, red below.
* **CPU score** (purple) and **GPU score** (blue): the last performance benchmark (test 42), where 100 is the
  baseline you saved on this PS5. Hover for details.

**The status bar** (bottom right) shows live values, every 2 s:

* **CPU / GPU:** whole-system load. The GPU load comes from the kernel's load sensor when it has one, else from
  the GPU time of your processes; hover to see which, and what a sample costs.
* **🎮 Game:** while a game runs, its name, the share of the CPU and GPU it uses and, with MangoHud logging on,
  its FPS.
* **↓ / ↑:** download and upload traffic over the network interfaces, from `/proc/net/dev`.
* **Hz:** the refresh rate of the display the app is on.
* **Live:** switch it off to stop sampling. It also pauses while the window is minimized.

It slows down by itself when sampling gets expensive, so it is safe to keep running while you play.

**Settings** opens a panel over the window (close it with ✕, Esc or a click outside):

| Section | What it holds |
|---|---|
| Privacy | What is stored and sent, the test history, log masking, administrator rights |
| General | The notification after a long run, copying the full reports to the Desktop |
| System overview | The model, active CUs, CPU cores and threads, the last speed test, NVMe size and free space, and the package count, at a glance. Hover a box for details. |
| Logs & history | Clean up logs |
| About | Version, build date, repository, license |
| Print results | The results card |

### Running and stopping

* **Run all tests** never includes the benchmark (42), the disk speed test (43) or the internet speed test (44);
  **Run all &lt;category&gt; tests** runs every test on that page.
* Only one run happens at a time; the buttons are off while it runs.
* **Stop** stops the current run: the tests first end their CPU and GPU load and remove their temporary files.
  The test that was running goes back to not run.
* A test takes the color of the worst line it logged (error over warning over success over info). Its output
  also streams into the terminal of the test's own category page. The **Hints** panel collects suggested fixes
  and background notes, each with the number of its test.
* The stress test, the benchmark, the disk speed test and the internet speed test each ask before they start and
  say what they will do.

### Administrator password

Most checks read root-only logs and sysfs, so the tests run through `sudo`. When sudo needs a password, a masked
prompt appears; the password goes straight to sudo and is never stored or logged. sudo remembers it for its usual
timeout, so you are not asked for every test. *Settings › Privacy* can turn sudo off (fewer checks, never a
password), and **Forget sudo authentication now** makes sudo forget the password right away.

### Logs

Every run is saved as `~/.local/share/bazzite-test/logs/<YYYYmmdd-HHMMSS>_<scope>.log`. **Show Logs** on a page
lists that page's runs; *Show all logs* lists every run. With *Mask personal data in saved GUI logs* on (the
default, *Settings › Privacy*), host and user name, home folder, drive serial numbers, MAC and IP addresses, the
machine id and the speed test's ISP and result URL are replaced by placeholders in these files; the terminal
shows everything. The full reports are not masked: check them before you post them anywhere.

Below the list of runs, **Files mentioned in this run** lists every log, CSV and config file the selected run
refers to (the full report, the stress CSV, the GPU load tool's log, and so on). Click one to read it. A warning
icon means the file is not on this machine; very large files show their last 2 MiB; root-only files show the
`sudo less` command to use instead. For a CSV, **Show graph** plots it and **Open CSV** opens it in LibreOffice
Calc.

**Clean up logs** (*Settings › Logs & history*) removes the run logs older than N days (default 30), or all logs.
The dialog shows what goes before anything happens. Removing old logs keeps the results in the history; *Remove
ALL* also empties the history. The full reports are owned by root, so removing them asks for your password.
`bench-baseline.json` and the benchmark and speed test history CSVs are always kept.

### History

Every result is stored in a small SQLite database, `~/.local/share/bazzite-test/history.db`: per run the date,
scope, active CUs and cores/threads (kernel version and mitigation state only when turned on in
*Settings › Privacy*); per test the status and the number of hints; and the numbers worth comparing (benchmark
scores, stress clocks and temperatures, disk and internet speeds, package counts). No test output is stored in
it. Full reports that are not in the history yet (in `/var/log/bazzite-test` and the Desktop folder) are imported
at startup. The history and the logs are readable by your user only. When the history is damaged or was changed
outside the app, it is kept aside as `history.db.damaged-<date>` and a new, empty history starts. With *Keep a
test history* off (*Settings › Privacy*), results are kept for this session only.

On the **History** page, **From** / **to** pick the dates and **All dates** shows everything again.

* **One run selected:** its results per category, its measurements and the files it wrote. **Show logs** opens
  its log and full report; click a test name to open its page.
* **Two runs selected** (Ctrl-click or Shift-click): side by side, the older run on the left, with the tests
  whose result changed and every measurement with the difference. Green is better, red is worse; differences
  under 2% count as the same (measurement noise). Untick *Only differences* to see every test.

Typical use: run everything and the benchmark, change something (a kernel update, the CPU boost, the cooling),
run them again, and compare the two runs.

### Integrity of the tests

Before every run the app checks that the test files are exactly the ones that came with this version and that
only an administrator can change them (see *Why `/opt`?* above). If not, no tests run, since they would run with
administrator rights, and a red bar at the top says so: reinstall the app.

### Graphs

**Show graph** opens a chart window for the CSV files the tests write:

* **Stress telemetry** (next to the stress settings): the latest stress run as panels over time. Pick older runs
  from the *File* list. A clock that drops while the temperature climbs is thermal throttling; a line that simply
  stops is the moment the console froze.
* **Benchmark history** (Performance page): bar charts per run of the scores against the baseline. Bars are
  labeled *#run CUs threads*; hover for the date, mitigations and kernel.
* **Disk write test** (Storage and memory page): the write speed and the drive temperature against the amount
  written.
* **Speed test history** (Network page): every internet speed test side by side.
* **Any CSV** in Show Logs: one panel per numeric column.

Drag a rectangle to zoom in, right-click to zoom out, hover a line for its value. *Save as PNG…* saves all panels
as one image. **Open CSV**, beside each Show graph, opens the file in LibreOffice Calc.

### Stress test and benchmark settings

* **Stress test (41):** *Stress duration* is how long the load runs (10–3600 s, default 120), *Sample interval*
  the seconds between telemetry samples (default 2). It loads all CPU threads (`stress-ng`, or shell busy-loops)
  and the GPU (`memtest_vulkan`, which also checks the memory for errors and is recommended, or `vkpeak`,
  `vkmark`, `glmark2`, `vkcube`). This is a deliberate attempt to reproduce lockups under load: the system is
  sluggish while it runs and may freeze. If it does, the last telemetry line is the console's final operating
  point. The app asks before it starts.
* **Benchmark (42):** *CPU time per phase* is the seconds per `stress-ng` phase (5–300, default 20); keep it the
  same between runs you compare. Close games and other heavy apps first. How to save the baseline:
  [Performance score](#performance-score-comparing-kernels-and-settings).
* **Disk speed test (43):** *also test writes* adds the write part, *Write size (GiB)* sets how much it writes
  (1–256, default 8). See [Storage and memory](#storage-and-memory).

### Game details

The **Game details** page records a game while you play. Its *Steam setup* card shows two launch lines, each with
a copy button: one starts the game unchanged, the other starts it under MangoHud so FPS is recorded too (when
MangoHud is not installed, the game still starts). Put one in the game's *Properties → Launch options* in Steam.
No root is needed.

* While the game runs, a sample goes to a CSV every few seconds: FPS, the game's CPU and GPU share, the total
  load, the GPU clock and temperature, VRAM and GTT, the SoC and CPU temperatures, the fan's duty and the free
  system memory. A value the PS5 does not report stays empty.
* A game appears on the page after its first session. Per game: **Record this game** turns recording on or off,
  **Sample every** sets the interval (1–60 s), and the page shows the playtime, the last session and the recorded
  sessions, newest first, as graphs.
* A screenshot of the game is taken once, about 45 s into the first recorded session, and shown on the page.
  **New screenshot** removes it, so the next recorded session takes a fresh one.
* **Checks for the last session** give a verdict per subject: the real 1% and 0.1% lows and the stutter share
  from MangoHud's per-frame log, whether the session was GPU- or CPU-bound, whether VRAM, GTT or the system
  memory ran out, the temperatures, whether the GPU clock dropped over the session, and any amdgpu errors the
  kernel logged while the game ran. They always describe the newest session; older sessions keep their graphs.
* **FPS** comes from MangoHud's log, which is off by default. **Enable FPS logging** adds `output_folder` and
  `autostart_log=1` to `~/.config/MangoHud/MangoHud.conf` (and to the copy of Steam's Flatpak when there is
  one); nothing else in the file changes. The game must still run with MangoHud: use the second launch line.
  Without logging, the game's name and its CPU and GPU share are still recorded.
* **In-game overlay:** *Show overlay* puts a small translucent box on the screen with the live values. It never
  takes focus and lets all mouse input through. *Test overlay* shows it with sample numbers for about 45 s; drag
  it where it should sit, and the position is saved for the games. It is a normal window: it shows over windowed
  and borderless-fullscreen games on the desktop, while Game Mode and exclusive fullscreen can cover it.
* **Set MangoHud overlay style** is for those: it writes the app's own MangoHud config,
  `~/.config/bazzite-test/MangoHud.conf`, in the overlay's look and with FPS logging on. The launch lines pass
  it to MangoHud, so your own `MangoHud.conf` is untouched. It takes effect at the next game start.
* The page also reads the launch options in Steam: a game whose line starts the game monitor from a folder or a
  python that is gone would not start at all, so it is listed with the line to put in its place; **Refresh**
  checks again. Copy the launch line from the installed app, not from a checkout: a line from a checkout stops
  working when that folder moves.

## Output files

All files of the test engine go to `/var/log/bazzite-test/`:

| File                                     | Contents                                                                    |
|------------------------------------------|-----------------------------------------------------------------------------|
| `ps5-test-results-<YYYYmmdd-HHMMSS>.log` | Full report.                                                                |
| `ps5-stress-<YYYYmmdd-HHMMSS>.csv`       | Stress telemetry, written only by a stress run.                             |
| `ps5-gpuload-<YYYYmmdd-HHMMSS>.log`      | Output of the GPU load tool, written only by a stress run.                  |
| `ps5-memtest-<YYYYmmdd-HHMMSS>.log`      | memtest_vulkan's own log, when it was the GPU load tool.                    |
| `ps5-bench-<YYYYmmdd-HHMMSS>.json`       | Benchmark result, written only by the benchmark.                            |
| `ps5-bench-vkpeak-<YYYYmmdd-HHMMSS>.log` | vkpeak output of the benchmark.                                             |
| `ps5-bench-history.csv`                  | One line per benchmark run, to compare configurations over time.            |
| `bench-baseline.json`                    | The benchmark baseline (= 100), once you saved one.                         |
| `ps5-disk-<YYYYmmdd-HHMMSS>.csv`         | Write speed and drive temperature per 256 MiB, only when writes are tested. |
| `ps5-speedtest-<YYYYmmdd-HHMMSS>.json`   | Raw speed test result, only by the internet speed test.                     |
| `ps5-speedtest-history.csv`              | One line per internet speed test.                                           |

The report and the files of that run are copied to `~/Desktop/bazzite-test/` of the desktop user at the end of
the run for easy sharing (*Settings › General › Copy the full reports to ~/Desktop/bazzite-test after each run*,
on by default). During a stress run the files are flushed to disk after every sample, so they survive a hard
lockup.

The app additionally keeps its own captured output of every run as
`~/.local/share/bazzite-test/logs/<YYYYmmdd-HHMMSS>_<scope>.log`. These are not the files above, just what the
test engine printed during that run.

The stress CSV's columns are `elapsed_s, sclk_mhz, mclk_mhz, gpu_busy_pct, vram_used_mib, gtt_used_mib,
gpu_temp_c, gpu_power_w, vddgfx_mv, cpu_tctl_c, cpu_mhz_avg, fan_rpm, load1, fan_duty_pct, soc_temp_c`. The PS5
reports no GPU power, GPU voltage, memory clock or fan speed in RPM, so those columns stay empty; the fan is in
`fan_duty_pct`. `gpu_busy_pct` comes from the kernel's `gpu_busy_percent` when it works; otherwise the test
measures the GPU engine time of every GPU client from `/proc/*/fdinfo`. The log states which source was used.

The stress summary reports peak VRAM and GTT use as a percentage of each budget, warning at 90% VRAM
(allocations spilling into GTT) and 85% GTT (the GPU is close to running out of memory).

Game details writes one CSV per gameplay session to
`~/.local/share/bazzite-test/game-logs/ps5-game-<game>-<YYYYmmdd-HHMMSS>.csv` (columns `elapsed_s, fps,
game_cpu_pct, game_gpu_pct, cpu_pct, gpu_pct, sclk_mhz, mclk_mhz, gpu_temp_c, gpu_power_w, vram_used_mib,
gtt_used_mib, vddgfx_mv, fan_rpm, cpu_temp_c, cpu_mhz_avg, mem_avail_mib, soc_temp_c, fan_duty_pct`). Next to
each CSV is a small `.json` with what is only measured once per session: the VRAM and GTT budget, the real 1% and
0.1% lows and stutter share from MangoHud's per-frame log, and the amdgpu errors the kernel logged while the game
ran. The game's screenshot is `ps5-game-<game>.png` in the same folder; the per-game settings and playtime are in
`~/.config/bazzite-test/games.ini`.

Every line of a report is tagged `SUCCESS`, `INFO`, `NOTE`, `WARNING` or `ERROR`, and a `[SUMMARY]` block at the
end reports the overall verdict. In the app these become the button colors, the counters and the hints panel.

---

## Tests

### System

| #  | Test                         | Checks                                                                          |
|----|------------------------------|---------------------------------------------------------------------------------|
| 00 | Platform Identification      | Confirms a PlayStation 5 (DMI) with its model (launch model, Slim or Pro; disc or digital edition), the ps5-linux kernel's PS5 drivers, Bazzite, the kernel, and that the loader's `bzImage` on `/boot/efi` is the running kernel. |
| 01 | Running Services             | Lists every active systemd service.                                             |
| 02 | Failed Units                 | Errors on any unit in a failed state.                                           |
| 03 | System Uptime                | Reports uptime and load average.                                                |
| 11 | Resource Consumption         | Top CPU and memory consumers.                                                   |
| 12 | Boot Time                    | `systemd-analyze` breakdown, warns on units taking over a minute.               |
| 31 | File and Directory Integrity | Verifies `/var/log` exists and is writable.                                     |

### Network

| #  | Test                   | Checks                                                                    |
|----|------------------------|---------------------------------------------------------------------------|
| 04 | Network Connectivity   | Pings `google.com`.                                                       |
| 05 | DNS Resolution         | Resolves `google.com`.                                                    |
| 06 | Public Internet Access | Fetches `https://www.example.com`.                                        |
| 07 | Open Ports             | Lists listening TCP/UDP sockets.                                          |
| 08 | NTP Synchronization    | Confirms the clock is synchronized.                                       |
| 30 | SSH Service            | Reports `sshd.service` / `sshd.socket` state (off by default on Bazzite). |
| 53 | Wi-Fi Adapter          | The PS5's built-in Wi-Fi: the IW620 on the `moal` driver (or a MediaTek card), whether its driver is loaded and its firmware is in place. |
| 44 | Internet Speed         | **Opt-in**: run it from its button on the Network page. See below.        |

**How test 44 measures the connection** (Ookla's `speedtest`, or `speedtest-cli` as a fallback; about 30 s):

* **Download and upload** in Mbps, plus the data used (roughly 1 GB on a fast line).
* **Idle latency and jitter**, and the **latency while downloading and uploading**. When the loaded latency is
  more than 100 ms above idle the line suffers from *bufferbloat*: games lag whenever something else uses the
  connection. The fix is SQM (fq_codel or CAKE) in the router. Only Ookla's CLI measures loaded latency.
* **Packet loss** (Ookla only): over 1% is a warning.
* **The local link**: the interface the traffic uses (Ethernet or Wi-Fi) and its link speed. A 10 or 100 Mbit/s
  Ethernet link is a warning (a damaged or 2-pair cable); a download near the link speed means the port is the
  limit.
* A VPN in the path is noted, because then the VPN is measured, not the line.
* Every run is appended to `ps5-speedtest-history.csv`; **Show graph** compares all runs.
* Install Ookla's CLI: download the Linux x86_64 `.tgz` from <https://www.speedtest.net/apps/cli> and put the
  `speedtest` binary in `~/.local/bin`. Running it accepts Ookla's license and GDPR terms, and the result is
  stored on speedtest.net.

### Storage and memory

| #  | Test                             | Checks                                                                                 |
|----|----------------------------------|----------------------------------------------------------------------------------------|
| 09 | Disk Configuration               | Filesystem usage and mount points.                                                     |
| 10 | NVMe Devices                     | Detection; PCIe link speed and width against what the drive and the slot support; DRAM cache or host memory buffer (DRAM-less); SMART health: wear, media errors, spare, temperature and time spent throttling, unsafe shutdowns. No NVMe drive is only reported: the PS5 may run from a USB drive. |
| 14 | Memory and Swap                  | RAM usage and the full swap topology: zram, zswap, disk swap, overlaps and swappiness. |
| 37 | Unified Memory and VRAM Pressure | VRAM and GTT usage, OOM-kill history, framebuffer pin failures, the VRAM split in `/boot/efi/vram.txt`, `vm.max_map_count`. |
| 49 | CPU Memory Bandwidth             | `stress-ng` STREAM-like bandwidth on 1 thread and all threads; shows the GDDR6 latency cost the CPU pays for the GPU's console-class bandwidth. |
| 43 | Disk Speed (read, write, SLC cache) | **Opt-in**: run it from its button on the Storage and memory page. See below.       |

**How test 43 measures the system disk** (the disk that holds `/var/tmp`):

* **Sequential read**: `dd` reads 4 GiB straight from the partition with direct I/O. Nothing is written. On an
  NVMe drive the result is compared with the PCIe link ceiling.
* **Random 4K read** at queue depth 1 and 32: `fio --readonly` over the whole partition, 10 s each. This part is
  skipped without a system-wide `fio` (a fio in Homebrew or `~/.local/bin` is not run as root). A high latency
  at queue depth 1 is typical of a DRAM-less drive without a host memory buffer.
* **Sequential write and SLC cache**, only with *Disk speed test (43): also test writes* ticked:
    * Writes a temporary file in `/var/tmp` in 256 MiB chunks (direct I/O, flushed) and deletes it afterwards.
      Btrfs compression is switched off for the file (`chattr +C`), as compression would fake the result.
    * Each chunk's speed and the drive temperature go to `ps5-disk-<timestamp>.csv`; **Show graph** plots it.
    * The point where the speed falls below 60% of the starting speed is reported as the SLC cache size. If the
      drive was at its warning temperature at that moment, it is reported as thermal throttling instead.
    * Pick a size larger than the expected cache: a few GiB on cheap or QLC drives, tens of GiB on large TLC
      drives. It needs that size plus 5 GiB free. The run stops early if the drive reaches its critical
      temperature.

**DRAM cache detection (test 10)**:

* No drive reports "has DRAM" directly.
* DRAM-less NVMe drives ask the host for a *Host Memory Buffer* (the `HMPRE` field of `nvme id-ctrl`). The
  kernel logs it as `allocated N MiB host memory buffer`.
* The test reads both. If neither is present, the drive has its own DRAM.
* On the PS5 the buffer comes out of the RAM that is shared with the GPU.

### System logs

| #  | Test           | Checks                                                                           |
|----|----------------|----------------------------------------------------------------------------------|
| 15 | Boot Logs      | Current-boot kernel errors, with known-benign PS5 and Bazzite noise filtered out. |
| 16 | System Journal | Journal errors from the last 7 days, same filtering.                             |

The log tests follow the log lines with a hint per kind of line: what it means and what to do about it, with the
number of lines it covers.

### GPU and graphics

| #  | Test                  | Checks                                                                     |
|----|-----------------------|----------------------------------------------------------------------------|
| 17 | amdgpu Driver         | Confirms `amdgpu` is bound to the PS5's APU.                               |
| 18 | GPU Governor          | The kernel's `ps5-gpufreq` (devfreq) sets the GPU clock, no governor service is needed: its governor (`simple_ondemand` follows the load) and its temperature limit. Warns when a GPU governor service made for other hardware is active. |
| 19 | GPU Frequency Scaling | The `ps5-gpufreq` clock steps, the allowed range, the clock now and the clock changes since boot. |
| 20 | Vulkan / Mesa         | Confirms RADV reports GFX1013 and not the llvmpipe software fallback.      |
| 21 | Compute Unit Count    | Active CUs from the kernel (36 on a PS5, 60 on a Pro), and RADV's view when `vulkaninfo` is there. |
| 47 | Vulkan Futureproof Matrix | Vulkan API level and the feature set modern games need: ray tracing, mesh shaders, VRS, pipeline libraries and the VRAM carveout against today's 8 GiB recommendation. Hard evidence of which current and upcoming titles can run at all. |
| 50 | Video Decode and Encode (VCN) | `vainfo` codec matrix: H.264/HEVC/VP9/AV1 decode and encode. Matters for streaming, OBS recording and video playback while gaming. |
| 51 | HDMI-CEC | The PS5's CEC adapter (the kernel's `ps5-cec`), whether the TV answers a poll, and Bazzite's CEC mode. Whether the PS5 can turn the TV on and off; see [HDMI CEC Manager](cec.md). |
| 52 | HDMI-CEC Services | Whether the services behind the TV control run: Valve's CEC daemon (`cecd`), HDMI CEC Manager's background service when installed, and Bazzite's dGPU CEC services when enabled. A service that is installed but not running is a warning; one that is not installed is only reported. |
| 29 | Display Session       | Display manager, session and compositor, and the PS5 HDMI state.           |

### CPU and firmware

| #  | Test                      | Checks                                                                          |
|----|---------------------------|---------------------------------------------------------------------------------|
| 23 | IOMMU                     | Counts IOMMU groups. Information only: on the PS5 the IOMMU may stay on.        |
| 24 | CPU Mitigations           | Whether `mitigations=off` is on the kernel command line (the ps5-linux default, for speed; a choice, not a fault) and what the CPU reports per vulnerability. |
| 25 | CPU Core and Thread Count | Reports cores and threads: the PS5's CPU has 8 cores and 16 threads.            |
| 26 | CPU Power Management      | The PS5 has no cpufreq: the CPU clock now, and the boost of ps5-linux-tools (`ps5boost.service`, 3.5 GHz) when installed. |

### Stability and thermals

| #  | Test                          | Checks                                                                        |
|----|-------------------------------|-------------------------------------------------------------------------------|
| 22 | Hardware Sensors              | `ps5_fan` (the SoC and mainboard temperatures, the fan's duty, mode and curve), `k10temp` (CPU), the GPU (ps5-linux kernel 7.3.1 and later) and NVMe. The SoC from 85 °C and the CPU from 85 °C are a warning. |
| 27 | Handheld Daemon               | Confirms `hhd.service` is masked: the PS5 has no handheld controls and it can cause micro-stuttering. |
| 28 | Suspend Targets               | Whether the kernel can suspend (s2idle), whether systemd may, the sleep hooks and the suspends since boot. |
| 40 | Power Delivery and Throttling | The GPU's clock ceiling and temperature limit, and the kernel's throttle and power messages. The PS5 gives no GPU power reading. |

The fan's control, with a thermal guard, is [Fan Control](fan.md).

### Crash forensics

| #  | Test                                | Checks                                                                                      |
|----|-------------------------------------|---------------------------------------------------------------------------------------------|
| 34 | Previous Boot Shutdown Integrity    | Flags previous boots that ended with no shutdown sequence: the signature of a hard lockup.  |
| 35 | GPU Hang and Reset History          | Ring timeouts, GPU resets, VM faults and soft recoveries across retained boots.             |
| 36 | Kernel Panic, Lockup and Crash Dump | Oopses, soft/hard lockups, call traces, `coredumpctl` records and NMI watchdog state.       |

### Gaming

| #  | Test                           | Checks                                                                                  |
|----|--------------------------------|-----------------------------------------------------------------------------------------|
| 38 | Steam and Gaming Stack         | Steam, gamescope, gamemode, MangoHud, umu; library paths and free space.                |
| 39 | Audio Stack                    | PipeWire/WirePlumber state, default sink and ALSA cards.                                |
| 48 | Real-Game Frametime (MangoHud logs) | Reads the most recent MangoHud logs from real play sessions: average FPS, 1% and 0.1% lows and stutter share. Evidence from actual games, which synthetic benchmarks cannot give. |
| 41 | CPU + GPU Stress and Telemetry | **Opt-in.** Loads the PS5 and records the GPU clock, the temperatures (GPU, SoC, CPU), the fan's duty and the load throughout; includes a sustained-performance verdict (first minute against last minute). |

**What test 41 watches for.** The load stops by itself when the GPU, the SoC or the CPU reaches 95 °C, or when
the free RAM drops below 5% (at least 512 MiB). Afterward it reports whether the GPU was really loaded and its
clock followed, whether the clock held over the run (97% of the first minute's average or more is a pass, under
90% a warning), any moment the GPU load stopped, the memory errors memtest_vulkan found, and the GPU hangs,
panics, throttling and out-of-memory events the kernel logged during the run.

### Performance

| #  | Test                                    | Checks                                                                                              |
|----|-----------------------------------------|-----------------------------------------------------------------------------------------------------|
| 42 | Performance Benchmark (CPU / GPU score) | **Opt-in**: run it from its button. CPU single- and multi-thread and GPU FP32 compute, scored against a baseline saved on this PS5, plus a comparison ladder against known systems. |

See [Performance score](#performance-score-comparing-kernels-and-settings) below.

### PS5

| #  | Test                      | Checks                                                                          |
|----|---------------------------|---------------------------------------------------------------------------------|
| 54 | Loader and Boot Partition | Where the loader's FAT partition is (a USB stick or SSD) and that it is `/boot/efi`; `bzImage`, `initrd.img` and `cmdline.txt` on it; that `root=` in `cmdline.txt` points at a drive that is there; `vram.txt`; a second partition labeled `boot` (the wrong one may be mounted); free space. |
| 55 | HDMI Output (ps5-linux)   | The HDMI bridge's state: recovery status, mode, color depth, HDCP mode and failures, FRL (4K at 120 Hz), ALLM. |
| 56 | Bluetooth (IW620 / MediaTek) | Whether the IW620's Bluetooth half runs its firmware or fell back to ROM mode (only a cold boot reloads it), the controller, and the sleep hook that keeps it across suspend; a MediaTek combo on other consoles. |
| 57 | ps5-linux-tools           | The boost (`ps5boost`: CPU 3.5 GHz) and fan (`ps5fan`) services of ps5-linux-tools, when installed, and the light bar. |
| 58 | Firmware Versions         | The model (CFI-...), the south bridge revision, the GPU's firmware (PSP, VCN and others), the IW620's driver and firmware, the last connected DualSense's. The PS5 system software version is not visible to Linux. |
| 59 | USB Storage               | USB drives (the loader's drive, data SSDs): the bridge chip, UAS or usb-storage, the link speed, whether `smartd` polls their SMART data, and USB resets this boot. |

### Updates

| #  | Test                   | Checks                                                                           |
|----|------------------------|----------------------------------------------------------------------------------|
| 13 | Security Configuration | firewalld zones and SELinux enforcement mode.                                    |
| 32 | OSTree Deployment      | On an Atomic Bazzite: the deployments, and a staged one waiting for a reboot. A flattened PS5 image has none. |
| 33 | Update and Patch       | Available updates, read-only: `dnf` on a flattened image, `rpm-ostree` on an Atomic one; Flatpak remotes. |
| 45 | Installed Packages     | Counts installed software per source: image RPMs, layered and overridden packages, Flatpak apps (system and user), Homebrew, AppImages and Distrobox containers. Names and versions only. |

---

## Performance score: comparing kernels and settings

Test 42 runs fixed workloads and scores them against a **baseline: a run on your own PS5 with its usual
settings** = 100. A score of 108 means 8% faster than the baseline. Use it to compare kernels and settings: the
CPU boost, the GPU's governor, the cooling.

| Score     | Workload                                                              |
|-----------|-----------------------------------------------------------------------|
| CPU score | `stress-ng --cpu-method matrixprod`, all threads                      |
| (CPU 1T)  | Same on one thread, reported in the log and the history               |
| GPU score | `vkpeak` FP32 GFLOPS (the best of fp32-scalar and fp32-vec4)          |

vkpeak's `copy-d2d` memory bandwidth is recorded too. The log names the configuration of the run: cores and
threads, CUs, the GPU's top clock, whether the CPU boost is on, mitigations and the kernel. It warns when the
system is not idle, as background load lowers the scores.

1. With the PS5 in its usual settings (the boost as you use it, nothing else running), tick *Save as baseline
   (this PS5, usual settings)* on the Performance page and run test 42 once. This writes
   `/var/log/bazzite-test/bench-baseline.json`, the 100 mark.
2. Change something and run test 42 again. The CPU and GPU score boxes at the top show the result; *Benchmark
   history* lists all runs, with the scores recalculated against the current baseline, and **Show graph**
   compares them.

Once a baseline exists, *Save as baseline* is off: delete `bench-baseline.json` to save a new one. Without a
baseline there are no scores; the raw results are still saved.

The log ends with a **comparison ladder**: the measured FP32 figure as a percentage of the published theoretical
peaks of known systems (a Steam Deck, an XBOX Series S, the PS5's own figure from Sony, desktop graphics cards).
It ranks raw shader compute only, not FPS: memory bandwidth, drivers, the Vulkan feature set (test 47) and the
CPU decide how games run.

It needs `stress-ng` for the CPU score and `vkpeak` for the GPU score
([releases](https://github.com/nihui/vkpeak/releases), put the binary in `~/.local/bin`); without one of them
that score is missing.

---

## After a freeze

After a freeze or a sudden restart, start the console again and:

* run tests **34**, **35** and **36** (Crash forensics): boots that ended without a shutdown, GPU hangs and
  resets, kernel panics and lockups;
* run test **37**: out-of-memory kills and framebuffer pin failures. The PS5 shares one 16 GB memory pool
  between the CPU and the GPU, so running out of it can freeze the console;
* run test **22** for the temperatures and the fan.

To reproduce it under observation, set *Stress duration* to 300 s and run the stress test (41). A telemetry line
prints to the page's terminal about every 10 seconds, and the files are flushed after every sample, so the last
values are the console's final operating point.

Useful follow-up commands:

```bash
journalctl --list-boots                  # which boots are still retained
journalctl -b -1 -n 50                   # last entries before the previous boot ended
coredumpctl list --since "-14 days"      # crashed applications
cat /sys/class/devfreq/ps5-gpufreq/cur_freq    # the GPU clock now, in Hz
```

## The VRAM split

The loader reads the size of the GPU's own memory (the VRAM carveout) from `/boot/efi/vram.txt`; the GPU borrows
system RAM on top of it (GTT). Tests 37 and 54 report the split, test 41 and Game details how much of it was
used. What the tests advise:

* **Framebuffer pin failures** (test 37) mean the carveout is too small for your games. Only a larger split
  fixes that: set it in `/boot/efi/vram.txt` (for example `0x80000000` for 2 GiB), then reboot.
* **A small split** caps the total at the split plus half the RAM. Test 37 then advises
  `ttm.pages_limit=3014656` (about 11.5 GiB) in `/boot/efi/cmdline.txt`, then a reboot.

Both files are on the loader's partition. The app only reads them.

## Requirements

The app never installs anything: it only detects what is already there. The optional helper shipped with the
app installs the tools below. It asks per group:

```bash
/opt/bazzite-test/development/tools/install-requirements.sh          # interactive
/opt/bazzite-test/development/tools/install-requirements.sh --all    # everything, no questions
```

It layers the packages `stress-ng`, `lm_sensors`, `vkmark`, `nvme-cli` and `fio` with `rpm-ostree` (active after
a reboot; this group needs an Atomic image) and downloads `vkpeak`, `memtest_vulkan` and Ookla's `speedtest`
into `~/.local/bin`.

| Tool                                 | Used by             | Without it                                                              |
|--------------------------------------|---------------------|-------------------------------------------------------------------------|
| `stress-ng` or `stress`              | Test 41 CPU load    | Shell busy-loops, one per thread. Still saturates the CPU.              |
| `stress-ng`                          | Tests 42, 49        | No CPU score; no memory bandwidth.                                      |
| `vkpeak`                             | Test 42 GPU score   | No GPU score.                                                           |
| `memtest_vulkan` or `vkpeak`         | Test 41 GPU load    | vkmark, glmark2 or vkcube (much lighter).                               |
| `vkmark`, `glmark2` or `vkcube`      | Test 41 GPU load    | CPU-only stress plus a warning.                                         |
| `lm_sensors`                         | Test 22             | The test reads the sensors from sysfs itself.                           |
| `vulkaninfo` (vulkan-tools)          | Tests 20, 21, 47    | Those checks are skipped; test 21 uses the kernel's value.              |
| `nvme-cli` or `smartctl`             | Test 10             | DRAM or host memory buffer guessed from the kernel log; no SMART health. |
| `fio`                                | Test 43             | Random 4K read skipped (sequential read and write use `dd`).            |
| `vainfo` (libva-utils)               | Test 50             | No codec matrix.                                                        |
| `cec-ctl` (v4l-utils)                | Test 51             | The adapter is named, but not read.                                     |
| Ookla `speedtest` or `speedtest-cli` | Test 44             | Test 44 warns and is skipped. `speedtest-cli` has no loaded latency or packet loss. |

* The order of preference for the GPU load is memtest_vulkan, vkpeak, vkmark, glmark2, vkcube.
* **memtest_vulkan is recommended.** It keeps the GPU fully busy and also checks the memory for errors; any
  error found is reported as an ERROR. It isn't packaged: download the Linux build from
  [its releases](https://github.com/GpuZelenograd/memtest_vulkan/releases) and put the `memtest_vulkan` binary in
  `~/.local/bin` (the app finds it there).
* **User-installed tools never run as root.** The app finds tools in `~/.local/bin` and Homebrew itself instead
  of adding those folders to root's PATH. Anything writable by your user is run as your user, not as root. `fio`
  needs root to read the raw partition, so a fio from Homebrew or `~/.local/bin` is not used.
* A Flatpak version of a tool is not detected: the binary has to be on `PATH`.
* memtest_vulkan is limited to three quarters of the VRAM carveout (at least 2 GiB) and at most half of the
  available RAM, so it cannot fill the memory the desktop needs.
* Memory safety during the stress run: the GPU load tool is the OOM killer's first victim, the test protects
  itself so it can always stop the load, the tool is wrapped in `timeout` so it never outlives the test, and a
  memory guard stops the run when the available RAM drops below 5% (at least 512 MiB).
* vkmark and glmark2 render one light frame at a time and may not keep the GPU busy; test 41 then warns that
  the GPU was never meaningfully loaded. As a fallback they run in a 2560x1440 window.
* The CPU load runs at the lowest priority (`SCHED_IDLE`, or `nice 19` without `chrt`), so it never slows the
  GPU load tool or the desktop.
* vkcube is a spinning cube: it registers, but does not push the GPU hard enough to be a real stability test.
* Screen locking, blanking and sleep are inhibited for the length of the stress run.

## What goes over the network

The app itself sends nothing: no telemetry, no account, no update check. Some tests contact the internet, only
when you run them:

* tests 04–06 ping and resolve `google.com` and open `https://www.example.com`;
* test 33 asks for available updates (`dnf check-update`, or `rpm-ostree upgrade --check` on an Atomic image);
* test 44 runs the speed test: its servers see your public IP address, and the result is stored on
  speedtest.net.

See [Privacy](../privacy.md) for the suite as a whole.

---

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/bazzite/LICENSE).
It is distributed in the hope that it will be useful, but **without any warranty**.

Third-party components: Qt 6 (LGPL v3), PyQt6 (GPL v3), the Inter font (SIL Open Font License 1.1).
