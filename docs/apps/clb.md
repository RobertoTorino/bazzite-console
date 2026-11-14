<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![XBOX Remote Play](../assets/apps/clb.webp){ .app-logo }

# XBOX Remote Play

XBOX Remote Play brings XBOX games to a PS5 that runs Bazzite. Sign in with your Microsoft account, and the app
lists your XBOX consoles and the games of XBOX Cloud Gaming you may play. Stream your own XBOX to this PS5
(Microsoft calls this Remote Play), or play a game from the cloud.

In this chapter **this PS5** is the PS5 that runs Bazzite and the app, and **the XBOX** is the console you stream
from.

The app does not change how this PS5 runs. It talks to Microsoft's XBOX services only when you sign in, refresh,
wake an XBOX or stream. It is an independent community client: what works depends on the account, the XBOX, the
network and Microsoft's services.

## What you need

- **A Microsoft account with an XBOX profile.** An account that never signed in to XBOX gets its profile by
  signing in once on [xbox.com](https://www.xbox.com).
- **For your own XBOX:** remote play switched on, on the XBOX: Settings > Devices & connections > Remote features
  > **Enable remote features**. To wake it from this PS5, the XBOX's power mode must be **Sleep**; an XBOX that is
  shut down cannot be woken over the network.
- **For XBOX Cloud Gaming:** with **Game Pass Ultimate** you can play its cloud games. Without it, the app lists
  only the games that are free to play in the cloud. XBOX Cloud Gaming is not open to every account or in every
  country.
- **A controller on this PS5:** connected by USB cable or paired over Bluetooth with this PS5, not with the XBOX.
  Any controller the system knows will do. The keyboard works as a controller too (see
  [The stream](#the-stream)).
- **A good connection:** the stream comes over the internet from Microsoft's services, so a cable or a strong
  Wi-Fi signal helps.

## Install

Install it from the portal (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/clb/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/clb/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/clb/install.sh --uninstall             # remove it; keeps its settings and the signed-in account
apps/clb/install.sh --uninstall --purge     # also remove its settings and forget the account
```

Run it as your own user, without `sudo`. The launcher is `~/.local/bin/ps5-xbox-remoteplay`. The app has its own
Python environment in `~/.local/share/ps5-xbox-remoteplay/venv`, with PyQt6, aiortc (the stream's WebRTC, with
PyAV for the video and sound) and pygame-ce (the controllers).

## Using it

The boxes at the top show the **Account** (your gamertag), how many **Consoles** the account has, and which
**Cloud** games it may play (**Game Pass** or **Free to play**). The log at the bottom shows what the app does.

**Microsoft account:**

- **Sign in:** the app asks Microsoft for a code and shows it with the address of Microsoft's page
  ([microsoft.com/link](https://www.microsoft.com/link)). Open that address on a phone or any computer, enter the
  code and sign in there. The window goes on by itself once you are signed in. The code is valid for a limited
  time, about 15 minutes; **Cancel** stops waiting. You sign in on Microsoft's own page, so the app never sees
  your password.
- **Sign out:** forgets the account on this PS5, after asking.

The app stays signed in after it closes, so you sign in once.

**Consoles** (the first tab) lists the account's XBOX consoles with their model, their power state (**On**,
**Sleep** or **Off**) and whether remote play is on.

- **Wake:** wakes the selected XBOX from sleep. Give it a few seconds, then **Refresh** or **Stream**.
- **Stream** (or a double click): streams the XBOX to this PS5.

**Cloud games** (the second tab) lists the games the account may play from the cloud, by name. Type in **Find a
game** to narrow the list. **Stream** (or a double click) starts the selected game. When many people play, the
cloud may put you in a queue first: the stream's window shows the expected wait.

**Refresh**, at the top right, asks XBOX Live for the consoles and the cloud games again.

Escape closes the main window. During a stream the keys are the game's, and Escape does not leave it.

## The stream

The stream opens full screen: the picture scaled to fit, the sound on the default audio output, and the first
controller connected as the XBOX's controller, with its rumble. Only one stream runs at a time.

- **F11** switches between full screen and a window.
- **Leave the stream:** hold **View** and **Menu** on the controller for two seconds, press **Ctrl+Q**, or close
  the window. The session ends with Microsoft too, so the XBOX goes back to its home screen and a cloud server is
  freed.
- **The keyboard as a controller:** the arrow keys are the d-pad, **Enter** is A, **Backspace** B, **X** and **Y**
  their buttons, **Tab** View, **M** Menu and **Home** the XBOX button.
- When a game asks something in a dialog (for example whether to quit), the app shows it and sends your answer.

## Where it keeps what

- `~/.config/ps5-xbox-remoteplay/account.json`: the sign-in, so the app stays signed in. Anyone with this file can
  use your account with the XBOX services, so it is readable only by you. **Sign out** removes it.
- `~/.config/ps5-xbox-remoteplay/ps5-xbox-remoteplay.ini`: the window size.

Uninstalling without `--purge` keeps both.

## Privacy

What the app sends, and to whom:

- **To Microsoft, when you sign in:** the code request and, while you sign in on Microsoft's page, the question
  whether you did. The sign-in itself happens in your browser.
- **To Microsoft's XBOX services, when you refresh, wake or stream:** the account's tokens, to list your consoles
  and the cloud games, to wake an XBOX, and to start and keep a stream. The stream itself carries your
  controller's input to the XBOX or the cloud server, and the picture and sound back.
- **Nobody else.** The app has no statistics and no crash reports.

The app's log masks personal details: the account's tokens are never shown, your gamertag is hidden, an XBOX's ID
shows only its last four characters and a network address only its last part. The consoles' names (Living room)
are not masked: check them before you share a log if you gave an XBOX your own name. The suite's
[Privacy](../privacy.md) page covers all the apps.

## When it does not work

- **Signing in says the account has no XBOX profile:** sign in once on [xbox.com](https://www.xbox.com), then sign
  in again here. A child account needs an adult to add it to a Microsoft family first.
- **The code expired before it was entered:** sign in again for a new one.
- **The app says to sign in again:** Microsoft no longer accepts the saved sign-in. Sign in again with a new code.
- **No consoles:** the XBOX must be signed in with the same account. Check remote features on the XBOX (see
  [What you need](#what-you-need)), then **Refresh**.
- **Wake does nothing:** the XBOX's power mode must be **Sleep**, not shut down, and remote features must be on.
- **Remote play is off:** switch it on on the XBOX (see [What you need](#what-you-need)).
- **No cloud games:** XBOX Cloud Gaming is not open to the account, or not in its country. The free-to-play games
  need no Game Pass, only the account.
- **The stream ends with "the connection to the stream was lost":** the network between this PS5 and the XBOX or
  the cloud dropped. A cable, or a Wi-Fi close to the router, helps.
- **No sound:** the sound goes to the default audio output; choose the output in the system's sound settings.
- **The controller does nothing:** check that it is connected to this PS5 and not to the XBOX. The keyboard works
  as a controller in the meantime.

## Disclaimer

<!-- disclaimer -->

## License

GPL-3.0-or-later. The protocol code is ported from [Greenlight](https://github.com/unknownskl/greenlight) and
[xal-node](https://github.com/unknownskl/xal-node), both MIT, Copyright (c) 2019 and 2023 UnknownSKL (Jim Kroon);
the files ported from them say so in their header, and the app's README keeps the MIT notice. The stream uses
[aiortc](https://github.com/aiortc/aiortc) (BSD-3-Clause) and [PyAV](https://github.com/PyAV-Org/PyAV)
(BSD-3-Clause, its wheels bring FFmpeg, LGPL-2.1-or-later), installed from PyPI.
