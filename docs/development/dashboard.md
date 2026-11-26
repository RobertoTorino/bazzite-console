<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<span class="page-icon">:material-view-dashboard-outline:</span>

# Dashboard

The **Nexus Dashboard for PS5** (`dev/dash/` in the repository) is the one door to the tools for working on the suite.
Its tiles start the development apps of the checkout, each in a window of its own, and open the suite's tools;
below them, Test local apps starts the suite's own apps and its wiki from the checkout. Like every development app
it runs from the checkout it lives in, takes Nexus's design and icon, and has no releases of its own: nothing of it
is in the portal.

The suite's own scripts stay in `tools/`: the dashboard runs them there. A tile is grayed out where it does not run
on this system, and says why in its tooltip.

## Start it

From the repository's root, with the checkout's venv (`.venv-linux`, see
[Set up and test](index.md#set-up-and-test)). Nothing is copied when you install it: the menu entry always
starts the app of the checkout you installed it from. After moving the checkout, install it again.

```bash
dev/dash/run.sh                             # open it
dev/dash/install.sh                         # app menu entry and Desktop icon
dev/dash/install.sh --no-desktop-shortcut   # app menu entry only
dev/dash/install.sh --uninstall             # remove them; the checkout stays
dev/dash/install.sh --uninstall --purge     # also remove the settings
```

Run the installer as your own user, not with sudo. Then a double-click on **Nexus Dashboard for PS5** on the Desktop, or
its menu entry, opens the dashboard.

Opening the dashboard while it is already open closes the open window and opens a new one: the app runs from the
checkout, so the new window has the code as it is now. An open dashboard that does not answer within 5 seconds is
ended.

## The window

The header holds the icon, the name and the checkout's last commit with its time (a development app has no
version). A click on the icon opens the suite's wiki. Below it are the tiles, then
[Test local apps](#test-local-apps), and under them a line for each click: which app started and where its log is,
or why a tile is off.

The first tiles are the development apps of the checkout. A click starts the app with its run script, in a window
of its own that keeps running when the dashboard closes.

| Tile | What it opens |
|---|---|
| **Nexus Release Tool** | The release front end: a release's versions, CHANGELOG entries, pins and portal bump, and the board checks ([Releases](releases.md)). |
| **Nexus Demo Recorder** | A portal installation recorded with OBS ([below](#demo-recorder)). |
| **Nexus Deps** | The suite's Python packages and tools on this machine, what is missing or outdated, and Fix for it ([below](#deps)). |
| **Nexus Garbage Remover** | The garbage on this machine, with its size, and Delete for it ([below](#garbage-remover)). |
| **Nexus Installer Tests** | The suite's installer tests, one at a time ([below](#installer-tests)). |
| **Nexus Marketing for PS5** | Writes an article that presents the portal and its apps, as a web page to share ([below](#marketing)). |
| **Nexus Remix Studio** | Mixes a voice with a synthesized background and saves the result ([below](#remix-studio)). |
| **Nexus Sound Lab** | Short sound effects for the suite's windows, made from sliders ([below](#sound-lab)). |
| **Nexus TTS** | Speaks an English text in a natural voice and saves it as a sound file ([below](#nexus-tts)). |

The other tiles work on the suite:

| Tile | What it opens |
|---|---|
| **Portal video tour** | Records the portal's tour ([below](#video-tours)). |
| **Apps video tour** | Records a short tour of each app you tick ([below](#video-tours)). |
| **Convert icons** | Makes a category's icons from your images ([below](#convert-icons)). |
| **Close issues** | Closes the open issues on GitHub you tick ([below](#close-issues)). |

## Test local apps

Under **Test local apps** are the suite's portal and every app window of it in the checkout, as an icon (the portal
first). A click starts that app from the checkout, to try a change before its release. They start as
`python -m <package>` with the checkout's venv and its `core`, as `run.sh` starts a development app. When the
portal is already open, its icon warns instead of starting: a second portal never opens (starting it only brings
the open window to the front), so close it first. An app that changes how the board runs (an orange **!**
on its icon) asks first, as in the portal; started from the checkout it uses the scripts in the checkout. Each app
writes its output to `~/.cache/nexus-dashboard-ps5/local/<package>.log`. When an app stops with an error, the end of its log
shows below. The apps keep running when you close the dashboard. The round **i** beside the title says the same.

The last icon is the wiki: **Bazzite Console Suite wiki (local)** serves it from the checkout with `mkdocs serve`
(the development venv has MkDocs) and opens it in the browser at `http://127.0.0.1:8775/bazzite-console/`, with its
design panel open. It rebuilds on every save; its log is `mkdocs-root-local.log` there. When it is already
running, a click only opens the page again. The wiki, like the apps, keeps running when you close the dashboard,
which has no button that stops it. A wiki started before the checkout changed (after a pull, or a change to
`mkdocs.yml` or the design panel) can still show the old setup: stop it, then click its icon again.
`pkill -f "mkdocs serve"` stops it.

With **Wiki on the network** ticked, the icon serves the wiki on every address of the computer, at port 8795, so a
handheld, a laptop or the TV opens it too: the addresses for those devices show below once the wiki started. The
computer's firewall has to let them in.

## Close issues

**Close issues** lists the open issues on GitHub, such as the weekly Upstream review, each with a tick box. **Run**
closes the ticked ones with `gh issue close`, one after the other, with a comment when you write one; their output
shows below, and when one fails the ones after it stay open. It needs the GitHub CLI with a login
(`gh auth login`). A double click opens an issue on GitHub.

## Video tours

The tours are recorded from the checkout as it is now, from the real windows, offscreen: nothing shows on the
screen while they record. They go to your Videos folder, with music under them that fades out over the last two
seconds (untick **Music under the video, faded out over the last two seconds** for a video without sound).
**Size** is 1080p (1920 × 1080) by default, the wiki's; choose 2160p (4K, 3840 × 2160) for a video for YouTube,
which shows a 4K upload far sharper than a 1080p one: the same tour, drawn at twice the scale so the text stays
crisp, about four times the time, and `-2160p` before `.mp4` in its name (1440p is the step between). A recording runs in the background; its output shows in the dialog,
**Stop** ends it, and **Play** opens the video in your video player.

- **Portal video tour** records the portal's tour, about three minutes: `ps5-portal-tour-v<portal version>.mp4`.
  The dialog checks **A voice reads the captions out, with Nexus TTS's speech engine** at first. Uncheck it for a
  tour without the voice.
  Tick **Also write the copy on the wiki's Portal Tour page** to write `docs/videos/portal-tour.mp4` and its poster
  in the checkout too, for you to review and commit.
- **Apps video tour** lists every app of the suite. Tick the apps (**All**, **None**), set the **Length** (40
  seconds by default) and choose **Record**: each tour takes a few seconds,
  `ps5-<app>-tour-v<version>.mp4`. Double-click an app to play its video. What an app reads from the board is
  real, so watch a video before you publish it.

The dialogs run `tools/record-tour.sh` and `tools/record-app-tour.sh` with the checkout's development environment;
they need ffmpeg. The same scripts run from a terminal:
[The wiki's pictures and tours](index.md#the-wikis-pictures-and-tours) says how. The music under every tour is in
`tools/sounds/`.

## Convert icons

Every app in a category shares the category's icon, kept in `icons/<category>/` at 1024, 512, 256 and 128 px.
**Convert icons** makes a category's icons from your images: one image for every size, or an image for a single
size. They are scaled, saved under the category's names as WebP (the 128 px icon as PNG), and copied to every app
of the category, the portal's tiles and the wiki, as `icons/categories.toml` says. Images must be square.

The dialog shows the current icons of the chosen category; **Convert and copy to the apps** runs
`tools/sync_icons.py`, whose output shows in the dialog; the icons and their copies are changed in the checkout, for
you to review and commit.

## Demo Recorder

The **Nexus Demo Recorder** (`dev/demo/`) records a demo of a portal installation with OBS: a portal release
extracted in Downloads (found by itself; **Find in Downloads** looks again, **Choose folder…** takes another), or,
without one, the suite in this checkout, whose `portal/install.sh` installs the released apps from the checkout's
source. `dev/demo/run.sh` and `dev/demo/install.sh` start and install it on their own.

Before you record, have:

- **The checkout's venv** with `requirements-dev.txt` installed: it brings the OBS WebSocket client (`obsws-python`)
  and the desktop portal's client (`dbus-fast`).
- **OBS Studio 30 or newer**, running, which has WebSocket 5.3 built in: the recorder sets the recordings folder
  through it. On Bazzite the flatpak `com.obsproject.Studio` (or an `obs` on the PATH). **Open OBS** starts it.
- **In OBS, a scene with a screen-capture source** (on Wayland: Screen Capture through PipeWire) whose preview
  shows your desktop.
- **OBS's WebSocket server on:** Tools, WebSocket Server Settings, **Enable WebSocket server**, with a password.
  Note the port (4455 unless you changed it) and the password for step 1.
- **A portal release:** an extracted portal release in Downloads, or the suite in this checkout. **Open the
  releases page** goes to them.
- **A clean system for a fresh install:** the portal not installed, and the app you want to show not installed.
  The recorder checks both and keeps **Start recording and install portal** off until they are gone.
- **A terminal emulator** (Konsole, GNOME Terminal, Ptyxis, Xfce Terminal, foot, Alacritty, kitty or xterm, or the
  one `$TERMINAL` names) for the installer and its password prompts, and a desktop whose portal offers global
  shortcuts (KDE Plasma, as on Bazzite) for the stop shortcut.

1. **OBS setup:** OBS needs a scene with a screen-capture source (on Wayland, Screen Capture through PipeWire) and
   its WebSocket server enabled (Tools, WebSocket Server Settings); **Setup instructions** has the steps. Enter the
   port and the password and **Test connection**: the recordings go to `~/Videos/demos`.
2. **Portal release and app:** the release and the optional app to show; the portal and that app must not be
   installed yet, since the demo is a fresh install.
3. **Record:** **Start recording and install portal** starts the OBS recording and the portal's installer in a
   terminal, for its output and its password prompts; the window hides. Once the installer is done the portal
   opens: show PS5 Board Test, install the chosen app and open it. The global shortcut the window named
   (Ctrl+Alt+F12 by default) stops the recording and brings the window back; **Recent recordings…** lists the
   videos and plays one.

## Installer tests

**Nexus Installer Tests** (`dev/itests/`) runs the suite's installer tests, `tools/installer-tests/*.sh`, one at a
time (bash, with fakeroot), with their live output on the right and each one's result at the end of its row. Tick
the tests and **Run selected**, or **Run all**; **Stop** ends the one that runs and skips the rest. Each test
installs an app from the checkout as its installer does on a board and removes it again, in a temporary home:
nothing of yours is touched. The tests use fixed temporary folders under `/tmp`, so the same test is never run
twice at once. `dev/itests/run.sh` and `dev/itests/install.sh` start and install it on their own.

## Sound Lab

**Nexus Sound Lab** (`dev/sounds/`) makes and tries the short sound effects a window plays, such as the tick when
the controller moves the focus in the portal. Choose a **Preset** to start from (Tick, High tick, Blip, Thock, Click,
Select, Back, Error, Tick after silence) and a **Waveform** (sine, triangle, square, saw or noise), then shape the
sound with the sliders: the pitch at the start and the end of a tone (a sweep when they differ), the length of a
tone, the attack (the rise to full volume) and the decay (how fast it dies away, per second), the number of tones
and the interval between them in semitones (two tones a fifth apart make a blip), the noise over the tone and its
own decay, the silence before the sound, and the volume (its peak). The sound is drawn beside the sliders and plays
each time a slider is let go, with **Play**, or when the focus moves between the buttons of **Try it: move
between the buttons** (Tab, the arrow keys or a controller's d-pad; A plays it again), the way a window plays it
while you navigate. Once a slider
has left the preset the box says Custom. **Save as WAV…** writes the sound as 16-bit mono at 44.1 kHz, for the
portal's sounds folder (`portal/bazzite_console_portal/sounds/`, where it plays a sound by its file name). The last
sound, the preset and the save folder are remembered.

**Keep the audio link awake**, on by default, plays a silent loop while the window is open. Without it a short
sound can stay silent on a TV: PipeWire pauses the output when nothing plays, and an HDMI TV mutes a moment after
the stream stops and needs time to unmute when it starts again, so a 50 ms tick is over before it is heard. The
preset Tick after silence shows the same from the other side: with the link asleep, only its tick comes through. A
window that plays such sounds needs the same loop while it is open. `dev/sounds/run.sh` and
`dev/sounds/install.sh` start and install it on their own, and the dashboard's tile does the same.

## Nexus TTS

**Nexus TTS** speaks an English text in a natural voice and saves the speech as a sound file. Use it for a video's
voice-over or a spoken note. The voices run on the machine itself, and nothing of your text leaves it. The app is in
`dev/text/`.

Type or paste the text, choose a **Voice** and a **Speed**, and click **Speak**. Ctrl+Enter does the same. The first
sentence plays while the app makes the next ones. An empty line in the text gives a longer pause. **Stop** ends the
speech, and so does Esc.

- **Voice** lists the 15 English female voices of the Kokoro model. Each one shows whether it is American or
  British. The list opens on Heart. The model's male voices and its voices in other languages are not offered.
- **Speed** goes from 0.50 to 2.00. At 1.00 the voice speaks at its own pace. The app opens on 0.85.
- **Save as…** writes the speech as an Ogg Vorbis, MP3, FLAC or WAV file, at 24 kHz mono. The file's suffix sets the
  format. You do not have to click **Speak** first. A text you just heard is saved as you heard it.

The text must be English. The app does not speak a text with letters of another script, such as Cyrillic or
Chinese, and says so in the status line. It cannot tell another language in Latin letters from English, and reads
such a text with English sounds.

The app remembers the text, the voice, the speed, the save folder and the format.

### The speech engine

The speech engine is the program that makes the speech. It is not in the repository, so the app downloads it once.
The first time, the window shows **Set up the speech engine** in place of the text. Click it, and the window shows
each step. The download is about 350 MB, and it goes to `~/.local/share/nexus-text-to-speech/`. After that, the
window opens on the text.

The setup needs one of these:

- [uv](https://docs.astral.sh/uv/), which brings the right Python by itself. Install it with `brew install uv`.
- A Python from 3.10 to 3.13 on the PATH

The engine has its own Python because onnxruntime, one of its packages, has no build for the Python of the
checkout's venv. The app checks each model file against its SHA-256 before it keeps the file. When a step fails, the
window says so. Click **Set up the speech engine** again to retry.

The app uses the half-precision model, `kokoro-v1.0.fp16.onnx`, a file of 164 MB. On the test machine it makes speech
about three times faster than the voice speaks it. It is as fast as the full model, at half the download. The engine
starts with the window and stays, so the model loads once. When the engine stops by itself, the window says so, and
**Speak** starts it again. The engine's own messages are in the app's log. The dashboard names that log when it
starts the app.

`dev/text/run.sh` starts the app without the dashboard, and `dev/text/install.sh` gives it a menu entry.
`dev/text/install.sh --uninstall --purge` removes the speech engine and the settings.

## Remix Studio

**Nexus Remix Studio** mixes a voice with a synthesized background and saves the result as a sound file. Use it to
put a soft pad under a voice-over. Everything is made on the machine itself. The app is in `dev/studio/`.

The window has three parts, from top to bottom.

### Voice

- **Open a sound file…** takes a WAV, Ogg Vorbis, FLAC or MP3 file as the voice.
- **From a text…** opens a small window. Type an English text, choose a voice and a speed, and click **Make the
  voice**. [Nexus TTS](#nexus-tts) speaks it, so its speech engine must be set up first.
- **Remove** takes the voice out. The mix is then the background alone.
- **Remove silence** cuts the silence at the start and the end of the voice. A pause inside the voice stays.
- **Save a copy…** writes the voice alone, as it is now, as an Ogg Vorbis, MP3, FLAC or WAV file.

The voice is drawn below the buttons.

**Silence below** sets what counts as silence, from -60 dB to -20 dB. The app opens with -40 dB. A higher level cuts
further into a soft start or end. Choose -20 dB to cut a slow fade-in up to the first loud sound. The status line
says how much was removed.

**Remove silence** changes only the voice in the window. The sound file stays as it is. Open the file again to get
the whole voice back. To trim a sound file, open it, click **Remove silence** and then **Save a copy…**. The copy
gets a name of its own, because the app never writes over the voice's file.

### Background

The background is a sustained sound, a pad or a drone, that the app makes itself.

- **Preset** is a sound to start from. There are six: Warm pad, Soft strings, Drone, Glass, Choir and Dark. The box
  says Custom once you change a control.
- **Key**, **Octave** and **Chord** set the notes that sound together.
- **Tone** goes from dark and soft to bright.
- **Movement** sets how much the sound drifts and swells over time. With the slider at 0, the sound stands still.
- **Space** is the reverb, from a dry sound to a large hall.

**Try background** plays 12 seconds of it alone.

### Mix

- **Voice volume** and **Background volume** set how loud each track is. The app opens with the background at 40 %,
  so the voice stays clear.
- **Lead-in** is how long the background plays before the voice starts, and **Tail** how long it goes on after.
- **Fade** is the background's fade in at the start and its fade out at the end.
- **Length** is how long the mix lasts. Without a voice you set it freely, from 5 to 600 seconds. With a voice it
  is the lead-in, the voice and the tail together, and moving it changes the tail.

The pills at the top work on the mix. **Play** makes the mix and plays it. Ctrl+Enter does the same. **Stop** ends
it, and so does Esc. The mix is drawn
below the sliders, with its length. A minute of mix takes about five seconds to make.

**Save as…** writes the mix as an Ogg Vorbis, MP3, FLAC or WAV file, at 48 kHz stereo. The file's suffix sets the
format. You do not have to click **Play** first. A mix you just heard is saved as you heard it. The same settings
always give the same sound.

**Reset** puts the background and the mix back on the values the app starts with. The voice stays.

When both tracks together are too loud for the file, the app turns the whole mix down. It says by how much under
the drawing. Nothing is clipped.

The app remembers the voice file, the silence level, the background, the mix, the save folder and the format.

`dev/studio/run.sh` starts the app without the dashboard, and `dev/studio/install.sh` gives it a menu entry.

## Deps

**Nexus Deps** (`dev/deps/`) lists the Python packages and external tools of the suite's apps installed on this
machine, which apps and features use them, and what is missing or must be updated; **Fix** installs that. On top,
it shows whether a Bazzite update waits for you and every update the machine has: Bazzite's image, the Flatpaks,
Homebrew, Rust, the development venv and Prime95's mprime when it is in `~/mprime`. It runs from the checkout, like every development app; its catalog of the
suite is `dev/deps/nexus_deps/catalogs/bazzite-console.toml`.

```bash
dev/deps/run.sh                             # open it
dev/deps/run.sh --fix                       # open it and offer Fix as soon as the check is done
dev/deps/run.sh --remind                    # no window: the hourly check once, from a terminal
dev/deps/run.sh --sync-upstreams            # the list of emulators in line with the apps' pins again
dev/deps/install.sh                         # app menu entry, Desktop icon and the hourly reminder
dev/deps/install.sh --no-desktop-shortcut   # the same without the Desktop icon
dev/deps/install.sh --uninstall             # remove them and the reminder; --purge also the settings
```

Installing it removes the development machine's hourly `nexus-dev-updates.timer`: Nexus Deps takes its place.

**Bazzite**, the first card, shows the Bazzite image the machine runs (its version and build date), whether a newer
one is installed and waits for a reboot, and when Bazzite's updater last ran. That updater, `uupd`, runs every
night by itself and updates the image, Flatpaks, Homebrew and distroboxes; a new image takes effect at the next
boot, so an update can wait unnoticed for days. The card turns to **Reboot to update** then. It also warns when
the updater failed on its last run or has not run for over a week. This card only reads (from `rpm-ostree status`
and `systemctl`, without root or the network).

On a flattened image (one that does not boot from ostree, such as a PS5 image, where `rpm-ostree` refuses with "not
booted via libostree") the card shows the version from `/etc/os-release` and the running kernel instead. Nothing
waits for a reboot there: dnf updates the packages in place, in the System packages card below. The updater line
stays, since `uupd` still updates the Flatpaks, Homebrew and distroboxes.

**The machine's updates** follow, a card per source the machine has, each with what is newer (installed → new):

| Card | Asked with | Update runs |
|---|---|---|
| Bazzite image | `rpm-ostree upgrade --check` | `rpm-ostree upgrade`: the new image is used after a restart |
| System packages (dnf), on a flattened image instead of Bazzite image | `dnf -q check-update` | `pkexec dnf upgrade -y` with the packages checked in its question; a new kernel is used after a restart |
| Flatpak | `flatpak remote-ls --updates` | `flatpak update -y --noninteractive` |
| Homebrew | `brew update`, then `brew outdated` (formulae and casks) | `brew upgrade` |
| Rust | `rustup check` (the toolchains and rustup) | `rustup update` |
| Python venv (.venv-linux) | `pip list --outdated` and a dry run of `requirements-dev.txt` | `pip install --upgrade` of the outdated packages within `requirements-dev.txt` |

**Update** on a card asks with its command and runs it in a window with its output; **Fix** runs every card's with
the packages' and tools' fixes. A source whose tool is missing has no card; one that could not be checked (offline)
says why. The venv card lists the packages `requirements-dev.txt` holds back (MkDocs below 2, say), which no
Update installs, and the packages missing from the venv: its `python` links to Bazzite's `/usr/bin/python3`, so a
Bazzite image with a newer Python leaves the venv without its packages, and the card says so. Bazzite's updater
still installs the image, the Flatpaks and Homebrew's packages every night by itself; Update only does it sooner.
**Updates** in the header counts them, with the emulators' below.

The **i** beside each card's name says what its Update does and how to handle what goes wrong (going back to the
version before, keeping one package where it is). What needs care is said on the card itself, in orange: a new
**major** version (marked on its row: it can change how a tool behaves), a Bazzite image that is used after a
restart, a venv left on an older Python. An update that should not be installed by a click has no Update and shows
**By hand**: a Bazzite image of a new Fedora release (44 → 45, say) changes the kernel, Mesa and the system's
Python at once, so its i gives the steps instead: read its release notes, `ujust update` in a terminal, restart,
open Nexus Deps again for what the new Python left without packages, and how to roll back.

**Emulators and firmware** follow, the programs and firmware the suite's apps use, each on a card with the latest version and an
i that says how to handle it. None of them is installed from here:

| Card | Asked | What an update means |
|---|---|---|
| RPCS3, PCSX2, PPSSPP, Vita3K, Xenia Canary, shadPS4 | GitHub's latest release | Each app installs the build it was tested with (its pin). **Installed** behind the pin: open the app and use its Install. **On GitHub**, newer than the pin: it comes with a release of the app, after a test on a board. |
| DualSense firmware (and the Edge's) | Sony's firmware list | A new version since the last look: connect the controller with a USB cable and update it in PS5 Controller. |
| PS4 system software | Sony's PS4 update list | A new version since the last look: update on the console. |
| PS5 system software, PlayStation Portal | nothing a program can read | **On the device**: the i says where the device shows its updates. |

GitHub is asked with the GitHub CLI's login (`gh auth login`): without one it allows 60 requests an hour, and a card
then says its hourly limit is used up, and until when.

An app installed without its emulator so far is no update; the card says so. Sony's versions are news once: the
first look learns them, a later one shows what changed. The list is `dev/deps/nexus_deps/catalogs/upstreams.json`:
which program each app uses and how its versions compare, written by hand, with the pins, repositories, names and
launchers read from the apps' code and the portal's `apps.toml`. After a pin moves, `dev/deps/run.sh
--sync-upstreams` brings it in line; CI fails until it is, and so does a new emulator app it does not list.

**Python packages** are checked where each app runs: Nexus Deps finds every installed app by its launcher and
reads the package versions in that app's Python environment (the suite's shared one, or the app's own). A card
shows the version in each environment, whether it meets the app's requirement, and the latest version on PyPI.
A package that no installed app uses is shown as **Not needed**. Each installed version is also looked up in
[OSV.dev](https://osv.dev), which collects the GitHub, PyPA and NVD advisories: a green **✓ CVE** means no known
vulnerability, a red **✗ CVE** lists each one by its CVE ID, linked to
[Snyk's vulnerability database](https://security.snyk.io/), with the release that fixes it, and **CVE ?** means the
check could not run (no network) or no installed app has the package.

**External tools** are checked for availability, on your PATH and in `~/.local/bin` and Homebrew, where the apps
also look. Each app says whether it needs the tool (required) or uses it when it is there (optional); the links
open the app's chapter in the wiki. Tools that do their work only as root are marked **Needs root.**; the apps run
them through sudo or pkexec. Remote Play's FFmpeg, inside its native core, is asked for its version through the
app's own Python.

### Fix

**Fix**, beside the check button, is on when something can be fixed; its tooltip says what. A click lists every
command it will run and asks first; **No** changes nothing. **Yes** runs them one after the other in a window that
shows their output and stops at the first that fails, then the check runs again.

- A Python package that is **Missing**, at a **Wrong version** or that **Needs update** is installed with pip into
  the environment of the app that needs it, at the version the apps in that environment allow (and at least the
  release that fixes a known vulnerability). One command per environment.
- A missing tool an installed app **needs** is installed with Homebrew when Homebrew has it (no restart), else
  layered into the Bazzite image with `rpm-ostree install`, which may ask for your password. A layered package is
  there after a restart: the window says so and gives the command (`systemctl reboot`); Nexus Deps never restarts
  by itself. On a flattened image the same package is installed with `pkexec dnf install -y` and is there at once.
- The machine's updates: each card's **Update** command (above), after the packages and the tools.
- A dnf step lists each of its packages with a checkbox in the question, all checked: only the checked ones are
  installed or updated. **All of …** checks them all, or clears them when all were checked; **Yes** is off when
  nothing is left to run. Uncheck the kernel (`linux-ps5`, `kernel`) to keep the one you have.
- Optional tools are left out: the apps work without them. A tool neither Homebrew nor Fedora has (`ujust`, Steam,
  a tool an app brings itself) is left to the app's chapter, which says how to get it.

The catalog says how each tool is installed: `brew` (the Homebrew formula) and `rpm` (the Fedora package).

### The hourly reminder

Every hour (or at the next login, when the machine was off then) Nexus Deps runs its check
without a window and, when something needs you, says so in a desktop notification: a Bazzite update waiting for a
reboot, Bazzite's updater failing or not running, the machine's updates (per source, with how many), a venv left
on an older Python, the emulators with news (each piece of news once), Python packages missing or to
update, tools an installed app needs. **Fix…** opens the window and asks to fix it, the same question as the
button; **Open Nexus Deps** opens the window. When all is well it says nothing. It is a systemd user timer,
`nexus-deps-reminder.timer`, that `install.sh` adds and `--uninstall` removes;
`systemctl --user disable --now nexus-deps-reminder.timer` switches it off.

### What the statuses mean

Each card has one status, the most urgent that applies. The boxes at the top count them.

| Status | For | Meaning |
|---|---|---|
| **Up to date** | package | Installed where the apps need it, at PyPI's latest version, no known vulnerability. |
| **Update available** | package | PyPI has a newer version. Nothing is wrong: newer versions come with an app release, after they are tested; Fix leaves it. |
| **Needs update** | package | An installed app needs a newer version, or a newer release fixes a known vulnerability. Fix updates it. |
| **Vulnerable** | package | An installed version has a known vulnerability that no release fixes yet. |
| **Wrong version** | package | An installed version does not meet an app's requirement. Fix installs one that does. |
| **Missing** | package | Not in the Python environment of an installed app that uses it. Fix installs it. |
| **Missing** | tool | Not found, and an installed app needs it. Fix installs it when the catalog says how. |
| **Not installed** | tool | Not found, but the installed apps only use it when it is there. |
| **Available** | tool | Found; the card shows where (and the version, where the check can read one). |
| **Unsupported build** | tool | Found, but in a form the app cannot use. |
| **Not needed** | both | No installed app uses it. |
| **Check failed** | package | PyPI could not be reached (no network). |

The check sends the names and versions of the Python packages to PyPI and OSV.dev, nothing else.

## Garbage Remover

**Nexus Garbage Remover** (`dev/garbage/`) shows the garbage on this machine and deletes what you check. Garbage is
files nobody needs again, which fill up a disk over time. Our tools' own leftovers are not in it:
`tools/clean_caches.py` removes those before every local CI run.

The table lists each place that holds 1 MB of garbage or more, the largest first. The Trash shows whenever it holds
a file, however small:

| What | Where | Removed with |
|---|---|---|
| **Crash dumps** | `/var/lib/systemd/coredump` | `sudo find /var/lib/systemd/coredump -mindepth 1 -delete` |
| **Steam's crash reports** | `config/htmlcache/BrowserMetrics` in Steam's folder | `find <that folder> -mindepth 1 -delete` |
| **Trash** | `~/.local/share/Trash` | `find ~/.local/share/Trash -mindepth 2 -delete` |
| **Picture previews** | `~/.cache/thumbnails` | `find ~/.cache/thumbnails -mindepth 1 -delete` |
| **pip's download cache** | `~/.cache/pip` | `find ~/.cache/pip -mindepth 1 -delete` |
| **Homebrew's downloads** | `~/.cache/Homebrew` | `brew cleanup --prune=all` |

The size of Homebrew's row leaves out the folders `api`, `bootsnap` and `tool-selection`. `brew cleanup` keeps
them, because Homebrew needs them to run.

Each row shows its size, and its tooltip says what the files are. Every row is checked at first. Uncheck a row to
keep that place. **Can be removed** shows the total, and **Checked** shows what **Delete** would remove. **Delete**
asks first and lists each place with its size. The crash dumps belong to the system, so for them the app asks for
your password once. The folders themselves stay, only their content goes. The round symbol at the right of the
title looks again.

Every hour, or at the next login when the machine was off, the app measures the garbage without a window. From
1 GB on, a desktop notification says how much there is, with the largest places. It says so once a day, or sooner
when the garbage grew by another GB. **Open** opens the window. The notification deletes nothing. It is a systemd
user timer, `nexus-garbage-remover-reminder.timer`, that `install.sh` adds and `--uninstall` removes.
`systemctl --user disable --now nexus-garbage-remover-reminder.timer` switches it off.

## Marketing

**Nexus Marketing for PS5** (`dev/marketing/`) writes an article that presents the portal and every app in it.
The article is a web page to share, in the suite's own design. It covers the portal and its apps only, never the
development apps. It has these parts:

- a hero with the headline and the buttons
- the board's numbers, when `copy.md` has them
- the number of apps, categories and quickfixes
- the portal, with a picture of its Settings page
- each category with a picture of its tab and a card per app
- **And more...**, the small touches of the portal and the apps
- the Portal Tour, the four steps to get it, and the links
- the license and the disclaimer from the suite's README, then the notes on the board's numbers

The board's numbers come from the **Specs** part of `copy.md`. Each line is a number, a space and its label.
A label that ends in `*` or `**` gets a small mark. Its note under **Spec notes** starts with the same mark.
The notes show at the bottom of the page.

The links go to the latest release, the wiki, the Portal Tour and the repository on GitHub. **Watch the tour**
and the video's picture play the video itself. Only the footer's link opens the Portal Tour page. Each app's card
opens its chapter of the wiki. An app that changes the board carries **Changes the board** on its card, in the portal's orange.

The article keeps up with the suite by itself. The apps, their order, their categories and their marks come from
`portal/apps.toml`. The words come from `dev/marketing/nexus_marketing/copy.md`, with a line for each category and
each app. The window lists every app of the portal with its line. **Apps with a line** turns red when an app has
none. The app's tests fail then too. The pencil after the line under the table opens `copy.md` in your
text editor. Write the new line there, then click the round symbol to read it again.

The pictures of the portal are stills of the real portal from this checkout, in `dev/marketing/images/shots/`.
`tools/portal_shots.py` takes them offscreen, the way `tools/portal_tour.py` records the Portal Tour. **Screenshots** shows whether they
are **Current**. It says **Out of date** when the portal changed since. Then the **Screenshots** pill takes them
again. For the hero's background, put a picture named `hero.webp` in the app's `images` folder. Without one, the
article draws a purple placeholder.

The pills:

- **Preview** opens the article in the browser. It is one file with the pictures and fonts inside, so a browser
  in a Flatpak shows it whole.
- **Export** writes the article to a new folder in the folder you choose. The folder holds `index.html` with its
  pictures and fonts. An export never writes over a folder that is there already.
  A git checkout, such as the website's folder, is the exception. There, Export writes the files straight into it,
  over the old ones. It removes nothing. Publish then commits and pushes them.
- **Screenshots** takes the stills of the portal again.
- **Text check** runs `tools/text_check.py` on `copy.md`. Its output shows below the table.
- **Publish** sends the article to the website. Its caption says how many files differ from the website's folder,
  or **Up to date**. The first click asks for the website's folder, the checkout of its repository. The app
  takes only a checkout of `RobertoTorino/console-suite`, this suite's website, and remembers it.
  Then Publish asks first. It writes the article into the folder and removes the pictures it no
  longer has. It commits only the article's files as "see the changelog" and pushes to GitHub. The website shows
  the new article a minute or two later. Other files in the folder, such as `.nojekyll`, stay as they are.
  **Other folder…** in the question takes another folder. The pill is off while the website is up to date.

The globe beside the round **i** opens the website in the browser. Its address comes from the website's folder. A
`CNAME` file there gives a domain of your own. Without one, the address is GitHub Pages' address of the repository,
in the form `https://robertotorino.github.io/<repository>/`. The globe is off until Publish knows the folder.
