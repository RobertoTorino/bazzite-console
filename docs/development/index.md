<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<span class="page-icon">:material-code-braces:</span>

# Development

How the repository is laid out, how to set it up and test it, how the wiki's pictures and tours are made, and how
the versions and releases fit together. How every app is built, and how to add one:
[Architecture and consistency](architecture.md). The development apps, from Nexus Dashboard for PS5 to Nexus Dependencies:
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
                              dev/deps/ Nexus Dependencies for PS5, dev/text/ Nexus TTS, dev/studio/ Nexus Remix Studio,
                              dev/garbage/ Nexus Garbage Remover, dev/flight/ Nexus Flight Recorder,
                              dev/textcheck/ Nexus Text Check for PS5
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

The tools the machine needs are in [The development machine](#the-development-machine).

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
it is. `tools/check-release.sh local` does the same and starts the portal, with the apps from the pinned GitHub
releases (`--source release`); `release` and `draft` install a published portal release or the draft of one
(`release` takes the draft while the release is not published).

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
is keyed on that file. The build folder of the native job's cargo is kept in the cache folder too. So cargo builds only what changed since the last run. The folder starts empty again when `Cargo.lock` changes, as GitHub's cache is keyed on that file. It works on a copy of the checkout with every change staged, as the commit will
have it. The copy is named as the checkout, as GitHub's is named after the repository. The installers job gets a copy of its own,
made before any job starts. The other jobs write in theirs while they run, such as pytest's cache in an app's folder.
An installer copies an app's folder with tar, which stops when the folder changes during the copy. On GitHub each
job has its own checkout as well. One run goes at a time on a
computer: a second one, from a terminal or Nexus Release Tool's Push, says that another run is going and waits until
it ends, as the two would share the venvs and the logs. Within a run the jobs go several at a time: half the cores, fewer when the free memory is short (one job per
1.5 GB, at least two; `--workers N` sets the number yourself), except a job that compiles (`native`, with
cargo): it runs after the others, alone, since its compilers need the computer's memory for themselves. The push commands Nexus Release Tool shows run it first
(`tools/ci-local.sh && git push`): no push when a job fails.
Each job's line shows when the job ends, with the seconds it ran.

Before each run it removes what earlier runs and tests left on the computer (`tools/clean_caches.py`): a venv no run
used for a week, the files pytest kept in `/tmp` of runs a day ago or longer, an AI assistant's scratch folders in
`/tmp` that did not change for six hours, and container images without a name. `/tmp` is kept in memory on Bazzite, so
what stays there takes memory from the tests. `python3 tools/clean_caches.py --dry-run` only says what would go. It
reports the system's crash dumps once they pass 1 GB, with the command that removes them (it takes sudo).
`./test.sh` keeps no files of a test that passed.

### Keeping the wiki accurate

Two checks keep the wiki in step with the code. The first fails on a name the wiki gives that is gone. The second
tells you which sections to read again after a change.

`tools/tests/test_wiki_names.py` runs with the other tests. It fails when a page names something that is not there:

- a path of the repository, in code style
- a constant or a function, in code style
- an option of one of the suite's scripts
- a window label that an app's chapter tells you to use

A name of something outside the suite goes in `OUTSIDE` in `tools/wiki_names.py`, with the reason.

`tools/check_wiki.py` lists each section that names a changed file but did not change itself. A section names a
file through its path, its file name, its module name or a name the file defines. An app's chapter names its whole
app folder. Read each listed section against the change, and correct what is no longer true:

```bash
python3 tools/check_wiki.py --base origin/main                 # what changed since origin/main, with the work tree
python3 tools/check_wiki.py --base <commit> --head <commit>    # between two commits
```

The list never fails a run. Nexus Release Tool's **Commit your changes** step shows it first on the **Commands** tab.

### Line endings and file names

- **Line endings:** `.gitattributes` makes every text file LF in the repository and in the working tree. Scripts,
  units and `.desktop` files reach the board with LF. CI rejects CRLF.
- **Executable bit:** when a script lost its executable bit, run `tools/fix-modes.sh` after `git add`: it marks every
  `.sh` as executable in the index. CI fails when a script is missing the bit.
- **Venv:** one venv in the checkout, `.venv-linux/`, ignored by git.
- **File names:** Linux and GitHub are case-sensitive. Keep links and asset names in exactly the case of the file.

## The development machine

This part says what a Bazzite machine needs to work on the suite, and how it stays up to date. The checks before a
push are in [CI on your own machine](#ci-on-your-own-machine).

### Tools

A tool the work needs more than once is installed for good. It is not run once in a container. The prerequisites
belong on every development machine. The optional tools belong on the machine that does that work.

#### Prerequisites

`./test.sh` and `tools/ci-local.sh` need these:

| Tool | What uses it | How to get it |
|---|---|---|
| Git | everything | comes with Bazzite |
| Python 3.11 or newer | the venv and every tool in `tools/` | comes with Bazzite as `python3`, without PyQt6 |
| The development venv | `./test.sh`, `mkdocs` and the tools, with pytest, PyQt6, MkDocs Material and Pillow | `.venv-linux/`, see [Set up and test](#set-up-and-test) |
| Homebrew | installs the tools below | comes with Bazzite |
| podman | `tools/ci-local.sh` runs CI's jobs in a container, and the text check runs LanguageTool in one | comes with Bazzite |
| shellcheck | the shell checks of CI | `brew install shellcheck` |
| fakeroot | the installer tests in `tools/installer-tests/` | `brew install fakeroot` |
| zip, tar, sha256sum | `tools/build_release.py` | come with Bazzite |

#### Optional

Each one serves one tool or one kind of work. Without it, that tool does not run, or its test skips.

| Tool | What uses it | How to get it |
|---|---|---|
| Vale | the text check, `tools/text_check.py`, for style and readability | `brew install vale` |
| Node.js | the design panel's test, `tools/tests/test_design_panel.py` | `brew install node` |
| GitHub CLI (`gh`) | runs and releases from a terminal, and Nexus Release Tool's sign-in | `brew install gh` |
| actionlint | a changed workflow in `.github/workflows/`, checked before the push with `actionlint` at the root | `brew install actionlint` |
| mawk | Board Test's `tests/test_awk.py`, which runs each awk program under gawk and mawk, the awk of Debian and Ubuntu | `brew install mawk` |
| ffmpeg | the video tours, `tools/record-tour.sh` and `tools/record-app-tour.sh` | comes with Bazzite |
| Nexus TTS's speech engine | the voice of the Portal Tour, `tools/record-tour.sh` | **Set up the speech engine** in [Nexus TTS](dashboard.md#nexus-tts). It needs uv (`brew install uv`) or a Python from 3.10 to 3.13 |
| Rust, maturin, nasm and the libva headers | Remote Play's native core, for `cargo test` or `maturin build` on the machine itself | rustup from [rustup.rs](https://rustup.rs), `brew install nasm`, and maturin with pip in the venv |
| OBS Studio, with its WebSocket server on | Nexus Demo Recorder (`dev/demo/`) | the Flatpak `com.obsproject.Studio` |
| notify-send | the hourly notifications of Nexus Dependencies and Nexus Garbage Remover | comes with Bazzite |
| setools (`sesearch`, `seinfo`) | reading the SELinux policy on the board, such as which label a file needs | in a distrobox, see below |

The container of `tools/ci-local.sh` has Rust, maturin, nasm and the libva headers, so a CI run needs none of
them on the machine.

`setools-console` is a Fedora package that Homebrew does not have. A distrobox keeps it off the image, without
`rpm-ostree install` or a restart. It puts the two commands in `~/.local/bin`:

```bash
distrobox create --name nexus-tools --image registry.fedoraproject.org/fedora-toolbox:44 --yes
distrobox enter nexus-tools -- sudo dnf -y install setools-console
distrobox enter nexus-tools -- distrobox-export --bin /usr/bin/sesearch --export-path ~/.local/bin
distrobox enter nexus-tools -- distrobox-export --bin /usr/bin/seinfo --export-path ~/.local/bin
```

Inside the distrobox, the board's own files are under `/run/host`, so give the policy by that path:
`sesearch -A -s unconfined_service_t -c system -p module_load /run/host/etc/selinux/targeted/policy/policy.35`.
`distrobox rm nexus-tools` removes it again.

Homebrew installs to `/home/linuxbrew/.linuxbrew/bin`. A shell that is not interactive, such as a timer or an IDE's
terminal, may need it on `PATH`.

### Staying up to date

Bazzite keeps itself current. Its updater, `uupd.timer`, runs every day at 04:00, or at the next boot when the
machine was off. It updates the image, the Flatpaks and Homebrew's packages. `ujust update` runs the same now. A new
image is used after a restart. The venv is pip's and the Rust toolchain is rustup's, so nothing updates those for
you.

[Nexus Dependencies](dashboard.md#deps) shows every source with a newer version at once: Bazzite's image, the Flatpaks,
Homebrew's packages, the Rust toolchain and the packages of `.venv-linux`. **Update** on a card installs that
source's updates after it shows the command and asks. Its hourly notification says when something is newer.

The venv's packages are upgraded within what `requirements-dev.txt` allows. The venv's `python` links to Bazzite's
`/usr/bin/python3`, so a Bazzite image with a newer Python leaves the venv without its packages. Nexus Dependencies says so,
and **Update** installs `requirements-dev.txt` for the new Python.

### Starting the previous Bazzite version once

A Bazzite update keeps the version before it on the drive. Starting that version once shows whether a problem came
with the update, such as with its kernel. `rpm-ostree status` lists both versions, and a dot marks the running one.

GRUB is the program that starts Bazzite. Its menu shows for one second, with the new version first and the previous
one second. `grub2-reboot` chooses an entry for the next start only. Bazzite's `/boot/grub2/grub.cfg` never reads
that choice, so the command alone changes nothing. It does read `/boot/grub2/custom.cfg`. Write the missing step
there once, when the file does not exist yet:

```bash
sudo tee /boot/grub2/custom.cfg > /dev/null <<'EOF'
# Start the entry that grub2-reboot chose, once.
if [ "${next_entry}" ]; then
  set default="${next_entry}"
  set next_entry=
  save_env next_entry
fi
EOF
sudo grub2-script-check /boot/grub2/custom.cfg
```

Then choose the previous version and restart:

```bash
sudo grub2-reboot 1
systemctl reboot
```

Entry `1` is the previous version and entry `0` is the new one. After the restart, `uname -r` shows the kernel of
the previous version. The start after that one uses the new version again. `custom.cfg` can stay. It does nothing
until `grub2-reboot` runs again.

Each Bazzite version keeps its own `/etc`. A change made there while the previous version runs is missing in the
new version. Make it again after the next start.

### Keeping it clean

[Nexus Garbage Remover](dashboard.md#garbage-remover) shows what can go from the machine. That is crash dumps, Steam's
crash reports, the Trash and caches that fill up. It deletes what you check, after it asks. Its hourly notification says
when there is 1 GB or more. Our tools' own leftovers go by themselves: `tools/clean_caches.py` removes them before
every local CI run.

### Git identity and signing

Git takes your name and email from its global settings. Without them, it makes some up from the user and host name,
and warns at every commit. GitHub links a commit to an account by its email. So use the account's noreply address,
which GitHub shows under **Settings**, **Emails**. Sign commits with the SSH key the account has as a signing key,
under **Settings**, **SSH and GPG keys**:

```bash
git config --global user.name "Your Name"
git config --global user.email "<id>+<user>@users.noreply.github.com"
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
## so that git log --show-signature can verify your own commits
echo "$(git config --global user.email) $(cat ~/.ssh/id_ed25519.pub)" > ~/.ssh/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

Leave tag signing off. The release tags are plain tags, made by `tools/tag-release.sh`. A signed tag needs a
message, which breaks `git tag <name>` in the tools' tests. These settings are per machine and per user account, so
a new system or a new home folder starts without them. Check them with `git config --global --list`. After a commit,
`git log -3 --format='%an <%ae> %G?'` shows `G` for a good signature.

## Colors

[DESIGN.md](https://github.com/RobertoTorino/bazzite-console/blob/main/DESIGN.md) lists every color of the suite: the
rules that make its design recognizable, every tint of each hue and why it is there, and where each color is used
(the apps' themes and state colors, the wiki, the development apps, the apps' own colors). Each color shows a sample
from `design/colors/`. Both are written by `tools/make_design.py` from the listing in it: change the listing and run
it, never DESIGN.md itself. DESIGN.md also lists every icon of the suite and where it is used. `tools/design_icons.py`
reads that part from the repository.

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
or from [Nexus Dashboard for PS5](dashboard.md#video-tours).

`tools/record-tour.sh` records the portal's tour, about three minutes long. It opens as the portal does:

1. The title card shows in silence.
2. The intro plays with its own sound.
3. The welcome plays after the intro.
4. The music starts when the welcome has ended and fades out over the last two seconds.

The music is `tools/sounds/the_quiet_engine_remix.ogg`, made with generative AI tools. `--no-music` leaves it out.

A voice reads every caption out. Nexus TTS's speech engine makes it, in its default voice. Set the engine up once in
[Nexus TTS](dashboard.md#nexus-tts) with **Set up the speech engine**. The music plays quietly under the voice. A
caption stays on screen until the voice has spoken it. The tour spells a few words another way for the voice, so it
says them right. The list is `SPOKEN` in `tools/tour_frames.py`. With `--no-voice` the tour has no voice. The music
then plays at full volume. Without the voice, a caption stays until there was time to read it.

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
  `~/.local/share/bazzite-console-suite/state`), the shared venv `~/.local/share/bazzite-console-suite/venv` (PyQt6
  and pygame-ce, used by all suite GUIs and removed with the last of them), plus each app's settings, results and launchers.
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
the new pin tried on the board first. Until then, users can choose the newer build themselves in the manager's
version manager.

Each emulator manager pins the build that version of the app was tried with. **Install** installs that build and puts
it back in use. In the manager's version manager (core's `builds`), you can download
any other build the emulator publishes on GitHub, a stable release or a nightly. The app checks it against the
SHA-256 GitHub publishes. So the pin says which build was tried on the board, not which builds users may run.

The PS5 shadPS4 Manager was tried with one shadPS4 release, pinned in `apps/shadps4/shadps4_manager/emulator.py`
(`VERSION`, `TAG`, `ASSET`, `SHA256`). The tool checks it: a newer stable release, with the Linux zip and the
SHA-256 GitHub publishes for it that a new pin needs, and the SHA-256 of the pinned zip. A new shadPS4 can change
what the app relies on (its `config.json`, the shadNet protocol), so a new pin also needs a look at what changed.

PS5 KytyPS5 Manager was tried with one KytyPS5-Native release. It is pinned in
`apps/kytyps5/kytyps5_manager/emulator.py` as `VERSION`, `PUBLISHED`, `SIZE_MB` and `SHA256`. KytyPS5-Native names
a release after its date and commit, so the tool compares the dates. It checks these:

- a release published later than the pinned one, with its Linux archive and the SHA-256 GitHub publishes for it
- the SHA-256 of the pinned archive

A new KytyPS5-Native can change its options, the files in its archive or its GPU helper. So a new pin also needs a
look at what changed, and a try on the board.

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

The PS5 Vita3K Manager was tried with one Vita3K build, pinned in `apps/vita3k/vita3k_manager/emulator.py`
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

The tests hold the `config.yml` a Vita3K build writes on its first start (`tests/fixtures/config-4377.yml`); a new
pin replaces it with the new build's, renamed for it.

The PS5 Xenia Manager was tried with one Xenia Canary build, pinned in `apps/xenia/xenia_manager/emulator.py` (`BUILD`,
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
the tool reads the version from Ookla's Homebrew formula. The same script installs Prime95's mprime: the release
mersenne.org's download page lists, with the SHA-256 listed there. `MPRIME_URL` and `MPRIME_SHA256` in it are one
known release, used only when the page cannot be read. Nexus Dependencies compares `~/mprime/.release` with the page.

```bash
python3 tools/check_upstream.py            # all of them
python3 tools/check_upstream.py helixsr    # one: shadps4, kytyps5, helixsr, ppsspp, pcsx2, rpcs3, vita3k, xenia,
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
| `widgets` | `AppHeader` (the window header), `StatusPill`, `StatusText` (a state beside a title; with a name, the name alone, a green or red dot and the state in its tooltip), `MetricBox`, `Pill` (a `MetricBox` that is a button), `same_width()`, `RefreshButton`, `ClickableLogo`, `Terminal`, `TextDialog`, `RoundedToolTip`, `WheelGuard`, `show_tooltip()`, `page_header()`, `hint_label()`, `accent_button()`, `set_button_active()` |
| `app` | `create_app()` / `run_app()` / `exec_app()`: names, Fusion with the theme, tooltip, wheel guard, icon, SIGTERM |
| `exit_keys` | `install(app)`: Escape and a controller's B close the app's window, after a key the window takes for itself and through its `closeEvent`; the controller, read with pygame-ce, works the app (the d-pad and the stick move the focus, A presses, LB and RB change the tab, B is Escape for what has the focus, the touchpad moves a uinput mouse at the portal's **Touchpad** speed), and only for the app that has had the focus for a moment; `install(app, controller=False)` for Escape alone, the class attribute `exit_keys = False` for a window that keeps every key. SDL's dummy drivers are in the environment only while SDL starts, so a program the app starts never gets them. Self-contained, so an app not on core carries a copy |
| `card` | `CardWindow`: the template of a small window, with the header's two symbols and rows of five even places |
| `action_tab` | `ActionTab`: the last tab of a `QTabWidget` as a button (Start game in the game managers): a click acts and the open page stays open |
| `log_page` | `LogPage`, the View logs tab of a game manager. Two radio buttons choose the app's log or `emulator.log` beside it, which the run wrapper writes. Clear logs empties the log shown |
| `gamelog.sh` | The emulator log of a game manager's run wrapper. The wrapper sources it and ends with `gamelog_run`. It writes the game's build, board, game, controllers, displays and memory before the start. After the end it writes the exit code, the time the game ran and the system log's crashes. Every line has its time and a level |
| `settings` | `open_settings(info)` at each app's existing file, geometry helpers, `SettingsStore` (typed defaults) |
| `help` | `HelpView` (the content stays in the app) |
| `updates` | `latest_release()` (with a tag prefix for the per-app tags: GitHub's release pages, newest first, are followed until one holds the prefix, since other releases can fill the first page), `UpdateStatus`, `UpdateChecker` (any job, off the GUI thread) |
| `builds` | Several builds of an emulator side by side (the game managers' version manager): each in a folder of its own with a `build.json`, `current` pointing to the one in use; `install()` (checked against its SHA-256, GitHub's digest or a pinned one), `use()`, `delete()`, `add_custom()`, `replaced()`, `github_builds()` and `github_latest()` (a repository's builds with GitHub's SHA-256) |
| `builds_dialog` | `BuildsDialog`, the version manager's window (Installed: Use, Delete, Add; Download: Refresh, Download; the tested build marked Tested), and `fill_menu()`, the menu of a manager's version pill |
| `platform` | XDG folders, `xdg_open()`, `launch_in_terminal()` (with an exit file the caller can watch), `show_in_folder()`; `private()`, a path or a text with the home folder as `~`, never the user's name, which `applog.setup(private=True)` applies to every line of a log |
| `processes` | `find()` gives a program's running processes in `/proc` by name, without zombies. `end()` ends them and everything they started, as the managers' **Exit** button does (standard library only) |
| `steam` | Steam's folders and users, `installed()`, `with_steam_closed()`, `shortcuts.vdf` and the shortcuts' artwork in `grid/`, `shortcut_number()` and `play_url()` (a shortcut's number in Steam's file, and the address that starts it), `signed_in()` (whether Steam runs and is signed in, from its connection log), and `steam_environment()` (Steam started without the SDL values of our controller readers) (standard library only) |
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
