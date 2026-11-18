<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# CLAUDE.md

The owner's rules for working on a suite. **This file is the same, word for word, in every suite's repository**
(owner, 18-11-2026: "one generic CLAUDE.md that can be used in whatever suite we are working on"). A change to it is
made in every suite in the same piece of work. It names no suite, no board and no app that only one suite has.

What only this suite has is in [.claude/suite.md](.claude/suite.md): its name, its hardware, its repository, the
names of its packages and folders, its apps, and the rules that hold for it alone. Read it with this file:

@.claude/suite.md

This file, not a local memory, carries the standing rules. The owner may change them when the need is there.

## A suite and its twin

**A suite is standalone** (owner, 13-11-2026: "it is and stays a standalone repo ... it should run on its own using
its own tooling"). Everything it needs is in its repository: its tools, its core and its development apps. Nothing
depends on a checkout of Nexus or of another suite, and nothing is taken from one at run, test or release time. The
tooling began as a copy of Nexus's and is the repository's own now. A change to it is made here.

**The suites are twins** (owner, 15-11-2026: "basically identical", the only difference is the board each one runs
on). They are checked out beside each other and share their release logic (NRT, `tools/`, the workflows, CI), design
features, category icons and the apps' design. These stay equal. A change to any of them is made in every suite in
the same piece of work, with each one's CHANGELOG and wiki. Only what the hardware makes different differs: names,
`TAG_PREFIX`, the board's apps and checks. Standalone still holds: no suite reads another at run, test or release
time. The handover names what changed in each.

Whether a suite may name its twin is in its `.claude/suite.md`.

## Rules from the owner

- **Never commit, tag or push.** The owner does every git commit, tag and push. Finish work in the working tree and
  say what is ready; don't offer to commit.
- **NRT handles the releases** (owner, 15-11-2026). Nexus Release Tool works out each version from the CHANGELOG
  entries since the last tag (`Breaking.` major, `Added.` minor, `Fixed.` patch), bumps the `VERSION`s, pins the
  portal's `apps.toml` and starts the release; the owner runs it. Claude never bumps a `VERSION`, tags, builds or
  publishes release assets, pins a release in `portal/apps.toml` or writes the release entries in the CHANGELOGs, and
  doesn't offer to. When finished work will need a release, the handover says which app and why. Claude may change
  the release tools and their tests.
- **READMEs and the wiki hold no status, plans, step numbers or decision notes.** No placeholder folders that only
  describe future work. CHANGELOG entries are history and may mention steps.
- **The wiki keeps up with the work** (owner, 28-10-2026): new information, a new way of working or new logic worth
  knowing goes into its chapter of the wiki in the same change as the code, as a CHANGELOG entry does: what it does
  and how to use it, written for the person using it, never status or plans. The handover names the chapters it
  changed.
- **CHANGELOG for every change:** the root CHANGELOG for suite-wide changes, the app's (or core's, the portal's, a
  dev app's) for its own. Format: a `Changelog: DD-MM-YYYY HH:MM:SS` line, a blank line, then plain sentences; newest
  first. The time is Europe/Amsterdam (CET/CEST), whatever the machine's own zone:
  `python3 -c "import datetime, zoneinfo; print(datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Amsterdam')).strftime('%d-%m-%Y %H:%M:%S'))"`.
- **Every entry starts with its kind** (owner, 15-10-2026): `Breaking.` (removed, or no longer working as before:
  major), `Added.` (a new feature: minor) or `Fixed.` (a bug or security fix: patch); 0.x apps too. NRT takes
  the number from them.
- **VERSION is the single source** of each app's version. Copies in code (`__version__`, shell `VERSION=`,
  pyproject, Cargo) must match: `tools/check_versions.py`.
- **Every folder that was a repository once** (each app, `core/`, `portal/`) keeps LICENSE, .gitignore, VERSION and
  CHANGELOG; each `dev/` app keeps LICENSE, .gitignore and CHANGELOG, and has no VERSION (owner, 15-11-2026: a
  development app is never released; its header shows the checkout's commit and its time, as NRT's does). GitHub
  workflows live only in the root `.github/`.
- **An info symbol where space is limited** (owner, 01-11-2026): a window never carries long lines of explanation.
  Where a line of hint text would take the room, a small round "i" (core's `InfoButton`) opens the text on a click,
  with its links; a short line under a control stays a `hint_label`.
- **Open by default.** Everything about the suite may be public: code, plans, issues, test data and recordings from
  the boards. Only personal data stays out (names, addresses, host and user names, serial numbers, MAC and IP
  addresses, keys, account details), as the apps mask it in their logs. When in doubt whether something is personal,
  ask.
- **Ask** before decisions that are the owner's (what an app does, repo layout, anything on the board). Do the
  obvious housekeeping without asking.
- **Warn before board changes.** An app that changes how the board runs is marked `changes_board` and the portal
  asks first. Frame it as standard caution: the apps are software-only and reversible, not "risky". Every such app
  says what it changes (owner, 03-11-2026): its `board_change` in `portal/apps.toml`, a few plain sentences on what
  it touches, what stays after a reboot or a power off, what it never touches (the BIOS, the firmware) and how it is
  undone, written from the code, not from the README. The tile's tooltip shows it under "Changes the board", and the
  app's wiki chapter opens with the same text, word for word, in a `!!! warning "Changes the board"` box right after
  its title; `tools/check_manifest.py` compares the two (the word Disclaimer stays the wikis' liability notice). The
  suite's `.claude/suite.md` lists its apps that change the board.
- **"Board" in "changes the board"** (owner, 18-11-2026: "We always use the word 'board' in the context of 'changes
  the board'"). The mark, the box, the tooltip and every text about such an app say board, whatever the hardware is
  called elsewhere in the suite.
- **Advice, not reboots.** No app reboots, powers off or logs out the board; when one is needed, the app says so
  (and which command does it). A suite's exceptions, each the owner's decision, are in its `.claude/suite.md`. A new
  reboot anywhere else is the owner's decision.
- **The current releases are the baseline.** They were tested on the hardware. Moving code must not change
  behavior; a finding in existing code is "a code path to check", not a known failure. Prove "unchanged" (diffs,
  pixel comparisons, the installer tests) rather than assume it.
- **Not limited to the owner's setup.** The owner's board, TV, cable and settings are one case, not the target:
  apps read what the hardware reports and offer every option it supports (a CEC 2.0 TV, another display mode, a
  second adapter), and say so where an option does not apply, rather than leaving out what the owner's setup lacks.
  Recorded data from the owner's board makes good test fixtures; tests also cover other setups. An app does not
  assume that hardware features or paths of another device apply here.
- **Consistent architecture.** Every app is built the same way, so one that works is the pattern for the next:
  - Layout: `apps/<name>/` holds its Python package(s) directly (`<package>/__main__.py`, no wrapper folder),
    `<name>` a short name and `<package>` the app's name without the suite's prefix (owner, 17-10-2026; a renamed
    app's old key goes in `RENAMED` in the portal's manifest.py), `images/`, `tests/`, `install.sh` and the four
    files; data the package reads (a catalog, tables) sits in the package or beside it in the app folder.
    `tools/tests/test_layout.py` checks the layout. An app's icons are copies of its category's icon:
    `icons/categories.toml` assigns them, `tools/sync_icons.py` writes them.
  - Code: shared code comes from the suite's core (bundled per app); the installer writes a launcher in
    `~/.local/bin` whose exec line names the app's python, a menu entry and an optional Desktop icon; every app has
    its installer test (`tools/installer-tests/<name>.sh`).
  - Window: the first line is the app's icon at 96 px on the left, spanning the title (with the version) and a
    second line below it (status boxes or the app's main controls). An app's actions are pills (core's
    `ActionPill`), never small buttons (owner, 16-11-2026). No long lines of text in the window (owner,
    01-11-2026): where space is limited, an info symbol (core's `InfoButton`) opens the explanation; what is
    applied already cannot be applied again (its Apply is off).
  A new app copies the structure of an existing one; any deviation is the owner's decision. The wiki's
  [Architecture and consistency](docs/development/architecture.md) describes it all, with the steps for a new app.
- **A design per system** (owner, 25-10-2026): a suite keeps the design of its system, for the apps' theme and the
  wiki's. Never carry another system's design over to it, nor its design to another system. The development apps
  keep Nexus's names and Nexus's design (teal, the theme `NEXUS`).
- **Scope is the suite, not the system.** We answer for the portal and its apps, not for the operating system. A
  system-wide package is in scope only where one of our apps uses it (Nexus Deps lists it then); its updates and
  security fixes are the system's. Our own code, and the Python packages in our apps' environments, are ours. One
  exception (owner, 15-10-2026): Nexus Deps shows the system's update state (the running image, an update waiting
  for a reboot, the updater's last run). Since 09-11-2026 (owner) it shows every update of the machine (the system's
  image, Flatpaks, Homebrew, Rust, the development venv), installs them with a card's Update after it asks, and
  reminds hourly; the system's updater still installs them nightly by itself. Its Fix (owner, 07-11-2026) installs
  what an installed app needs and lacks, after it lists the commands and asks: Python packages with pip, a missing
  tool with Homebrew, else layered with rpm-ostree (active after a restart, which it advises and never does).
- **A name that is kept out** of a suite (another project's, a twin's) is listed in its `.claude/suite.md`, with
  where it may still stand.

## What a suite is

A **portal** installs and starts the apps listed in its manifest, `portal/apps.toml`. One app is always installed
and always listed first; every other listed app is an optional tile. The release tags start with the suite's
`TAG_PREFIX`: `<prefix><app>-v<x.y.z>` and `<prefix>portal-v<x.y.z>`. The suite's system is in `SYSTEM`. App keys,
release tags, installer tests and wiki chapters use the same short folder name.

Every app has a `category` in `portal/apps.toml`, the same as its icon's in `icons/categories.toml` (sustainable,
graphics, gaming, utilities). The portal is one fullscreen view for the keyboard, the mouse and a controller (owner,
01-11-2026). It shows a category strip with the notice of updates beside it, and the always-installed app as the
first tile on Sustainable (owner, 20-10-2026). There is no Development category (owner, 27-10-2026): the portal
lists only released apps.

## Layout

The repository is the suite, and the tools know only this one (`tools/suites.py`). The names of the portal's and
core's packages and of the suite's folders are in `.claude/suite.md`.

- `portal/`: the portal's package, `apps.toml` (one pinned release per app), its tests and `install.sh`. It installs
  as a copy in the home folder (owner, 15-11-2026): the program in the suite's data folder under `portal`, what it
  remembers in `state` beside it; no `/opt`, no sudo for the portal. Installed from a checkout, it installs the apps
  from that checkout.
- `apps/<name>/`: one app per folder, with its Python package, `images/`, `tests/`, `install.sh`, requirements and
  its own VERSION, CHANGELOG, LICENSE and .gitignore.
- `core/` with `core/VERSION`: the shared Python code, **bundled per app** at release time (`tools/stage_app.py`),
  so each app runs on the core it was tested with; the suite's shared venv holds only PyQt6 and pygame-ce (the
  portal's controller reader). In a checkout an app's `install.sh` and its tests find core at `../../core` from the
  app folder. Core names the suite's folders and addresses. Its `nexus.py` is the design of the development apps
  (the theme `NEXUS`) and their header (`header()`: the checkout's commit and its time, `checkout_stamp()`).
- `tools/`: the release and check tools (`build_release.py`, `stage_app.py`, `check_versions.py`,
  `check_manifest.py`, `pin_app.py`, `suite_release.py`, `publish_release.sh`, `tag-release.sh`, `release_commit.py`,
  `ci_state.py`, `ci_matrix.py`, `check-release.sh`: the board checks of a portal release), `all_tests.py`
  (`ALL-TESTS.md`, the list of every test, written from the tests; CI compares them), CI on this machine
  (`ci-local.sh`, `ci_local.py`, `ci-local/`, `ci-qt-libs.sh`), `suites.py`, `sync_icons.py`, `new_app.py`,
  `check_upstream.py`, `fix-modes.sh`, `nrt.sh`, the tours (`portal_tour.py`, `app_tour.py`, `tour_frames.py`,
  `record-tour.sh`, `record-app-tour.sh`, their music in `sounds/`), `portal_screenshot.py`,
  `make_portal_sounds.py`, `apply_design.py`, `make_design.py` (DESIGN.md and its samples in `design/colors/`),
  `text_check.py` with `text_check/` (what is wrong with the text people read; no test and no CI check), `mkdocs/`
  (the wiki's hooks, the design panel, the disclaimer and the overrides), `tests/` and `installer-tests/`
  (installers on Linux with fakeroot shims).
- `dev/<name>/`: the development apps, each with `.checkout-only`: they run from the checkout, are never released
  and are in no portal. They import the suite's core directly. Nexus Dashboard (`dev/dash`) opens them all:
  - Nexus Release Tool (`dev/nrt`), the release front end
  - Nexus Installer Tests (`dev/itests`), the installer tests one at a time
  - Nexus Demo Recorder (`dev/demo`), a portal installation recorded with OBS
  - Nexus Sound Lab (`dev/sounds`), short sound effects for the windows
  - Nexus Deps (`dev/deps`), the suite's packages and tools on the machine, with Fix; its catalog is in
    `dev/deps/nexus_deps/catalogs/`
  - Text to Speech (`dev/text`), a text spoken with the Kokoro model; its speech engine has a venv of its own
    outside the checkout, `~/.local/share/nexus-text-to-speech/`, since onnxruntime has no wheel for the dev venv's
    Python
  - Nexus Remix Studio (`dev/studio`), a voice mixed with a synthesized background; its From a text uses Text to
    Speech's engine from `dev/text`

  A portal that runs from the checkout, or was installed from one, installs the released apps from that checkout's
  source: that is how a release is tried on a board before its tag. Install every app through the portal, so what
  is installed stays in step.
- `docs/` and `mkdocs.yml`: the wiki; `icons/`: the category icons and `categories.toml`; `install.sh`: the
  portal's installer from a checkout; `test.sh`: every test folder; `requirements-dev.txt`: the development venv.
- `CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md`: for contributors.
- `.github/workflows/ci.yml`: every check on every push and pull request; `release.yml`: a release, started by Nexus
  Release Tool's Start new release on the release commit (or a tag pushed by hand); `docs.yml`: the wiki on GitHub
  Pages; `upstream.yml`: the weekly upstream check. `.github/dependabot.yml`: a weekly pull request for newer
  actions.
- `.claude/`: `suite.md` (this suite), `writing.md` (how to write the text), `text-decisions.md` (the owner's
  decisions on the text) and the `/rewrite-text` command with its workflow.

## Working tree

- **Line endings:** every text file is LF in git and in the working tree (`.gitattributes`: `* text=auto eol=lf`).
- **Exec bits:** a checkout with `core.fileMode=false` records new files as 100644. Before committing,
  `tools/fix-modes.sh` marks every `.sh` executable in the index; CI fails otherwise.
- **Venv:** one at the repo root, `.venv-linux/`; `./test.sh` takes it. The system's `python3` has no PyQt6:
  `python3 -m venv .venv-linux && .venv-linux/bin/python -m pip install -r requirements-dev.txt`.
- **Tests keep settings in a temp folder:** the conftest fixtures turn settings into .ini files there.
- Keep path and link case exact: Linux and GitHub are case-sensitive.
- The development tools run on Linux only (owner, 15-11-2026).

## Checks before handing work over

`tools/ci-local.sh` runs every job of ci.yml as GitHub runs it (Python 3.12, each job with only its own
requirements, in a podman container); run it before saying work is ready. `./test.sh` runs every test folder (extra
arguments go to pytest). By hand, from the repository root:

```bash
./test.sh                                                   # every folder with tests/
(cd <folder> && python -m pytest tests)                     # one folder: portal, tools, apps/<name> or dev/<name>
python3 tools/check_versions.py
python3 tools/check_manifest.py --base origin/main   # portal/apps.toml rules, the bump since the last portal release
python3 tools/sync_icons.py --check
shellcheck -x -S warning tools/*.sh apps/*/install.sh portal/install.sh
for t in tools/installer-tests/*.sh; do [ "${t##*/}" = shims.sh ] || bash "$t"; done   # every installer test
mkdocs build --strict                                # the wiki, from the venv
```

Every app (and every `portal/apps.toml` entry) has an installer test, `tools/installer-tests/<name>.sh`, and CI runs
each one; a new app adds both (`tools/tests/test_installer_tests.py` checks it). Nexus Installer Tests lists the
scripts in that folder by itself.

**Missing tooling is installed, not worked around** (owner, 26-10-2026): when a check needs a tool the machine lacks
(shellcheck, fakeroot, podman, Node.js for the design panel's script), get it (`brew install` on Bazzite) and run the
check, rather than reviewing by eye. **Frequently needed tools are installed for good** (owner, 05-11-2026): a tool
the work needs more than once is installed permanently on the development machine (Homebrew, or a distrobox for a
Fedora package Homebrew lacks), not run once in a throwaway container.

## Releases

Nexus Release Tool handles the releases: it works out the versions from the CHANGELOG kinds, and its release tab
starts `release.yml` on the release commit; one release by hand is `tools/tag-release.sh <prefix><app>-v<x.y.z>`,
which tags and pushes only a pushed commit that passed CI, and `release.yml` builds and publishes it on GitHub
(owner, 15-11-2026: the same in every suite). GitHub's Latest release is the newest portal.
`tools/check_upstream.py`, weekly in `.github/workflows/upstream.yml`, says when an upstream an app pins moved past
the pin. Moving a pin is code Claude may prepare (with its CHANGELOG entry); the board test and the app's release
are the owner's, and the handover says so.

## Style

Code reads like the code around it: the same comment density, naming and idiom. Docs are plain, short sentences,
written for the person using the tool, as [`.claude/writing.md`](.claude/writing.md) describes;
`tools/text_check.py` lists what is wrong. **American English** (owner, 26-10-2026) in everything written: color,
gray, center, canceled, license, catalog, labeled; identifiers, settings keys, file names and recorded data keep the
spelling they have. **Pictures are WebP wherever WebP is accepted** (owner, 26-10-2026): a picture on a page or in
an app's window is a `.webp` copy of its source; a PNG stays only where WebP is not accepted or expected (a favicon,
the `-128.png` menu and Desktop icons, the source drawings in `icons/`).

The manual (`docs/`, built with MkDocs) is called **the wiki** in user-facing text: the header link and the Home
page's footer say Wiki. The repository's own GitHub wiki stays unused.
