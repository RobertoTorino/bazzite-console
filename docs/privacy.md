<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<span class="page-icon">:material-eye-off-outline:</span>

# Privacy

The Bazzite Console Suite collects nothing about you. It has no accounts, no statistics, no analytics, no crash
reports and no advertising, and there is no server of ours that anything could be sent to. What the apps store
stays on the console, in your home folder. The few things that go over the network are listed below, with when and
to whom.

Everything about the suite itself is public: the code, the plans and the issues are on
[GitHub](https://github.com/RobertoTorino/bazzite-console). Personal data is the exception, and the apps keep
it out of what they show and save where they can.

## What goes over the network

Each request names the app and its version (for example `ps5-shadps4-manager/1.0.0`) and nothing about you.
The servers see your IP address, as any website you open does.

**GitHub** (`github.com`, `api.github.com`, `raw.githubusercontent.com`), for releases:

- The [portal](portal.md) downloads the apps you install from the suite's releases, and at start asks whether a
  newer portal release is out.
- The shadPS4, RPCS3, PPSSPP, PCSX2, Vita3K and Xenia Managers ask for the emulator's newest release when their
  window opens, and download the release you install.

**Sony** (`fwupdater.dl.playstation.net`): [Controller](apps/controller.md) asks Sony's update server for the
controllers' latest firmware (at most once a day), and downloads the firmware when you update a controller.

**PyPI**: installing an app downloads its Python packages from PyPI.

**Only when you ask for it:**

- [Remote Play](apps/remoteplay.md) talks to your own consoles on your own network, and to PlayStation (PSN) only
  to find your account ID; the sign-in happens in your browser. Its window and log mask your account ID, online ID
  and the consoles' addresses.
- [XBOX Remote Play](apps/clb.md) talks to Microsoft's XBOX services when you sign in, refresh, wake a console or
  stream; the sign-in happens in your browser, with a device code. It keeps the account's refresh token and its
  settings in `~/.config/ps5-xbox-remoteplay`. Its log masks the account's tokens, your gamertag, the consoles' IDs
  and network addresses.
- [shadPS4 Manager](apps/shadps4.md): shadPS4 signs in to the shadNet server you set, with the account you set.
  shadPS4 keeps the password as it is and shadNet sends it unencrypted: use one you use nowhere else.
- [SFTP Tools](apps/sftp.md) connects only to the host you enter.
- [Bazzite DatStation](apps/datstation.md) loads the PlayStation Blog's feed on its news page.
- [Bazzite Test](apps/bazzite.md): its network tests resolve and ping `google.com` and ask `www.example.com` for a
  page header; the optional speed test uses Ookla's servers.
- The [portal](portal.md) shows the weather in its header only for a place you choose in its Settings: the name
  you search for, then that place's coordinates every 30 minutes, go to Open-Meteo
  (`geocoding-api.open-meteo.com`, `api.open-meteo.com`), which needs no account.
- [Webcam](apps/webcam.md) downloads a camera's firmware from GitHub (`raw.githubusercontent.com`) only when you
  ask it to.
- The managers' **Steam artwork…** takes the covers of your games from SteamGridDB, with the API key you enter.

Links you click (a release page, the wiki, a PlayStation page) open in your browser, under that site's own privacy
terms.

## What stays on the console

Each app keeps its settings in `~/.config/<app>` and its data and logs in `~/.local/share/<app>`. Nothing of it is
uploaded. Uninstalling with `--purge` removes the settings and logs too.

Some of it can identify you: host and user names, serial numbers, MAC and IP addresses, account IDs. Where an app
shows or saves such details, it masks them: [Bazzite Test](apps/bazzite.md) in saved logs (**Settings › Privacy**),
[Remote Play](apps/remoteplay.md) in its window and log, and [XBOX Remote Play](apps/clb.md) in its log. Before
you share a log or a screenshot, for example in an issue, look it over for anything you would rather keep to
yourself.

## This wiki

The wiki is served by GitHub Pages, so GitHub's
[privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)
applies to your visit, as it does on any GitHub page. The wiki itself adds nothing: no analytics and no cookies,
and its fonts and scripts come from the wiki, not from other sites. The theme keeps a little state, such as the
search, in your browser's session storage, which stays in your browser and is gone when you close it.

## A privacy problem

To report one, open an issue on [GitHub](https://github.com/RobertoTorino/bazzite-console/issues), or, when it
should not be public before it is fixed, use **Security → Report a vulnerability** as the
[security policy](SECURITY.md) says. Leave personal data out of the report.
