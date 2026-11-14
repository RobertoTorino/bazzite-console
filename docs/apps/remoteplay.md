<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Remote Play](../assets/remoteplay/ps5-remoteplay.webp){ .app-logo }

# Remote Play

Remote Play connects a PS5 that runs Bazzite to a PS4 or PS5 on your network. The app finds the consoles, wakes
them from rest mode, registers with them, and starts a session and its stream. The consoles' own name for this is
Remote Play, and it has to be switched on there.

In this chapter **this PS5** is the PS5 that runs Bazzite and the app, and **the console** is the PS4 or PS5 you
stream from.

The app does not change how this PS5 runs. It talks to a console, or to PSN for your account ID, only when you
press a button. It streams the console's picture and sound to a window on this PS5, and plays with the controllers
connected to this PS5.

Remote Play is an independent client, not a Sony-certified app. Registration and the stream depend on the console,
its system software and the network.

## What you need

- **Remote Play on the console:** Settings > System > Remote Play > Enable Remote Play.
- **To wake it from rest mode:** on a PS5, Settings > System > Power Saving > Features Available in Rest Mode:
  switch on **Stay Connected to the Internet** and **Enable Turning On PS5 from Network**. A PS4 has the same two
  switches under Settings > Power Saving Settings > Set Features Available in Rest Mode.
- **The same network:** this PS5 and the console in one local network. Remote Play over the internet is not part
  of this app.
- **Your PSN account ID:** the number of your PlayStation Network account, not your online name. PlayStation does
  not show it anywhere; **Find my account ID…** reads it through the PlayStation sign-in (see below). The app also
  takes the number itself (for example `4782394583276428394`) or the 12-character code that ends with `=`, as
  other Remote Play apps show it. It is the same for every console you register with this account.
- **A controller on this PS5:** connected by USB cable or paired over Bluetooth with this PS5, not with the
  console. A DualShock 4 or DualSense works best, but any controller the system knows will do: the app reads them
  with the system's SDL3. A controller that is paired with the console connects to the console itself when you
  press its PS button, and the console then ends Remote Play.

## Install

Install it from the portal (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/remoteplay/install.sh                       # the app, its launcher, a menu entry and a Desktop icon
apps/remoteplay/install.sh --no-desktop-shortcut # without the Desktop icon
apps/remoteplay/install.sh --uninstall           # remove it; keeps its settings and the registered consoles
apps/remoteplay/install.sh --uninstall --purge   # also remove its settings and the registered consoles' keys
```

Run it as your own user, without `sudo`. The launcher is `~/.local/bin/ps5-remoteplay`. The app has its own Python
environment in `~/.local/share/ps5-remoteplay/venv`, with PyQt6 and cryptography.

The stream runs on the app's native core, written in Rust, with FFmpeg inside for the video. A release brings it
ready to install, so the portal needs nothing else for it.

From a checkout, `install.sh` builds the native core when Rust is installed ([rustup](https://rustup.rs) installs
it in your home folder), which takes a minute or two the first time. The video decoder needs FFmpeg built first,
once: `apps/remoteplay/native/ffmpeg/build.sh` downloads FFmpeg's sources, checks them and builds it into
`~/.cache/ps5-remoteplay` (without `nasm` installed, decoding in software is slower). Without the native core,
everything but the stream works; without the decoder, **Test stream** does not decode the frames.

Removing the app, with or without `--purge`, does not unlink it on the console: a PS5 still lists it under Link
Device, where you remove it too.

## Using it

The boxes at the top show how many consoles answered the last search (**On the network**), how many are
**Registered**, how the **Last session** went, and **Console type**: the selected registered console's model and
system software (**PS4 Pro · 14.00**; the exact model once a session has run). Hold the mouse over it for more: its
state and what runs on it (the game's name and title ID) as the last search found them, its Remote Play version
and the last stream's network test. A PS5 does not report its system software this way, so for a PS5 the box
shows the model only.

The window then has four numbered steps, each with its buttons on the right: **1 Find** the console, **2
Register** with it, **3 Console** (the selected console's login passcode, and removing it) and **4 Game Mode**.
Below them are two lists, **Consoles on the network** and **Registered consoles**, and under those the buttons for
the selected console, with **Stream** on the right. The log at the bottom shows each step.

**Settings…**, at the top right, has the app's own settings: **Show personal details** (see [Privacy](#privacy))
and **Steam comes to the front on the PS button** (see [When it does not work](#when-it-does-not-work)).

Escape closes the main window; a dialog keeps its own Escape. In a stream, Escape only leaves full screen and never
ends the session.

**1 Find:**

- **Search network:** asks every PS4 and PS5 on the network to answer. Each one is listed under **Consoles on the
  network** with its name, model, address, state (**On** or **Rest mode**) and system software (a PS4's, 14.00 for
  example; a PS5 reports a code instead), and whether it is registered.
- **Search address** (the address in the field, then the button or Enter): asks one address. Use it when the
  search finds nothing, for example on a network that does not pass broadcasts (some mesh systems, a guest network,
  a VPN). The app remembers the address.

**Find my account ID…** (step 2, for the account ID):

1. Press **Open the PlayStation sign-in**: your browser opens the PlayStation sign-in page. Sign in with the PSN
   account you use on the console. (**Copy the link** is for a browser on another device.)
2. The sign-in then shows a page that only says "redirect". Copy that page's address from the browser's address
   bar: the app sees it on the clipboard and takes it by itself. (Pasting it in the dialog and pressing **Get
   account ID** works too.)

While the dialog is open the app looks at the clipboard only for that address; it ignores anything else, and what
was on the clipboard before. The sign-in stays in your own browser, so the app never sees your password. The app
sends the code in that address to PSN once, reads your account ID and fills it in. It keeps only the account ID,
nothing of the sign-in. The code works for a few minutes: if PSN refuses it, sign in again.

**2 Register:**

1. On a PS5, open Settings > System > Remote Play > **Link Device**; on a PS4, Settings > Remote Play Connection
   Settings > **Add Device**. It shows an 8-digit PIN for a few minutes.
2. In the app, select the console under **Consoles on the network**, enter your account ID and the PIN, and press
   **Register**.

The console hands the app its keys, and the console appears under **Registered consoles**, with its name, model,
address, Remote Play version and whether a login passcode is set. Click it to select the console; the buttons of
steps 3 and 4 and the ones under the lists stay grayed out until one is selected, then act on it. A double click
on it starts **Stream**. A wrong PIN or a wrong account ID is reported in the log at the bottom.

**The buttons for the selected console** (under the lists, and in steps 3 and 4):

- **Wake:** turns the console on from rest mode. It takes about 20 seconds; **Search network** then shows it as
  On.
- **Rest mode:** puts the console in rest mode, through a short session.
- **Test session:** starts a Remote Play session, keeps it for 3 seconds and closes it. When it works, the
  registration and the connection to the console are in order. The log shows each step.
- **Test stream:** starts a session, runs a short network test, then the stream for 5 seconds, and closes it all.
  The stream asks for what the console's **Stream settings…** say: by default 1080p at 60 frames per second from a
  PS5 and a PS4 Pro and 720p from a PS4, all in H.264. When it works, the message says how many frames arrived,
  how many were rebuilt and how many were lost, and whether they were decoded. Frames with a few packets lost are
  rebuilt from the spare packets the console sends along. When a frame cannot be rebuilt, the app asks the console
  for a fresh key frame (a picture that needs no earlier one) and leaves out the frames until it comes, so the
  picture freezes for a moment instead of smearing. The frames are decoded but not shown: with the GPU's video
  decoder (VA-API) where its driver offers one, else by the processor; the message names which. It needs the app's
  native core (see [Install](#install)).
- **Stream:** the same start, then the console's picture in a window of its own, until you close it. **F11** or a
  double click switches to full screen, **Escape** back. The mouse pointer hides over the picture after 2 seconds
  without moving, and comes back when you move the mouse. The line under the picture shows its size and how many
  pictures per second are shown. The sound plays on the default audio output (the TV over HDMI, for example);
  **M** mutes it. The controllers on this PS5 play: the buttons (the PS button too), the sticks, L2 and R2 and the
  touchpad, its click included. Controllers connected during the stream are picked up, and the log names each one.
  Several controllers act as one. The motion sensors play too, on a controller that has them (a DualShock 4 or
  DualSense): games that steer or aim by tilting the controller see the tilt. The other way, the controllers
  rumble when the game makes them, and the light bar takes the color the console gives it (on a controller with
  motors and a light bar). A DualSense's adaptive triggers are not used. Closing the window ends the stream; the
  log then has the same counts as Test stream.
- **Stream settings…:** how the selected console streams, from its next stream on (the Game Mode shortcut's
  too). Each console keeps its own.
    - **Resolution:** Automatic asks for 1080p from a PS5 or a PS4 Pro and 720p from a PS4; or 360p, 540p, 720p,
      1080p. Lower is lighter for the network and for this PS5. A PS4 that is not a Pro streams at most 720p.
    - **Frame rate:** 60 or 30 frames per second.
    - **Bitrate:** Automatic (2, 6, 10 or 15 Mbit/s by resolution) or your own, 1 to 50 Mbit/s. More is sharper in
      busy scenes and needs a better network; on Wi-Fi less is safer.
    - **Picture:** Fit shows the whole picture with black bars where the screen's shape differs; Stretch fills the
      screen and distorts the picture; Fill fills the screen and cuts off the picture's edges. The console always
      sends 16:9.
    - **Audio delay:** plays the sound later, up to 500 ms, for a TV or audio system that shows the picture later
      than it plays the sound.
    - **Low latency:** a shorter sound buffer and the decoder's low-delay mode: a little less delay, with more
      risk of short gaps in the sound on a busy network.
- **Controller test…:** every button, stick, trigger and the touchpad of the controllers on this PS5, live, and
  the motion sensors. Each button is marked once it has been pressed; a stick that does not come back inside the
  small circle when you let go drifts. **Rumble left**, **Rumble right** and **Light bar** try the motors
  and the light. The window names the model: a DualShock 4 v1 (CUH-ZCT1), v2 (CUH-ZCT2), a DualSense or DualSense
  Edge, by the ID the controller gives. For a Sony DualShock 4 or DualSense it also shows whether the controller
  is genuine or fake (**Genuine DS4v1**, **Genuine DS4v2**, **Fake DS4**, ...), from its firmware information
  (build date and versions) and the calibration of its motion sensors, which fake controllers get wrong.
- **History…:** the games played through the app, per console, with the time played and when last played, and the
  total. During a stream the app asks the console every 30 seconds what it runs and adds the time to that game;
  time on the home screen is not counted. Streams from the Game Mode shortcut count too; play on the console
  itself does not. **Clear history** forgets it all.
- **Add to Game Mode** (step 4): a Steam shortcut for the selected console, so it can be played from Bazzite's
  Game Mode like a game, with artwork drawn from the app's icon and the console's name and model on it. Starting
  it wakes the console when it is in rest mode and streams it full screen. Steam has to close for the change: the
  app asks, closes it and starts it again. The button is off in Game Mode itself: add the shortcut from Desktop
  Mode. Once the console has a shortcut the button reads **Update in Game Mode**: press it after a change of the
  console's name. The shortcut runs `~/.local/bin/ps5-remoteplay`, so the app has to be installed. From a
  terminal, `ps5-remoteplay --stream <console>` does the same: the console's name, host id or address.
- **Login passcode…** (step 3): when the PSN account on the console has a 4-digit login passcode, the console asks
  for it at the start of a session. Enter it here once; an empty passcode removes it.
- **Remove** (step 3): forgets the console's keys on this PS5. When the console has a Game Mode shortcut, the app
  offers to remove it from Steam too (Steam closes for it and starts again; in Game Mode itself, remove it in
  Desktop Mode or in Steam). A PS5 lists the app under Link Device: remove it there too to undo the registration
  completely. A PS4 has no such list. It keeps a history of the connections under Settings > Remote Play
  Connection Settings > **Connection History**.

When a console gets another address from the router, the next search finds it, and the app updates the address of
the registered console.

## Where it keeps what

- `~/.config/ps5-remoteplay/consoles.json`: the registered consoles, their keys and their stream settings. Anyone
  with these keys can start a session with your account on the console, so the file is readable only by you.
- `~/.config/ps5-remoteplay/ps5-remoteplay.ini`: your account ID, the last address you searched and the window
  size. The account ID only identifies the account; it gives no access to it.
- `~/.config/ps5-remoteplay/history.json`: the games played through the app and their time (**History…**). Which
  games you played when is personal, so the file is readable only by you.
- `~/.local/state/ps5-remoteplay/streams/`: a statistics file for each stream, one line per second (see
  [When it does not work](#when-it-does-not-work)); the newest 20 are kept. They hold no account details, and the
  console's address only masked.

## Privacy

Your PSN account ID, your PSN online ID and the consoles' addresses are personal details: they identify you and
your home network. The window masks them. The account ID shows only its last four characters, an address only its
last part (`•••.•••.•••.20`), the online ID nothing at all. That holds for the fields, the tables and the log.
**Show personal details** in **Settings…** shows them in full until you switch it off again, for example to type
or correct the account ID; the app starts with them masked every time. Whatever you copy from the log is masked,
even while the window shows the details in full, so a log you send with a question keeps them to yourself. The
consoles' names (PS4-728, Living room PS5) are not masked: check them before you share a log if you gave a console
your own name.

What the app sends, and to whom:

- **To your consoles, on your own network:** the account ID once, when you register; after that the keys from
  registration, to start a session, and the stream itself (your controller's input). During a stream the app also
  asks the console what it runs, for the history; that answer stays on this PS5.
- **To PlayStation (PSN), only with Find my account ID…:** the one-time code from the sign-in, once, to read your
  account ID and online ID. The sign-in itself happens in your browser; the app never sees your password.
- **Nobody else.** The app has no statistics and no crash reports.

What it keeps is listed under [Where it keeps what](#where-it-keeps-what); the online ID is not kept. **Add to
Game Mode** writes the console's name into Steam's list of non-Steam games on this PS5. The suite's
[Privacy](../privacy.md) page covers all the apps.

## When it does not work

- **Search finds nothing:** check that Remote Play is on, and that the console is on or in rest mode with the two
  rest-mode switches on. Try **Search address** with the console's address (the console shows it under Settings >
  Network > Connection Status). The console answers on UDP port 9303 to 9319 of this PS5: a strict firewall may
  block them.
- **Registration: no answer:** the PIN screen (Link Device on a PS5, Add Device on a PS4) must be open on the
  console while you register, and the PIN is only valid for a few minutes.
- **The console was switched off completely:** Wake and the tests only reach a console that is on or in rest mode.
  For the app to reach it in rest mode, switch on **Stay Connected to the Internet** and turning it on from the
  network in its rest-mode settings (see [What you need](#what-you-need)).
- **The console asks for the login passcode:** enter it with **Login passcode…**.
- **Test stream: no answer on the stream port:** the stream uses UDP port 9296 of the console, the network test
  port 9297. Test session working but Test stream not points to a firewall or router between the two that blocks
  them.
- **Test stream: the native core is missing:** install the app again through the portal, or see
  [Install](#install) for a checkout.
- **The controller does nothing in the stream:** try it in **Controller test…** first: a button that does nothing
  there is the controller's fault. The log names each controller it found. When it names none, check that the
  controller is connected to this PS5 and not to the console (a cable or a Bluetooth pairing with this PS5).
- **In Game Mode the controller has no touchpad or motion, or acts twice:** Steam gives a game it starts a virtual
  controller in place of the real one; the app reads the real one and leaves Steam's out while a real one is
  there. The log names the controllers it uses.
- **The PS button brings up Steam:** Steam reads the controllers too and comes to the front on the PS button.
  Switch off **Steam comes to the front on the PS button** in **Settings…**. It is Steam's own setting (Settings >
  Controller > Show Advanced Settings > **Guide Button Focus Steam**): the app closes Steam for the change, after
  asking, and starts it again in the background. In Game Mode Steam keeps the PS button for its own menu, and the
  setting is off there.
- **The sound stutters, or the picture or the controller lags:** every stream writes a statistics file, one line
  per second, in `~/.local/state/ps5-remoteplay/streams/` (the newest file is the last stream). Each line shows
  the frames received, the time to decode a frame, the frames lost and the key frames asked for, the pictures
  shown and how old they were when drawn, how late the window ran, the sound buffer, the controller's reads and
  how busy the processor was. Send the file with a question: it shows which part falls behind, and when.
- **The stream ends after you press PS:** the controller most likely connected to the console, not to this PS5.
  Connect it to this PS5 (see [What you need](#what-you-need)).

## Disclaimer

<!-- disclaimer -->

## License

AGPL-3.0. The protocol code is ported from [chiaki-ng](https://github.com/streetpea/chiaki-ng), which is
AGPL-3.0-only with an OpenSSL exception; those files keep that license, the app's own files are AGPL-3.0-or-later.
The files marked `SPDX-License-Identifier: AGPL-3.0-only` are modified from chiaki-ng's code (ported to Python and
Rust). The native core links [FFmpeg](https://ffmpeg.org) (LGPL-2.1-or-later), built from its own sources by
`native/ffmpeg/build.sh`.
