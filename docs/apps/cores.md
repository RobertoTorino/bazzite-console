<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 Core Unlock](../assets/cores/ps5-cores-bisect.webp){ .app-logo }

# PS5 Core Unlock

!!! warning "Changes the board"
    The app sends the SoC's SMU one mailbox message over PCI configuration space with setpci. The message sets the core
    presence mask to 0xFF in the SMU's own memory. The governor's service shares the mailbox, so the app stops it around
    the message and starts it again. The mask takes effect on the next warm reboot and survives warm reboots. A full
    power off reverts it to the stock 6 cores. The 8 cores stay across power offs only through the root service that
    Core Unlock installs, ps5-cores-unlock.service. After a cold boot the service sends the message again and
    warm-reboots once. A guard keeps it from reboot loops. Nothing is written to the BIOS, the firmware, the CMOS or the
    kernel's arguments. Uninstall in Core Unlock disables the service and removes its files. The cores stay on until the
    next full power off, and after it the board is stock. Core Unlock restarts the board after the core unlock,
    and between its rounds when Same boot is off. It counts down 15 seconds first, and Pause stops it.

PS5 Core Unlock tells **bad CPU cores** apart from an **unstable core unlock** on the AMD PS5 (Cyan Skillfish).
Use it *before* you trust or keep the 8C/16T core unlock.

The PS5 ships with 6 of its 8 Zen 2 cores enabled. Its core presence mask is `0x77`. Core 3 of each CCX
(core complex) is fused off, the same in both. That symmetry smells like product segmentation, not harvesting.

The SMU (System Management Unit) is the chip's own controller. It has a quirk, queue-3 message `0x98`, that writes
`0xFF` to any SMN address. SMN is the chip's internal register bus. One of those addresses is the core presence mask
at SMN `0x5A870`, which the host can't write. That write enables all 8 cores on the next warm restart.

**The catch:** that primitive is all-or-nothing. Unlike a GPU CU unlock there is no per-core mask, so you can't
leave one bad core disabled. If *either* extra core is bad, you can't use the core unlock on your board. You want
to know that before you keep it and let a flaky core corrupt data.

`ps5-cores-bisect.sh` does its own unlock, so it needs no other tool. It tests in a way that separates the
possible causes. It is a sibling project of [ps5-cu-bisect](compute.md), which does the same for the GPU CUs.

> **Warning:** this talks to the SMU and runs heavy CPU load. A bad core can freeze the system or
> corrupt data. Save your work first. Use at your own risk.

## How it works

You can't enable the cores one at a time. So the isolation happens **after** the core unlock. The script pins the
load with `taskset` to exactly the threads under test.

| Item           | When            | Pinned to                       | Separates                                             |
|----------------|-----------------|---------------------------------|-------------------------------------------------------|
| `control`      | before unlock   | all stock cores (6C/12T)        | board / power / heat / load tool problems             |
| `post-control` | after unlock    | one stock core (2 threads)      | "the core unlock destabilizes the SoC" from bad cores |
| `coreN`        | after unlock    | one new core on its own         | which new core (if any) is bad                        |
| `combined`     | after unlock    | both new cores together         | cores that pass alone but fail together               |

```
          core0   core1   core2   core4   core5   core6   core3   core7
           ██      ██      ██      ██      ██      ██      ..      ..

██ stock, always enabled (6C/12T)    .. fused off, enabled by the unlock, tested one by one
```

The order isn't a typo. The map groups the stock cores first and the unlocked ones last, where their verdict cells
live.

Why cores 3 and 7 specifically? The mask `0x77` is binary `0111 0111`, one nibble per 4-core CCX. In *each* CCX
it's core 3 that is fused off. CCX0 keeps cores 0,1,2 and CCX1 keeps 4,5,6. The core unlock adds core 3 (CCX0) and
core 7, which is the "core 3" of CCX1. The same position is disabled in both CCXs. That symmetry is what smells like
product segmentation rather than harvesting of defective silicon.

The script shows this map live. It puts `>>` on the core under test. Once a core has a verdict, the map shows one
of these marks:

- `ok` for GOOD
- `xx` for FAILS EVERY TIME
- `??` for RANDOM

The script finds failures in four ways:

- **Machine-check events** in the kernel log (`journalctl -k`). They are the classic symptom of marginal cores.
- **Wrong results, not only crashes.** `stress-ng --verify` recomputes and checks every stressor result.
- **Full crashes**, crash-safe. Before every attempt the script saves what it's doing. After a freeze, restart and
  run it again. It then records the crash and shows the MCE (machine-check event) lines of the previous boot.
- **Optional burn-in extras.** These are `mprime`'s torture test (`--load mprime|both`) and hardware error counters
  from `rasdaemon` (`--rasdaemon`). See [Longer burn-in](#longer-burn-in-mprime--rasdaemon).

The test plan has the same philosophy as the CU bisect:

- **Control first.** The script only offers the core unlock after the stock cores pass every control round. With a
  failing control, the results say nothing about the new cores.
- **Rounds.** Every item runs 3 times by default. The rounds are interleaved, so heat and time don't favor one.
- **One attempt per boot** (default). Warm restarts keep the core unlock, so isolation costs nothing.
- **State machine across boots.** The steps are control → unlock → verify the cores actually came up → bisect →
  verdict. The script detects a cold boot mid-run, because the mask is back to `0x77`, and handles it.
- **Mask gate.** The script refuses boards whose stock mask isn't `0x77`. A different mask strongly suggests
  genuinely defective silicon that was purposefully skipped.

## The verdict and the decision

- **`control` fails** → board, power, heat or load tool. Fix that first.
- **`post-control` fails** → the core unlock destabilizes even the stock cores on your board. Cold boot to revert,
  and don't keep it.
- **A core FAILS EVERY TIME** → likely genuinely bad silicon. The core unlock is all-or-nothing, so **don't use it
  at all.** A cold boot (full power off) reverts everything.
- **RANDOM failures** → points to power or heat, not silicon. Improve cooling and retest.
- **Everything GOOD, alone and combined** → the core unlock looks safe. Keep it, as described below.

## Requirements

- AMD PS5, Linux with bash 4+. Tested against Bazzite (Fedora Atomic).
- `setpci` (pciutils). SMN/SMU access goes through the PCI config space of `0000:00:00.0`.
- `stress-ng` and `taskset` (util-linux).
- sudo rights. The script uses sudo for `setpci`, the kernel log and the governor's service.
- Optional: `mprime` (Prime95) for the torture test and `rasdaemon` (`ras-mc-ctl`) for hardware
  error counters. You only need them if you ask for them.

## Before you start

1. Start from a **cold boot** (full power off). That guarantees the stock `0x77` state.
2. Close background workloads. The load must land only on the pinned cores.
3. The script stops `cyan-skillfish-governor-smu` for the few milliseconds of the SMU write, because the governor
   shares the mailbox. It starts the governor again afterward.

## Usage

Run it as your normal user:

```bash
chmod +x ps5-cores-bisect.sh
./ps5-cores-bisect.sh                 # 3 rounds, 600 s verified load per attempt
./ps5-cores-bisect.sh -t 1800 -r 5    # longer load, more rounds (recommended before trusting it)
./ps5-cores-bisect.sh --same-boot     # no reboots between bisect attempts (faster, less isolation)
./ps5-cores-bisect.sh --auto          # no prompts, auto-reboot, continues after every login
./ps5-cores-bisect.sh --load both     # stress-ng *and* the mprime torture test per attempt
./ps5-cores-bisect.sh --rasdaemon     # also count hardware errors via ras-mc-ctl
./ps5-cores-bisect.sh --status        # results so far, report + logs in ~/Desktop/ps5-cores-bisect/
./ps5-cores-bisect.sh --scan          # read the cores and what a run needs, write nothing
./ps5-cores-bisect.sh --only post-control   # run only the attempts of one item
./ps5-cores-bisect.sh --reset         # delete the results and start over
./ps5-cores-bisect.sh --help
```

The smallest `-t` is 60.

A run goes through these steps:

1. You run the script.
2. It runs the control rounds, one per boot.
3. It offers the core unlock.
4. You do a warm restart.
5. It detects the new cores.
6. It runs the bisect rounds, one per warm restart.
7. It shows the final summary, the report and the decision.

At the end of a run, and on every `--status`, the script copies everything to `~/Desktop/ps5-cores-bisect/`.
That makes it easy to share.

| File                                         | Contents                                                     |
|----------------------------------------------|--------------------------------------------------------------|
| `ps5-cores-bisect-results-<date>.txt`      | The report: core map, verdicts, decision, every attempt.     |
| `runs.tsv`                                   | The raw results table, one line per attempt.                 |
| `config`                                     | The run's settings and detected cores.                       |
| `logs/<date>-r<round>-<item>.log`            | stress-ng output of each attempt, with verification failures.|
| `logs/<date>-r<round>-<item>-mprime.log`     | mprime torture output, when mprime is part of the load.      |
| `ras-mc-ctl-errors.txt`                      | rasdaemon's error table, with `--rasdaemon`.                 |
| `auto.log`                                   | Everything the script printed in `--auto` runs.              |

The working copies live in `~/.local/share/ps5-cores-bisect/`. `--reset` deletes those, not the Desktop folder.
stress-ng keeps its temporary files in `logs/` there. So the script works from any folder, a read-only one too.

Pick `-t`/`-r` before you start and keep them. You *can* change them mid-run. The script then keeps the results so
far and asks you to confirm. But the evidence is then mixed. The report lists the load of every attempt. A control
that finished with fewer rounds keeps them. For a uniform result, use `--reset` and start over.

For `--auto`, install the autostart unit, so the script resumes after every login. See
`ps5-cores-bisect-auto.service.example`.

### Running truly unattended (`--auto` checklist)

`--auto` makes the *script* hands-off, but the *system* must get back to your session on its own:

1. **Autologin.** After each restart someone must log in, or the run stalls at the login screen. Turn it on in
   your desktop. On Bazzite/KDE it is System Settings → Colors & Themes → Login Screen (SDDM) → Behavior →
   auto-login. On GNOME, it is Users → auto-login.
2. **Passwordless sudo** for your user. The script needs `setpci` and `journalctl -k` without a prompt. When it
   runs from the unit, there is no terminal to type a password into.

   ```bash
   echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/ps5-bisect
   sudo chmod 440 /etc/sudoers.d/ps5-bisect
   sudo visudo -cf /etc/sudoers.d/ps5-bisect   # must print "parsed OK"
   sudo -k && sudo -n true && echo OK    # must print OK without asking
   ```
   Revert after testing with `sudo rm /etc/sudoers.d/ps5-bisect`.
   If you edit the file by hand, use `sudo visudo -f /etc/sudoers.d/ps5-bisect`. It refuses to save a broken line.
   A broken line makes every `sudo` command print a warning, or stops sudo working at all.
3. **The autostart unit installed.** Without it nothing starts the script again after login. You would have to
   start it by hand at every boot.
4. **No credential popups at login (KDE Wallet / ksshaskpass).** With autologin the KDE Wallet can't unlock by
   itself. So an "SSH credentials" or wallet dialog can appear at session start. It blocks the chain until you
   answer it. There are two ways around it. Give the wallet a blank password. Open it in `kwalletmanager5` first,
   then choose Change Password → empty. Or turn the wallet subsystem off. Plasma 6 has no checkbox for it anymore,
   so use this command:

   ```bash
   kwriteconfig6 --file kwalletrc --group Wallet --key Enabled false   # kwriteconfig5 on Plasma 5
   ```
   Turn it on again afterward with `... --key Enabled true`. Also uncheck "Use KWallet for the Secret
   Service interface" in System Settings → KDE Wallet. Then apps don't route secrets to the disabled wallet.

Check on it while it runs:

```bash
systemctl --user status ps5-cores-bisect-auto.service   # ran / running / failed this boot
tail -f ~/.local/share/ps5-cores-bisect/auto.log        # live output of the current attempt
./ps5-cores-bisect.sh --status                          # progress and results so far
```

When all attempts are done, the script stops restarting on its own. In `--auto` mode it also disables the autostart
unit by itself. It removes the live-output entry too, which is described below. So nothing starts at the next
login. If you ran without `--auto`, disable the unit by hand with
`systemctl --user disable --now ps5-cores-bisect-auto.service`.

Want the live output on the board's screen instead of a shell? Add a desktop autostart entry that opens a terminal
following the log at every login. This is a KDE example. See the comments in
`ps5-cores-bisect-auto.service.example`.

```bash
cat > ~/.config/autostart/ps5-cores-bisect-watch.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=PS5 bisect live output
Exec=konsole --title "ps5-cores-bisect" -e tail -n 40 -f .local/share/ps5-cores-bisect/auto.log
EOF
```

### How long does it take?

A full run is `5 × rounds` attempts. The items are control, then post-control, core3, core7 and combined. Each
attempt runs the load for `--time` seconds. Add one warm restart for the core unlock.

In the default one-attempt-per-boot mode, add a restart and login of about 1–2 min per attempt. With `--same-boot`
there are only 2–3 restarts in total, plus a 30 s cooldown between attempts. Indications:

| Invocation                           | Attempts | Pure load | Wall clock (approx.)   |
|--------------------------------------|----------|-----------|------------------------|
| default (`-t 600 -r 3`)              | 15       | 2 h 30 m  | ~3 h (15 reboots)      |
| `--same-boot` (`-t 600 -r 3`)        | 15       | 2 h 30 m  | ~2 h 45 m (3 reboots)  |
| `-t 1800 -r 5` (recommended)         | 25       | 12 h 30 m | ~13 h (25 reboots)     |
| `-t 1800 -r 5 --same-boot`           | 25       | 12 h 30 m | ~12 h 45 m (3 reboots) |

The longer runs are for unattended use. Combine them with `--auto` and the autostart unit, and let the run finish
overnight. You don't have to do it in one sitting either. The state survives restarts. So run the script again at
any time, and it continues where it left off. `--status` shows the progress.

### Longer burn-in (`mprime` / `rasdaemon`)

`stress-ng --verify` is the default load and is enough for most boards. For a harder, longer burn-in before you
trust the core unlock, you can add two optional tools:

```bash
./ps5-cores-bisect.sh --load mprime              # mprime torture test instead of stress-ng
./ps5-cores-bisect.sh --load both                # stress-ng first, then mprime
./ps5-cores-bisect.sh --mprime-bin ~/mprime/mprime
./ps5-cores-bisect.sh --rasdaemon                # count hardware errors around every attempt
./ps5-cores-bisect.sh -t 1800 -r 5 --load both --rasdaemon --auto --same-boot
```

- **`--load stress-ng|mprime|both`** (default `stress-ng`). `mprime` runs Prime95's torture test with
  `StressTester=1` and no PrimeNet. It is pinned to exactly the same CPUs as stress-ng. It runs from a private
  working directory under `~/.local/share/ps5-cores-bisect/mprime/<item>/`. The workload is AVX/FMA-heavy,
  in-cache FFT. It catches a different class of marginal silicon than stress-ng's mixed stressors. A torture
  error gives the attempt the outcome **`MPRIME-FAIL`**.
- With **`--load both`** the two tools run **one after the other**, never at the same time. So they don't fight
  over the same threads. Each attempt then takes **2 × `--time`**. Budget double the wall clock from the table
  above.
- **`--mprime-bin PATH`** points at a mprime binary in another place than the ones named under
  [Installing mprime](#installing-mprime).
- **`--rasdaemon`** reads `ras-mc-ctl --errors` before and after every attempt and records the difference. Any
  new hardware error makes the attempt **`RAS-ERROR`**. It needs a running `rasdaemon` service. If `ras-mc-ctl`
  is missing, the script stops and says so. If the service is not running or `ras-mc-ctl` fails, the script
  warns you and carries on without the count. The script exports the full error table as `ras-mc-ctl-errors.txt`.
- The script records both extras per attempt. `runs.tsv` gained a **load tool** and a **rasdaemon errors** column.
  The report lists the load of every attempt, so a mixed run stays readable. The script still reads older result
  files from before this feature correctly.

Like `-t`/`-r`, pick these before you start. The script stores the settings in `config` and reuses them after every
restart. They also go into the command line of the `--auto` service.

#### Installing mprime

[Quickfix](quickfix.md#quickfix) installs mprime with its **Prime95** pill. To install it by hand, download it from
[mersenne.org](https://www.mersenne.org/download/), because no package installs it. Then unpack it into a folder.
These commands do that for version 30.19 build 20, for 64-bit Linux:

```bash
mkdir -p ~/mprime && cd ~/mprime
curl -O https://download.mersenne.ca/gimps/v30/30.19/p95v3019b20.linux64.tar.gz
echo "4ce2377e03deb4cf189523136e26401ba08f67857a128e420dd030d00cdca601  p95v3019b20.linux64.tar.gz" | sha256sum -c
tar -xzf p95v3019b20.linux64.tar.gz
```

The third line compares the download with the SHA-256 that mersenne.org's download page lists, and prints
`p95v3019b20.linux64.tar.gz: OK`. You need nothing more. PS5 Core Unlock and Nexus Deps look for `mprime` in these
places, in this order:

1. `$PATH`
2. `~/mprime/mprime`
3. `~/.local/bin/mprime`
4. `/opt/mprime/mprime`
5. `/usr/local/bin/mprime`

To try it by hand, `./mprime -t` in that folder starts the torture test on all cores right away, without the
questions about PrimeNet. It runs until Ctrl+C stops it, and writes its settings and `results.txt` into the
folder. The core bisect does not use these. It runs mprime from a working folder of its own, with its own settings.

## Making it persistent

Only after a clean verdict:

```bash
sudo ./ps5-cores-unlock.sh --install
```

The core unlock is volatile. It survives warm restarts, and a full power off reverts it. A fresh write only takes
effect on the *next* restart.

So `--install` copies the script to `/usr/local/sbin`, owned by root, and enables a root service. The service
checks the mask early at every boot. After a cold boot it applies the core unlock again and does **one** warm
restart. A guard file prevents restart loops if the core unlock ever stops taking effect.

`--uninstall` removes the service and the copy. The stock 6C/12T returns after the next full power off. `--status`
shows the mask, the threads, and the state of the service and the guard.

> **Note.** A custom BIOS is another route to a lasting core unlock. It is not part of the suite, which stays
> software-only and reversible on the stock P5.00 BIOS.

## The window

![The window of PS5 Core Unlock](../assets/cores/ps5-cores-bisect-gui.webp)

The window runs the core test for you, step by step. You see which cores are on, what is tested now and what comes
next. It runs `ps5-cores-bisect.sh` and `ps5-cores-unlock.sh` itself, inside the window. No terminal opens.

Four boxes under the title show where you are:

- **Cores on now** shows how many of the 8 cores are on, for example **6 of 8**.
- **Boot unlock** says whether the boot service is **Installed**.
- **Attempts done** shows how far the test is.
- **Test** says whether the test is ready, running, paused, stopped or done.

The info symbol says what the app does. The round symbol at the right end of the title row reads the results, the
cores and the boot service again.

Under the boxes are the five steps, one row each. Each row says **Done**, **Do this now**, **Running**, **Stopped** or
**Later**. A row that is done says what came out of it, for example "Passed 3 of 3 rounds on the 6 stock cores."

The row of the step you're on says the one thing to do now, for example "Click **Start**. The test of cores 3 and 7
takes about 20 minutes." The pill it names sits on that row, with an accent border all round. The other pills sit at
the bottom left. While the test runs, the row says that there is nothing to do.

Click a row that is done to look at that step again. A click on a row only shows the step. It doesn't start anything.

When everything is done, a green bar over the steps says so: "Finished. Your board runs all 8 cores at every boot.
There is nothing left to do." The bar also shows when you chose to stay at the stock cores.

While a script runs, an orange turning symbol beside the pills says what runs and for how long. An example is
"Running: round 1, core3 · 64 s". While the window follows a test, it moves to the step that runs, attempt by attempt.

The window opens 900 pixels wide, as wide as the map needs. It never opens higher than your screen. When the page is
higher than the window, the page scrolls. An example is with **Details** open. The **Details** and **Advanced** pills
are at the right end of the bottom row. Under the name they say **Show** or **Hide**.

The map shows the 8 physical cores. Each cell shows its state in words and in color:

- green, **On**: a stock core, or a healthy core that the installed unlock has turned on
- gray, **Not tested**: a new core without a result yet
- yellow, **Testing**: the core under test now
- blue, **Healthy**: it passed every round and is not kept on at every boot yet
- red, **Fails**: it failed every round
- orange, **Random**: it failed in some rounds only

**Step 1, Scan.** **Scan** reads the core presence mask and the cores with `--scan`. It writes nothing to the SMU.
You're asked for your password, because the mask needs root. The window then says how many cores are on, which are
switched off, and what the mask is. It also says how long each part of the test takes. These block the test:

- A core unlock is active, so all 8 cores are on already. Switch the board fully off once, then scan again.
- The mask isn't the usual `0x77`. Your switched-off cores are then very likely defective.
- `stress-ng` isn't found, while the load tool needs it.

**Start test** asks once, then starts the test of the stock cores. **Help** shows the script's own help as a page.

**Step 2, Test the stock cores.** This is the control. The 6 stock cores run the load together, before anything is
unlocked. When a round fails, the window stops here. The board itself, its power or its heat is then at fault. The
window names the round's outcome and offers these pills:

- **Stay at 6** ends the test. Nothing is installed.
- **Start over** deletes the results after a question, so you can test again.
- **Details** shows the script's results.

**Step 3, Unlock and restart.** When every round of the stock cores passed, a notification says so. **Unlock** asks
first. Then the script writes the core unlock, and the board restarts by itself 15 seconds later. **Restart now**
doesn't wait, and **Pause** stops the countdown. After a pause, **Restart** restarts the board.

Restart the board, but don't switch it off. A full power off undoes the core unlock. When the new cores didn't come up,
step 3 says so and offers **Unlock** again.

**Step 4, Test the new cores.** After the restart, the window opens by itself after the login. Step 4 then says what
to do: "Click **Start**." **Start** asks once, then runs the test of the new cores:

- **post-control**, a stock core, for comparison
- each new core on its own, for example **core3** and **core7**
- **combined**, both new cores together

During an attempt, the line under the pills shows the round, the item, the load time, the temperature and the clock.
**Stop** stops the attempt as Ctrl+C does. The attempt then runs again later.

When the board was switched fully off during the test, the new cores are off. Step 4 then offers **Unlock**. That runs
`ps5-cores-unlock.sh --apply`, and the board restarts by itself. The test goes on after the login.

**Step 5, Install.** When every new core passed every round, alone and together, a notification says so. **Install**
asks first. Then it installs the boot service with `ps5-cores-unlock.sh --install`. The cores are on already, so no
restart is needed. The green bar then says that you're finished. From then on, the service turns all 8 cores on at
every boot, also after a full power off.

When a core failed, step 5 advises you to stay at 6 cores. The core unlock turns on all cores or none, so it can't keep
only the healthy one. **Stay at 6** ends the test. Then switch the board fully off once, to put back the stock cores.

**Uninstall** removes the boot service. The cores stay on until the next full power off. Then the board is back at
the stock cores. **Install** and **Uninstall** ask for your password in a masked prompt. The password goes to
`sudo -S` only and is never stored. When the service is installed but not all 8 cores are on, **Root status** shows what
the service did at this boot.

**One boot or restarts.** By default, **Same boot** is on, and every attempt of a step runs in one boot. Between
attempts, the script lets the cores cool down for 30 seconds. You type your password once, and you can leave the
board alone until the step is done. The price is that each attempt inherits the board's state from the attempt
before.

Turn **Same boot** off under **Advanced** to give each attempt a fresh boot. A warm restart keeps the core unlock.
After an attempt, a countdown of 15 seconds runs, with **Restart now** and **Pause**. While the test runs, an autostart
entry opens the window after each login. That entry is `~/.config/autostart/ps5-core-unlock-resume.desktop`. The
window then counts down 20 seconds, with **Go on now** and **Pause**, and runs the next attempt. You're asked for your
password after each restart, unless sudo needs none.

**Pause** removes the autostart entry, and **Go on** adds it again. The entry also goes by itself when the test is
done.

**No sleep during a test.** While a test runs, the board doesn't go to sleep. The window holds the standard sleep
block of `systemd-inhibit`, with the reason "A core test is running". The screen may still turn off or lock, and the
test goes on. The block ends with each run of the script, so nothing stays behind.

**When a step ends.** You don't have to watch the window. When a step ends, a desktop notification appears and stays
until you click it:

- **Stock cores passed** says that step 3 is next.
- **Core test passed** says that the new cores passed and that step 5 is next.
- **Core test done** names the items that fail every time or at random.
- **Core test stopped** says that the stock cores failed, or why the script stopped.

No notification comes when you press **Stop** or **Pause** yourself. A frozen board can't send anything, so its
screen just stays as it was.

**After a freeze.** Switch the board off and on. A power off also undoes the core unlock, so step 4 offers **Unlock**
first. After that restart, the window asks whether the board froze, crashed or restarted by itself. **Yes** records a
crash of that attempt. **No** runs the attempt again.

**The script's questions.** The script can warn before an attempt, for example about a busy system. The window then
shows the warnings and asks once for the whole test. When you change the options during a test, the window asks
whether to go on with the new settings.

**Advanced** opens the test's options. A test that has started keeps its own options, and the fields show them:

- **Load per attempt** (`-t`)
- **Rounds per item** (`-r`)
- **Load tool** (`--load`), with the choices stress-ng, mprime and both
- **Same boot** (`--same-boot`), on by default, with no restarts between attempts
- **Hardware log** (`--rasdaemon`)

Hover a choice of **Load tool** to see what it does, and see [Longer burn-in](#longer-burn-in-mprime--rasdaemon).

**Details** opens what both scripts print. **Report** writes the results so far to a text file on your Desktop,
with `--status`. The window remembers its position and the advanced options.

**Installing it: `install.sh`.** Run it from a clone or the extracted release tarball. It installs these parts:

* a root-owned copy of the tools in `/opt/ps5-cores-bisect-v<version>`, with `/opt/ps5-cores-bisect`
  pointing at it
* a private PyQt6 venv in `~/.local/share/ps5-cores-bisect-app/venv`
* the launcher `~/.local/bin/ps5-cores-bisect-gui`
* an app menu entry and a Desktop icon

It also removes the separate unlock window of earlier versions. Run it as your own user. Only the copy to `/opt`
asks for the sudo password.

```bash
./install.sh                         # install or update
./install.sh --no-desktop-shortcut   # app menu entry only, no Desktop icon
ps5-cores-bisect-gui               # or launch it from the app menu
./install.sh --uninstall             # remove the app and its autostart entry; keeps results, settings, logs and the unlock
./install.sh --uninstall --purge     # also remove results, settings, logs and the autostart unit
```

Your bisect results stay in `~/.local/share/ps5-cores-bisect`. The installer never touches that folder unless
you pass `--purge`.

Per-user alternative, no `/opt` and nothing root-owned:

```bash
bash packaging/bazzite/install-bisect-gui.sh     # venv + launcher + menu entry "PS5 Core Unlock"
bash packaging/bazzite/uninstall-bisect-gui.sh   # removes all of that again (keeps your results and the unlock)
```

**From a venv (development):**

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m cores_bisect   # --script PATH and --unlock-script PATH to use other scripts
```

## Known side effect

After the core unlock, `pp_dpm_sclk` and the `hwmon` file `freq1_input` report nonsense GPU clocks of tens of MHz.
This is cosmetic. The SMU's own clock getters stay correct, and this script ignores GPU clocks.
Diagnostics that read those files will flag it, for example tests 19/40 of [Board Test](board.md). That is
expected while the core unlock is active. The GPU governor's `fix-freq` option puts the real clock back.

## Credits

[rw-r-r-0644/ps5-core-unlock](https://github.com/rw-r-r-0644/ps5-core-unlock) (MIT) discovered and documented
the SMU quirk. The quirk is queue-3 message `0x98`, which writes `0xFF` at SMN `0x5A870`. This project
is an independent implementation built around those hardware facts. It adds the control/bisect/verdict
method, crash-safe multi-boot state, and reversible persistence.

## License

GNU GPLv3, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/cores/LICENSE).
