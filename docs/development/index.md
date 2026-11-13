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
