<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<span class="page-icon">:material-code-braces:</span>

# Development

How the repository is laid out, how to set it up and test it, how the wiki's pictures and tours are made, and how
the versions and releases fit together. How every app is built, and how to add one:
[Architecture and consistency](architecture.md). The development apps, from Nexus Dashboard to Nexus Deps:
[Dashboard](dashboard.md). How a release is made and published: [Releases](releases.md). The repository's settings
on GitHub and Dependabot's pull requests: [GitHub settings](github-settings.md).

## Layout

The repository is the suite. Paths in this wiki are written from the root of the repository.

```
portal/                       the portal: app, apps.toml (the pinned app releases), its tests and install.sh
apps/<name>/                  one folder per app, each with its own VERSION, CHANGELOG, LICENSE and .gitignore
core/bazzite_console_core/    the shared Python package the apps bundle at release time (see bazzite_console_core
                              below)
tools/                        release and CI (build_release, stage_app, check_versions, check_manifest, pin_app,
                              tag-release.sh, ci_state, ci_matrix, check-release.sh, ci-local.sh), all_tests, new_app,
                              sync_icons (the category icons), check_upstream, the screenshot and tour scripts,
                              mkdocs/ (the wiki's hooks and design panel), tests/ and installer-tests/
dev/<name>/                   the development apps, run from the checkout and never released: dev/dash/ is Nexus
                              Dashboard (the door to the others), dev/nrt/ Nexus Release Tool, dev/demo/ Nexus
                              Demo Recorder, dev/itests/ Nexus Installer Tests, dev/sounds/ Nexus Sound Lab,
                              dev/deps/ Nexus Deps, dev/text/ Text to Speech, dev/studio/ Nexus Remix Studio
docs/ mkdocs.yml              this wiki (MkDocs Material)
icons/                        the category icons
DESIGN.md design/colors/      every color of the suite and its samples (tools/make_design.py writes them)
install.sh                    the portal's installer for a checkout
test.sh                       runs every test folder (core, tools, dev/, the portal and the apps)
SYSTEM                        the system the suite is made for: bazzite
TAG_PREFIX                    the prefix of every release tag: ps5-
.github/workflows/            ci.yml (every check), release.yml (a release), docs.yml (the wiki on GitHub Pages),
                              upstream.yml (the weekly upstream check)
```

## Set up and test

```bash
python3 -m venv .venv-linux && .venv-linux/bin/python -m pip install -r requirements-dev.txt

./test.sh                                   # every test folder, offscreen
python3 tools/check_versions.py             # hard-coded versions = VERSION
mkdocs build --strict                       # the wiki
```

The suite is worked on and tested on Bazzite.

### Install from a checkout

To try the portal and the apps as they are in the repository, not as they were released, run `./install.sh` in the
repository's root on a PlayStation 5 running Bazzite, as your own user. It copies the portal into your home folder,
as a release does; the installed portal names the checkout and installs the apps from it, so keep the checkout where
it is. `tools/check-release.sh local` does the same and starts the portal; `release` and `draft` install a published
portal release or the draft of one (`release` takes the draft while the release is not published).

A test cleans up after itself. On a board without the suite, what the test installs is marked as a test's and
removed again when the portal closes: the apps installed during the test, the portal and Board Test. A board that
had the suite installed keeps it, and `--keep` keeps what a test installed.

```bash
tools/check-release.sh status            # what of the suite is installed, and whether a test put it there
tools/check-release.sh restore           # put back the install a test went over, when the test did not
tools/check-release.sh remove            # remove every app, the portal, Board Test and Quickfix; settings stay
tools/check-release.sh remove --purge    # their settings and logs too
```

Nexus Release Tool's **Remove suite** tab runs `remove` in a terminal.

### CI on your own machine

GitHub runs `ci.yml` on every push and pull request: the versions and the portal's manifest, the pytest matrix
(core, tools, every `dev/` app, the portal and every app), the native Rust job for Remote Play, the shell checks
(`bash -n`, shellcheck, line endings, exec bits, the four files of every folder, workflows only at the root), the
installer tests and the wiki build. A release waits for it: a commit CI did not pass gets no release.

A push runs the jobs of what it changed. A first job, `plan` (`tools/ci_matrix.py plan`), compares the push with
the commit before it and names them:

| What changed | What runs |
|---|---|
| A file of a folder with `tests/` (an app, the portal, a `dev/` app) | That folder's tests |
| Anything | The tests of `tools`, which hold the repository's rules, the versions and the shell checks |
| `portal/apps.toml` or `icons/categories.toml` | Also the tests of every folder whose tests read that file |
| An app, a `dev/` app, the portal or a tool | The installer tests that name it, side by side |
| `apps/remoteplay` | Also the native job |
| Anything but Python code | Also the wiki build |
| `core`, a workflow, `tools/ci_matrix.py`, an action or a script the jobs run (`.github/actions/`, `tools/ci-apt.sh`, `tools/ci-qt-libs.sh`, `tools/ci-font.sh`), `requirements-dev.txt` | Every job |
| The local CI (`tools/ci_local.py`, `tools/ci-local.sh`, `tools/ci-local/`) | As any tool: no job on GitHub runs it |

Every job also runs every Monday, with **Run workflow** on the CI workflow's page on GitHub, and when the commit
before the push is not known (a new branch, a forced push). The pytest matrix and the installer tests are read from
the folders, so a new app needs no edit to a workflow: its folder, its installer test and its `install.sh` are in
CI at once.

[All tests](all-tests.md) lists every test with what it checks and the time it took, and the installer tests.
`tools/all_tests.py` writes that page (`ALL-TESTS.md` at the root) from the tests themselves:

```bash
python3 tools/all_tests.py            # the list as the tests are now; the times stay as they were
python3 tools/all_tests.py --run      # run every test folder first, for each test's cases and time
python3 tools/all_tests.py --check    # is the list what the tests are? (a test of tools asks this in CI)
```

Nexus Release Tool's **Commit** runs the first form before it adds the changes, so the list follows the tests by
itself. By hand, run it after adding, renaming or removing a test; CI fails otherwise.

`./test.sh` runs every test folder in one venv that holds everything, on whatever Python your system has. GitHub's
CI runs each job on Python 3.12 with only that job's own requirements, so a test can pass here and still fail there:
a Python 3.13 function, or a package only the full venv has. `tools/ci-local.sh` runs the jobs of `ci.yml` the way
GitHub does, in a container (podman, which Bazzite has, or docker):

```bash
tools/ci-local.sh                            # the jobs of what changed since origin/main, under a minute
tools/ci-local.sh --all                      # every job, about two minutes once the image is built
tools/ci-local.sh shell pytest/tools         # some jobs; a matrix job by its value, pytest for all of them
tools/ci-local.sh --list                     # the jobs
```

It reads the jobs from the workflow itself and runs its plan job as GitHub does, against what differs from
`origin/main`, so it runs the same jobs the push will, and a new app needs no change. The first run builds the image from `tools/ci-local/Containerfile` (Python 3.12 and the packages GitHub's
runner has) and Remote Play's FFmpeg; both are kept, with the venvs and the logs, in
`~/.cache/bazzite-console-ci-local`. FFmpeg is built again when `apps/remoteplay/native/ffmpeg/build.sh` changes, as GitHub's cache
is keyed on that file. It works on a copy of the checkout with every change staged, as the commit will
have it. The copy is named as the checkout, as GitHub's is named after the repository. One run goes at a time on a
computer: a second one, from a terminal or Nexus Release Tool's Push, says that another run is going and waits until
it ends, as the two would share the venvs and the logs. Within a run the jobs go several at a time: half the cores, fewer when the free memory is short (one job per
1.5 GB, at least two; `--workers N` sets the number yourself), except a job that compiles (`native`, with
cargo): it runs after the others, alone, since its compilers need the computer's memory for themselves. The push commands Nexus Release Tool shows run it first
(`tools/ci-local.sh && git push`): no push when a job fails.

### Line endings and file names

- **Line endings:** `.gitattributes` makes every text file LF in the repository and in the working tree. Scripts,
  units and `.desktop` files reach the board with LF. CI rejects CRLF.
- **Executable bit:** when a script lost its executable bit, run `tools/fix-modes.sh` after `git add`: it marks every
  `.sh` as executable in the index. CI fails when a script is missing the bit.
- **Venv:** one venv in the checkout, `.venv-linux/`, ignored by git.
- **File names:** Linux and GitHub are case-sensitive. Keep links and asset names in exactly the case of the file.

## Colors

[DESIGN.md](https://github.com/RobertoTorino/bazzite-console/blob/main/DESIGN.md) lists every color of the suite: the
rules that make its design recognizable, every tint of each hue and why it is there, and where each color is used
(the apps' themes and state colors, the wiki, the development apps, the apps' own colors). Each color shows a sample
from `design/colors/`. Both are written by `tools/make_design.py` from the listing in it: change the listing and run
it, never DESIGN.md itself.

```bash
python3 tools/make_design.py            # write DESIGN.md and its samples
python3 tools/make_design.py --check    # only say what is out of date (tools/tests runs it)
```

The check also compares the wiki's stylesheet, `docs/stylesheets/suite.css`, with its listing: a color added to the
stylesheet goes into the listing too, with what it is for.

The wiki's design panel, part of `mkdocs serve`, tries other colors on the pages; `python3 tools/apply_design.py
mkdocs.yml` writes what it changed into the wiki's stylesheet.

## The wiki's pictures and tours

To preview the wiki locally, run `mkdocs serve` from the repository root with the development venv active,
then open <http://127.0.0.1:8000/bazzite-console/>. Stop the server with Ctrl+C.

`.github/workflows/docs.yml` builds the wiki from `main` on every push and publishes it on GitHub Pages at
<https://robertotorino.github.io/bazzite-console/>. The Install page's link to the portal's release and the archive's
name are the tag of the newest published portal release (`tools/mkdocs/hooks.py`), so publishing a portal release
builds the wiki again. GitHub Pages deploys from `main` only, and a release's run belongs to its tag: that run starts
the workflow on `main` and builds nothing itself, so the Actions list shows two Wiki runs for a release. By hand:
`gh workflow run docs.yml --ref main`.

The picture of the portal on the home page (`docs/images/home/portal.webp`) is taken from the portal itself:
`tools/portal_screenshot.py` opens its window offscreen on this checkout's `apps.toml` and icons, in a home folder
of its own, with a fixed demo state (one update, one app not installed, the Gaming tab open), and saves it. The
wiki's workflow runs it before every build, so the published picture always shows the portal as it is on main. Run
it yourself to see the same picture in `mkdocs serve`:

```bash
python tools/portal_screenshot.py          # from the venv; --out FILE to save it elsewhere
```

The video tours are made the same way, frame by frame from the real windows, offscreen, from a terminal as below
or from [Nexus Dashboard](dashboard.md#video-tours). `tools/record-tour.sh`
records the portal's tour, about two minutes, with music under it that fades out over the last two seconds
(`tools/sounds/the_quiet_engine_remix.ogg`, made with generative AI tools; `--no-music` leaves it out).
`tools/record-tour.sh --wiki` also writes the copy on the [Portal Tour](../portal-tour.md) page,
`docs/videos/portal-tour.mp4` (1280 × 720) and its poster, and a fingerprint of the portal it was recorded from
(`tools/portal-tour.stamp`: the portal's code and pictures, its tiles in `portal/apps.toml` (their names,
categories and marks, not the tags or checksums), and the tour's script). The video shows no version number, so a
release does not make it out of date. While it is out of date, [Nexus Release Tool](releases.md) shows an orange
banner with **Record new video now**, and its Start new release waits for it. The checks fail when
the portal changed since, until the tour is recorded again with `--wiki`;
`python3 tools/portal_tour.py --check` says so from a terminal, and `--stamp` marks the video as current
for a change that does not show in it. A change the wiki describes goes into its [Portal](../portal.md) page in the
same change.
The video itself goes to `~/Videos`, outside the repository, at 1920 × 1080. For YouTube, record it at 4K:
`--size 2160p` renders the same tour at 3840 × 2160 (the window drawn at 240 % instead of 120 %, so the text stays
crisp) into `~/Videos/ps5-portal-tour-v<portal version>-2160p.mp4`.
YouTube shows a 4K upload far sharper than a 1080p one, since it gives it a better codec and more bits. `--size
1440p` is the step between. The wiki's copy is the same whatever the size.
`tools/record-app-tour.sh` records one app's, about 40 seconds, the same script for every app, with music under it
that fades out over the last two seconds (`tools/sounds/the_quiet_engine.mp3`, made with generative AI tools):

```bash
tools/record-app-tour.sh fan                          # ~/Videos/ps5-fan-tour-v<version>.mp4
tools/record-app-tour.sh cec cec.mp4 --seconds 30     # another file, another length
tools/record-app-tour.sh fan --no-music               # without sound; --music FILE for another track
tools/record-app-tour.sh fan --size 2160p             # at 4K for YouTube: ...-tour-v<version>-2160p.mp4
```

The app starts from the checkout in a home folder of its own. The tour points at the controls of its header, with
their tooltips as captions, and opens its tabs or pages; it presses no buttons and nothing runs as root. What the
app reads from the board is real, so watch the video before you publish it.

## Where things are installed

- **Root-owned `/opt`:** Board Test (`board`), whose test engine runs as root: a normal user cannot change code that
  sudo runs.
- **Your home folder:** the portal (`~/.local/share/bazzite-console-suite/portal`, what it remembers beside it in
  `~/.local/share/bazzite-console-suite/state`), the shared venv `~/.local/share/bazzite-console-suite/venv` (PyQt6,
  used by all suite GUIs and removed with the last of them), plus each app's settings, results and launchers.
- **`bazzite_console_core` per app:** each app's release carries the `bazzite_console_core` it was tested with, next
  to its own code. Apps with different release tags never share a core version they were not tested with.

[Portal](../portal.md#install) has the full table.

## Versions and tags

`core/`, `portal/` and every app have a `VERSION` file; it is the single source of the version. Versions that are
also written in a script or package (`VERSION="…"`, `__version__ = "…"`, pyproject `version`) must match it, which
CI checks with `tools/check_versions.py`. The development apps in `dev/` have no version: they are never released,
and their header shows the checkout's last commit and its time.

Each app is released on its own tag (`ps5-board-v0.1.0`, `ps5-fan-v2.0.0`, …); the release workflow builds
`<tag>.tar.gz` and `SHA256SUMS`. The portal has `ps5-portal-vX.Y.Z` and pins one release of every app in
`portal/apps.toml`; a change there since the last portal release needs a portal version bump at least as large as
the largest app bump. The release steps are in [Releases](releases.md).

How the releases are titled on GitHub, and why its **Latest** release is always the newest portal:
[The releases on GitHub](releases.md#the-releases-on-github).

### Upstream releases an app pins or follows

`tools/check_upstream.py` compares what the apps pin or follow with their upstreams, each described
below. It exits with 0 when every one is in step, 1 when one moved and 2 when one could not be checked. The Upstream
workflow (`.github/workflows/upstream.yml`) runs it every Monday and can be started by hand. What moved goes into the
open **Upstream review** issue (a new one when none is open, else its list is updated with a comment), which
notifies everyone who watches the repository. The workflow never closes it: close it once every item on it is
handled on `main`, else next Monday's run opens it again. **Close issues** in [Nexus
Dashboard](dashboard.md#close-issues) does it, or a command with a gh login:

```bash
gh issue list                                                  # the open issues, with their numbers
gh issue close <number> --comment "PPSSPP pinned at 1.20."     # close one, saying how it was handled
```

The run fails only when an upstream could not be checked. A moved pin means a new version of the app is due, with
the new pin tried on the board first. It also moves Nexus Deps' list of the programs the apps use: run
`dev/deps/run.sh --sync-upstreams` from the repository's root, else CI fails
([Nexus Deps](dashboard.md#deps)).

The shadPS4 Manager installs one shadPS4 release, pinned in `apps/shadps4/shadps4_manager/emulator.py`
(`VERSION`, `TAG`, `ASSET`, `SHA256`). The tool checks it: a newer stable release, with the Linux zip and the
SHA-256 GitHub publishes for it that a new pin needs, and the SHA-256 of the pinned zip. A new shadPS4 can change
what the app relies on (its `config.json`, the shadNet protocol), so a new pin also needs a look at what changed.

The PPSSPP, PCSX2 (its stable channel) and RPCS3 Managers each pin one release: `VERSION` or `LANDMARK` in the app's
`emulator.py`. RPCS3's `emulator.py` also holds the size of the pinned AppImage (`SIZE`), by which the app sees that
RPCS3 replaced itself with another build, so a new pin moves it too. The same tool reports a newer stable release
than the pin; the apps check the checksum of what they download themselves.

The PS5 Upscaler Manager pins no HelixSR release: it gets the latest of one major version (`SUPPORTED_MAJOR`), or
the fallback HelixSR's developer names. Its `apps/upscaler/upscaler/acquire.py` holds `SUPPORTED_MAJOR`,
`KNOWN_VERSION`, the newest release the app was checked against, and `FALLBACK_VERSION`. The same tool reports a
newer stable release (users get it at once, so what changed in its setup, its zip and `helixsr.ini` needs a look and
a try on the board; then `KNOWN_VERSION` moves), a newer major version (users do not get it until the app is moved
to it), a fallback named in the latest release's notes that is not `FALLBACK_VERSION`, and a fallback release
without its zip.

The Vita3K Manager installs one Vita3K build, pinned in `apps/vita3k/vita3k_manager/emulator.py`
(`BUILD`, `SEMVER`, `COMMIT`, `SHA256`, `SIZE`). Vita3K has no stable releases: every change is a build, kept as a
release of `Vita3K/Vita3K-builds` tagged with its number, with `Vita3K-x86_64.AppImage` and the SHA-256 GitHub
publishes for it. Builds come almost daily; the tool reports the newest build when it is past the pin (with how many
builds later), and a pinned AppImage that is gone from GitHub or was replaced. The app itself already tells its users
when a newer build is out, so a report is a reminder, not a fault: move the pin when a build is worth trying. A new
pin takes the asset's digest and size from that release, and a look at what the app relies on in Vita3K's source at
the new build:

- the command line (`vita3k/config/src/config.cpp`): `-r <title ID>`, `--frontend sdl`, `--firmware`,
  `--pkg` with `--zrif`, and a `.vpk`, `.zip` or folder as the positional argument;
- the folders (`vita3k/app/src/app_init.cpp`, `init_paths`): settings in `$XDG_CONFIG_HOME/Vita3K/config.yml`, the
  storage in `$XDG_DATA_HOME/Vita3K/Vita3K` unless `pref-path` in config.yml moves it, games in its `ux0/app`;
- the firmware's three parts (`vita3k/app/src/app.cpp`, `get_firmware_state`): `vs0`, `sa0` and `pd0` counted as
  installed when they hold anything;
- the SDL frontend (`vita3k/sdl-frontend`): it runs the game given by `-r` and quits with it, and has no full screen
  of its own. `--fullscreen` is not used: Vita3K writes it into config.yml as `boot-apps-full-screen`;
- the AppImage's self-updater (`bin/10-self-updater.hook` in the AppImage): it overwrites the AppImage with the
  newest continuous build unless `DISABLE_AUTO_UPDATES=1`, which the run wrapper sets. `vita3k --version` on the new
  AppImage confirms the build and commit.

The tests hold the `config.yml` a Vita3K build writes on its first start (`tests/fixtures/config-4186.yml`); a new
pin replaces it with the new build's, renamed for it.

The Xenia Manager installs one Xenia Canary build, pinned in `apps/xenia/xenia_manager/emulator.py` (`BUILD`,
`COMMIT`, `PUBLISHED`, `SHA256`, `SIZE`). Xenia has no stable releases either: every change is a release of
`xenia-canary/xenia-canary`, tagged with its commit, with `xenia_canary_linux.AppImage` and the SHA-256 GitHub
publishes for it. A tag is no number, so the app and the tool take a release published after `PUBLISHED` as a newer
build; the tool also reports a pinned AppImage that is gone or replaced, as for Vita3K. A new pin takes the asset's
digest and size and the release's date, and a look at what the app relies on in Xenia's source at the new commit:
the `--fullscreen` option and the positional path (`src/xenia/app/xenia_main.cc`), the storage root in
`$XDG_DATA_HOME/Xenia` (the same file, and `GetUserFolder` in `src/xenia/base/filesystem_posix.cc`), the places of
the game partition in a disc image (`src/xenia/vfs/devices/disc_image_device.cc`, which `GAME_PARTITIONS` in the
app's `games.py` copies), and GTK on X11 (`GDK_BACKEND` in `src/xenia/ui/windowed_app_main_posix.cc`).

Remote Play builds FFmpeg from one release (`FFMPEG_VERSION`, `FFMPEG_SHA256` in
`apps/remoteplay/native/ffmpeg/build.sh`) and takes libva's headers from one release where the system has
none (`LIBVA_VERSION`, `LIBVA_SHA256`). The tool reads FFmpeg's release tags (`n<version>` on its GitHub mirror) and
libva's latest release, and reports a newer FFmpeg on the pinned branch (its fixes), a newer FFmpeg branch (a bigger
move: the decoder calls of the native core) and a newer libva (its headers only; the libraries stay the system's).

PS5 Webcam downloads each camera's firmware from one commit of a GitHub repository (`PINNED` in
`apps/webcam/webcam/firmware.py`). The tool downloads the file at that commit, which must still have
the pinned SHA-256, and the same file on the repository's default branch: changed or gone there is reported.

PS5 Board Test runs whichever speedtest CLI is installed; its development tool installs one release of Ookla's
(`SPEEDTEST_VERSION` in `apps/board/development/tools/install-requirements.sh`). Ookla publishes no API;
the tool reads the version from Ookla's Homebrew formula.

```bash
python3 tools/check_upstream.py            # all of them
python3 tools/check_upstream.py helixsr    # one: shadps4, helixsr, ppsspp, pcsx2, rpcs3, vita3k, xenia,
                                           # ffmpeg, webcam or speedtest
```

## bazzite_console_core

Code shared by the suite's apps (`core/`). Nothing in it imports an app: each app passes its constants in as an
`AppInfo`.

| Module | What it holds |
|---|---|
| `appinfo` | `AppInfo` (id, name, version, logo, tag prefix, settings names) |
| `theme` | The suite's theme (`THEMES`, `theme_name()`, `save_theme_name()`, `apply_theme()`, `surface_style()`, `muted()`), `STATE_COLORS`, bundled Inter font, `header_font()`, `HOVER_STYLESHEET`; self-contained, so an app not on core carries a copy |
| `text` | `fmt()` (`%1` placeholders), `fill()` (`{name}` placeholders), `plain_tooltip()`, `window_title()` |
| `widgets` | `AppHeader` (the window header), `StatusPill`, `MetricBox`, `Pill` (a `MetricBox` that is a button), `same_width()`, `ClickableLogo`, `Terminal`, `TextDialog`, `RoundedToolTip`, `show_tooltip()`, `page_header()`, `hint_label()`, `accent_button()`, `set_button_active()` |
| `app` | `create_app()` / `run_app()` / `exec_app()`: names, Fusion with the theme, tooltip, icon, SIGTERM |
| `exit_keys` | `install(app)`: Escape and a controller's B close the app's window, after a key the window takes for itself and through its `closeEvent`; B, read with pygame-ce, is Escape for what has the focus, and only for the app that has had the focus for a moment; `install(app, controller=False)` for Escape alone, the class attribute `exit_keys = False` for a window that keeps every key. Self-contained, so an app not on core carries a copy |
| `action_tab` | `ActionTab`: the last tab of a `QTabWidget` as a button (Start game in the game managers): a click acts and the open page stays open |
| `settings` | `open_settings(info)` at each app's existing file, geometry helpers, `SettingsStore` (typed defaults) |
| `help` | `HelpView` (the content stays in the app) |
| `updates` | `latest_release()` (with a tag prefix for the per-app tags: GitHub's release pages, newest first, are followed until one holds the prefix, since other releases can fill the first page), `UpdateStatus`, `UpdateChecker` (any job, off the GUI thread) |
| `builds` | Several builds of an emulator side by side (the game managers' version manager): each in a folder of its own with a `build.json`, `current` pointing to the one in use; `install()` (checked against its SHA-256, GitHub's digest or a pinned one), `use()`, `delete()`, `add_custom()`, `replaced()`, `github_builds()` and `github_latest()` (a repository's builds with GitHub's SHA-256) |
| `builds_dialog` | `BuildsDialog`, the version manager's window (Installed: Use, Delete, Add; Download: Refresh, Download; the tested build marked Tested), and `fill_menu()`, the menu of a manager's version pill |
| `platform` | XDG folders, `xdg_open()`, `launch_in_terminal()` (with an exit file the caller can watch), `show_in_folder()`; `private()`, a path or a text with the home folder as `~`, never the user's name, which `applog.setup(private=True)` applies to every line of a log |
| `steam` | Steam's folders and users, `installed()`, `with_steam_closed()`, `shortcuts.vdf` and the shortcuts' artwork in `grid/`, `shortcut_number()` and `play_url()` (a shortcut's number in Steam's file, and the address that starts it) (standard library only) |
| `steam_art` | `draw_icon_art()`: a shortcut's four pictures drawn from an app's icon, in the icon's color |
| `upstream` | `publish()` / `read_all()`: the updates outside the suite an app can install now, for the portal's notice (standard library only; HelixSR carries a copy) |
| `sensors` | `Sensors.read()`: the board's live values from `/proc` and `/sys` without root (CPU, GPU, the GPU governor's temperature limit, VRAM, RAM, temperatures, network, disk, the fan), `Reading`, `Fan` |
| `nexus` | The development apps' design (the theme `NEXUS`) and their header (`header()`: the checkout's last commit and its time in place of a version) |

Core is **bundled per app**: `tools/stage_app.py` copies `bazzite_console_core/` next to the package of every app
that imports it, so each release runs on the core it was tested with. The development apps import it from the
checkout.

### Tests

```bash
cd core && QT_QPA_PLATFORM=offscreen python -m pytest -q tests
```
