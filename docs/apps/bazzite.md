<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Bazzite Test](../assets/bazzite/bazzite-test.webp){ .app-logo }

# Bazzite Test

Read-only diagnostics for a PlayStation 5 running Bazzite on the ps5-linux kernel: about fifty tests in eleven
groups, from the platform, the GPU and the sensors to the network, the disks, the logs and crash forensics. Each test
reports SUCCESS, INFO, NOTE, WARNING or ERROR lines, with a hint where something can be done.

## Install

Install it from the portal (the **Sustainable** tab), or from a checkout of the repository:

```bash
apps/bazzite/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/bazzite/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/bazzite/install.sh --uninstall             # remove it; --purge removes its settings too
```

The launcher is `~/.local/bin/bazzite-test`; the app runs on the suite's shared Python environment.

## What it checks

| Group | Tests |
| --- | --- |
| System | the platform (a PS5 on the ps5-linux kernel, Bazzite, the loader's bzImage on /boot/efi), services, failed units, uptime, resources, boot time, file integrity |
| Network | connectivity, DNS, internet access, open ports, NTP, SSH, Wi-Fi (the IW620 on moal), internet speed (opt-in) |
| Storage and memory | disks, NVMe, memory and swap, VRAM and GTT (the split in /boot/efi/vram.txt), CPU memory bandwidth, disk speed (opt-in) |
| System logs | kernel errors of this boot and the journal, with known harmless lines filtered out |
| GPU and graphics | amdgpu, the GPU clock (ps5-gpufreq: governor, temperature limit, steps 500-2230 MHz), Vulkan, CU count (36), video decode and encode, HDMI-CEC (ps5-cec), the display (the PS5 HDMI state) |
| CPU and firmware | IOMMU, mitigations, cores (8C/16T), CPU power (no cpufreq on the PS5; ps5-linux-tools' boost) |
| Stability and thermals | sensors (ps5_fan: SoC, board, fan duty and curve; CPU; GPU), handheld daemon, suspend (s2idle), throttling |
| Crash forensics | unclean shutdowns, GPU hangs and resets, kernel panics and lockups |
| Gaming | Steam stack, audio, real-game frametimes from MangoHud logs |
| Updates | security settings, ostree (none on a flattened image), updates (dnf or rpm-ostree), installed packages |

The tests run as root (they read the kernel log, SMART data and the like), so the app asks for your password when you
start them. They only read: nothing on the PS5 changes. The stress test, the performance benchmark, the system score
and the game page of the BC250 suite's version come in a later version, with baselines measured on a PS5.

## The window

The header shows the app's state beside its name and a status box under it; **Refresh** reads again.
