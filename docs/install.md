<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Install

You install one thing: the **portal**. It is the suite's app library, and it installs every other app for you, each
with one click. The many other downloads on GitHub are those apps; you never need to download them yourself.

## What you need

- A PlayStation 5 running Bazzite, in Desktop Mode.
- An internet connection.
- Your own user account. Do not use `sudo`: the portal installs into your home folder.

## Install the portal

1. Open **Konsole**, the terminal, from the app menu.
2. Copy the block below, paste it into Konsole (**Ctrl+Shift+V**) and press **Enter**.

    ```bash
    mkdir -p ~/Downloads/bazzite-console && cd ~/Downloads/bazzite-console &&
    curl -fLO https://github.com/RobertoTorino/bazzite-console/releases/download/{{ portal_tag }}/{{ portal_tag }}.tar.gz &&
    curl -fLO https://github.com/RobertoTorino/bazzite-console/releases/download/{{ portal_tag }}/SHA256SUMS &&
    sha256sum --check SHA256SUMS &&
    tar -xzf {{ portal_tag }}.tar.gz &&
    ./{{ portal_tag }}/install.sh
    ```

    It downloads the portal, checks that the download is intact, unpacks it and installs it, together with Bazzite
    Test, the suite's first app. This takes a minute or two. It ends with **Installed.**

3. Start **Bazzite Console Suite** from the app menu or from its icon on the Desktop.

If a line fails, nothing after it runs: read its message, fix what it names (most often the internet connection) and
paste the block again.

Prefer the browser? The same two files, `{{ portal_tag }}.tar.gz` and `SHA256SUMS`, are on the
[portal's release page](https://github.com/RobertoTorino/bazzite-console/releases/tag/{{ portal_tag }}). Extract
the archive and run `install.sh` in the extracted folder.

## Install the apps

In the portal, pick a category, choose an app's tile and confirm. The **Install all apps** symbol in the header
installs every app of the open category at once. [Portal](portal.md) describes the rest.

## Update

The portal looks for a newer portal at every start and says so in an orange banner: click it, or press **Y** on the
controller. It downloads the new portal, checks it, installs it and starts it. A newer portal brings the newer apps:
a red dot marks each tile with an update, and **Install all updates** installs them all.

## Uninstall

Remove the apps first, each from its tile's menu (**Uninstall**). Then remove the portal in Konsole:

```bash
~/.local/share/bazzite-console-suite/portal/install.sh --uninstall
```

Add `--purge` to remove the portal's settings too. Bazzite Test stays until you remove it with its own installer:
`~/.local/share/bazzite-test/app/install.sh --uninstall`.

## After a Bazzite update to a new Python

The apps run in Python environments in your home folder. When a Bazzite update brings a new version of Python, such
an environment no longer finds its packages, and the portal and the apps stop starting. Install the portal again
with the block above: it makes the environment again. Then reinstall from the portal any app that still does not
start (**Reinstall** in its tile's menu).
