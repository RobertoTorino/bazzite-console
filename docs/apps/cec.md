<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![HDMI CEC Manager](../assets/cec/ps5-hdmi-cec.webp){ .app-logo }

# HDMI CEC Manager

HDMI-CEC lets the console and the TV talk over the HDMI cable. With it you can turn the TV on and off from a
**PlayStation 5** running **Bazzite**, switch the TV to the PS5's input, set the volume, and use the TV remote on
the PS5.

The app does not change how the console runs. It sends CEC messages to the TV when you press a button. While
**Pause videos and music** is on, it asks the TV every 5 seconds whether it is on.

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

- **The adapter is there from boot,** on the console's own HDMI port. When the app finds none, the kernel is not a
  ps5-linux one or its CEC module did not load. [Bazzite Test](bazzite.md) shows the kernel and checks HDMI-CEC.
- **The TV answers** only when CEC is switched on in the TV. TVs give CEC a brand name in their settings: Anynet+
  (Samsung), SimpLink (LG), Bravia Sync (Sony), HDMI control or HDMI CEC (others). Plug the HDMI cable straight
  into the TV: some AV receivers and switches do not pass CEC.

The app sends its messages with `cec-ctl` (v4l-utils), which Bazzite has. The adapter belongs to the logged-in
user, so nothing here needs root.

## Using it

The top row shows the **CEC adapter**, the PS5's **physical address** (the HDMI input it is on, from the TV's EDID;
"None" when the PS5 sees no display), the **display**'s name and the **TV power** after a check. Opening the app
only reads these; nothing goes to the TV. With more than one CEC adapter (a USB one as well, for example), the app
uses the one that sees a display.

**TV:**

- **Turn TV on:** wakes the TV and switches it to the PS5 (Image View On, then Active Source).
- **Switch to PS5:** switches the TV to the PS5's input when it shows something else.
- **TV standby:** puts the TV in standby.
- **Check TV:** asks the TV whether it is there and on. The status next to the title then says **TV answers** or
  **TV does not answer**.
- **Volume −**, **Volume +** and **Mute:** go to an AV receiver when one answered the last check, else to the TV.
- **Devices on the bus…:** asks every device on the HDMI bus who it is, and lists them. Read-only.
- **TV info…:** what the TV tells about itself: its CEC version, power status, name and type, vendor ID, menu
  language, its CEC 2.0 features, its volume and mute status, its lip-sync delay, and whether an AV receiver or
  soundbar is connected (with its name and volume). A CEC 1.4 TV says "not supported" to the CEC 2.0 questions; a
  CEC 2.0 TV shows what it can do, for example ARC or taking an exact volume. These are only questions: nothing on
  the TV changes.
- **Name on the TV** and **Set name:** the name the TV shows for the PS5 in its list of inputs and devices, at
  most 14 plain characters. The app tells the TV the new name right away; with Valve's CEC daemon running, it
  restarts the daemon with it.

The line under the buttons says what the last message did. When the TV does not answer, the app says what to
check: CEC switched on in the TV, the TV on, and the HDMI cable plugged straight into the TV.

The first message configures the adapter when nothing has yet, or when it carries another name (a plain
`cec-ctl --playback` names it "Playback", and the TV lists the input as that): the PS5 then shows up on the TV as a
playback device with your name (**PS5** until you set another), and the app tells the TV. With Valve's CEC daemon
running, the daemon names the adapter. Some TVs only update the name in their input list after switching inputs or
turning the TV off and on.

## When the TV turns off and on

**Pause videos and music while the TV is off** pauses the media players that play when the TV goes to standby
(browsers, mpv, VLC, Spotify and other players that offer media controls), and continues them when the TV is on
again. Only the ones that were playing continue. Games are not media players: they keep running.

It uses a small background service that starts with your desktop session and asks the TV every 5 seconds whether
it is on. One missed answer does not count as "off": only three in a row do, for example when the TV is unplugged.
So a hiccup on the HDMI bus pauses nothing.

## At boot

The PS5's kernel turns the TV on and switches it to the PS5 by itself at boot (`hdmi.one_touch_play`). The app adds
nothing there and installs no system service.

## Automatic: Valve's CEC daemon

Bazzite ships Valve's CEC daemon, `cecd`, the one SteamOS uses. It runs with your desktop session and can:

- **Turn the TV on when the PS5 wakes from sleep.**
- **Put the TV in standby when the PS5 goes to sleep.**
- **Use the TV remote as a keyboard:** arrows, OK, back and the media keys arrive as key presses.
- **Put the PS5 to sleep when the TV goes to standby.**

The daemon is Bazzite's **native** CEC mode, made for a machine with its own CEC adapter like the PS5. Bazzite's
other mode, **dGPU**, is for USB adapters. The app shows the mode Bazzite is in and whether the daemon runs. When
it shows another mode than native, **Use Valve's CEC daemon…** runs Bazzite's own `ujust cec-mode native` in a
terminal; it asks for your password. Press **Check again** when it is done. The four switches can be changed in
native mode; in another mode they only show the daemon's settings.

The four switches are the daemon's settings for your account. The app writes them to
`~/.config/cecd/config.d/99-ps5-hdmi-cec.toml` and tells the daemon to read them again. They win over Bazzite's
defaults (`98-bazzite-cec-mode.toml`). Where SteamOS Manager runs, its own settings (`99-steamos-manager.toml`) win
over the app's.

The buttons under **TV** send their messages themselves, so they work whichever CEC mode Bazzite is in.

**Remote buttons…** chooses the key each button of the TV remote gives. The buttons most TVs pass on come first:
OK, the arrows, back, the media buttons, the four colored buttons, info and the channel buttons. After them come all
the others the daemon knows (numbers, menus, guide, …); which of those arrive depends on the TV. Each button can
keep the daemon's **Default**, give one key (for example **F12** for a Steam screenshot, **Super** for the app
launcher, **Play/pause**), or do **Nothing**. A button gives one key, not a combination.
The daemon reads the buttons when it starts, so saving restarts it. As soon as one button differs from the default,
the app writes the daemon's whole table with your changes, in the same file.

## Remote control keys

With the daemon running, every key the PS5 receives from the TV remote shows in the list, with its CEC name; the
list keeps the last 12. The TV sends the keys only while it shows the PS5's input.

## Files

- `~/.config/ps5-hdmi-cec/ps5-hdmi-cec.ini`: the window size.
- `~/.config/cecd/config.d/99-ps5-hdmi-cec.toml`: the daemon settings, the name on the TV and the remote's
  buttons, once you change one. Uninstalling keeps it, so the TV keeps behaving the same;
  `install.sh --uninstall --purge` removes it.
- `~/.config/systemd/user/ps5-hdmi-cec-watch.service`: the background service of **Pause videos and music**, only
  while it is on. Uninstalling removes it. It writes a line to the journal each time it pauses or continues:
  `journalctl --user -u ps5-hdmi-cec-watch`.

## Install and remove

The portal installs and removes the app; it is on the **Utilities** tab. By hand, from a clone or a release
folder, as your own user and without root:

```bash
./install.sh                         # app menu entry and Desktop icon
./install.sh --no-desktop-shortcut   # app menu entry only
./install.sh --uninstall             # remove the app; keeps its settings and the daemon settings it wrote
./install.sh --uninstall --purge     # also remove its settings and the cecd settings it wrote
```

It installs:

- the app in `~/.local/share/ps5-hdmi-cec/app`;
- PyQt6 in the suite's shared venv `~/.local/share/bazzite-console-suite/venv`;
- the launcher `~/.local/bin/ps5-hdmi-cec`, an app menu entry and a Desktop icon.

## License

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/cec/LICENSE).
