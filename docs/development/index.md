<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Development

The suite follows the shared app layout and release rules. The Bazzite-specific release and installer tools are in
`tools/`; the docs design panel is part of `mkdocs serve`. The Nexus developer applications have been adapted under
`dev/` for this suite only.

## Install from a checkout

To try the portal and the apps as they are in the repository, not as they were released, run this from the repository
root on a PlayStation 5 running Bazzite, as your own user:

```bash
bash ./install.sh
```

A portal installed this way installs the apps from the same checkout. `tools/check-release.sh local` does the same
and starts the portal; `release` and `draft` install a published portal release or the draft of one (`release`
takes the draft while the release is not published).

A test cleans up after itself. On a machine without the suite, what the test installs is marked as a test's and
removed again when the portal closes: the apps installed during the test, the portal and Board Test. A machine
that had the suite installed keeps it, and `--keep` keeps what a test installed.

```bash
tools/check-release.sh status            # what of the suite is installed, and whether a test put it there
tools/check-release.sh remove            # remove every app, the portal and Board Test; settings stay
tools/check-release.sh remove --purge    # their settings and logs too
```

The release planner's **Remove suite** tab runs `remove` in a terminal.

## The development apps

Open `dev/dash/run.sh` for the developer dashboard. Starting it while it is open closes the open window and opens a new
one, with the checkout's code as it is now. It launches the release planner (`dev/nrt/run.sh`), dependency
checker (`dev/deps/run.sh`), installer-test runner, OBS demo recorder, and sound lab. The release planner's
`--list` mode is safe for a terminal overview; its release actions are user-driven. The video-tour scripts are
`tools/record-tour.sh` and `tools/record-app-tour.sh`; the dashboard provides their UI.

The wiki's Portal Tour keeps up with the portal. `tools/record-tour.sh --wiki` writes the copy on the
[Portal Tour](../portal-tour.md) page and a fingerprint of the portal it was recorded from
(`tools/portal-tour.stamp`: the portal's code and pictures, and the tour's script). The checks fail when the portal
changed since, until the tour is recorded again:

```bash
python3 tools/portal_tour.py --check     # says whether the portal changed since the wiki's tour was recorded
tools/record-tour.sh --wiki              # record it again, with the wiki's copy
python3 tools/portal_tour.py --stamp     # a change that does not show in the video: mark the video as current
```

A change the wiki describes goes into its [Portal](../portal.md) page in the same change.

## Releases

A release is made from the release planner's first tab, step by step: get up to date, commit, push, wait for CI, then
**Start new release**. Start writes the versions, the `Release x.y.z.` CHANGELOG entries, the new tags in
`portal/apps.toml` and the portal's version, commits and pushes that, and starts `.github/workflows/release.yml` on
the commit, so there is nothing to apply, pin or bump by hand. Its **Contents** tab lists what the release holds:
each app that ships something new since its last release, and the portal. A part whose only changes since its last
tag are its version and its `Release x.y.z.` entry (or a withdrawal's entry) ships nothing new and is left out. The
run:

1. waits until CI passed on the commit;
2. builds and publishes every app whose pinned tag has no release yet, side by side;
3. writes their checksums into `apps.toml` in a commit `Pin ...` on `main`;
4. builds the portal from that commit as a **draft** release, which no installed portal sees.

**Device test** then installs the draft on this machine (`tools/check-release.sh draft`). **Publish** makes it the
portal's release, its tag and GitHub's Latest release; **Not OK** leaves it a draft, and after the fix the steps start
again from Commit (apps already out are skipped, the portal is built anew). The last step pulls the pin commit.

A run started again skips what is already published. By hand, without the planner:
`gh workflow run release.yml --ref main -f commit="$(git rev-parse origin/main)"`.

One release by hand, built on this machine instead, is `tools/tag-release.sh ps5-<app>-v<x.y.z>`, run in a terminal.
The workflow does not run on a pushed tag.

A release that must not be used any more is withdrawn on the planner's **Retract app** tab: **Retract** marks the
pinned release withdrawn in `portal/apps.toml`, with the reason the consoles show, and **Take back** removes the
mark. **Test withdrawal**, on a console with the app installed, starts the portal from the checkout: it must say the
app is not available any more and remove it. Mark the release on GitHub with the command the tab shows, then release
the portal from the first tab: Commit asks for the portal bump the withdrawal needs, and Start new release releases
the portal, not the withdrawn app.

The Install page's link to the portal's release and the archive's name are filled in from `portal/VERSION` when the
wiki is built (`tools/mkdocs/hooks.py`), so they follow each portal release.

The dependency checker uses `dev/deps/nexus_deps/catalogs/bazzite-console.toml`, which tracks the suite's
`requirements.txt` files and relevant system tools. Keep it synchronized when app dependencies change. Its emulator
cards ask GitHub for each newest release, signed in with the GitHub CLI's login (`gh auth login`): without one
GitHub allows 60 requests an hour, and the cards say "hourly limit is used up" until the hour is over.

Run the local checks from the suite root:

```sh
./test.sh                        # every folder with tests/: tools, dev/, the portal and each app, offscreen
./test.sh -k profile             # extra arguments go to pytest
tools/ci-local.sh                # the versions, the manifest, the icons' copies, and the tests of tools/ and dev/
python3 tools/check_versions.py
```

`./test.sh` takes the venv for this system (`.venv-linux/`; `$PYTHON` picks another interpreter). The portal and the
apps are made for Bazzite (`SYSTEM`), so on another system only `tools/` and `dev/` run; `NEXUS_SYSTEM=bazzite
./test.sh` runs them there too. Create the venv once:

```sh
python3 -m venv .venv-linux && .venv-linux/bin/python -m pip install -r requirements-dev.txt
```

The version check covers core, the portal, developer tools, and apps in this suite. To apply a design-panel mock to
the wiki stylesheet, run `python3 tools/apply_design.py mkdocs.yml`; the Bazzite Console palette samples are in
`design/colors/`.

## Icons

Every app's icon is its category's. The category icons are in `icons/<category>/`, at 1024, 512 and 256 px as WebP
and at 128 px as PNG; `icons/categories.toml` names each app's category and where its copies go. After changing an
icon, write the copies:

```sh
python3 tools/sync_icons.py                                    # write the copies that differ
python3 tools/sync_icons.py --check                            # only list them (CI runs this)
python3 tools/sync_icons.py --category gaming --from new.png   # a category's four icons from one square image
```

The copies are each app's `images/<icon>.webp` and `<icon>-128.png`, the portal's tile pictures in
`portal/images/apps/` (the wiki shows these too) and `portal/images/categories/`. A changed copy reaches an
installed app with that app's next release.

## The wiki

`.github/workflows/docs.yml` builds the wiki from `main` on every push and publishes it on GitHub Pages at
<https://robertotorino.github.io/bazzite-console/>. The repository's Pages source must be **GitHub Actions**
(Settings, Pages). `mkdocs serve` shows it locally.

Publishing a portal release builds the wiki again, so the Install page names that release. GitHub Pages deploys from
`main` only, and a release's run belongs to its tag: that run starts the workflow on `main` and builds nothing itself,
so the Actions list shows two Wiki runs for a release. By hand: `gh workflow run docs.yml --ref main`.

The picture of the portal on the home page (`docs/images/home/portal.webp`) is taken from the portal itself:
`tools/portal_screenshot.py` opens its window offscreen on this checkout's `apps.toml` and icons, in a home folder
of its own, with a fixed demo state (one update, one app not installed, the Gaming tab open), and saves it. The
wiki's workflow takes the picture again from the portal on `main` each time it builds the wiki, so the published home
page keeps up with the portal by itself; the file in the repository is what a local `mkdocs serve` shows. To see it
or refresh that file:

```bash
python tools/portal_screenshot.py          # from the venv; --out FILE to save it elsewhere
```

## Dependabot

`.github/dependabot.yml` has Dependabot open one pull request a week when the actions the workflows use
(`actions/checkout`, `setup-python`, `upload-pages-artifact`, `deploy-pages`) have a newer release. CI runs on that
pull request as on any branch; merge it when the checks pass. `gh pr list --author app/dependabot` lists the open ones.

## Git

After `git add`, `tools/fix-modes.sh` marks every `.sh` executable in the git index, so a script added from Windows
still runs from a Linux checkout or a release. Nexus Release Tool's Commit step runs it.
