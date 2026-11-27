<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 CU Unlock](../assets/compute/ps5-cu-bisect.webp){ .app-logo }

# PS5 CU Unlock

!!! warning "Changes the board"
    For the CU unlock, the app writes the GPU's shader array and WGP mask registers with umr. It does so as root, while
    the driver runs. The registers are volatile. Any reboot puts the stock 24 CUs back, and nothing is burned into the
    chip. The unlock stays across reboots and power offs only through the root service that CU Unlock installs. That
    service is ps5-cu-unlock.service, with the masks in /etc/ps5-cu-bisect. It writes the registers again early at
    every boot. Nothing is written to the BIOS, the firmware, the CMOS or the kernel's arguments. Uninstall in CU Unlock
    disables the service and removes its files. The unlock then lasts until the next reboot, and after it the board is
    stock. CU Unlock runs every attempt of a test in one boot by default, and writes the board's own masks back between
    attempts. With Same boot off, it asks once and then restarts the board by itself after each attempt. While such a
    test runs, an autostart entry opens the window again after each login. The entry goes when the test ends, is paused
    or is removed with the app.

PS5 CU Unlock tells **bad CUs** apart from an **unstable CU unlock** on the AMD PS5 (Cyan Skillfish, gfx1013).
A CU is a compute unit of the GPU. CUs come in pairs, and a pair is a WGP.

Every PS5 die differs. AMD fuses off WGPs that failed validation. But a crash after a CU unlock doesn't have to
mean a bad WGP. A runtime unlock writes GPU registers while the driver is running. The kernel and RADV keep their
24-CU view. Extra CUs draw more power at the same voltage. Crashes that move from one CU pair to another usually
point to the CU unlock, power or heat, not to bad silicon.

`ps5-cu-bisect.sh` does its own unlock, so no other tool is involved. It tests in a way that separates these
causes.

> **Warning:** this writes GPU registers. A bad WGP or the CU unlock itself can freeze the system. Save your
> work first. Use at your own risk.

<a id="cu-levels"></a>

!!! warning "24, 32 or 40 CUs, and the counts in between"
    **The 24 CUs differ per board.** Every board runs 24 CUs out of the box, but not the same 24 on every board. In
    each of the 4 shader arrays, the chip has 2 of its 5 WGPs switched off. Which 2 they are differs per chip. So the
    stock masks differ per board too. For example, one board runs `0x07,0x07,0x07,0x0b`, because on its last row WGP2
    is off and WGP3 is on.

    Never copy another board's masks, and don't take `0x07,0x07,0x07,0x07` for granted. The window and
    `ps5-cu-bisect.sh` without `--baseline` read your board's own masks. The script refuses a baseline that
    switches off a WGP your chip runs.

    **24, 32 and 40 CUs are the even levels.** They unlock the same number of WGPs on every row.

    | WGPs per row | Example mask          | Total CUs              | What you get                       |
    |--------------|-----------------------|------------------------|------------------------------------|
    | 3            | `0x07,0x07,0x07,0x07` | **24** (stock/default) | What the board does out of the box |
    | 4            | `0x0f,0x0f,0x0f,0x0f` | **32**                 | +1 good WGP on each of the 4 rows  |
    | 5            | `0x1f,0x1f,0x1f,0x1f` | **40** (max)           | +2 good WGPs on each of the 4 rows |

    The per-row mask doesn't have to be exactly `0x0f` or `0x1f`. If WGP3 is bad on a row but WGP4 is good, `0x17`
    is also 4 WGPs. For an even level, all 4 rows unlock the *same count*. On a row where the chip switched off
    WGP2, stock is `0x0b`.

    **The counts in between.** When some rows have more healthy WGPs than others, a board can run 28 or 36 CUs, or
    32 with uneven rows. The GPU has two halves, the shader engines SE0 and SE1, with two rows each. The two halves
    run in step. Inside a half, the two rows add up. So a mask runs like 4 CUs for each WGP in its smaller half.

    For example, one bad WGP leaves 5, 5, 4 and 5 WGPs on the rows. That is 10 WGPs in SE0 and 9 in SE1. All 38 CUs
    then run like 36. A mask of 4, 5, 4 and 5 WGPs is 36 CUs, runs like 36 and uses less power.

    This was measured on one board on 27-11-2026 with the `vkpeak` benchmark. The masks were written live, and the
    registers were read back before each run. A game can gain less than this compute score.

    | CUs | WGPs per row | WGPs in SE0 / SE1 | Score (fp32-scalar) | Against 24 CUs |
    |-----|--------------|-------------------|---------------------|----------------|
    | 24  | 3·3·3·3      | 6 / 6             | 5664                | stock          |
    | 26  | 4·3·3·3      | 7 / 6             | 5668                | no gain        |
    | 28  | 4·4·3·3      | 8 / 6             | 5669                | no gain        |
    | 28  | 3·3·4·4      | 6 / 8             | 5670                | no gain        |
    | 28  | 4·3·4·3      | 7 / 7             | 6606                | **+17%**       |
    | 28  | 3·4·3·4      | 7 / 7             | 6607                | **+17%**       |
    | 28  | 4·3·3·4      | 7 / 7             | 6607                | **+17%**       |
    | 30  | 4·4·4·3      | 8 / 7             | 6610                | **+17%**       |
    | 32  | 4·4·4·4      | 8 / 8             | 7547                | **+33%**       |

    CU Unlock offers every count above your highest even level in step 4, each with the rows that give it the most
    speed. A count that runs slower than its number says what it runs like. `ps5-cu-unlock.sh` and the window accept
    every mask with 3, 4 or 5 WGPs on every row. For a mask that runs slower than its count, such as
    `0x1f,0x1f,0x07,0x07` (5/5/3/3), they say what it runs like. They refuse a mask with fewer than 3 WGPs on a row.

## Unlocking extra CUs, step by step

New here? This is the whole process, start to finish. If you only read one section, read this one.

**What you're doing.** Your board ships with **24 CUs** active. Up to 16 more are switched off. AMD fused some of
them off because they are defective. Others are fine. These scripts find out which are good, and then switch on
the good ones at every boot.

**The outcomes.** The GPU has 4 identical rows, called shader arrays, in two halves. The even levels are 24, 32 and
40 CUs. With uneven rows, a board can also reach 28 or 36 CUs. [The box above](#cu-levels) explains them, with the
masks and the measured scores.

------------------------|-----------------------|-----------------------------------|
| **24 CUs** (default)   | `0x07,0x07,0x07,0x07` | What the board does out of the box |
| **32 CUs**             | `0x0f,0x0f,0x0f,0x0f` | +1 good WGP on each of the 4 rows |
| **40 CUs** (max)       | `0x1f,0x1f,0x1f,0x1f` | +2 good WGPs on each of the 4 rows |

The masks in this table are examples. Which WGPs a chip has switched off differs per board. One board runs
`0x07,0x07,0x07,0x0b`, because on its last row WGP2 is off and WGP3 is on. The scripts and the window read your
board's own masks when they start.

The tools **reject** anything in between. One example is 5 extra CUs on one row and none on another. It would
boot and run, but no faster than 24 CUs. It would also use more power and make more heat. So you're aiming for
32, and trying for 40.

---

**Step 1 — Install the prerequisites and read the warning.**
See [Requirements](#requirements) and [Before you start](#before-you-start). You need `umr`, and ideally
`memtest_vulkan`. Close your games and save your work. This *will* freeze the machine at some point, by design.

**Step 2 — Find out which switched-off CUs are good (`ps5-cu-bisect.sh`).**

```bash
chmod +x ps5-cu-bisect.sh
./ps5-cu-bisect.sh
```

It tests **one** switched-off WGP (2 CUs) at a time, under real GPU load. Then it asks you to restart and run it
again for the next one. There are 8 switched-off WGPs and 3 test rounds each, so about **27 boots** in total.
Expect this to take a day or two of on-and-off work. With `--auto`, it restarts by itself without asking, see
[Running truly unattended](#running-truly-unattended---auto-checklist). Each WGP ends up with one of the three
verdicts in [Results](#results):

- GOOD
- FAILS EVERY TIME, which is bad silicon, so leave it off
- RANDOM

**Step 3 — Read the suggestion at the end.**
When every WGP has a verdict, the script prints the best **even** mask your board supports. For example:

```
- WGPs that passed every round: SE0.SH0.WGP3 SE0.SH1.WGP3 SE1.SH0.WGP3 SE1.SH1.WGP3
  Combined: 0x0f,0x0f,0x0f,0x0f (32 CUs, WGPs per row: 4 4 4 4).
```

If one row had a bad WGP, the script also names the even version, with the other rows trimmed down to match. Its
commands use that even mask. The uneven mask is tested and installed the same way.

**Step 4 — Retest that exact combination (this step is not optional).**
WGPs that each pass alone can still fail *together*. More active CUs draw more power at the same voltage. So run
the suggested command, which tests the full combined mask in one go:

```bash
./ps5-cu-bisect.sh --reset && ./ps5-cu-bisect.sh --baseline 0x0f,0x0f,0x0f,0x0f --control-only --rounds 1
```

Replace the mask with the one *your* run suggested. This is a single boot, not another 27.

**Step 5 — Make it permanent (`ps5-cu-unlock.sh`).**
A CU unlock is only ever register writes. Nothing is burned into the chip, so it's gone after a restart. This
second script applies it again at every boot. It does that as a system service that runs before your desktop
starts:

```bash
chmod +x ps5-cu-unlock.sh
sudo ./ps5-cu-unlock.sh --install 0x0f,0x0f,0x0f,0x0f
```

That's it. From now on the board comes up with 32 or 40 CUs on every boot. That includes cold boots and boots
after system updates. The script refuses to install a mask with fewer than 3 WGPs on a row.

**Step 6 — Verify it's actually live.**

```bash
sudo ./ps5-cu-unlock.sh --status     # "Live masks now:" is read straight off the GPU
```

Trust that line over any CU count that other GPU tools show. Most of them cache the number the driver saw at
boot, as [the note further down](#keeping-the-unlock-after-a-reboot) explains.

**Step 7 — Want to go back?**

```bash
sudo ./ps5-cu-unlock.sh --uninstall  # stock 24 CUs again from the next boot
```

Do this if the system starts misbehaving later. A WGP that passed the tests can still turn out unstable under a
different game or in a hotter room.

> **Prefer clicking to typing?** [The window](#the-window) runs these steps for you, one after the other. It scans
> the board, tests the unlock method and each WGP, and restarts the board in between. Then you choose how many
> CUs to turn on, and it runs the combined test and installs the unlock. **Install** stays off until the combined test passed.

## How it works

The script writes the three registers of a runtime CU unlock with [umr](https://gitlab.freedesktop.org/tomstdenis/umr):

| Register                         | Per shader array | Meaning                                    |
|----------------------------------|------------------|--------------------------------------------|
| `CC_GC_SHADER_ARRAY_CONFIG`      | yes              | Bits 16-20 mark WGPs inactive, cleared to 0 |
| `SPI_PG_ENABLE_STATIC_WGP_MASK`  | yes              | WGPs that get work, 5 bits of 2 CUs each   |
| `RLC_PG_ALWAYS_ON_WGP_MASK`      | no               | Union of the four SPI masks                |

The board has 4 shader arrays of 5 WGPs each, which is 40 CUs. The arrays are SE0.SH0, SE0.SH1, SE1.SH0 and
SE1.SH1. Stock is 24 CUs.

```
             WGP0   WGP1   WGP2   WGP3   WGP4      mask (bit4..bit0)
             bit0   bit1   bit2   bit3   bit4
SE0.SH0       ██     ██     ██     ..     ..      0x07
SE0.SH1       ██     ██     ██     ..     ..      0x07
SE1.SH0       ██     ██     ██     ..     ..      0x07
SE1.SH1       ██     ██     ██     ..     ..      0x07

██ baseline, always unlocked (the stock 24 CUs)   .. locked WGP, 2 CUs, not yet tested
```

Each row is a 5-bit `SPI_PG_ENABLE_STATIC_WGP_MASK` value. WGP0 is bit 0 and WGP4 is bit 4. A set bit means that
WGP is unlocked (2 CUs). Read the stock row above from right to left, WGP4 first, to get `00111`, which is `0x07`.
In it, WGP0-2 are unlocked and WGP3-4 are locked. A row with all 5 WGPs unlocked is `11111`, which is `0x1f`.

The 4 rows are always written together as `SE0.SH0,SE0.SH1,SE1.SH0,SE1.SH1`. So the baseline in the map above is
`0x07,0x07,0x07,0x07` (24 CUs). A fully unlocked board would be `0x1f,0x1f,0x1f,0x1f` (40 CUs). This is exactly
the format that `--baseline` takes, and that `--status` and the window print back.

That's a common layout, but not the only one. 3 of the 5 WGPs per shader array ship unlocked, which is 24 CUs. Which 3
they are differs per board. The other 2 per array are fused off at the factory. Those 8 WGPs (16 CUs) are what this
script tests one by one. The script shows this same map live while it runs. `>>` marks the WGP under test. Once a WGP
has a verdict, it shows `ok` for GOOD, `xx` for FAILS EVERY TIME or `??` for RANDOM. See [Results](#results).

**24, 32 and 40 CUs are the even levels.** The box [24, 32 or 40 CUs, and the counts in between](#cu-levels) at the
top of this chapter explains them and the counts in between.

The test plan:

- **Control.** The same register writes with your baseline masks, so no extra CUs. If the control fails, the
  unlock method, power or heat is at fault. The WGP verdicts then can't blame your CUs.
- **One step per locked WGP.** The baseline plus that single WGP (2 CUs). The script tests every locked WGP on
  its own.
- **Rounds.** Every item runs several times, 3 by default. The rounds are interleaved, so heat and time don't
  favor one item.
- **One attempt per boot.** This is the default. Every attempt starts from the clean driver state.
- **Idle writes.** The script only writes the masks while the GPU is idle, then reads them back. During the load
  it reads them again every 10 s to catch masks that drift.
- **Correctness, not only crashes.** `memtest_vulkan` reports wrong results. The script uses vkpeak, vkmark or
  glmark2 when it's missing, but those only show crashes.
- **Crash-safe.** Before every phase the script saves what it's doing. After a freeze, cold boot and run it
  again. It then records the crash and its phase, either writing the masks or under load. It also records the
  GPU faults in the kernel log of the previous boot.

## Requirements

- AMD PS5, Linux with bash 4+. Tested against Bazzite (Fedora Atomic).
- `umr`, owned by root, in `/usr/bin`, `/usr/sbin` or `/usr/local/bin`.
  On Bazzite, run `sudo rpm-ostree install umr`, then restart. "Already requested" means it's waiting for that
  restart. [Quickfix](quickfix.md#quickfix) installs it too, with the RPM packages.
- A GPU load tool, preferably [memtest_vulkan](https://github.com/GpuZelenograd/memtest_vulkan/releases)
  in `~/.local/bin`. vkpeak, vkmark and glmark2 work too.
- sudo rights, only for umr and the kernel log.

## Before you start

1. Every boot must start at the stock state. Turn off anything that applies a CU unlock at boot, and don't run
   other CU tools during the test. The script refuses to start when a CU unlock is already active.
2. Cap the GPU governor at 1500 MHz, for example in `/etc/cyan-skillfish-governor-smu/config.toml`. Then power
   and heat don't hide the result. The script warns when the ceiling is higher.
3. Close games and video players.
4. Start without `--baseline`, so the script takes your board's own masks. A baseline must keep every WGP your chip
   runs. The script refuses one that switches off such a WGP, and names it.

## Usage

Run it as your normal user:

```bash
chmod +x ps5-cu-bisect.sh
./ps5-cu-bisect.sh                 # baseline = the stock masks of this boot, 3 rounds, 180 s load
./ps5-cu-bisect.sh -t 300 -r 5     # longer load, more rounds
./ps5-cu-bisect.sh --baseline 0x07,0x07,0x07,0x0b   # masks you trust, with every WGP your chip runs
./ps5-cu-bisect.sh --baseline 0x0f,0x0f,0x0f,0x0f --control-only --rounds 1   # re-validate a combined mask, control only
./ps5-cu-bisect.sh --scan          # live masks and what a run needs, writes no register
./ps5-cu-bisect.sh --only control  # only the control's rounds, as the window's safety check does
./ps5-cu-bisect.sh --reset && ./ps5-cu-bisect.sh --control-only --rounds 1 --writes spi,rlc   # SPI and RLC only
./ps5-cu-bisect.sh --status        # results so far, report on the Desktop
./ps5-cu-bisect.sh --same-boot     # no reboots: restore the baseline live between attempts
./ps5-cu-bisect.sh --auto          # no prompts, auto-reboot after each attempt (see below)
./ps5-cu-bisect.sh --reset         # delete the results and start over
./ps5-cu-bisect.sh --help
```

After each attempt it offers to power off or restart. Powering off is best, because it gives a cold boot. Power
on and run it again until all attempts are done. With 3 rounds and 8 locked WGPs that's 27 boots. `--same-boot`
is faster, but every attempt then inherits the state of the previous one.

### How long a full run takes

Total attempts = rounds × (1 + locked WGPs). The 1 is the control. Each attempt takes about 15 s to settle, then
the load time, then a few seconds of overhead. The load time is `--time`, 180 s by default. That is roughly
`load time + 20 s` of active GPU time per attempt. On top of that:

| Test type                                   | Per-attempt overhead                         | Example: 3 rounds, 8 locked WGPs (27 attempts), default 180 s load |
|----------------------------------------------|-----------------------------------------------|---------------------------------------------------------------------|
| Default, a restart or power off between attempts | a full boot, and your own clicks          | 27 × ~200 s plus 27 boots, typically 2 to 3 hours with the restarts |
| `--same-boot`                                 | 30 s cooldown, no restart                     | 27 × ~230 s ≈ 1 h 45 min hands-off                                   |
| `--auto` with the systemd unit, see below     | a full boot, but no manual steps              | same wall-clock as the default mode, but unattended                 |
| `--control-only`                              | only the control item is tested               | `rounds` attempts instead of `rounds × (1 + WGPs)`, for example 3 instead of 27 |

More rounds (`-r`) or a longer load (`-t`) scale the total time linearly. Each extra locked WGP adds one more
item, which is `rounds` more attempts.

### Running truly unattended (`--auto` checklist)

Clicking through 27 restarts by hand is slow. `--auto` keeps one attempt per boot, so nothing is lost in
correctness. It removes the manual steps:

- It doesn't ask anything. It takes an unfinished attempt for a crash, and it goes on past warnings.
- It restarts on its own when more attempts are left, and doesn't ask.

Combine it with the included systemd user unit. The script then also starts again after every login. That turns
the whole bisect run into a loop you only have to start once:

```bash
mkdir -p ~/.config/systemd/user
cp ps5-cu-bisect-auto.service.example ~/.config/systemd/user/ps5-cu-bisect-auto.service
# edit ExecStart in that file to the real path of ps5-cu-bisect.sh
systemctl --user enable --now ps5-cu-bisect-auto.service
systemctl --user status ps5-cu-bisect-auto.service 
```

`--auto` makes the *script* hands-off, but the *system* must get back to your session on its own:

* **Autologin.** After each restart someone must log in, or the run stalls at the login screen. Turn autologin
  on in your desktop. On Bazzite with KDE, go to System Settings → Colors & Themes → Login Screen (SDDM) →
  Behavior → auto-login. On GNOME, go to Users → auto-login.
* **sudo without a password.** The script still needs sudo for `umr` and the kernel log. There's no terminal to
  type a password into. Add a drop-in file for sudo:

```bash
echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/ps5-cu-bisect
sudo chmod 440 /etc/sudoers.d/ps5-cu-bisect
sudo visudo -cf /etc/sudoers.d/ps5-cu-bisect   # must print "parsed OK"
sudo -k && sudo -n true && echo OK    # must print OK without asking
```
Revert after testing with `sudo rm /etc/sudoers.d/ps5-cu-bisect`.
If you edit the file by hand, use `sudo visudo -f /etc/sudoers.d/ps5-cu-bisect`. It refuses to save a broken
line. A broken line makes every `sudo` command print a warning, or stops sudo working at all.

The script first tries `systemctl reboot` with `--no-ask-password`. With that option it fails where it would
otherwise open a password dialog that nobody is there to answer. Then it falls back to `sudo -n systemctl reboot`.
If both fail, the script stops, so it doesn't hang, and tells you to restart by hand. Most desktops let the
logged-in user restart and power off directly. If yours doesn't, add passwordless sudo for `systemctl reboot`
and `poweroff` too.

For a truly unattended run, for example overnight, make sure of this as well:

* **The autostart unit installed.** Without it nothing starts the script again after login. You'd have to start
  it by hand at every boot.
* **No credential popups at login (KDE Wallet / ksshaskpass).** With autologin the KDE Wallet can't unlock by
  itself. So an "SSH credentials" or wallet dialog can appear at session start. It blocks the chain until you
  answer it. Either give the wallet a blank password, or turn the wallet subsystem off. For a blank password,
  open the wallet in `kwalletmanager5` first, then choose Change Password and leave it empty. Plasma 6 has no
  checkbox for the wallet subsystem anymore, so turn it off with this command:

```bash
kwriteconfig6 --file kwalletrc --group Wallet --key Enabled false   # kwriteconfig5 on Plasma 5
```

Turn it on again afterward with `... --key Enabled true`. Also uncheck "Use KWallet for the Secret Service
interface" in System Settings → KDE Wallet. Then apps don't send secrets to the wallet that is off.

Check on it while it runs:

```bash
systemctl --user status ps5-cu-bisect-auto.service   # ran / running / failed this boot
tail -f ~/.local/share/ps5-cu-bisect/auto.log         # live output of the current attempt
./ps5-cu-bisect.sh --status                           # progress and results so far
```

When all attempts are done, the script stops restarting on its own. In `--auto` mode it also turns
`ps5-cu-bisect-auto.service` off by itself. It removes the optional live-output autostart entry below too. So
nothing starts at the next login.

Starting a new `--auto` run turns the unit on again if it's still installed but was left off. If the unit isn't
installed at all, the script warns. The run then can't continue past a restart. If you ran without `--auto`,
turn the unit off by hand with `systemctl --user disable --now ps5-cu-bisect-auto.service`.

A real freeze still needs a power cycle by hand, the same as without `--auto`. The script resumes from there as
usual.

Want the live output on screen and not in a log file? Add a desktop autostart entry that opens a terminal
following it at every login. This is a KDE example. The comments in `ps5-cu-bisect-auto.service.example` say
more:

```bash
cat > ~/.config/autostart/ps5-cu-bisect-watch.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=PS5 bisect live output
Exec=konsole --title "ps5-cu-bisect" -e tail -n 40 -f .local/share/ps5-cu-bisect/auto.log
EOF
```

## Results

While it runs, and in the summary and the report, the same CU map shows where it's at:

```
             WGP0   WGP1   WGP2   WGP3   WGP4
SE0.SH0       ██     ██     ██     ok     ..
SE0.SH1       ██     ██     ██     xx     ..
SE1.SH0       ██     ██     ██     ..     ??
SE1.SH1       ██     ██     ██     >>     ..

██ baseline  >> testing now  ok passed every round  xx fails every time  ?? random  .. not tested yet
```

Outcomes per attempt:

| Outcome       | Meaning                                                                |
|---------------|------------------------------------------------------------------------|
| `PASS`        | Load ran the full time, no errors, no kernel faults, masks held        |
| `ERRORS`      | memtest_vulkan reported wrong results                                  |
| `FAULT`       | GPU fault in the kernel log, such as a ring timeout, GPU reset or page fault |
| `LOAD-FAIL`   | The load tool stopped early                                            |
| `CRASH-LOAD`  | The system went down under load                                       |
| `CRASH-APPLY` | The system went down while writing the masks on an idle GPU           |
| `DRIFT`       | The masks changed after they were written                              |
| `MISMATCH`    | The masks didn't read back as written                                  |
| `ABORTED`     | Stopped by hand, so the attempt runs again                             |

Verdict per WGP:

- **GOOD.** It passed every round.
- **FAILS EVERY TIME.** Likely a bad WGP, so leave it locked. It says "(memory errors)" when memtest_vulkan
  found errors.
- **RANDOM.** It failed in some rounds only. A bad WGP normally fails every time, so this points to the unlock
  method, power or heat.

`CRASH-APPLY`, `DRIFT` and `MISMATCH` point to the CU unlock itself. When the control fails, the WGP verdicts are
not reliable.

> **Note: how the script measures GPU load.** The script reads the kernel's `gpu_busy_percent` file first. On
> the board the kernel can't fill that file. The script then adds up how long the GPU worked for each program.
> The kernel lists that time per program in `/proc/<pid>/fdinfo`. Board Test measures the load the same way.
> `GPU load only reached X%` means the load tool kept the GPU busy less than half the time.

When everything is done and the control passed, the script suggests a combined mask of the good WGPs. WGPs that
pass one by one can still fail together, because they draw more power at the same voltage. So test the
combination:

```bash
./ps5-cu-bisect.sh --reset && ./ps5-cu-bisect.sh --baseline <masks> --control-only --rounds 1
```

With `--control-only`, the script doesn't bisect the WGPs that are still locked in `<masks>` again. One example
is a WGP you already know is bad and left out on purpose. Only the `control` item runs, so this is a single-boot
check and not another full bisect run.

The summary's commands use the even mask, at 24, 32 or 40 CUs. If one row has a bad WGP, the script trims the
other rows down to match. An uneven mask is tested and installed the same way. Once the
combination also passes, make it survive a restart with
[ps5-cu-unlock.sh](#keeping-the-unlock-after-a-reboot).

Files, in `~/.local/share/ps5-cu-bisect/`:

- `umr-runs.tsv`: one line per attempt, with the columns listed below
- `umr-config`: baseline, rounds and load time
- `logs/`: the load tool's output per attempt

The columns of `umr-runs.tsv`:

- time
- boot
- round
- item
- masks
- outcome
- memtest errors
- kernel faults
- drift
- max temperature
- max clock
- max GPU busy
- note

The script writes a readable report to the Desktop when all attempts are done, and with `--status`.

## Keeping the unlock after a reboot

A runtime unlock resets to stock at every boot. It only ever writes registers, and nothing is fused. So by
default you're back to 24 CUs the next time you start the system.

`ps5-cu-unlock.sh` is a separate, standalone script. At every boot it applies a mask again that you've already
validated. It does that as a root systemd service that starts before the display manager. It does not retest
anything, and it's not a diagnostic. Only use it once a mask has passed the bisect run above.

`--install` writes nothing to the GPU. The masks turn on at the next restart. Writing them while the desktop runs can
freeze the board.

```bash
chmod +x ps5-cu-unlock.sh
sudo ./ps5-cu-unlock.sh --install 0x0f,0x0f,0x0f,0x0f   # save, enable at every boot, on after a restart
./ps5-cu-unlock.sh --status                             # installed masks, service state, live masks
sudo ./ps5-cu-unlock.sh --uninstall                     # disable it; stock 24 CUs from the next boot
```

`--status` shows the live masks only when you run it with sudo, or when sudo needs no password.

**Every row needs 3, 4 or 5 WGPs.** `--install` checks the mask before it touches a single register. So does a
bare apply. They refuse a mask with fewer than 3 WGPs on a row. For a mask that runs slower than its count, they
print a note and go on:

```
$ sudo ./ps5-cu-unlock.sh --install 0x1f,0x1f,0x0f,0x1f
Mask 0x1f,0x1f,0x0f,0x1f - 5/5/4/5 WGPs on SE0.SH0/SE0.SH1/SE1.SH0/SE1.SH1.
SE0 has 10 WGPs and SE1 has 9. The two run in step, so the mask runs as fast as
36 CUs while it draws the power of 38 CUs.
Installed and enabled. 0x1f,0x1f,0x0f,0x1f is applied at every boot. Restart the board to turn it on.
```

**Once `--install` has run, the CU unlock is persistent.** The systemd service applies the saved mask again on
every single boot from then on. You don't need to do anything more, and you don't need to run the script again.
It survives restarts, power-offs, cold boots, and kernel and OS updates alike. Only `--uninstall` turns that off
again, or deleting the service and its config by hand.

Only install a mask that:

- passed with the control, so no crashes with just the baseline masks
- came back GOOD for every WGP in it, on its own, in `ps5-cu-bisect.sh`
- was then also tested as the combined mask itself, because WGPs that pass alone can still fail together
- has 3, 4 or 5 WGPs on each of the 4 shader arrays, which the script enforces

> **Worked example: what an uneven mask gives.** Say your bisect run found one bad WGP, `SE1.SH0.WGP4`, and
> everything else good. The "everything that passed" combination would be `0x1f,0x1f,0x0f,0x1f`. That is 38 CUs,
> with `5/5/4/5` WGPs per row. SE0 then has 10 WGPs and SE1 has 9.
>
> The two halves run in step, so the tenth WGP in SE0 has no partner. `38` CUs (`5/5/4/5`) performs the same as
> `36` CUs (`4/5/4/5`). The extra WGP only adds power and heat.
>
> So the window offers `4/5/4/5`, which is `0x0f,0x1f,0x0f,0x1f`, as **36 CUs**. It offers **38 CUs** too, marked
> **Like 36 CUs**. From the terminal, retest the mask you choose as a whole first:
> ```
> ./ps5-cu-bisect.sh --reset && ./ps5-cu-bisect.sh --baseline 0x0f,0x1f,0x0f,0x1f --control-only --rounds 1
> ```
> When that retest passes, the window shows **Accepted**. You get 36 usable CUs over the stock 24.

Config and the systemd unit:

- `/etc/ps5-cu-bisect/masks`: the installed masks, one line
- `/etc/systemd/system/ps5-cu-unlock.service`: the service, with `Before=display-manager.service`

With `Before=display-manager.service`, the service applies the CU unlock before anything starts using the GPU.

A real hang is still a real hang. A WGP you thought was GOOD can turn out unstable under different conditions
later. Then boot, run `sudo ./ps5-cu-unlock.sh --uninstall`, and restart to go back to stock.

> **If the CU unlock doesn't survive a restart: `--install` now fails loudly instead of lying.**
>
> `systemctl enable` can fail. Causes include SELinux and a read-only `/etc/systemd/system` on some images.
> Earlier versions printed "Installed and enabled" regardless. You'd only find out after the next restart that the
> unlock never turned on.
>
> `--install` now checks the actual result. It exits with an error and doesn't claim success. The error names
> `systemctl status ps5-cu-unlock.service` and `journalctl -u ps5-cu-unlock.service` to check. If you're on
> an older copy of the script, update it and run `--install` again to see the real reason for the failure.
>
> **How to be 100% certain of the live CU count.** More than one thing can report a CU count, and they are
> not all equally trustworthy:
>
> - `sudo ./ps5-cu-unlock.sh --status` → **"Live masks now"** reads the actual GPU registers right now. This
>   is the ground truth for the current boot.
> - Test #21 of [Board Test](board.md) reads the exact same registers, read-only. It agrees with the line above by
>   construction.
> - `--status` → **"Configured masks"** is just what's saved in `/etc/ps5-cu-bisect/masks`. This is what you
>   *asked* to install, not proof that it's active. If `--install` failed without saying so, as described above,
>   this can show 32 CUs while the live registers are back to 24.
> - Third-party GPU info and monitoring apps, such as `rocm-smi` and Vulkan/OpenCL CU counts. These typically
>   read the CU count that the `amdgpu` driver cached once, when it probed the GPU at boot or driver load. They
>   don't read the registers again. Say you unlock registers at runtime, or a persistence service runs after
>   the driver already probed. Then these can keep showing a stale number until the driver probes again, which
>   takes another restart. That goes in either direction.
>
> When in doubt, trust `--status`'s "Live masks now" or test #21 over anything else. They are the only ones that
> read the hardware directly, at the moment you ask.

### The window
![ps5-cu-bisect-gui.webp](../assets/compute/ps5-cu-bisect-gui.webp)

The window runs the CU test for you, step by step. You see which CUs are on, what is tested now and what comes next.
It runs `ps5-cu-bisect.sh` and `ps5-cu-unlock.sh` itself, inside the window. No terminal opens.

Four boxes under the title show where you are:

- **Active now** shows the CUs the GPU runs, from the last scan or from the boot service at this boot.
- **Boot unlock** shows the CUs the boot service applies, or **Stock**.
- **Attempts done** shows how far the test is.
- **Test** says whether the test is running, paused, stopped or done.

The info symbol says what the app does. The round symbol at the right end of the title row reads the results and
the boot unlock again.

Under the boxes are the four steps, one row each. Each row says **Done**, **Do this now**, **Running**, **Stopped** or
**Later**. A row that is done says what came out of it, for example "Passed 3 of 3 rounds."

The row of the step you're on says the one thing to do now, for example "Click **Start test**. A question opens.
Answer **Yes**." The pill it names sits on that row, with an accent border all round. The other pills sit at the
bottom left. While the test runs, the row says that there is nothing to do.

Click a row that is done to look at that step again. **Choose and install** is always open, so you can always remove
the boot unlock. A click on a row only shows the step. It doesn't start anything.

When everything is done, a green bar over the steps says so. An example is "Finished. Your board runs 32 CUs at every
boot. There is nothing left to do." The bar also shows when you chose to stay at the stock CUs.

While a script runs, an orange turning symbol beside the pills says what runs and for how long, for example "Running:
round 1, control · 64 s". It shows for the scan, the test, **Start over**, **Report**, **Install** and **Uninstall**.
While the window follows a test, it moves to the step that runs, attempt by attempt.

The window opens 900 pixels wide, as wide as the map needs. It never opens higher than your screen. When the page is
higher than the window, the page scrolls. An example is with **Details** open. The **Details** and **Advanced** pills
are at the right end of the bottom row. Under the name they say **Show** or **Hide**.

The map shows the four shader-array rows, SE0.SH0 to SE1.SH1, with five WGPs each. Each cell shows its state in
words and in color:

- green, **On**: a WGP the GPU runs now
- gray, **Not tested**: a locked WGP without a result yet
- yellow, **Testing**: the WGP under test now
- blue, **Healthy**: it passed every round
- red, **Fails**: it failed every round
- orange, **Random**: it failed in some rounds only

At the right end of each row, the **Mask** column shows that row's mask. A mask is the hex value of the green WGPs,
such as `0x0b`. Under it are the same bits, for example `01011`, read from WGP4 on the left to WGP0 on the right. So
`0x07,0x07,0x07,0x0b` is the four values in the column, top to bottom. Step 1 also names your masks in one line.

**Step 1, Scan.** **Scan** reads the live masks with `--scan` and writes no register. You're asked for your
password, because umr needs root. The window then says how many CUs are on and how many WGPs are locked. It also says
how many attempts the test takes, and about how long. Two things block the test:

- A CU unlock is active from the boot. Remove it with **Uninstall** in step 4, then restart.
- No GPU load tool is found. Put `memtest_vulkan` in `~/.local/bin`.

A GPU ceiling above 1500 MHz only gives a warning. **Start test** asks once, then starts the safety check.
**Help** shows the script's own help as a page.

**Step 2, Safety check.** The safety check is the control. It writes your stock masks the way the unlock does, and
adds no CUs. Its rounds run first, with `--only control`. When a round fails, the window stops here. The unlock
method then breaks on this board, and testing single WGPs means nothing. The window names the round's outcome and
offers these pills:

- **Stay at 24** ends the test. Nothing is installed.
- **Restart** puts back the stock masks. It shows when the failed round ran in this boot.
- **Start over** deletes the results after a question, so you can test again.
- **Details** shows the script's results and the kernel's lines.

**Step 3, Test each WGP.** Each locked WGP is tested on its own, for as many rounds as **Rounds per item** says.
During an attempt, the line under the pills shows the round, the WGP, the load time, the temperature and the clock.
**Stop** stops the attempt as Ctrl+C does. The attempt then runs again later.

**Step 4, Choose and install.** When every attempt is done, the window shows the levels your healthy WGPs allow:

- **24 CUs** keeps the stock board. Nothing is installed.
- **32 CUs** needs 4 healthy WGPs on every row.
- **40 CUs** needs all 5 WGPs healthy on every row.

A level that the healthy WGPs don't reach is off and says **Not healthy**. Under the pills, a second row offers
every count above your highest even level, for example **34 CUs**, **36 CUs** and **38 CUs**. Each gets the rows that
give it the most speed. A count that runs as fast as its number shows its WGPs, such as **4·5·4·5 WGPs**. A slower
one says what it runs like, such as **Like 36 CUs**. You test and install such a count the same way as a level. The link **What the counts in between give** leads to
[24, 32 or 40 CUs, and the counts in between](#cu-levels). When you choose
a count, the window first keeps a copy of the bisect results, in `bisect-runs.tsv` and `bisect-config`. Then it runs
the combined test of that mask for one round. That is `--reset`, then `--baseline <mask> --control-only --rounds 1`.

When the combined test fails, the higher levels say **Failed together**. You can then pick a lower level or count. When it
passes, **Install** saves the mask for every boot. It writes nothing to the GPU now. Writing the masks while the
desktop runs can freeze the board. Step 4 then says "Restart the board to turn on 32 CUs." **Restart** asks
first, then restarts the board. The boot service turns the unlock on before the desktop starts. After the restart,
the green bar says that you're finished.

**Uninstall** turns the boot unlock off, and the board is stock again from the next restart. Both ask for your
password in a masked prompt. The password goes to `sudo -S` only and is never stored.

**One boot or restarts.** By default, **Same boot** is on, and every attempt of the test runs in one boot. Between
attempts, the script writes your own masks back and lets the GPU cool down for 30 seconds. You type your password
once, and you can leave the board alone until the test is done. After the safety check passes, the WGP test starts
by itself. The price is that each attempt inherits the GPU's state from the attempt before.

Turn **Same boot** off under **Advanced** to give each attempt a fresh boot. This helps to test a WGP again that
failed or was random. **Start test** then asks once and says how many restarts the test needs. After an attempt, a
countdown of 15 seconds runs, with **Restart now** and **Pause**. While the test runs, an autostart entry opens the
window after each login. That entry is
`~/.config/autostart/ps5-cu-tools-resume.desktop`. The window then counts down 20 seconds, with **Go on now** and
**Pause**, and runs the next attempt. You're asked for your password after each restart, unless sudo needs none.

**Pause** removes the autostart entry, and **Go on** adds it again. The entry also goes by itself when the test is
done.

**No sleep during a test.** While a test runs, the board doesn't go to sleep. The window holds the standard sleep
block of `systemd-inhibit`, with the reason "A CU test is running". The desktop's power menu shows it, and refuses a
manual sleep too. The screen may still turn off or lock, and the test goes on. The block ends with each run of the
script, so nothing stays behind. The scan and the report don't block sleep.

**When the test ends.** You don't have to watch the window. When a test ends, a desktop notification appears and
stays until you click it:

- **CU test done** names the attempts, the WGPs that fail every time or at random, and the highest even level.
- **CU test stopped** says that the safety check failed, or why the script stopped.
- **Combined test passed** or **Combined test failed** gives the result of the level you chose.

No notification comes when you press **Stop** or **Pause** yourself. With **Same boot** off, the last attempt
restarts the board first, so the notification comes after the login. A frozen board can't send anything, so its
screen just stays as it was.

**After a freeze.** Turn the board off and on. After the login, the window opens by itself, or you open it. It asks
whether the board froze, crashed or restarted by itself. **Yes** records a crash of that attempt. **No** runs the
attempt again.

**The script's questions.** The script can warn before an attempt, for example about a high GPU clock. The window
then shows the warnings and asks once for the whole test. When the GPU stays busy, the window asks whether to write
the masks anyway.

The test always starts from your board's own masks, which the script reads when it starts. You can't pick or type
other masks in the window.

**Advanced** opens the test's options. They count from the next attempt:

- **Load per attempt** (`-t`)
- **Rounds per item** (`-r`)
- **Same boot** (`--same-boot`), on by default, with no restarts between attempts
- **No watch** (`--no-watch`)

**Details** opens what both scripts print. **Report** writes the results so far to a text file on your Desktop,
with `--status`. The window remembers its position and the advanced options.

Run it straight from a clone, on any distribution:

```bash
cd bazzite-console/apps/compute
python3 -m venv _python && _python/bin/pip install -r requirements.txt && _python/bin/python -m cu_bisect
```

On Bazzite, `install.sh` installs it for your user. You get:

- a private venv under `~/.local`
- a launcher
- an app-menu entry
- an icon
- a Desktop icon

It layers nothing with `rpm-ostree` and puts nothing outside your home directory. It also removes the separate
unlock window of earlier versions. Run it as your own user, not with sudo:

```bash
./install.sh                         # install or update
./install.sh --no-desktop-shortcut   # app-menu entry only, no Desktop icon
ps5-bisect-gui                     # or launch it from the app menu
./install.sh --uninstall             # removes the app and its autostart entry, not the results, settings or unlock
./install.sh --uninstall --purge     # also removes the results, settings, logs and autostart entries
```

`install.sh` runs `packaging/bazzite/install-bisect-gui.sh`, which also works on its own.

## Releases

Releases have the tag `ps5-compute-v<x.y.z>` in the suite repository. You find them on its
[releases](https://github.com/RobertoTorino/bazzite-console/releases) page as `ps5-compute-v<x.y.z>.tar.gz`, with
a `SHA256SUMS` file. The tarball holds the whole set of tools:

- `ps5-cu-bisect.sh`
- `ps5-cu-unlock.sh`
- the window
- `packaging/`
- images and docs

If you just want to run the scripts or the window, download and extract it on the board. You don't need to clone
the repository. The portal installs it for you too.

## Related

[ps5-cores-bisect](cores.md) is the sibling project. It uses the same strategy for the 2 fused-off CPU cores.
That is a control, a per-core bisect run, a verdict, then a reversible persistent 8C/16T unlock.

[Board Test](board.md) holds the diagnostics for the board on Bazzite. Its test number 21 reads the live CU
masks from the same registers, read-only.

## License

GNU GPLv3, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/compute/LICENSE). This
keeps the project free and open source, with any forks or redistributions of it. Anyone can use, study and
change it. A closed-source or proprietary fork isn't allowed. Derivatives must stay under the same license and
keep their source available too.
