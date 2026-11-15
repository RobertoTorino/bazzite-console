<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<span class="page-icon">:material-harddisk:</span>

# PS5 Linux boot partition

The PS5 Linux loader is sent to the PS5 as a payload. It starts Linux from a FAT32 partition on a USB drive or SSD.
Linux mounts this partition at `/boot/efi`. The loader takes four files from it: `bzImage`, `initrd.img`,
`cmdline.txt` and `vram.txt`. The other files on the partition are backups of these files, helpers, or files Windows
leaves behind when the drive is opened on a PC.

The partition is FAT, so any computer can open the drive. When Linux does not start after a change, you can fix the
files on another computer.

[Boot Command Line](apps/helpers.md#boot-command-line) in Console Helpers edits `cmdline.txt` and the fallback lines.
PS5 Board Test's test 54 checks the partition: where it is, that the loader's files are there, that `root=` points at
a drive that is there, `vram.txt` and the free space.

## What the PS5 needs

| File | What it is |
|---|---|
| `bzImage` | The kernel the loader starts, built by the PS5 Linux kernel builder. |
| `initrd.img` | The kernel's initramfs. It holds the CPU microcode, the dracut image, amdgpu and the kernel modules. Its version must match `bzImage`. |
| `cmdline.txt` | The kernel command line: one line of arguments the loader passes to the kernel (see below). |
| `vram.txt` | How much of the PS5's memory the loader sets aside as fixed VRAM (see below). |
| `lib/nxp/pcieuartiw620_combo_v1.bin` | The firmware of the PS5's Wi-Fi and Bluetooth chip (NXP IW620). The distribution and the kernel package do not ship it. A service copies it into the system's firmware folder at boot, before the Wi-Fi driver loads. Without it the Wi-Fi driver loads, but the chip is never found. |

## `cmdline.txt`

The line the loader starts Linux with. Every argument is separated by a space. A typical PS5 Linux line:

```text
root=LABEL=bazzite rw rootwait console=ttyTitania0 console=tty0 video=DP-1:1920x1080@60 mitigations=off idle=halt preempt=full hdmi.frl_4k120=0 nvme.max_host_mem_size_mb=0 nvme_core.default_ps_max_latency_us=0 hdmi.hdcp_mode=2
```

| Argument | What it does |
|---|---|
| `root=LABEL=<name>` | The partition Linux starts its system from, found by its label. |
| `root=UUID=<id>` | The partition found by its file system's ID. Use this when two drives carry the same label, because then a label can lead to the wrong drive. |
| `rw` | Mounts the system read-write from the start. |
| `rootwait` | Waits until the system's drive appears instead of stopping with an error. A USB drive or an SSD comes up a few seconds after the kernel starts. |
| `console=ttyTitania0` | A console on the PS5's own serial port (the Titania UART inside the console). It is harmless without a cable on it. |
| `console=tty0` | A console on the screen. The last `console=` on the line gets `/dev/console`, so keep `console=tty0` last to see the boot messages on the TV. |
| `video=DP-1:1920x1080@60` | Starts the HDMI output in 1080p60. The GPU calls the HDMI port `DP-1`. This avoids a black screen on a TV that mishandles the mode it picks by itself. The desktop can still switch to 4K after login. |
| `mitigations=off` | Turns off the kernel's guards against the CPU's speculative execution flaws (Spectre, Meltdown and the like), for speed in games. Without them, a program could in principle read the memory of other programs. Keep them on where the console runs code you do not trust. |
| `idle=halt` | The CPU idles with plain HLT instead of the deeper MWAIT C-states. This works around hangs in the APU's low-power states. Remove it only if you see microstutter. |
| `preempt=full` | A fully preemptible kernel (the kernel is built `PREEMPT_DYNAMIC`), for lower latency on the desktop and in games. |
| `hdmi.frl_4k120=0` | The PS5 HDMI driver does not try 4K120 over HDMI 2.1 FRL. It stays on TMDS, up to 4K60. This avoids a black screen on a TV whose FRL negotiation fails. `1` tries 4K120. While Linux runs, `/sys/module/hdmi/parameters/frl_4k120` changes it. |
| `hdmi.hdcp_mode=2` | The PS5 HDMI driver's HDCP mode: `-1` keeps what is set, `0` on, `1` off, `2` on with HDCP 2.2, `3` off with the HDCP 2.2 bit set (the kernel's default). `2` fixes a TV that shows a signal but a black picture and no sound, also at 4K60. While Linux runs, `/sys/module/hdmi/parameters/hdcp_mode` changes it, from the next mode change. |
| `nvme.max_host_mem_size_mb=0` | Turns off the NVMe Host Memory Buffer: the system memory an SSD without DRAM of its own borrows as its cache. The PS5 patches use it as a workaround for SSDs without DRAM. |
| `nvme_core.default_ps_max_latency_us=0` | Turns off NVMe APST. The SSD never enters its low-power states, so it cannot drop off the bus. |
| `plymouth.enable=0` | Turns off the boot splash (Plymouth) in the started system. Only needed while the splash itself gets in the way, for example to find the cause of a black screen. |
| `rd.plymouth=0` | Turns off the boot splash in the initramfs (a dracut `rd.` option). Goes with `plymouth.enable=0`. |
| `amd_iommu=off` | Keeps the kernel from using the IOMMU. By default leave the IOMMU off. If it is on and you experience an unstable system, turn it off again. |
| `ttm.pages_limit=<pages>` | How many 4 KiB pages of system memory the GPU may use: GB × 262144 (`ttm.pages_limit=3145728` is 12 GB). This is the other way to give the GPU more memory than `vram.txt` sets aside. |

### The fallback lines and the backups

Other `cmdline.txt.*` files on the partition are not read by the loader. The loader reads only `cmdline.txt`; to
start Linux with another line, copy it over `cmdline.txt`.

- `cmdline.txt.usb` and `cmdline.txt.m2` are fallback lines. They point `root=` at the system on the USB drive or on
  the M.2 SSD. When the system on one drive does not come up (after a new kernel, for example), copy the other line
  over `cmdline.txt` and start the loader again. Afterward, copy the first line back.
- `cmdline.txt.bak-YYYYMMDD-HHMMSS` is a copy Boot Command Line keeps of a file before it saves a new line over it.
  The fallback lines get their own (`cmdline.txt.usb.bak-…`).
- Other copies, such as `cmdline.txt.bak` or `cmdline.txt.pre-<change>`, are backups made by hand or by a tool before
  a change. Together they show what changed when.

## `vram.txt`

The loader reads this file, not the kernel. The PS5 has 16 GB of GDDR6 that the CPU and the GPU share. The file holds
one hex number: how much of that memory the loader sets aside as fixed VRAM for amdgpu.

```text
0x20000000
```

`0x20000000` is 512 MiB, the loader's default. With it the GPU grows into system memory (GTT) as it needs. Raise the
number for more fixed VRAM. `ttm.pages_limit=` in `cmdline.txt` is the other way to give the GPU more memory.

## `kexec.sh`

A warm reboot: it starts Linux again straight from the running system, without going back through the PS5's own
system and the loader. Run it as root (`sudo /boot/efi/kexec.sh`).

```sh
#!/bin/sh
set -e
BOOT=/boot/efi
kexec -l "$BOOT/bzImage" --initrd="$BOOT/initrd.img" --command-line="$(cat $BOOT/cmdline.txt)"
kexec -e
```

| Line | What it does |
|---|---|
| `set -e` | Stops at the first command that fails, so `kexec -e` never runs when the load failed. |
| `BOOT=/boot/efi` | Where this partition is mounted in the running system. |
| `kexec -l …` | Loads the kernel and the initramfs from this partition into memory, with what `cmdline.txt` says now as the command line. A changed `cmdline.txt` applies from the next kexec. |
| `kexec -e` | Starts the loaded kernel: the running kernel hands over directly, without the firmware or the loader. |

## A kernel update and its way back

A tool that installs a new kernel on the partition can keep the previous one, so you can go back when the new one does
not start:

- `backup-prev/bzImage` and `backup-prev/initrd.img`: the previous kernel and its initramfs. `backup-prev/INFO.txt`
  says which kernel it is, when it was backed up, and where the matching kernel modules are kept (a tarball on the
  system drive).
- `RECOVERY.txt`: what is installed, what the previous kernel was, and the steps back to it.

The steps back, with the drive in a PC:

1. Copy `backup-prev/bzImage` and `backup-prev/initrd.img` over the ones on the partition.
2. Copy the fallback line (`cmdline.txt.usb`) over `cmdline.txt`, so Linux starts the system on the other drive, which
   still has the previous kernel's modules.
3. Start Linux with the loader, connect over SSH, and put the previous kernel's modules back on the first system:
   mount it, unpack the modules tarball onto it, and copy its line (`cmdline.txt.m2`) back over `cmdline.txt`.
4. Restart into it, for example with `kexec.sh`.

## Files from Windows

A drive opened on a Windows PC gets `$RECYCLE.BIN/` and `System Volume Information/` (the recycle bin, the search
indexer's ID of the drive and a storage settings file). The PS5 does not use them; they are safe to delete.
