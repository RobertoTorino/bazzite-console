<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Bazzite DatStation](../assets/datstation/ps5-datstation.webp){ .app-logo }

# Bazzite DatStation

Bazzite DatStation is the PlayStation knowledge part of the DatStation Android app, on **Bazzite**. A front page
of tiles opens a PlayStation quiz against the clock, the history of every PlayStation console, every system
software release, the region codes explained, Sony's user guides and the latest PlayStation news, and keeps your
quiz scores and trophies.

The app does not change how the console runs. Nothing is installed system-wide and nothing is layered with
`rpm-ostree`.

## What it needs

- Python 3.10 or newer: Bazzite ships `python3`. The installer makes the app's own virtual environment with PyQt6
  in it (the wheel bundles Qt, with Qt Multimedia for the quiz music) and pygame-ce for the controller.
- A network connection for PS News and for the links to PlayStation's pages. Everything else works offline: the
  questions, the history, the system versions and the region codes ship with the app.
- For Game Mode: Steam, for the non-Steam game the app adds.

## Install

Install it from the portal (the **Gaming** tab), or from a checkout of the repository:

```bash
apps/datstation/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
apps/datstation/install.sh --no-desktop-shortcut   # without the Desktop icon
apps/datstation/install.sh --uninstall             # remove it; keeps its settings and scores
apps/datstation/install.sh --uninstall --purge     # also remove its settings and scores
```

Run it as your own user, without `sudo`. It installs:

- `~/.local/share/ps5-datstation/app`: the app, and `venv` next to it with PyQt6.
- `~/.local/bin/ps5-datstation`: the launcher, which starts the window.
- An app menu entry ("Bazzite DatStation") and an icon on the Desktop.

Install it again to update.

**Steam Game Mode:** in the app, open the **Menu** beside the title and choose **Add to Steam (Game Mode)**. It
adds the app as a non-Steam game for every Steam user on the console, with artwork drawn from the app's icon, and
the title line shows **In Steam**. Steam closes while its shortcut file changes and starts again afterwards, so do
this from Desktop Mode; from Game Mode the app asks you to switch. **Remove from Steam** takes it out again.

## Using it

The first line shows the logo, the name and version, whether the app is in Steam, and the **Menu** (Add to Steam,
Remove from Steam, Scores & Trophies, the project page, About). Under it the front page: four rows of four tiles,
one per feature; the others say Coming Soon and are grayed out. A tile opens its page; **Back** returns to the
tiles.

The arrow keys move between the tiles, and Enter or Space opens the one in focus. Escape, or the controller's B
button, closes the active window or dialog. The keys 1 to 4 answer a quiz question.

### PlayStation Quiz

Pick a category (ALL, TRUE/FALSE, PS1 to PS5, PSVITA, PSP, CONTROLLER, GENERAL, DIALOGUE, APPS; the tooltip says
how many questions it has), or the **Quick Quiz**: 6 questions, nothing saved.

A round starts with 42 seconds on the clock. A right answer adds 5 seconds and the question's points (10); a
wrong answer or **Skip** takes 5 seconds. The clock stops while an answer is shown and while the game is paused
(**Pause**, then **Resume**). The right answer turns green, a wrong choice red, and for a wrong answer the right
one is named, with an explanation where the question has one.

The round ends when all its questions are answered, or when the clock runs out. The results show the right and
wrong answers, the time left, the total score with the share of right answers and, for a complete round, a review
with a bronze (50 % and more), silver (75 %) or gold (95 %) star. A round with every answer right is a **Perfect
round**: **Next round** then asks five questions more, with the score and the clock kept. Otherwise **Retry**
starts the category again from zero. **Change** picks another category.

Every finished round of a saved game adds a score to Scores & Trophies; a perfect round adds a Perfect trophy. The
quick quiz adds nothing. The music can be turned off with **Music on / Music off** beside the title; the choice
is kept.

### PlayStation History

Every console since 1994 with its launch year, what it sold and how many titles it had: the PlayStation,
PlayStation 2, Sony PSX, PlayStation Portable, PlayStation 3, PlayStation Vita, PlayStation 4, PlayStation 5 and
the PlayStation Portal. Under the totals, a brief overview of each console's legacy. Click a console's name, in
either list, for pictures of it on the web, in your browser.

### System Version History

The systems on the left, the versions of the chosen one on the right: every system software release with its
release date, its notes and, where the data has them, its region, model, color, size and hardware facts. The
PlayStation 6 entry is a placeholder until there is one.

### Region Codes Explained

Per PlayStation, what the prefix of a title ID says about the market and the publisher (PPSA, ELJM, BCES, SLUS,
...), in a table, and for the PS1 and PS2 what the last digit of the model number says about the region.

### PlayStation User Guides

Opens Sony's online manuals for every PlayStation product (`manuals.playstation.net`) in your browser.

### PS News

The latest announcements from the PlayStation.Blog feed, with their date; a click opens the post in your browser.
**Upcoming Games** and **New Releases** open PlayStation's pages. **Refresh** loads the feed again. Only links to
PlayStation's own sites (`playstation.com`, `blog.playstation.com`, `store.playstation.com`) are opened; anything
else in the feed is blocked and said so in the status line.

### Scores & Trophies

Your best score, the top ten rounds with their category, round and time, and the trophies. **Clear scores** removes
them all, after asking.

## From the terminal

```bash
ps5-datstation              # the window
ps5-datstation --version    # the app's and core's version
```

The window opens once: a second launch (the menu entry, the Desktop icon, the Steam shortcut) brings the open
window to the front.

## Files

- `~/.local/share/ps5-datstation/scores.json`: the quiz scores and trophies.
- `~/.config/ps5-datstation/ps5-datstation.ini`: the window size and the music setting.
- Steam's `userdata/<user>/config/shortcuts.vdf` and `grid/`: the non-Steam game and its artwork, only when you
  choose Add to Steam, and removed again with Remove from Steam.

## Privacy

The app collects no personal data and sends none. It has no accounts, no analytics and no crash reporting. The
only network requests it makes are the ones you ask for: loading the PlayStation.Blog feed on the PS News page
(a plain HTTPS request to `blog.playstation.com`), and opening a PlayStation page or a picture search in your
browser when you click a link. Your scores, trophies and settings stay in the files above, in your home folder,
and go with `--uninstall --purge`. The suite's [Privacy](../privacy.md) page covers all the apps.

## When something does not work

- **"Could not load announcements":** the console has no network, or the feed did not answer. The page says why;
  **Refresh** tries again.
- **"Blocked unexpected link":** a link in the feed points outside PlayStation's sites, which the app does not
  open.
- **No music:** the music needs an audio output and Qt Multimedia, which the PyQt6 wheel brings. Check that
  **Music on** shows beside the quiz title; the quiz plays the same without it.
- **"The launcher ... does not exist" from Add to Steam:** the app runs from a checkout; run `install.sh` first,
  so Steam has a program to start.
- **"Steam did not close":** Steam was asked to close for the change and did not within 30 seconds; nothing was
  changed. Close Steam yourself and try again.
- **Add to Steam from Game Mode:** the app asks you to switch to Desktop Mode; closing Steam from Game Mode would
  end the session.

## Development

The app is the package `datstation/` in `apps/datstation/` (its data in `data/`, the music in `sounds/`), with
`images/` (the icon), `tests/`, `install.sh`, `VERSION`, `CHANGELOG` and `LICENSE`. The quiz engine (`quiz.py`)
and the feed reader (`news.py`) have no Qt in them, so their tests run without a display.

**Security around the build.**

- The app runs as your own user: `install.sh` refuses to run with sudo and installs only into your home folder.
  Nothing runs as root, nothing is layered, no service is installed.
- Its dependencies are PyQt6 and pygame-ce, each pinned to a major version (`PyQt6>=6.11,<7`,
  `pygame-ce>=2.5,<3`) and installed from PyPI into the app's own venv; the installer upgrades them within that
  range on every install, so a security fix reaches the app with the next install.
- The suite's shared code ships with the app, so it runs on the code it was tested with; the launcher puts the
  app folder first on Python's path, so a module in the folder you start it from cannot shadow the app's own.
- The feed is read with Python's standard library over HTTPS and parsed with `xml.etree`; titles are reduced to
  plain text before they are shown. Links are opened only when they are HTTPS on a PlayStation host.
- Only the app's own entry in Steam's shortcut file is added or removed, with Steam closed; the other shortcuts
  stay as they are.
- A release of the suite comes with `SHA256SUMS`; the suite's [security page](../SECURITY.md#verifying-a-download)
  describes how a download is checked.

## License

GPL-3.0-or-later.
