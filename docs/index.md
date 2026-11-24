---
template: home.html
hide:
  - navigation
  - toc
---
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<section class="home-hero" markdown>
<div class="home-hero__pictures" markdown>
![A PlayStation 5 console](images/home/console.webp){ .home-hero__board }
![A game controller](images/home/controller.webp){ .home-hero__controller }
</div>
<div class="home-hero__text" markdown>
# Bazzite Console Suite { .home-hero__lead }
<p class="home-hero__claim">Control your PlayStation 5 running Bazzite.</p>
<p class="home-hero__stage"><strong>Beta</strong> The suite is in active development: features and layout may still change between releases.</p>
</div>
</section>

<section class="home-section home-section--dark" markdown>
<div class="home-section__inner" markdown>
## What's in the suite?

<div class="home-grid" markdown>
<div class="home-card" markdown>
#### :material-stethoscope: Diagnostics

[PS5 Board Test](apps/board.md) checks the board with about sixty tests, with
[Quickfix](apps/quickfix.md) for its optional tools, MangoHud's FPS log, the memory map, the journal and
the boot command line,
[PS5 System Overlay](apps/overlay.md) keeps CPU, GPU, memory, fan and temperatures on top, and
[PS5 SSD Check](apps/ssd.md) shows the drives' health and information.
</div>
<div class="home-card" markdown>
#### :material-fan: Cooling

[PS5 Fan Controller](apps/fan.md) shows the temperatures and the fan, and its thermal guard warns, cools and shuts the
board down cleanly at a critical temperature.
</div>
<div class="home-card" markdown>
#### :material-speedometer: Tuning

[PS5 GPU Manager](apps/gpu.md) tunes the GPU governor. Its GPU sweep finds your board's safe overclock and undervolt.
</div>
<div class="home-card" markdown>
#### :material-lock-open-variant: Unlocks

[PS5 CU Unlock](apps/compute.md) and [PS5 Core Unlock](apps/cores.md) tell bad CUs and cores apart from an unstable
unlock, and keep a tested unlock.
</div>
<div class="home-card" markdown>
#### :material-expansion-card: Graphics

[PS5 Upscaler Manager](apps/upscaler.md) puts HelixSR, an FSR 3.1 drop-in upscaler with DLSS-style networks, into
games, and takes it out again.
</div>
<div class="home-card" markdown>
#### :material-gamepad-variant: Gaming

[shadPS4 Manager](apps/shadps4.md) plays PS4 games, [RPCS3 Manager](apps/rpcs3.md) PS3 games,
[PCSX2 Manager](apps/pcsx2.md) PS2 games, [PPSSPP Manager](apps/ppsspp.md) PSP games,
[Vita3K Manager](apps/vita3k.md) PS Vita games and [Xenia Manager](apps/xenia.md) XBOX 360 games, each with its
emulator, and [PS5 DatStation](apps/datstation.md) has a PlayStation quiz and console history.
</div>
<div class="home-card" markdown>
#### :material-television-play: Streaming

[Remote Play](apps/remoteplay.md) finds, wakes and registers PS4 and PS5 consoles and streams them, and
[XBOX Remote Play](apps/clb.md) streams XBOX consoles and XBOX Cloud Gaming.
</div>
<div class="home-card" markdown>
#### :material-television: Living room

[PS5 CEC Manager](apps/cec.md) turns the TV on and off with the PS5, [PS5 SFTP Tools](apps/sftp.md) moves files
between computers, [PS5 Webcam](apps/webcam.md) makes a PlayStation camera a webcam,
[PS5 Controller](apps/controller.md) manages DualSense controllers and updates their firmware,
[PS5 Bluetooth](apps/bluetooth.md) pairs your keyboard, mouse and controllers at boot, and
[PS5 Password Generator](apps/password.md) makes a random password and keeps it nowhere.

[PS5 Turing Screen](apps/turing.md): CPU, GPU, memory, fan and temperatures on a Turzx USB IPS screen (Turing Smart Screen 3.5").
</div>
</div>

[All the apps](apps/index.md){ .md-button }
</div>
</section>

<section class="home-section home-section--light" markdown>
<div class="home-section__inner home-split" markdown>
<div markdown>
## One dashboard for all the apps

The portal installs, opens, updates and removes the apps, fullscreen, with the keyboard, the mouse or a
controller. Each app is a tile: press it to open it, and its menu installs or uninstalls. A red dot shows an update.
Apps that **change the board** are marked, and the portal asks before it installs or opens them.

[About the portal](portal.md){ .md-button }
</div>
![The portal with its app tiles](images/home/portal.webp){ .home-split__picture }
</div>
</section>

<section class="home-section home-section--accent" markdown>
<div class="home-section__inner" markdown>
## Get started

Ready to set up your PlayStation 5? One download installs the **portal**: a fullscreen app library for the
controller, the keyboard and the mouse. It installs Board Test and Quickfix with it. Each fix of Quickfix,
such as MangoHud Config, Game Memory Map or Persistent Journal, is a tile on Utilities. From the portal you install,
open, update and remove every other app of the suite. You never download an app yourself.

[:material-download: Install the portal](install.md){ .md-button .md-button--primary }
[How the portal works](portal.md){ .md-button }
</div>
</section>

<section class="home-section home-faq" markdown>
<div class="home-section__inner" markdown>
## FAQ

### Do the apps change my board?

Only the apps marked **changes the board**: Fan Controller's thermal guard, Webcam's camera access, the SSH server
that SFTP Tools starts, the unlocks of CU Unlock and Core Unlock, CEC Manager's standby service and four of Quickfix's
fixes. They are software-only and can be undone, and the portal says what the app changes and asks
before it installs or opens it. Each of their chapters opens with a **Changes the board** box with the same text:
what the app touches, what stays after a reboot and how the change is undone. Board Test only reads.

### How do I undo a change?

In the app that made it: turn the thermal guard off in [PS5 Fan Controller](apps/fan.md), and stop the SSH server in
[PS5 SFTP Tools](apps/sftp.md#manage-ssh-servers), which leaves the firewall's rule for you to review. Uninstalling
[PS5 Webcam](apps/webcam.md) removes its camera rule, and uninstalling Fan Controller removes the guard.

### Do the apps change the board's own driver?

No. The apps read what the kernel's drivers for the board offer and install no driver of their own. Bazzite's own
packages and their updates are Bazzite's.

### Do the emulators come with games?

No. The managers install the emulators and add your games to Steam and Game Mode. The games, and the firmware or
BIOS an emulator needs, are yours to supply.

### Do I have to install the apps one by one?

No. Install the portal; it installs, updates and removes the apps, each from a tested release that it checks
before it unpacks it. See [Install](install.md).

### Does it work on other systems?

The suite is made for PlayStation 5 hardware running Bazzite.

### How do I check a download?

Every release comes with a `SHA256SUMS` file, and the lines on the Install page check the download with it before
they unpack it. See the [security policy](SECURITY.md#verifying-a-download).

### Is it open source?

Yes. The code of every app is on [GitHub](https://github.com/RobertoTorino/bazzite-console), under the licenses
below.

### What does the suite know about me?

Nothing it sends anywhere: no accounts, statistics or crash reports. What goes over the network, and when, is on the
[Privacy](privacy.md) page.

### Where do I get help?

Open an issue on [GitHub](https://github.com/RobertoTorino/bazzite-console/issues). For a security problem,
use **Security → Report a vulnerability** instead, as the [security policy](SECURITY.md) says.

## License

GPL-3.0-or-later, except Remote Play, which is AGPL-3.0 (its protocol code comes from chiaki-ng). Each app has its
own `LICENSE`. The icons were made with generative AI tools and edited by hand in Photoshop, and the music of the
video tours with generative AI tools. The portal's welcome sound was made in Nexus Remix Studio, with a voice generated by Nexus TTS. The other sounds were made without AI: the portal's intro sound by its own code, from
arithmetic alone, and the portal's sound on a controller action and DatStation's quiz music by hand in Audacity. All
are under the license of the app or tool they come with, like its code.

</div>
</section>
