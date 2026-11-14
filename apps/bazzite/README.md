<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Bazzite Test

Read-only diagnostics, a stress test and benchmarks for a **PlayStation 5** running **Bazzite** on the ps5-linux
kernel: about sixty tests in twelve groups (system, network, storage and memory, system logs, GPU and graphics, CPU
and firmware, stability and thermals, crash forensics, gaming, performance, PS5, updates), with hints where
something can be done. The tests run as root through a password prompt and only read; the stress test, the
benchmark, the disk speed test and the internet speed test are opt-in and ask before they start.

Install: `bash install.sh` (as your own user; it asks for your password once, for the root-owned copy in /opt).
Remove: `bash install.sh --uninstall`.
