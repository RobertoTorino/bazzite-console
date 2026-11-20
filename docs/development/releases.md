<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<span class="page-icon">:material-tag-outline:</span>

# Releases

The **Nexus Release Tool**, NRT for short (`dev/nrt/` in the repository), is the suite's release front end: a
window that makes a release with one action, **Start new release**: it writes the versions, the CHANGELOG entries,
the pins and the portal bump, commits and pushes them and starts the release on GitHub, then runs the device test on
a PS5. It commits and pushes only when you press a step's pill. It edits the checkout it lives in, so it is not in
the portal's releases and has none of its own. The header names the checkout's last commit and its time: the tool is
never released and has no version.

How the versions and tags fit together: [Versions and tags](index.md#versions-and-tags).

## Start it

From the repository's root, with the checkout's venv (`.venv-linux`, see
[Set up and test](index.md#set-up-and-test)). Nothing is copied when you install it: the menu entry always starts
the app of the checkout you installed it from. After moving the checkout, install it again.

```bash
tools/nrt.sh                                # open it (dev/nrt/run.sh)
tools/nrt.sh --list                         # the same overview in the terminal, with the system python3
dev/nrt/install.sh                         # app menu entry and Desktop icon
dev/nrt/install.sh --no-desktop-shortcut   # app menu entry only
dev/nrt/install.sh --uninstall             # remove them; the checkout stays
```

`tools/nrt.sh --install` and `tools/nrt.sh --uninstall` do the same as `dev/nrt/install.sh`. `--uninstall --purge`
also removes the settings.

## The release

A release of the suite is made from the tool's first tab, the release tab, with one action, **Start new release**.
It releases what changed since the last release: each app that ships something new, the portal, and core when it
changed. Everything a release writes (the versions, the CHANGELOG entries, the pins and the portal's version) is
written by that one action, so there is nothing to apply, pin or bump by hand.

The tab **Contents** lists what the release holds: each app that ships something new since its last release, the
portal, and core when it changed since its last version. A part whose only changes since its last tag are its
version and its "Release x.y.z." entry (or Retract's "Withdrawn:" entry) ships nothing new and is not in it. The
version offered first follows the CHANGELOG entries since the last tag (`Breaking.` major, `Added.` minor,
`Fixed.` patch, see [semantic versioning](architecture.md#versions-changelogs-and-releases)); type another to
override it. The portal's version says **auto**: it is worked out when the release is written, at least what the
app releases need, and can be typed too.

The release tab holds the release's steps, numbered, in the order you do them, each with its pill. The step to do
now has an orange ▶ and its pill lit; a step done has a green ✓, one that failed a red !, and the line beside each
says what there is to do. While a pill's command runs, its step has a teal ⋯ and its line says what runs
(**Push them** runs CI's jobs of what you changed here first, then pushes); the step is done when it
ends, and its output is on the Commands tab. Only the lit pill does anything, so you never need a command or
another tab. Every tab explains itself behind the round **i** in its first row: click it to read the whole
explanation.

1. **Get up to date** (**git pull**): only when GitHub has commits this checkout lacks, pushed from the other machine.
2. **Commit your changes:** the message field holds *see changelog*; keep it or type what the changes do, then
   **Commit**. It stages every change and new file and commits them after the version and manifest checks. When
   `apps.toml` changed since the last portal release (an app added, removed or withdrawn, a pin moved), that check
   needs a portal bump: the step asks first, with the version the release would suggest (the portal's CHANGELOG entries
   count: a Breaking entry makes it major), or the least the check accepts, whichever is higher, and writes it with
   its CHANGELOG entry on a yes, then commits. A no leaves the commit where it is.
3. **Push them** (**Push**): what GitHub has that this checkout lacks, such as the last release's `Pin ...`
   commit, comes in under your commits first (`git pull --rebase --autostash`); then CI's jobs run
   here first (`tools/ci-local.sh`): while they run, the step's line and the line under the header's
   pills count the jobs done and name a job that failed (GitHub knows nothing of this push yet). When a job fails,
   nothing is pushed and the step turns red, with the job's name and where its log is; fix it, commit and push, or
   push again when it was no fault of the code.
4. **CI passes:** the step waits until GitHub's CI (`ci.yml`) passed on that commit. When it failed, the line says
   so. A test that failed: fix it, then commit and push again. GitHub's own trouble (an error of its servers, a job
   that never started; [githubstatus.com](https://www.githubstatus.com) says when Actions are degraded): **Run CI
   again** starts the failed jobs again on the same commit. Once pressed, it stays off for those runs until GitHub
   shows them running again; a run that fails again can be started again.
5. **Start new release:** while the wiki's Portal Tour is older than the portal (its window or its tiles), an orange
   banner above the steps says so, with **Record new video now** (`tools/record-tour.sh --wiki`, about a minute, its
   output on the Commands tab), and this step waits until the video is recorded. Then check the versions on the
   Contents tab, and press it. It writes the release (the versions
   and their copies, the `Release x.y.z.` entries, the new tags in `portal/apps.toml`, the portal's version and its
   entry), commits it, pushes it and starts `.github/workflows/release.yml` on that commit. If the push stops, fix
   what it says; the pill then reads **Push and start**. It fetches GitHub's tags and `main` first: the portal is
   tagged on GitHub when you publish it, the last release of each part is read from the tags, and a release ends
   with a `Pin ...` commit on `main`. When that fetch fails, the message gives git's own words; for a tag here that
   points to another commit than GitHub's (git refuses to move it: "would clobber existing tag") it names the tag
   and the two commands that drop it and fetch again, since GitHub's tag is the one the release was published from.
   What came in is put under this checkout, the versions are read again, and the question before it writes shows
   each part's version as it will be. Each version comes from the part's CHANGELOG entries since its last tag
   (`Breaking.` major, `Added.` minor, `Fixed.` patch), so nothing is bumped by hand; type another one in the list
   only to override it.
6. **The release on GitHub:** `release.yml` starts at once on the release commit. Your release commit only writes
   the release, so the CI that passed on your commit in step 4 counts for it, and CI does not have to run again
   first ([below](#the-releases-on-github)). The run builds the new app releases side by side and publishes them,
   writes their checksums into `apps.toml` in a commit *Pin ...* on top of yours, and builds the portal from that
   commit as a **draft**, with the pinned releases of the required apps (Board Test and PS5 Quickfix) bundled
   in it, each checked against its pin: a draft has no tag yet, so no installed portal sees it. The line links the run; a run that
   ends badly gives a notification and lights **Resume run** (what is out already is skipped, the draft is made
   anew). **Stop run** stops a run that must not go on; stopping is safe until the portal is published. When the
   code must change for the run to pass (CI failed on the release commit, say), never start a new release: the
   release is written and pushed already. Fix it; the steps then light **Commit your changes**, **Push them** and
   **CI passes** for the fix, and step 6 reads **Start again on this commit**, which runs the release as it is
   written on the fix's commit.
7. **Device test,** on a PS5: it downloads the draft portal with `gh` (a draft needs the sign-in), checks it
   against its `SHA256SUMS`, installs it and starts it (`tools/check-release.sh draft`). Test it as a user would.
   When more than one portal of the run is still a draft, a choice beside Device test lists them; Device test,
   Publish, Not OK and the step's line follow the one picked there. Work pushed in the meantime (a fix found during
   the device test) does not end the release: while its draft waits, Device test and Publish stay at hand for it.
8. **Publish** when it works: the draft becomes a release, which makes its portal tag, and it becomes GitHub's
   **Latest** release; the installed portals offer it from then on. The new tag is fetched in the same command, so
   the step shows ✓ as soon as it ends: press Publish once. A portal that was open during the device test says its
   newest release as it was when it looked; **Y Check again** on its Settings page (or its hourly look) shows the
   release just published. **Not OK** leaves the draft unpublished: the Device test step turns red and says what
   comes next. Fix what the test showed; the steps start again from **Commit your changes**, then **Push them**,
   **CI passes** and **Start new release**, which builds the portal anew (a portal that was never published keeps
   its version; the apps already out are skipped). Until the fix is committed, **Device test** and **Publish**
   stay at hand, for a Not OK pressed by mistake.
9. **Bring in the pin commit** (**git pull**): the *Pin ...* commit is on main. Publish fetches main with the new
   tag, so it lights as soon as Publish ends (or as soon as GitHub's runs on main show that commit). Then every
   step shows ✓.

Above the steps, three boxes say how long the release takes: **This release**, **Previous release** and the
**Deviation** between the two. The time runs up to the device test and is GitHub's: CI on the commit the release
started from, plus the time from the release commit to the end of the release on GitHub. The waiting between the
two is not counted, nor the steps on this computer. While the release runs, its box shows the time so far. A
release that took more than 2 minutes longer than the one before it also shows the deviation in an orange banner;
a deviation under that, or of 0 or less, shows in its box only. Each box's tooltip names the release commit and
the two parts. The limit is `DEVIATION_LIMIT` in `dev/nrt/nexus_release_tool/flow.py`.

By hand, without the tool, the same run starts on the newest pushed commit with:

```bash
gh workflow run release.yml --ref main -f commit="$(git rev-parse origin/main)"
```

A run started again skips what is already published. A tag pushed by hand (`tools/tag-release.sh`, below,
`ps5-<app>-v<x.y.z>` or `ps5-portal-v<x.y.z>`) still releases that one app or portal, published at once. The
portal tag Publish makes starts `release.yml` too, as any pushed tag does; that run sees the release is published
already and ends at once. The tool's steps follow only the run Start started on main, never one on a tag.

## The window

The tabs are **Nexus release** (the steps above), **Contents** (what the release holds), **Retract app** (a
withdrawal, [below](#withdrawing-a-release)), **Remove suite** and **Commands**.

- **Remove suite**, on a PS5, opens a terminal that lists what of the suite is installed on the board and
  whether a test put it there (`tools/check-release.sh status`), then removes it all: every app, the portal,
  Board Test and Quickfix, each with its own uninstaller (`tools/check-release.sh remove`). Board Test asks for the sudo
  password. Settings, history and results stay; `tools/check-release.sh remove --purge` removes them too.
- **Device test** and the other tests of `tools/check-release.sh` clean up after themselves: on a PS5 without the
  suite, what the test installs is marked as a test's and removed again when the portal closes (the portal, Board
  Test and the apps installed during the test). On a PS5 that had the suite installed, the test saves the portal,
  Board Test and Quickfix first and puts them back when the tested portal closes, with the saved portal's own
  installer (Board Test asks for the sudo password); the apps installed during the test are removed, and an app
  updated during the test stays updated. `--keep` keeps what a test installed, and
  `tools/check-release.sh restore` puts the saved install back by hand, after a test that was cut short.
- What a step writes (the release, Retract, Test withdrawal, Remove suite) shows in **Commands**, under a line that
  names the step, with the output of the commands: one output tab. A step that writes its log opens Commands; open the step
  again to go on. The steps' logs go into the day's command log too (below).
- **The command line** in **Commands** runs a command in the checkout, so you need no separate terminal for the
  commands the steps show. Type it and press Enter; its output appears above the line as it runs. **Commands**
  lists the commands the last step showed (Retract's), one per line: pick one to put it on
  the line, then check it and press Enter. Up and Down bring back earlier commands, also from earlier sessions.
  **Stop** or Ctrl+C interrupts a command, along with anything it started in the background; `clear` or **Clear**
  empties the output.
  Each command runs with `bash -lc` in the folder the last `cd` left; variables you set do not carry over to the
  next command. A command cannot read input, so nothing can ask you something: git does not prompt for a password,
  opens no editor (commit with `-m`) and pages nothing. For a command that must ask, use a terminal; the
  `check-release` script, which asks for the sudo password and keeps the portal running, is handed to a terminal
  by itself when it is run from the line, and the output says so. After each command that changed the checkout (a
  commit, a push, a tag) the window reads it again, as **Refresh** does. Every command, its whole output and how it ended (its exit code) are also kept in a file of the day,
  `~/.cache/nexus-release-tool/commands/commands-<YYYY-MM-DD>.log`, so what a step said can be read again afterwards, or sent along when one
  went wrong.

**GitHub** in the header shows whether GitHub built your last push: every workflow run (CI, Release, Wiki) on its
commit, tags included. It reads the newest 30 runs of the repository; when they all belong to your commit (a
release of many apps starts many runs), it reads the rest of that commit's runs too, so the CI runs under them
count. It reads **building** while one runs, then **passed** or **failed**; right after a push, until GitHub has started the runs of that commit, it reads **building** too and the line under the pills says that it waits for GitHub, as the runs GitHub lists then are the commit's before; hover for each run, click
to open the run that failed (or still runs) on GitHub. A run GitHub canceled because a later run of the same
workflow on the same commit took its place is no failure: hover says **replaced by a later run**. It looks every 15
seconds while a build runs, every 10 seconds after a push until GitHub has started its runs (a few seconds after
the push), and every 5 minutes otherwise, and **Refresh** looks at once: its pill reads *Refreshing…* while it reads
the checkout and GitHub's runs (a second or two), then *Refreshed* with the time. When a run it saw running
finishes, a desktop notification says whether it passed. It needs no GitHub token: answers that did not change do
not count against GitHub's limit of 60 requests an hour.

The **ticker** under the pills says where the runs of that push stand, so you need not open GitHub to follow a
build. For each run that is still going it shows how many of its jobs are done, each job that runs with the step it
is at (*pytest (core): Run tests (4/7)*) and the time since the run started; a run that failed names its job and
step; a run that passed says so. The dot is blue while something runs, red when a run failed and green when all
passed. The line wraps when it is longer than the window is wide, so its end is always visible. Hover for every
job of every run; click to open the job that runs (or failed) on GitHub. While a run has failed, **Run again** at
its right starts that run's failed jobs again on the same commit (`gh run rerun <id> --failed`, in the Commands
tab). The jobs need a gh login (`gh auth login`): it then reads them every 10 seconds while a run goes. Without one
it shows the runs only, so the 60 requests an hour stay for the **GitHub** pill.

**GitHub status** beside it says whether GitHub itself works, as [githubstatus.com](https://www.githubstatus.com/)
reports it: a green dot while every part of GitHub is up, a red dot while the page reports a problem (an open incident,
also one GitHub is still monitoring after the page says All Systems Operational again, or a part such as Actions
or Pages degraded or down). A build that waits in *queued* for long is often such a
problem. Hover for the incident and the parts affected; click to open the status page. It looks every 5 minutes,
and **Refresh** looks at once.

**Claude tokens today** says how many tokens Claude Code on this computer used since midnight, read from its own
transcripts (`~/.claude`, or the folder `CLAUDE_CONFIG_DIR` names). Hover for the last 5 hours, the input, output and
cache tokens, and each model; click to open [Claude's usage page](https://claude.ai/settings/usage), which shows
your plan's limits. Other computers and claude.ai are not counted. Without Claude Code the pill is not shown. It
looks every 5 minutes, and **Refresh** looks at once.

The notifications are the desktop's own, through `notify-send` (without it, from the Nexus Release Tool icon in the
notification area, which appears with the first notification and goes when the window closes). A click on the
notification or the icon brings the window to the front.

A red line at the top of the window means a release tag points at a commit whose `VERSION` is not the tag's
version: the tag was made before the version bump was committed, and `release.yml` cannot build it. Delete the tag
(the line shows how), commit and push the bump, and tag again with `tools/tag-release.sh`.

`tools/tag-release.sh <tag> [...]` tags HEAD and pushes the tags, but refuses while HEAD does not hold each tag's
version (the bump is not committed yet), while that folder has uncommitted changes, while HEAD is not pushed to
`origin/main`, or when CI did not pass on HEAD: it asks GitHub (`tools/ci_state.py`) and waits while CI still runs,
up to an hour. A portal tag also waits for the app releases it pins: each one tagged on GitHub and pinned with its
sha256 (the release's *Pin ...* commit, or `tools/pin_app.py`), as the portal's release needs them. A plain `git tag` tags whatever HEAD is at that moment, also
the commit from before the bump or one CI failed. `release.yml` asks the same before it builds anything: a tag on a
commit CI did not pass gives no release. It then builds and publishes the release without an approval on GitHub
(see [GitHub settings](github-settings.md#environments)). `tools/tag-release.sh --help` prints its usage.

`tools/nrt.sh --list` lists every app with its version, its last tag and its pin, without Qt.

## Withdrawing a release

A release that must not be used any more, because of a privacy, security or any other problem, is withdrawn.
The release stays on GitHub, so its history is kept, but nothing installs it any more:

1. In Nexus Release Tool, tab **Retract app**: choose the app's pinned release, write why, and press
   **Retract**. This adds `withdrawn = "<reason>"` to its entry in `portal/apps.toml` and a CHANGELOG entry to the
   app. **Take back** removes it again.
2. **Test withdrawal** on the same tab with the app installed, on a PS5. It installs the portal from the
   checkout and starts it (`check-release.sh local`): the portal must say the app is not available any more,
   remove it, and then show **App not available** on its tile.
3. Mark the release on GitHub with the command the tab shows: `gh release edit <tag> --prerelease --title
   "Withdrawn: <tag>" --notes "..."`. A pre-release is skipped by every update check, so no app offers it.
4. Release the portal on the release tab, from **Commit your changes**: the commit asks for the portal bump the
   withdrawal needs (at least a minor version), and **Start new release** releases the portal. The withdrawn app
   is not released again. The portal's CHANGELOG entry names the withdrawal. A portal that updates to it removes
   the app; the portal update button says so beforehand ("withdraws ...").

Board Test and Quickfix, which are always installed, cannot be withdrawn.

## Checking a release

A release that `tools/build_release.py` built has the same content when you build its tag yourself, but usually
not the same checksum. The gzip compression of a `.tar.gz` differs between zlib builds (Fedora uses zlib-ng,
GitHub's Ubuntu runners zlib), so compare the unpacked files, not the `.tar.gz`. Board Test's build time in
`board_test/_build_info.py` is the commit time too:

```bash
git archive <tag> | tar -x -C /tmp/src
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct <tag>) python3 /tmp/src/tools/build_release.py <tag> /tmp/local
curl -LO https://github.com/RobertoTorino/bazzite-console/releases/download/<tag>/<tag>.tar.gz
mkdir -p /tmp/a /tmp/b && tar -xzf <tag>.tar.gz -C /tmp/a && tar -xzf /tmp/local/<tag>.tar.gz -C /tmp/b
diff -r /tmp/a /tmp/b
```

The checksum pinned in `apps.toml` is always the one of the published release. That is also why the release
tests pin their own local builds instead of the published ones.

## The releases on GitHub

Each release's title names the suite and the app, from the portal's name and `apps.toml`: *Bazzite Console Suite:
Portal 12.0.0*, *Bazzite Console Suite: Xenia Manager 0.11.0* (`tools/build_release.py` writes it). The tags start
with the suite's prefix, `ps5-` (`TAG_PREFIX`): `ps5-<app>-v<x.y.z>` and `ps5-portal-v<x.y.z>`.

A release is built and published by the release workflow (**Release**, `release.yml`): started on a release commit
by **Start new release** (or `gh workflow run`, above), or by a tag pushed by hand. Every push and pull request
starts **CI** (`ci.yml`); on the Actions page each run is titled with the push's commit message.

A release builds only a commit CI passed (`tools/ci_state.py`). The release commit is the exception that saves a
second CI run on the same code: when it changes nothing but what a release writes (`tools/release_commit.py`:
`VERSION` files and their copies, `Release x.y.z.` and `Version x.y.z.` entries on top of the CHANGELOGs, the `tag`
and `sha256` lines of `apps.toml`), the CI that passed on its parent, the commit you pushed before Start new
release, counts for it (`ci_state.py --release-commit`). Any other change in it, a line of code or a file added,
and the release waits for CI on the release commit itself, as does a commit whose parent CI failed on: the release
commit may fix what failed there, such as a version CI wanted bumped, so its own CI decides. CI still runs on the
release commit; nothing waits for it.

GitHub's **Latest** release is the newest portal. The app releases are published with `--latest=false`, so they
are never Latest, and the portal becomes Latest when it is published (by **Publish** for a draft, or by
`release.yml` for a portal tag pushed by hand). `/releases/latest`, which the READMEs and this wiki link to for the
download, therefore always opens the newest portal. Installed portals and apps do not use it: they find their
releases by their tag prefix (`portal-v`, `<app>-v`), reading GitHub's release list page by page, newest first,
until a page holds the prefix.
