<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Portal

The portal is the suite's fullscreen app library. It installs, opens, updates and removes the suite's apps, with a
controller, the keyboard or the mouse. [Install](install.md) says how to get it.

## The apps

The apps are in three categories, each a tab: **Sustainable**, **Gaming** and **Utilities**
([App categories](apps/categories.md)). The portal always opens on the first one.

Choose an app's tile to open the app, or to install it when it is not installed yet. A tile's menu holds every
action: **Open**, **Install** (or **Update**, **Reinstall**) and **Uninstall**. Installing, updating and
uninstalling run the app's own installer in a terminal window, which may ask for your password. The window closes by
itself when the installer ended well and stays open with the message when it failed.

An app that changes the system says what it changes and asks before it is installed or opened. Bazzite Test is
installed with the portal and cannot be removed from its menu.

## The header

| Symbol | What it does |
|---|---|
| **Refresh** | Looks again at which apps are installed. |
| **Sys info** | Shows the hardware, memory, drives and operating system, as the system reports them. |
| **Install all apps** | Installs every app of the open category that is not installed yet. |
| **Install all updates** | Installs every waiting update, one after the other. |
| **Files**, **Steam**, **YouTube** | Open the file manager, Steam, and YouTube fullscreen in Brave Browser (its Flatpak must be installed). |
| **Bluetooth**, **Network**, **Volume**, **Screen** | Open that page of the desktop's settings. |
| **☰** | Opens Settings. |
| **×** | Closes the portal. |

Beside the symbols the header shows how many apps are installed, the processor's and the graphics chip's load and
temperature, the date and time, and the weather once you chose a place.

## Updates

At every start the portal looks for a newer portal on GitHub. An orange banner says so; click it or press **Y** to
download, check and install it. A newer portal is how newer versions of the apps arrive. A red dot marks every tile
with an update, a category's name counts them, and the red notice beside the tabs lists them all.

## Settings

Press **☰**, or **Start** on the controller.

| Setting | What it does |
|---|---|
| **Icons on Desktop** | An icon on the Desktop for every installed app, or only the portal's. The apps' menu entries always stay. |
| **Sound** | The intro's sound and a short one for each action, on or off. |
| **Theme** | The look of every app in the suite: Gunmetal, Silver or Warm. A click takes the next one and the portal stays open; each app takes it the next time it starts, the portal too. |
| **Wallpaper** | A picture behind the portal: your own, one used before, the portal's example, or none, and how much of it shows through. Your own must be a PNG, JPEG or WebP of at least 1920 x 1080 pixels in 16:9. |
| **Clock** | 12 or 24 hours, the seconds and the time zone. |
| **Weather** | The place whose weather the header shows, from Open-Meteo. |
| **Touchpad** | How fast a controller's touchpad moves the mouse pointer. |

## Controls

| Controller | Keyboard and mouse | What it does |
|---|---|---|
| D-pad or left stick | Arrow keys | Moves between tiles. |
| **A** | **Enter** or a click | Opens the app, or offers to install it. |
| **X** | **Menu** key or a right click | Opens the tile's menu. |
| **Y** | Right click on a tile with an update | Updates the app, or the portal when a newer one is out. |
| **L1** and **R1** | A click on a tab | Changes the category. |
| **Start** | A click on **☰** | Opens Settings. |
| **R3** | | Shows or hides the on-screen keyboard. |
| **B** | **Escape** | Goes back, or closes the portal. |
| Touchpad | | Moves the mouse pointer. |

The portal closes at once when it is idle and asks first during a download or an installation.
