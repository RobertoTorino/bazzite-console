<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-8b4fd8)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# XBOX Remote Play

XBOX Remote Play streams an XBOX console or XBOX Cloud Gaming to PS5 hardware running Bazzite. Sign in with a
Microsoft account, select a console or cloud game, and start streaming. XBOX Cloud Gaming requires an eligible
subscription; service and device compatibility may vary.

## Install and use

Run `./install.sh` as your normal user from this checkout (or an extracted release containing
`bazzite_console_core`). Use `--no-desktop-shortcut` to omit the Desktop icon, `--uninstall` to remove the app
and its private environment while retaining settings and account, or `--uninstall --purge` to remove them too.
Launch `ps5-xbox-remoteplay` from the app menu or terminal. The app key is `clb`; its Python module is
`console_linkb`.

The app and its private venv live under `${XDG_DATA_HOME:-~/.local/share}/ps5-xbox-remoteplay/`. Its settings
and sign-in are under `${XDG_CONFIG_HOME:-~/.config}/ps5-xbox-remoteplay/`; the refresh token in `account.json`
is restricted to the user (mode 0600). The installer downloads PyQt6, aiortc (which includes PyAV as a dependency),
and pygame-ce into the private venv, separate from the suite environment. Until XBOX-specific artwork is available,
the desktop icon uses the suite's generic Gaming artwork.

Sign in using the device code shown, then select and stream your XBOX or a cloud game. Escape closes the main
window, but is passed to the game during a stream. The app communicates with Microsoft services over the internet.

## Disclaimer

Bazzite Console is an independent community project, not affiliated with or endorsed by Sony, Microsoft, or the
Bazzite / Universal Blue project. XBOX and XBOX Cloud Gaming are Microsoft trademarks; PlayStation and PS5 are
Sony trademarks. Names are used only to describe compatibility.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE). The protocol code is ported from [Greenlight](https://github.com/unknownskl/greenlight)
and [xal-node](https://github.com/unknownskl/xal-node), both MIT, Copyright (c) 2019 and 2023 UnknownSKL (Jim Kroon);
the files ported from them say so in their header and keep the MIT notice below. The stream uses
[aiortc](https://github.com/aiortc/aiortc) (BSD-3-Clause) and [PyAV](https://github.com/PyAV-Org/PyAV) (BSD-3-Clause,
its wheels bring FFmpeg, LGPL-2.1-or-later), installed from PyPI.

```
The MIT License (MIT)

Copyright (c) 2019 UnknownSKL (Jim Kroon) (Greenlight)
Copyright (c) 2023 UnknownSKL (Jim Kroon) (xal-node)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```
