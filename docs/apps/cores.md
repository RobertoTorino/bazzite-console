<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 CPU Tools](../assets/cores/ps5-cores-bisect.webp){ .app-logo }

# PS5 CPU Tools

!!! warning "Changes the board"
    The app sends the SoC's SMU one mailbox message over PCI configuration space with setpci, which sets the
    core presence mask to 0xFF in the SMU's own memory; the governor's service is stopped around the message, as
    it shares the mailbox, and started again. The mask takes effect on the next warm reboot, survives warm
    reboots, and a full power off reverts it to the stock 6 cores. The 8 cores stay across power offs only
    through the root service that CPU Tools installs, ps5-cores-unlock.service, which sends the message
    again after a cold boot and warm-reboots once, with a guard against reboot loops. Nothing is written to the
    BIOS, the firmware, the CMOS or the kernel's arguments. Uninstall in CPU Tools disables the service and
    removes its files; the cores stay on until the next full power off, and the board is then stock. CPU Tools
    reboots the board between its rounds, by itself with the unattended option, after a question otherwise.

Tells **bad CPU cores** apart from an **unstable core unlock** on the AMD PS5 (Cyan Skillfish),
*before* you trust or persist the 8C/16T unlock.

The PS5 ships with 6 of its 8 Zen 2 cores enabled (presence mask `0x77`: core 3 of each CCX fused
off, symmetric — which smells like product segmentation, not harvesting). The SMU exposes a quirk
(queue-3 message `0x98`) that writes `0xFF` to any SMN address, including the core presence mask at
SMN `0x5A870`, which the host can't write. That enables all 8 cores on the next warm reboot.

**The catch:** that primitive is all-or-nothing. Unlike a GPU CU unlock there is no per-core mask, so
you can't leave one bad core disabled. If *either* extra core is bad, the unlock is unusable on your
board — and you want to know that before you persist it and let a flaky core corrupt data.

`ps5-cores-bisect.sh` does its own unlock, so no other tool is involved, and tests in a way that
separates the possible causes. Sibling project of
[ps5-cu-bisect](compute.md), which does the same for the GPU CUs.

> **Warning:** this talks to the SMU and runs heavy CPU load. A bad core can freeze the system or
> corrupt data. Save your work first. Use at your own risk.

## How it works

Since the cores can't be enabled one at a time, the isolation happens **after** the unlock, with the
load pinned (`taskset`) to exactly the threads under test:

| Item           | When            | Pinned to                       | Separates                                       |
|----------------|-----------------|---------------------------------|-------------------------------------------------|
| `control`      | before unlock   | all stock cores (6C/12T)        | board / power / heat / load tool problems       |
| `post-control` | after unlock    | one stock core (2 threads)      | "the unlock destabilises the SoC" from bad cores |
| `coreN`        | after unlock    | one new core on its own         | which new core (if any) is bad                  |
| `combined`     | after unlock    | both new cores together         | cores that pass alone but fail together         |

```
          core0   core1   core2   core4   core5   core6   core3   core7
           ██      ██      ██      ██      ██      ██      ..      ..

██ stock, always enabled (6C/12T)    .. fused off, enabled by the unlock, tested one by one
```

The order isn't a typo: the map groups the stock cores first and the unlocked ones last, where their
verdict cells live. Why cores 3 and 7 specifically? The mask `0x77` is binary `0111 0111` — one
nibble per 4-core CCX, and in *each* CCX it's core 3 that is fused off. CCX0 keeps cores 0,1,2 and
CCX1 keeps 4,5,6; the unlock adds core 3 (CCX0) and core 7 (CCX1's "core 3"). That symmetry — the
same position disabled in both CCXs — is what smells like product segmentation rather than harvesting
of defective silicon.

The script shows this map live, with `>>` on the core under test and `ok`/`xx`/`??` once a core has a
verdict (GOOD / FAILS EVERY TIME / RANDOM).

Failures are detected four ways:

- **Machine-check events** in the kernel log (`journalctl -k`) — the classic symptom of marginal cores.
- **Wrong results, not only crashes:** `stress-ng --verify` recomputes and checks every stressor result.
- **Full crashes**, crash-safe: before every attempt the script saves what it's doing. After a freeze,
  reboot and run it again: it records the crash and shows the MCE lines of the previous boot.
- **Optional burn-in extras:** `mprime`'s torture test (`--load mprime|both`) and hardware error
  counters from `rasdaemon` (`--rasdaemon`); see [Longer burn-in](#longer-burn-in-mprime--rasdaemon).

The test plan, same philosophy as the CU bisect:

- **Control first:** the unlock is only offered after the stock cores pass every control round. A
  failing control means nothing can be concluded about the new cores.
- **Rounds:** every item runs several times (default 3), interleaved, so heat and time don't favor one.
- **One attempt per boot** (default): warm reboots preserve the unlock, so isolation costs nothing.
- **State machine across boots:** control → unlock → verify the cores actually came up → bisect →
  verdict. A cold boot mid-run is detected (mask back to `0x77`) and handled.
- **Mask gate:** boards whose stock mask isn't `0x77` are refused — a different mask strongly suggests
  genuinely defective silicon that was purposefully skipped.

## The verdict and the decision

- **`control` fails** → board, power, heat or load tool. Fix that first.
- **`post-control` fails** → the unlock destabilises even the stock cores on your board. Cold boot to
  revert; don't persist.
- **A core FAILS EVERY TIME** → likely genuinely bad silicon. Because the unlock is all-or-nothing:
  **don't use it at all.** Cold boot (full power off) reverts everything.
- **RANDOM failures** → points to power or heat, not silicon. Improve cooling and retest.
- **Everything GOOD, alone and combined** → the unlock looks safe; persist it (below).

## Requirements

- AMD PS5, Linux with bash 4+. Tested against Bazzite (Fedora Atomic).
- `setpci` (pciutils) — SMN/SMU access goes through the PCI config space of `0000:00:00.0`.
- `stress-ng` and `taskset` (util-linux).
- sudo rights (for setpci and the kernel log only).
- Optional: `mprime` (Prime95) for the torture test and `rasdaemon` (`ras-mc-ctl`) for hardware
  error counters. Both are only needed if you ask for them.

## Before you start

1. Start from a **cold boot** (full power off) so the stock `0x77` state is guaranteed.
2. Close background workloads; the load must land only on the pinned cores.
3. The script stops `cyan-skillfish-governor-smu` for the few milliseconds of the SMU write (the
   governor shares the mailbox) and restarts it afterwards.

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
./ps5-cores-bisect.sh --reset         # delete the results and start over
./ps5-cores-bisect.sh --help
```
Note: -t minimum = 60       

Flow: run → control rounds (one per boot) → it offers the unlock → warm reboot → it detects the new
cores → bisect rounds (one per warm reboot) → final summary, report and decision.

At the end of a run (and on every `--status`) everything is copied to `~/Desktop/ps5-cores-bisect/`
for easy sharing:

| File                                         | Contents                                                     |
|----------------------------------------------|--------------------------------------------------------------|
| `ps5-cores-bisect-results-<date>.txt`      | The report: core map, verdicts, decision, every attempt.     |
| `runs.tsv`                                   | The raw results table, one line per attempt.                 |
| `config`                                     | The run's settings and detected cores.                       |
| `logs/<date>-r<round>-<item>.log`            | stress-ng output of each attempt (verification failures etc).|
| `logs/<date>-r<round>-<item>-mprime.log`     | mprime torture output, when mprime is part of the load.      |
| `ras-mc-ctl-errors.txt`                      | rasdaemon's error table, when `--rasdaemon` is used.         |
| `auto.log`                                   | Everything the script printed in `--auto` runs.              |

The working copies live in `~/.local/share/ps5-cores-bisect/`; `--reset` deletes those, not the
Desktop folder.

Pick `-t`/`-r` before you start and keep them. You *can* change them mid-run (results so far are
kept and the script asks you to confirm), but the evidence is then mixed: the report lists the load of
every attempt, and a control that finished with fewer rounds keeps them. For a uniform result, use
`--reset` and start over.

For `--auto`, install the autostart unit (see `ps5-cores-bisect-auto.service.example`) so the script
resumes after every login.

### Running truly unattended (`--auto` checklist)

`--auto` makes the *script* hands-off, but the *system* must get back to your session on its own:

1. **Autologin** — after each reboot someone must log in, or the run stalls at the login screen.
   Enable it in your desktop (Bazzite/KDE: System Settings → Colors & Themes → Login Screen (SDDM) →
   Behavior → auto-login, or Users → auto-login on GNOME).
2. **Passwordless sudo** for your user — the script needs `setpci` and `journalctl -k` without a
   prompt (there is no terminal to type a password into when it runs from the unit):

   ```bash
   echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/ps5-bisect
   sudo chmod 440 /etc/sudoers.d/ps5-bisect
   sudo visudo -cf /etc/sudoers.d/ps5-bisect   # must print "parsed OK"
   sudo -k && sudo -n true && echo OK    # must print OK without asking
   ```
   Revert after testing with `sudo rm /etc/sudoers.d/ps5-bisect`.
   If you edit the file by hand, use `sudo visudo -f /etc/sudoers.d/ps5-bisect`: it refuses to save a broken line.
   A broken line makes every `sudo` command print a warning, or stops sudo working at all.
3. **The autostart unit installed** — without it nothing restarts the script after login and you'd
   have to start it manually every boot.
4. **No credential popups at login (KDE Wallet / ksshaskpass)** — with autologin the KDE Wallet
   can't auto-unlock, so a "SSH credentials" / wallet dialog can appear at session start and block
   the chain until answered. Either give the wallet a blank password (open it in `kwalletmanager5`
   first, then Change Password → empty), or disable the wallet subsystem (Plasma 6 has no UI
   checkbox for it anymore):

   ```bash
   kwriteconfig6 --file kwalletrc --group Wallet --key Enabled false   # kwriteconfig5 on Plasma 5
   ```
   Re-enable afterwards with `... --key Enabled true`. Also uncheck "Use KWallet for the Secret
   Service interface" in System Settings → KDE Wallet so apps don't route secrets to the disabled
   wallet.

Check on it while it runs:

```bash
systemctl --user status ps5-cores-bisect-auto.service   # ran / running / failed this boot
tail -f ~/.local/share/ps5-cores-bisect/auto.log        # live output of the current attempt
./ps5-cores-bisect.sh --status                          # progress and results so far
```

When all attempts are done the script stops rebooting on its own; in `--auto` mode it also disables
the autostart unit and removes the live-output entry (below) by itself, so nothing starts at the next
login. If you ran without `--auto`, disable the unit manually
(`systemctl --user disable --now ps5-cores-bisect-auto.service`).

Want the live output on the board's screen instead of a shell? Add a desktop autostart entry that
opens a terminal following the log at every login (KDE example; see the comments in
`ps5-cores-bisect-auto.service.example`):

```bash
cat > ~/.config/autostart/ps5-cores-bisect-watch.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=PS5 bisect live output
Exec=konsole --title "ps5-cores-bisect" -e tail -n 40 -f .local/share/ps5-cores-bisect/auto.log
EOF
```

### How long does it take?

A full run is `5 × rounds` attempts (control, then post-control + core3 + core7 + combined), each
running the load for `--time` seconds, plus one warm reboot for the unlock. In the default
one-attempt-per-boot mode add a reboot-and-login (~1–2 min) per attempt; with `--same-boot` only 2–3
reboots total plus a 30 s cooldown between attempts. Indications:

| Invocation                           | Attempts | Pure load | Wall clock (approx.)   |
|--------------------------------------|----------|-----------|------------------------|
| default (`-t 600 -r 3`)              | 15       | 2 h 30 m  | ~3 h (15 reboots)      |
| `--same-boot` (`-t 600 -r 3`)        | 15       | 2 h 30 m  | ~2 h 45 m (3 reboots)  |
| `-t 1800 -r 5` (recommended)         | 25       | 12 h 30 m | ~13 h (25 reboots)     |
| `-t 1800 -r 5 --same-boot`           | 25       | 12 h 30 m | ~12 h 45 m (3 reboots) |

The longer runs are meant to be unattended: combine them with `--auto` (and the autostart unit) and
let it finish overnight. You don't have to do it in one sitting either — the state survives reboots,
so run the script again at any time and it continues where it left off (`--status` shows progress).

### Longer burn-in (`mprime` / `rasdaemon`)

`stress-ng --verify` is the default load and is enough for most boards. If you want a harder,
longer burn-in before you trust the unlock, two optional tools can be folded in:

```bash
./ps5-cores-bisect.sh --load mprime              # mprime torture test instead of stress-ng
./ps5-cores-bisect.sh --load both                # stress-ng first, then mprime
./ps5-cores-bisect.sh --mprime-bin ~/mprime/mprime
./ps5-cores-bisect.sh --rasdaemon                # count hardware errors around every attempt
./ps5-cores-bisect.sh -t 1800 -r 5 --load both --rasdaemon --auto --same-boot
```

- **`--load stress-ng|mprime|both`** (default `stress-ng`). `mprime` runs Prime95's torture test
  (`StressTester=1`, no PrimeNet) pinned to exactly the same CPUs as stress-ng, from a private
  working directory under `~/.local/share/ps5-cores-bisect/mprime/<item>/`. It is an
  AVX/FMA-heavy, in-cache FFT workload, which catches a different class of marginal silicon than
  stress-ng's mixed stressors. A torture error gives the attempt the outcome **`MPRIME-FAIL`**.
- With **`--load both`** the two tools run **one after the other**, never at the same time, so they
  don't fight over the same threads. Each attempt therefore takes **2 × `--time`** — budget double
  the wall clock from the table above.
- **`--mprime-bin PATH`** points at an mprime binary that isn't on `$PATH` (the official builds from
  mersenne.org are a plain tarball, so this is the normal case).
- **`--rasdaemon`** reads `ras-mc-ctl --errors` before and after every attempt and records the
  difference. Any new hardware error makes the attempt **`RAS-ERROR`**. It needs a running
  `rasdaemon` service; if `ras-mc-ctl` is missing or unusable the script says so and carries on
  without it. The full error table is exported as `ras-mc-ctl-errors.txt`.
- Both extras are recorded per attempt: `runs.tsv` gained a **load tool** and a **rasdaemon errors**
  column, and the report lists the load of every attempt, so a mixed run stays readable. Older
  result files from before this feature are still read correctly.

Like `-t`/`-r`, pick these before you start: the settings are stored in `config`, reused after
every reboot, and carried into the `--auto` service's command line.

## Making it persistent

Only after a clean verdict:

```bash
sudo ./ps5-cores-unlock.sh --install
```

The unlock is volatile: it survives warm reboots, a full power off reverts it, and a fresh write only
takes effect on the *next* reboot. So `--install` copies the script to `/usr/local/sbin` (root-owned)
and enables a root service that checks the mask early at every boot; after a cold boot it re-applies
the unlock and warm-reboots **once** (a guard file prevents reboot loops if the unlock ever stops
taking effect). `--uninstall` removes the service and the copy; the stock 6C/12T returns after the
next full power off. `--status` shows mask, threads, service and guard state.

A BIOS-mod route exists for true permanence
([RescueMei/PS5-DXEv3-BIOSMOD](https://github.com/RescueMei/PS5-DXEv3-BIOSMOD)) but is out of
scope here: this project stays software-only and reversible.

## The window

![The window of PS5 CPU Tools](../assets/cores/ps5-cores-bisect-gui.webp)

`cores_bisect` is an optional PyQt6 window for both scripts, on one page. Its top half sets up a run of
`ps5-cores-bisect.sh` and starts it; its bottom half keeps a tested unlock with `ps5-cores-unlock.sh`. It doesn't
run the bisect itself: **Start** hands off to a terminal running the exact command line you'd have typed by hand,
and the window closes. Everything it does can also be typed by hand.

**Starting a run.** The pills under the title:

* **Help**: what the window does, then the script's own `--help` as a page: what the script does, the control,
  post-control and core items, and every option in a table.
* **Start**: shows a summary of the options and, after Yes, starts the run in a terminal.
* **Show status**: runs `--status` in a terminal: the results so far and the report. It starts nothing.
* **Reset**: runs `--reset` after a question: every saved result and log in `~/.local/share/ps5-cores-bisect` is
  deleted, and the script asks once more in the terminal.

Under them, on one line: **Load per attempt** (`-t`), **Rounds per item** (`-r`) and **Load tool** (`--load`:
stress-ng, mprime or both; hover a choice to see what it does, and see
[Longer burn-in](#longer-burn-in-mprime--rasdaemon)). Beside them is a rough estimate of the whole run, which
follows the options; its tooltip says how it is reckoned.

The switches are pills that say **On** or **Off**; a click turns one over:

* **Rasdaemon** (`--rasdaemon`) and **Same boot** (`--same-boot`).
* **Unattended** (`--auto`) turns on **Auto resume** with it. Auto resume writes and enables
  `~/.config/systemd/user/ps5-cores-bisect-auto.service`, which starts the run again after every reboot and
  login: the same steps as the [`--auto` checklist](#running-truly-unattended---auto-checklist). The script removes
  it again once every item is done. It can only be on with Unattended.

**Keeping the unlock.** The window reads the results that `ps5-cores-bisect.sh` left in
`~/.local/share/ps5-cores-bisect` and only enables **Install** once they accept the unlock. The row for it:

* **Accepted** or **Not accepted**: the verdict on the bisect results. Accepted only when the bisect phase is
  finished, no attempt is still in progress, control and post-control are clean, and every new core and the
  combined item passed **every** round. Its tooltip says why, e.g. a failing core or random failures; notes (the
  control ran fewer rounds, the load changed during the run) are shown there too but don't block.
* **Install**: enables the root service of `ps5-cores-unlock.sh --install`, which keeps the 8 cores at every
  boot. It is off until the results accept the unlock.
* **Uninstall**: removes the service; the cores stay on until the next full power off, then the board is back to
  the stock 6C/12T.
* **Refresh**: shows the threads, the service's and the guard's state (`--status`, no root needed; the mask too
  when sudo needs no password).
* **Root status**: the same status as root, asking for the sudo password when needed, so it always shows the
  core presence mask.
* **Re-check**: reads the bisect results again, for example after more rounds finished, and writes the verdict and
  its reasons in the log.

Uninstall, Refresh, Root status and Re-check don't depend on the verdict. Install, Uninstall and Root status run
`ps5-cores-unlock.sh` through `sudo` (a masked password prompt, passed to `sudo -S` only, never stored), and only
ask for the password when sudo needs one.

Under the row are the 8 physical cores in the order of the script's map: the 6 stock cores, then the 2 the unlock
adds, each marked `ok` (passed every round), `xx` (fails every time), `??` (random) or `..` (not tested yet). The
**i** beside them explains the marks.

**Show logs** opens what `ps5-cores-unlock.sh` prints, and **Hide logs** closes it again. When an action fails, a
red **!** with **Check logs** appears beside the button; it goes away when you open the log.

Hover a field, its label or a pill to see what it does. The window remembers its size and position between runs.

**Installing it: `install.sh`** (from a clone or the extracted release tarball): a root-owned copy of the toolset in
`/opt/ps5-cores-bisect-v<version>` (with `/opt/ps5-cores-bisect` pointing at it), a private PyQt6 venv in
`~/.local/share/ps5-cores-bisect-app/venv`, the launcher `~/.local/bin/ps5-cores-bisect-gui`, an app menu entry
and a Desktop icon. It also removes the separate unlock window of earlier versions. Run it as your own user; only
the copy to `/opt` asks for the sudo password.

```bash
./install.sh                         # install or update
./install.sh --no-desktop-shortcut   # app menu entry only, no Desktop icon
ps5-cores-bisect-gui               # or launch it from the app menu
./install.sh --uninstall             # remove the app; keeps results, settings and logs (and the unlock itself)
./install.sh --uninstall --purge     # also remove results, settings, logs and the autostart unit
```

Your bisect results stay in `~/.local/share/ps5-cores-bisect`; the installer never touches that folder unless
you pass `--purge`.

Per-user alternative, no `/opt` and nothing root-owned:

```bash
bash packaging/bazzite/install-bisect-gui.sh     # venv + launcher + menu entry "PS5 CPU Tools"
bash packaging/bazzite/uninstall-bisect-gui.sh   # removes all of that again (keeps your results and the unlock)
```

**From a venv (development):**

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m cores_bisect   # --script PATH and --unlock-script PATH to use other scripts
```

A terminal emulator is required to actually see/run the bisect (konsole, gnome-terminal, ptyxis, xfce4-terminal,
foot, alacritty, kitty, x-terminal-emulator or xterm - `$TERMINAL` is tried first); the window shows an error if
none is found.

## Known side effect

After the unlock, `pp_dpm_sclk` and `hwmon` `freq1_input` report nonsense GPU clocks (tens of MHz).
This is cosmetic — the SMU's own clock getters stay correct — and this script ignores GPU clocks.
Diagnostics that read those files (e.g. tests 19/40 of
[Board Test](board.md)) will
flag it; that's expected while the unlock is active. The GPU governor's `fix-freq` option puts the real clock back.

## Credits

The SMU quirk (queue-3 message `0x98` → `0xFF` at SMN `0x5A870`) was discovered and documented by
[rw-r-r-0644/ps5-core-unlock](https://github.com/rw-r-r-0644/ps5-core-unlock) (MIT). This project
is an independent implementation built around those hardware facts, adding the control/bisect/verdict
methodology, crash-safe multi-boot state, and reversible persistence.

## License

GNU GPLv3, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/cores/LICENSE).
