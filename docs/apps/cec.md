<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![HDMI CEC Manager](../assets/cec/ps5-hdmi-cec.webp){ .app-logo }

# HDMI CEC Manager

HDMI CEC Manager is an optional app for PlayStation 5 hardware running Bazzite. It controls the TV over HDMI-CEC
from the PS5.

## What it does

- Turns the TV on and off, and switches it to the PS5's input.
- Sets the volume.
- Shows what the TV tells about itself.
- Pauses videos and music while the TV is off.
- Lets Valve's CEC daemon (cecd, which Bazzite ships) wake and suspend the TV with the PS5, and turn the TV remote
  into key presses.

## Compatibility

The PS5's CEC adapter is part of the ps5-linux kernel (ps5-cec, `/dev/cec0`); it needs no USB adapter. The kernel
also turns the TV on and switches it to the PS5 at boot (`hdmi.one_touch_play`). What a TV answers and obeys over
CEC differs per TV.

## Install and remove

The portal installs and removes the app. By hand, as your own user and without root: `bash install.sh`, and
`bash install.sh --uninstall` to remove it. `--purge` also removes its settings and the cecd settings it wrote.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/cec/LICENSE).
