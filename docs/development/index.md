<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Development

The suite follows the shared app layout and release rules. The Bazzite-specific release and installer tools are in
`tools/`; the docs design panel is part of `mkdocs serve`. The Nexus developer applications have been adapted under
`dev/` for this suite only.

Open `dev/dash/run.sh` for the developer dashboard. It launches the release planner (`dev/nrt/run.sh`), dependency
checker (`dev/deps/run.sh`), installer-test runner, OBS demo recorder, and sound lab. The release planner's
`--list` mode is safe for a terminal overview; its release actions are user-driven. The video-tour scripts are
`tools/record-tour.sh` and `tools/record-app-tour.sh`; the dashboard provides their UI.

The dependency checker uses `dev/deps/nexus_deps/catalogs/bazzite-console.toml`, which tracks the suite's
`requirements.txt` files and relevant system tools. Keep it synchronized when app dependencies change.

Run the local checks from the suite root:

```sh
python3 -m pytest tools/tests
python3 tools/check_versions.py
python3 tools/check_changelogs.py --base <commit>
bash tools/git-setup.sh
```

The version check covers core, the portal, developer tools, and apps in this suite. The changelog check accepts the last pushed commit or
pull-request base and also works when this suite is nested in a larger checkout. To apply a design-panel mock to the
wiki stylesheet, run `python3 tools/apply_design.py mkdocs.yml`; the Bazzite Console palette samples are in
`design/colors/`. `git-setup.sh` registers the local CHANGELOG merge driver; it does not install Git hooks.

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

## Git

After `git add`, `tools/fix-modes.sh` marks every `.sh` executable in the git index, so a script added from Windows
still runs from a Linux checkout or a release. Nexus Release Tool's Commit step runs it.
