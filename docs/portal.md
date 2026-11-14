<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Bazzite Console Suite](assets/portal/bazzite-console-suite.webp){ .app-logo }

# Portal

The Bazzite Console Suite's front door: one fullscreen view that installs, opens, updates and removes the suite's
apps, for a TV and a controller as much as for a desk, as Steam's Big Picture is for Steam. It works with the
keyboard, the mouse or a controller alike. The [Portal Tour](portal-tour.md) shows it in a video.

The portal opens with a short animated intro, about three seconds, with its own sound: the suite's icon and its
name, **BAZZITE CONSOLE SUITE**, before the view appears. Press any key, click, or press any button on the controller
to skip it.

**The header**: the suite's icon, as large as a tile's (click it to open this wiki), its name with the version,
a small **i** that says where the apps install from, and a line that says in a few words what the open category is
for, with **☰ Settings** at the top right and, in the corner beside it, **✕ Exit**, which closes the portal. Under
them, in a row, eleven big symbols. Four act on the apps: **Refresh** (two
circling arrows: look again at which apps are installed), **Sys info** (a chip), **Install All apps** (a grid of
apps with an arrow down) and **Install All updates** (a circular arrow around an arrow down). Seven are shortcuts
to what is outside the suite: **Files** (a folder), **Steam**, **YouTube** (a screen with a play triangle),
**Bluetooth**, **Network**, **Volume** (a loudspeaker) and **Screen** (a screen on its foot). Each is described
below. Hover a symbol to see what it does. The one with the focus is framed in silver, as a tile is; a symbol that
has nothing to do is grayed out. On a screen 1280 pixels wide the symbols are drawn smaller when the row would not
fit otherwise. On the right of the symbols, how many apps are installed, and under it the status, a line each: the
CPU's and the GPU's load and temperature (**CPU 12% 54°C | GPU 3% 61°C**), the date and the time (**Thursday
11/5/26 | 07:44 PM CEST**) and, when you have chosen a place on the Settings page, the weather there (**Amsterdam
8°C Partly cloudy**, after its symbol). The line at the bottom says what the keys and the controller's buttons
do.

**Bazzite Test** is always installed with the portal; every other app is optional. Below the header is a strip
with a name for each [category](apps/categories.md): Sustainable, Gaming and Utilities (Graphics joins them once it has an app), and beside it
the notice of updates. Each app is a large tile under its category, left to right in the order of `apps.toml`
and as many to a row as the screen fits; Bazzite Test is always the first tile on Sustainable. The tile with the
focus is framed in silver; move it with the arrow keys, the d-pad or the stick, or point at a tile with the
mouse:

- **The icon**, its category's, drawn from a 512 px picture so it stays sharp on a 4K screen. It is gray while
  the app is not installed. Hover over the tile to see what the app does, its state and the release this portal
  pins.
- **The name** of the app.
- **Press the tile** (click it, Enter, or A on the controller) to open the app. Pressing a tile that is not installed offers to install it. An app that is open
  already, also one behind the portal or minimized, comes to the front instead, without the board warning again;
  that needs KDE's desktop (KWin), which Bazzite's desktop is.
- **Update** (a right click, or Y on the controller): installs the tile's update or reinstall at once; an app
  that changes the board asks first. While a newer portal is out, they update the portal instead (see
  **Updates** below). A right click on a tile with nothing to update opens its menu.
- **The tile's menu** (the Menu key or M; on the controller the left button of the four, X on an XBOX controller
  and Square on a PlayStation one) holds every action: **Open**, **Install** (an arrow into a tray; **Update**, in red, when an update is waiting;
  **Reinstall** for an installed app, in red with a circular arrow when its version is unknown) and
  **Uninstall** (a bin). What cannot be done now is grayed out. Bazzite Test has no Uninstall: it is removed
  together with the portal.
- **A red dot** in the icon and **Update** under the name: an update is available.
- **A red circular arrow** in the icon and **Reinstall needed** under the name: reinstall the app. It is
  installed, but not by this portal (by hand, or under an earlier name of the app), so the portal does not know its
  version. Reinstall in its menu installs the version this portal pins. An app installed from a checkout of the
  repository without its version recorded shows it too.
- **changes the board**, in orange under the name, for apps that change how the console's system runs. Hover
  over the tile: the popup says what the app touches, what stays after a reboot or a power off and how the change
  is undone, the same text that opens the app's chapter of this wiki.
- **App not available**, in red under the name: the release of this app was withdrawn because of a problem
  (privacy, security or another reason; hover over the tile to read which). It cannot be installed or opened. When
  it is installed, the portal says so at start and removes it with the app's own uninstaller in a terminal. If that
  fails, Uninstall stays in its menu, to try again.
- **Installing…**, **Removing…** or **Downloading…** in blue under the name while that runs on the app; a download
  counts its megabytes as it comes in (**Downloading… 40 MB**).

**The categories.** The line under the title says what the open category is for, and [The apps](apps/index.md)
lists the apps by category. Click a name in the strip, press LB or RB on the controller, or Page Up and Page Down
on the keyboard, to change the category. The portal always opens on the first one, Sustainable.

| Keyboard | Controller | Mouse | Does |
|---|---|---|---|
| Arrow keys | D-pad or left stick | Point | Move the focus between the tiles, the symbols and the notices |
| Enter | A | Click | Open the app, press a symbol, open a notice |
| U | Y | Right click | Update: the portal while a newer one is out, else the tile's app (update or reinstall) |
| Menu key, M | X (Square on a PlayStation controller) | | The tile's menu: Open, Install, Update, Reinstall, Uninstall |
| Page Up, Page Down (or Q, E) | LB, RB | Click a name | The category before and after |
| S | ☰ (Start) | Click ☰ | The Settings page, and back from it |
| K | R3 (the right stick pressed) | | Bazzite's on-screen keyboard (Plasma Keyboard), and away again; R3 works in a question or the file dialog too |
| Escape | B | Click ✕ | Close a menu or a question; on the Settings page, go back to the apps; else exit the portal |

**Exiting.** The **✕** symbol in the top right corner closes the portal, and so do B and Escape with no menu,
question or Settings page open. The portal closes at once, without a question. Only while a download or an install
runs it asks *Do you really want to exit the Portal?* first, and says what exiting does to it: the download stops,
or the installer finishes in its terminal window without the portal recording it. **No** has the focus there: move
to **Yes** with the arrow keys, the d-pad or the stick, and press Enter or A; B or Escape answers No.

**Questions.** In a question (Yes and No, Install and Cancel) the arrow keys, the d-pad and the stick move between
the buttons, and Enter or A presses the one with the focus.

**The on-screen keyboard.** R3 shows Plasma Keyboard, the desktop's virtual keyboard, so you can type with the
controller, for example a file name when you choose a wallpaper. Bazzite shows it only after touch or pen input,
which a controller is not, so while it shows the portal sets it to show for any input, and R3 again (or closing the
portal) hides it and sets your own choice back. When no virtual keyboard is chosen for the desktop, R3 says where to
choose it: System Settings, Keyboard, Virtual Keyboard, Plasma Keyboard.

The controller is read with [pygame-ce](https://pypi.org/project/pygame-ce/), which the portal's installer adds to
the suite's venv; it takes any controller SDL knows (XBOX, PlayStation, Switch Pro and most others). The portal
listens to the controller only while its own window has the focus, so a game's input never moves it. Without a
controller, the keyboard and the mouse work as always.

**The touchpad as the mouse.** On a DualShock 4, a DualSense or a DualSense Edge the touchpad moves the mouse
pointer, as Steam does for the Steam Controller: slide a finger to move it, press the pad to click, and press it
with two fingers on it for a right click. **Touchpad** on the Settings page sets how fast the pointer goes. Like the
rest of the controller it works while the portal has the focus, in its menus and questions too. The portal makes a
mouse of its own for it (Wayland lets no program move the pointer), which the desktop lists as **Bazzite Console Suite
touchpad** while the portal runs; Bazzite gives you the access it needs. A controller Steam Input owns has the
touchpad of Steam's desktop layout instead.

**The Steam Controller, and any controller Steam Input owns.** While Steam runs, it takes the controllers it has
Steam Input on for (always the Steam Controller and a Steam Deck's own controls): outside a game, its desktop layout
turns their buttons into keys and the mouse, and the portal sees only those keys. By default that layout gives the
d-pad the arrow keys, A Enter and B Escape, but LB, RB, R3, the back buttons and others have no key, so they do
nothing in the portal. There are two ways to get every button:

- **Start the portal from Steam.** In Steam, choose **Games**, **Add a Non-Steam Game to My Library**, and pick
  **Bazzite Console Suite** (or browse to `~/.local/bin/bazzite-console-suite`). Started from Steam, the portal reads
  the controller as an XBOX controller, with the buttons in the table above. Steam's controller settings for that
  entry can give the back buttons, the touchpads and the other extras any button or key you like.
- **Give the buttons keys in the desktop layout.** In Steam, open **Settings**, **Controller**, **Desktop Layout**
  (Edit), and set LB to Page Up, RB to Page Down, Y to U, X to M, ☰ to S and R3 to K (the keyboard column of the
  table). The back buttons can take any of these keys too. The layout is Steam's and applies to every program
  outside a game.

- Install, update and uninstall run **the app's own installer** in a terminal window, which opens over the portal,
  because installers may ask for the sudo password and print what they do. The portal watches for the result and
  refreshes. A terminal whose installer ended well closes by itself; one that failed stays open with what happened
  until you press Enter.
- Apps that change how the console's system runs (Fan Control's thermal guard, Webcam's camera rule, the SSH server
  of SFTP Tools) are marked **changes the board**. The portal warns before installing or opening them,
  and the tile's popup says what each one changes and how that is undone.
- Each portal release pins one tested release of every app in [`apps.toml`](https://github.com/RobertoTorino/bazzite-console/blob/main/portal/apps.toml). The portal downloads
  exactly those tarballs from the suite's GitHub releases and checks each against the SHA-256 pinned there, or
  against the release's `SHA256SUMS` until one is pinned. Then it unpacks the tarball without ever writing
  outside its folder.
- **Updates:** a red dot marks every app whose installed version differs from the one this portal pins; Update in
  its menu installs the pinned version. An app installed from a checkout of the repository counts as well:
  the portal records the checkout's version of it and compares that with the one it pins. A portal that runs from a
  checkout shows what it installed from there as installed, whatever it pins. The red notice beside the category
  strip counts them and the apps that need a reinstall, for example **● 2 updates, 1 reinstall**. Press it to list
  each one with its category and versions, and choose one to go to its tile. A category with such an app shows
  their number in red after its name, so none goes unseen on a category that is not open. Press Y or right-click
  a tile with an update to install it.
- **Portal updates:** newer app versions come with a newer portal release. At start the portal looks for one on
  GitHub; when there is one, an orange **PORTAL UPDATE AVAILABLE** shows under the name on the intro, and an
  orange **UPDATE AVAILABLE, PRESS Y TO UPDATE** beside the category strip. Its tooltip says what the release
  brings, for example **Portal 1.0.1: updates Fan Control and Remote Play**, with each app's old and new
  version. Press Y, right-click a tile, or click the banner (Enter or A with the focus on it) to update: the portal
  downloads the release, checks it against the release's `SHA256SUMS`, and runs its `install.sh` in a terminal,
  as your own user. The banner says **DOWNLOADING THE UPDATE…** and then
  **INSTALLING THE UPDATE…**. When the installer has ended well, the portal starts again as the new version, and
  the installed apps it updates show the red dot. When it fails, the terminal stays open with what happened, and
  Y tries again. While an app installs, the portal update waits for it. A release built again under the portal's
  own version is offered too (the tooltip says **a new build of this version**): the installer keeps the checksum
  of the tarball it installed from (`build.sha256` beside the program, when the tarball is next to the unpacked
  folder, as the install steps and the portal's own update leave it), and the portal compares it with the newest
  release's. A portal installed from a checkout is not offered the release of its own version (it would replace
  the checkout's portal); a newer version still is. The download is kept in `~/.local/share/bazzite-console-suite/state/portal-update/` until the next one.
- **Restart: portal x.y.z is installed:** a portal window that is open while you install a newer portal by hand
  (its `install.sh` in a terminal) keeps running the old one, with its old app versions, and starting the portal again only brings that window to the
  front. When you come back to the window, it sees the newer portal and shows this red button: click it to restart
  into the new portal, which then shows the red dot on the apps it updates. While an app installs or uninstalls,
  the button waits for it to end.
- **Installed apps**, on the right of the symbols: how many of the portal's apps are installed, for example
  **12/17 installed**. An app that is not available any more is not counted.
- **The status**, under it, in three lines. The first: the CPU's load and temperature and the GPU's load and
  temperature, read every two seconds. The second: the day, the date (month/day/year) and the time with its time
  zone, read every second; **Clock** on the Settings page sets how the time reads. The third, with a place chosen
  under **Weather** on the Settings page: the weather's symbol, the place, the temperature and the sky; without a
  place there are two lines. Nothing is read while the portal is minimized. The load is the share of the last two
  seconds.
  What the system does not report is left out of the line.
- **Install All updates**, a symbol at the top, enabled when the notice names any app; a red badge on it says how
  many, and its tooltip what it does.
  Click it to install them all, updates and reinstalls, one after the other. The portal asks once, with the list, and warns when one of them changes
  the system. Each app's installer runs in its own terminal, as a single install does. When one asks for your
  password, type it in that terminal: the next one waits until it has ended. While it runs, its badge shows which
  one of how many it is at, for example **2/5**. An install that fails does not stop the others; at the end the portal
  names those that failed, and Install in their tiles' menus tries again. **Refresh**, while it waits for a
  terminal that was closed, can stop waiting, and then stops the rest too.
- **Install All apps**, a symbol at the top, enabled when the open category has apps that are not installed yet
  (its tooltip says how many). Click it to install them, one after the other, the same way as **Install all updates**: one question with the
  list and the board warning, each installer in its own terminal, its badge showing which one of how many. It is
  disabled once every app of the category is installed. A portal installed for the first time fills a category with
  one click.
- **Files**, a symbol at the top: opens the desktop's file manager (Dolphin on Bazzite's KDE Plasma) on your home
  folder.
- **Steam**, a symbol at the top: opens Steam, or brings its window to the front when it runs already.
- **YouTube**, a symbol at the top: opens YouTube fullscreen in Brave Browser's kiosk mode; Alt+F4 closes it. Brave
  Browser must be installed as a Flatpak (`com.brave.Browser`, from Bazzite's software store or with
  `flatpak install flathub com.brave.Browser`); without it the portal says so and opens nothing.
- **Bluetooth**, **Network**, **Volume** and **Screen**, four symbols at the top: open the desktop's Bluetooth
  settings (pair or remove a controller, a headset), its network settings (the connections, Wi-Fi), its sound
  settings (the volume, the output and the input) and its display settings (the resolution, the refresh rate, the
  scaling). On KDE Plasma that is System Settings on that page, on GNOME its Settings.
- **✕ Exit**, the symbol in the top right corner: closes the portal, as B and Escape do. See **Exiting** above.
- **☰ Settings**, the symbol at the top right, or the ☰ button on the controller (Start, Options on a PlayStation
  controller): the Settings page, in place of the category strip and the tiles, under the same header. It holds
  the seven settings below, each a pill with a short line beside it; on a small screen the page scrolls, following
  the focus. Move between them with the arrow keys, the
  d-pad or the stick, and press A or Enter to change one. B, Escape or ☰ again goes back to the apps.
- **Icons on Desktop**, on the Settings page (Yes or No; click it to switch): on, every installed app has an icon on the Desktop; off, only the
  portal's icon is there and you start the apps from the portal. The apps stay in the app menu either way, so KDE's
  search and Steam's **Add a Non-Steam Game** still find them. The first time the portal starts with app icons on
  the Desktop, it asks whether to keep them. While the switch is off, the portal removes the icons the apps'
  installers put there, at start and after each install. It only touches the icons of the suite's apps, never its
  own or anything else on the Desktop.
- **Sound**, on the Settings page (Yes or No; click it to switch): the intro plays its sound when the portal opens,
  and every action gives a short sound: each move and button on a controller, each key that acts (the arrow keys,
  Enter, Space, Escape, Tab, Page Up and Page Down, Q, E, U, S, K, M and the Menu key) and each click on a tile, a
  symbol, a pill, a button, a category or a menu entry. Any controller works, also one Steam turns into keys. A key held down
  sounds once, and typing in a text field stays silent. No switches both off. The portal remembers the choice.
  When the console has no audio output, the pill says No and is disabled, and the portal stays silent.
- **Theme switcher**, on the Settings page, showing the theme; click it for the next one: the look of every app in the
  suite. **Gunmetal** (dark, cool blue-gray, the default), **Silver** (light) or **Warm** (dark warm gray with a
  bronze accent). It is one choice for all the apps, kept in `~/.config/bazzite-console/theme`: the portal shows it at
  once and stays open, and each app takes it the next time it starts.
- **Wallpaper**, on the Settings page: a picture behind the portal, none until you choose one, and seen through the
  pills that are not active. Click the pill, then
  **Choose a picture…** for your own (**Custom**), **Example wallpaper** to see how one looks with the picture that
  comes with the portal (**Example**), or **No wallpaper** for none. Your picture must be a PNG, JPEG or WebP of at least 1920 x 1080 pixels, in 16:9 (1920 x
  1080, 2560 x 1440, 3840 x 2160); the portal refuses another and says why. It fills the window, under a veil of the
  theme's color so the text stays readable. **Transparency**, a slider in the same menu, sets that veil from 0 to
  90 % (60 % at first): move it up for a dark or busy picture, so the icons stand out, down to see more of the
  picture. The window changes while you move it, and the portal remembers it. The portal keeps a copy in
  `~/.local/share/bazzite-console-suite/state/`, so the original may be moved or deleted; the portal's `--purge`
  removes it. The menu also lists the last 10 wallpapers you chose, newest first, under **Used before**: click one to
  use it again. The portal remembers only where each picture was (in `wallpapers.json` in the same folder), so one
  moved or deleted since shows as not found until it is back.
- **Clock**, on the Settings page, showing **12 h** or **24 h**: how the time in the status reads. Click it for
  its menu: **12-hour clock (AM/PM)** or **24-hour clock**, **Seconds** on or off, and the time zone: **the system's
  own** (the system's, as at first), **CET** (Central European Time, CEST in summer) or **UTC**. The date follows
  the zone too. The portal remembers the choice.
- **Weather**, on the Settings page, showing the place or **None**: the weather in the status at the top, from
  [Open-Meteo](https://open-meteo.com/), free and without an account. Click it, then **Choose a place…**: type a
  city or town (R3 brings the on-screen keyboard), **Search**, pick the right one from the list and **Use this
  place**. Its symbol (sun or moon, clouds, fog, rain, snow or thunder), its name, the temperature and the sky then
  show as the status' third line, under the date and the time; hover over it for the wind and the humidity too.
  The weather comes again every 30 minutes while the portal is not minimized, and **Update the weather now** asks at
  once. When Open-Meteo cannot be reached, the last weather stays and its tooltip says why. **No weather** removes
  it, and nothing goes to Open-Meteo any more. Until you choose a place nothing is sent; see
  [Privacy](privacy.md).
- **Touchpad**, on the Settings page, showing the speed: how fast the touchpad of a DualShock 4 or a DualSense moves
  the mouse pointer. Click it for the next speed: 50, 75, 100 (the normal speed, at first), 125 and 150 %, then 50
  again. The new speed applies at once, and the portal remembers it.
- **Sys info**, a symbol at the top: a small window with what the system reports about the console: the mainboard, the
  BIOS (with UEFI and Secure Boot), the CPU (model, cores and threads online, top clock, microcode), each GPU (name,
  driver, VRAM, shared memory, clock levels, VBIOS, PCIe link), the memory, the drives with the free space in your
  home folder, the displays (each output, the monitor's name and its preferred mode), the sound cards, the network
  adapters and Bluetooth controllers (driver and link), the USB devices, the input devices (keyboards, mice and
  controllers, each with the bus it is on: USB, Bluetooth, PS/2), the sensors (temperatures, fan speeds and
  the GPU's power at that moment) and the OS (version, Bazzite image, kernel, desktop). It is read each time the
  window opens; what a system does not report is left out. **Copy** puts it all on the clipboard as text, for an
  issue or a forum post. It holds nothing personal: no host or user name, no serial numbers, no MAC or IP
  addresses.

## Install

[Install](install.md) has the lines to paste into a terminal: they download the portal's release, check it and run
its `install.sh`, as your own user. Later versions install from the portal itself: press Y when it says **UPDATE
AVAILABLE** (see **Portal updates** above).

What it installs:

| What | Where | Why there |
|---|---|---|
| The portal, its `apps.toml` and the shared code it was tested with | `~/.local/share/bazzite-console-suite/portal` | In your home folder: the portal needs no root |
| What the portal remembers: the apps it installed and their releases, the wallpaper, a downloaded portal update | `~/.local/share/bazzite-console-suite/state` | Apart from the program, so an update of the portal keeps it |
| Bazzite Test (bundled in the portal release) | `/opt/bazzite-test`, through its own installer, which asks for the sudo password | Its tests run as root, so its test files are root-owned |
| The suite's shared venv with PyQt6 | `~/.local/share/bazzite-console-suite/venv` | One copy of the ~100 MB of Qt for all suite apps |
| Launcher, menu entry, Desktop icon | `~/.local/bin/bazzite-console-suite`, `~/.local/share/applications/`, the Desktop | The portal's icon is the one way in; the apps' own icons are optional (**Icons on Desktop**) |

Uninstall: remove the apps first, each from its tile's menu, then
`~/.local/share/bazzite-console-suite/portal/install.sh --uninstall`. This removes the portal and keeps its
settings and what it remembers; add `--purge` to remove those too. Bazzite Test stays until you remove it with its own installer:
`~/.local/share/bazzite-test/app/install.sh --uninstall`.

### What stays after an uninstall

Uninstalling an app removes the app. Two things can stay: **changes it made to the system**, which you undo in the
app before you uninstall it, and **your settings and results**, which `--purge` removes.

| App | Still active after its uninstall | Undo it with |
|---|---|---|
| SFTP Tools | An SSH server you started: `sshd` enabled at boot, and the firewall's rule for SSH | Stop the server in the app; review the firewall's rule yourself |

Fan Control's uninstall removes its thermal guard, and Webcam's removes its camera rule.

Settings live in `~/.config/<app>`, data and logs in `~/.local/share/<app>`. Each app's
`install.sh --uninstall --purge` removes them.
