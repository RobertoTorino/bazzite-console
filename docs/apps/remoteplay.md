<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Remote Play

The app finds PS4 and PS5 consoles on the local network, can wake a console from rest mode, and registers the
client for Remote Play. Registration uses the PSN account ID and the temporary PIN shown by the console. Use the
connection and stream checks before starting a session; network quality and console firmware affect the result.

## Install

Install it from the portal (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/remoteplay/install.sh                       # the app, its launcher, a menu entry and a Desktop icon
apps/remoteplay/install.sh --no-desktop-shortcut # without the Desktop icon
apps/remoteplay/install.sh --uninstall           # remove it; --purge removes its settings too
```

The launcher is `~/.local/bin/ps5-remoteplay`; the app runs on the suite's shared Python environment.

## Use it

Sign in to PSN to fill in the account ID, select a discovered console, and follow its on-screen steps to register.
After registration, select the console and start a session or stream. The registration keys are stored in
`~/.config/ps5-remoteplay/consoles.json` with owner-only permissions. Remove a console in the app to delete its
local keys; removing the app with `--purge` also deletes them, but does not unlink the client from the console.

Escape closes the main window when it is not otherwise handled; dialogs keep their normal Escape behavior. In a
stream, Escape only leaves full screen and never ends the session. Controller buttons remain available to the game.

Remote Play is an independent client, not a Sony-certified app. Actual console registration and stream
compatibility depend on the console, firmware, and network.
