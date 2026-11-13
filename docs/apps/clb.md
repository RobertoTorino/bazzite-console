<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Xbox Remote Play](../assets/apps/clb.webp){ .app-logo }

# Xbox Remote Play

Xbox Remote Play signs in to Microsoft, lists Xbox consoles and Xbox Cloud Gaming titles, and can stream a console
or cloud game. Streaming quality and availability depend on the account, console, network, and Microsoft's services.

## Install

Install it from the portal (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/clb/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/clb/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/clb/install.sh --uninstall             # remove it; --purge also removes account settings
```

The launcher is `~/.local/bin/ps5-xbox-remoteplay`. The app uses its own Python environment for its streaming
dependencies.

## Use it

Sign in with a Microsoft account using the device code in a browser; the app does not ask for your password. Then
select an Xbox console to wake or connect to, or choose an available Xbox Cloud Gaming title. The app stores its
account and settings under `~/.config/ps5-xbox-remoteplay`; uninstalling without `--purge` keeps them.

This is an independent community client and is not affiliated with or endorsed by Microsoft. Availability and
compatibility are subject to Microsoft's services and account requirements.
