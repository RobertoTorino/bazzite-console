<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-8b4fd8)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# PS5 GPU Manager

PS5 GPU Manager lets you set up and watch the GPU of an **AMD PS5** board running **Bazzite**. It is a PyQt6
window for **cyan-skillfish-governor-smu**, the GPU governor. A governor is the service that sets the GPU's clocks
and voltages. The board's APU is the Cyan Skillfish (`gfx1013`). Bazzite is a Fedora Atomic system that updates with
rpm-ostree. Its GPU sweep finds the highest GPU clock and the lowest voltage your board holds, one step at a time.

How to install and use it: [PS5 GPU Manager in the wiki](https://robertotorino.github.io/bazzite-console/apps/gpu/).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
