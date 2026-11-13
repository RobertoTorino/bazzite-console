<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Bazzite Test

Read-only diagnostics for a **PlayStation 5** running **Bazzite** on the ps5-linux kernel: about fifty tests in
eleven groups (platform, network, storage and memory, logs, GPU and graphics, CPU, sensors and thermals, crash
forensics, gaming, updates), with hints where something can be done. The tests run as root through a password
prompt and only read.

Install: `bash install.sh` (as your own user; it asks for your password once, for the root-owned copy in /opt).
Remove: `bash install.sh --uninstall`.
