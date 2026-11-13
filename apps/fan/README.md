<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Fan Control

Shows the **PlayStation 5**'s temperatures and its fan on **Bazzite**, and runs a thermal guard: a system service
that watches the SoC, the CPU and (kernel 7.3.1 and later) the GPU, also when no app is open, and warns, turns the
fan to full speed and the CPU boost off, and at a critical temperature shuts the console down cleanly.

The PS5 kernel already slows the GPU from 85 °C, runs the fan at full duty from 87 °C and forces it to maximum from
90 °C. The guard adds what the kernel does not do: a warning on the desktop, the CPU boost off, and the shutdown.

Install: `bash install.sh` (as your own user). Turning the guard on or off asks for your password (pkexec).
Remove: `bash install.sh --uninstall` (also removes the guard).
