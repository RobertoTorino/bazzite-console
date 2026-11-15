<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-8b4fd8)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# PS5 CEC Manager

HDMI-CEC for the **PlayStation 5** on **Bazzite**: turn the TV on and off from the PS5, switch it to the PS5's
input, set the volume, see what the TV tells about itself, pause videos and music while the TV is off, and let
Valve's CEC daemon (cecd, which Bazzite ships) wake and suspend the TV with the PS5 and turn the TV remote into key
presses.

The PS5's CEC adapter is part of the ps5-linux kernel (ps5-cec, `/dev/cec0`); it needs no USB adapter. The kernel
also turns the TV on and switches it to the PS5 at boot (`hdmi.one_touch_play`).

Install: `bash install.sh` (as your own user, no root). Remove: `bash install.sh --uninstall` (`--purge` also
removes its settings and the cecd settings it wrote).
