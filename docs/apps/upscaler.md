<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 Upscaler Manager](../assets/upscaler/ps5-upscaler.webp){ .app-logo }

# PS5 Upscaler Manager

PyQt6 front-end that deploys **[HelixSR](https://github.com/lonewolf0622/HelixSR)** – the FSR 3.1 drop-in
upscaler with DLSS-style neural networks – into games on a **PlayStation 5** running **Bazzite**
(Fedora Atomic / rpm-ostree), and keeps track of where it was put. HelixSR runs NVIDIA's DLSS Model E network as
plain compute shaders on an AMD GPU. Games talk to it as FSR 3.1.

HelixSR is not an injector: it is a replacement for the `amd_fidelityfx_upscaler_dx12.dll` /
`amd_fidelityfx_dx12.dll` a game ships with. Deploying it means renaming the game's DLL to `*.original.dll`
and dropping HelixSR's DLL, its two network files and an optional `helixsr.ini` in the same folder. The
`*.original.dll` is the backup, and HelixSR still uses it. HelixSR forwards frame generation and the other
FidelityFX effects to it. This app does exactly that, reversibly, and nothing else on the system is touched. No launch options, no
`WINEDLLOVERRIDES`, no Proton tweaks are needed. Only OptiScaler, for games without FSR 3.1, needs a launch
option; the app sets that one too (see below).

From HelixSR 3 on, what goes in is **HLX FSR 4**, HelixSR's FSR 4-class upscaler: one DLL from the release's
`HLX-FSR4` folder, which comes built with its network inside. Nothing is built on the PC for it, and no network files
or `helixsr.ini` go next to it. The app removes network files that an earlier HelixSR left there. In the game,
pick **AMD FSR**. Games without FSR 3.1 get **HelixSR Scaler**, with
HLX DLSS (see below).

---

## What it manages

- **Setup in one click** – *Download and build* fetches the latest HelixSR release from GitHub (checked against
  the SHA-256 GitHub publishes for it), reads the exact
  URLs and SHA-256 sums its setup scripts pin, downloads what the PC still needs **in parallel** and verified
  (NVIDIA's DLSS 310.7.0 DLL, 59 MB; Microsoft's DirectX Shader Compiler, 25 MB; on Bazzite a portable Python,
  67 MB), runs `helixsr-setup.sh --yes` with live output and imports the result as the payload. The DLSS DLL comes
  from NVIDIA's GitHub, under NVIDIA's license. The portable Python comes with numpy, on read-only systems such as
  Bazzite. The DLSS DLL is deleted afterwards. The downloads go into `~/.local/share/ps5-upscaler/work` and
  `~/.local/share/HelixSR`. The second folder is the script's own cache, and the setup uses it again next time.
  You can use a DLSS 310.7.0 DLL from a game you own instead. Check **Use a nvngx_dlss.dll already on this PC**
  and let *Find in Steam* find it. It compares checksums and offers only the exact build HelixSR pins. That skips
  NVIDIA's download. The downloads are not what takes time. The build is. The build itself is HelixSR's own script,
  unchanged, and takes about 5–6 minutes, because it compiles the network's shaders for both wave sizes through Proton. The Setup page shows the
  elapsed time. From HelixSR 1.7.0 on, the script ends with its own game installer, which asks about each Steam
  game; the app gives it no input, so it stops there and only the network files are built. From HelixSR 1.8.0
  on, the network is built into HelixSR's DLL instead of two separate files. Deploy then copies only the DLL and
  the ini. It removes network files that an older release left next to the DLL. From HelixSR 1.9.0 on, the script
  can also build frame generation for HelixSR Scaler (about 400 MB from NVIDIA); the app does not deploy that, so
  it skips this step (`--no-fg`). HelixSR 2.x keeps its DLL in the release's `HelixSR-fsrfg` folder, and its
  `helixsr-setup.sh --yes` would install HelixSR Scaler into every game it finds. For 2.x the app therefore runs what
  that script runs before its game installer: HelixSR's own builder (`setup/helixsr_setup.py`, unchanged) on
  `HelixSR-fsrfg`, with the same Python, shader compiler and Proton, and without frame generation (`--no-fg`). It
  then checks that the DLL carries the network. For HelixSR 3.x, *Download and build* downloads the release (about
  280 MB, checked against GitHub's SHA-256), imports HLX FSR 4 from its `HLX-FSR4` folder, which comes built, and
  builds HLX DLSS's network into the release's `HelixSR/helixsr.dll` for HelixSR Scaler, with HelixSR's own builder
  and without frame generation. When that build fails, HLX FSR 4 is ready all the same and the Setup page says why.
  *Native Vulkan kernels for HLX DLSS* (off by default) builds the network for Vulkan too: Vulkan games then run HLX
  DLSS in Vulkan instead of through HelixSR Scaler's DirectX 12 bridge. The build takes about twice as long, and
  HelixSR's builder downloads the Linux shader compiler for it once (13 MB). Turned on later, *Download and build*
  builds again; the Overview says whether the payload has them. Deploy again per game afterward.
  The whole release stays in the payload (as hard links where it can, so it takes no second copy): HelixSR Scaler
  and HelixSR's installer run from it. Your games are only changed from the Deploy and Games pages. When a later
  major version is out that the app does not support yet, the Setup page says so and the app keeps getting the newest
  release it supports.
- **Version choice** – *Version* on the Setup page picks the latest HelixSR release (the default) or HelixSR
  1.8.1, the version HelixSR's developer recommends when the latest one does not work for you (please then open
  an issue at [HelixSR](https://github.com/lonewolf0622/HelixSR/issues) with the game's `helixsr.log`). You find
  that file in the game folder.
  Switching builds the network files for that version and replaces the payload; deploy again per game
  afterwards.
- **Update checks** – at start (can be turned off) or with **Check now**: the payload against the latest HelixSR release
  on GitHub. The check at start is one small request. The app itself is updated through the Bazzite Console Suite portal. A newer HelixSR is flagged on the Overview; building again
  updates the payload and deployed games show *Older build* (*Newer build* after switching back to 1.8.1). After
  a build the app offers to update them; *Update older games* on the Overview does the same, for older builds and
  for games whose own DLL is back, keeping their `helixsr.ini`. *Download and build* needs about 1.5 GB free where
  it downloads and builds. It does not start with less.
- **Games** – every Steam game, each looked through in the background for an AMD FSR 3.1 DLL: the games that have
  one first, with HelixSR's state in each; the others grayed out (*Open on Deploy page* still takes them to
  OptiScaler). *Run with HelixSR* (or a double-click) puts HelixSR in when it is missing, older, or replaced by
  the game's own DLL after an update, then starts the game through Steam (`steam://rungameid/<AppID>`). It
  asks before the first install into a game and does nothing while the game runs. HelixSR goes in before the game
  starts. Choose **AMD FSR** in the game. A game with an FSR 3.1 DLL shows one of these states:

    - *Not installed*
    - *HelixSR x.y.z installed*
    - *x.y.z installed; a.b.c is available*, when the payload has a newer build
    - *The game put its own DLL back*

- **Payload** – one imported HelixSR release, kept under `~/.local/share/ps5-upscaler/payload`.
  It holds the DLL, the two network files and the ini.
  The Setup page fills it. You can also fill it by hand. Run the release's `helixsr-setup.sh` yourself in that
  folder once, then import the folder or the zip. *Import release zip…* takes the download as is. The network files
  are then missing. They arrive once the setup has run and you import the folder. The script builds
  `helixsr_weights.bin` and `helixsr_kernels.pak` from NVIDIA's DLSS DLL – those files are NVIDIA's property, so
  this app never ships them. They are for your own PC and are never part of this app or its releases. Only the
  known HelixSR files are copied; the payload survives updates and `./install.sh --uninstall`.
- **Deployments** – every place HelixSR was put, with a live status (in place, older or newer build, network
  files missing, original restored when a game update or Steam put the game's own DLL back, removed, folder gone), in `~/.config/ps5-upscaler/deployments.json`.
  *Forget entry* drops a line without touching the game. *Update older games* puts the payload's HelixSR into
  every deployment marked *Older build* or *Original restored*. It keeps the `helixsr.ini` there, and the game's
  backup. It leaves a game that is running alone. It does not touch deployments of a newer build, such as the
  fallback.
- **Two deploy modes**
  - *Replace the selected DLL* – for games with native FSR 3.1: pick the game folder (Steam libraries are
    scanned, including `libraryfolders.vdf` and the Flatpak Steam), the app finds every upscaler DLL (Unreal
    games bury it under `Engine/Plugins/.../ThirdParty/Win64`), backs it up and deploys. *Remove* restores
    the original. It deletes HelixSR's files and gives the `.original.dll` its name back. Deploying again over an
    existing deployment updates HelixSR's files. Re-deploying a newer build never overwrites the real original. With a HelixSR 3 payload this
    puts in HLX FSR 4 under the game's file name; it lists the game's own FSR (the `.original.dll`) after its own
    upscalers and uses it when it cannot start. A game deployed with HelixSR 1 or 2 shows *Older build*: *Update older
    games* puts HLX FSR 4 in, and *Remove* puts the game's file back as before.
  - *HelixSR Scaler* – for games without FSR 3.1 (DLSS, XeSS or FSR 2, also DirectX 11 and Vulkan games), with a
    HelixSR 3 payload; it takes the place of the stand-alone folder below. HelixSR Scaler is OptiScaler with HelixSR
    and runs HLX DLSS. Pick the game's folder; the app has HelixSR's own installer (the bridge HelixSR Desktop uses)
    put it next to the game's `.exe`: as `dxgi.dll`, which Proton loads without a launch option, or under another
    name when the game has its own `dxgi.dll` (the app then copies the Steam launch option it needs to the clipboard).
    The game's files it replaces are kept in `HelixSR-Scaler-backup`, and `HelixSR-Scaler.files` lists what it put
    in, so HelixSR's own setup and HelixSR Desktop can update or remove it too, and the other way round. Pick
    **DLSS** in the game; **Insert** opens its menu. HelixSR's frame generation is not installed. *Remove* puts the
    game's files back; *Update older games* brings a newer HelixSR in and keeps the game's `OptiScaler.ini`.
  - *Stand-alone folder for OptiScaler* – for games without FSR 3.1, with a HelixSR 1 or 2 payload (HelixSR 3 has no
    DLL for it; the fallback on the Setup page brings one): writes a folder with the DLL under both
    FidelityFX names, the network files and the ini. The folder is `<game>/HelixSR` by default.
    [OptiScaler](https://github.com/OptiScaler/OptiScaler) routes the game's upscaler calls to an FSR 3.1 DLL. With a payload from HelixSR 1.7.0 to 1.8.1, which ship the
    official OptiScaler (1.9.0 and newer do not; the fallback on the Setup page brings it, and the payload keeps
    it when you switch back to the latest), it also installs OptiScaler next to the game's `.exe` (Scan finds that folder): as
    `dxgi.dll`, or under the name of an OptiScaler the game already has, with `fakenvapi`, and its
    `OptiScaler.ini` pointed at the HelixSR folder. Select DLSS in the game. What it replaces is kept in the
    HelixSR folder's `backup`; *Remove* puts it back. That includes any `OptiScaler.ini` the game already had. Under Proton OptiScaler only loads with
    `WINEDLLOVERRIDES="dxgi=n,b"` in the game's Steam launch options, so for a Steam game the app adds that too:
    to the launch options already there (`WINEDLLOVERRIDES="dxgi=n,b" %command%` when there are none), for every
    Steam user. Steam writes its settings again when it closes, so it has to be closed for this: the app asks, closes
    Steam, sets them and starts Steam again. In Game Mode Steam stays open; the line is then copied to the clipboard
    to paste into the game's *Properties* in Steam. *Remove* puts the launch options back as they were, unless you
    changed them since. Uncheck **Install OptiScaler next to the game's .exe** to install OptiScaler yourself, as
    its documentation describes. The page then gives you three `OptiScaler.ini` lines to paste,
    `Dx12Upscaler=fsr31`, `FfxDx12Path` and `FfxDx12SRPath`. The two paths are `Z:\` paths. These are Windows paths, and `Z:` is the Linux root
    under Proton. Then pick **FSR HelixSR (3.1.5)** in OptiScaler's FFX Upscaler menu.
    Optionally it adds a second upscaler, for example AMD's `amd_fidelityfx_upscaler_dx12.dll` with FSR 4: it
    goes into the folder as `amd_fidelityfx_upscaler_dx12.amd.dll` with `UpscalerDll` pointing at it, and
    OptiScaler's FFX Upscaler menu lists its upscalers after HelixSR. The one you pick runs in that DLL.
- **helixsr.ini** – a form over every key HelixSR reads (`[Sharpening]`, `[ModelE]`, `[Log]`, `[Forwarding]`)
  with validation and a live preview that keeps the upstream comments. Save it as the default for new
  deployments or push it to an existing one. The page grays out what the payload's HelixSR version does not
  read: HelixSR 1.7 ignores `[Sharpening]` and `[ModelE] Network`; 1.8 reads sharpening again through
  `Sharpener` (`off`, `nvidia` or `rcas`), `Sharpness` and `UseGameSlider` instead of `Mode`. The keys are listed
  below.

## helixsr.ini keys

| Section | Key | Default | Meaning |
|---|---|---|---|
| [Sharpening] | Mode | off | *off* as in DLSS. *game* uses the game's FSR sharpness, or Sharpness if it sends none. *override* always uses Sharpness. |
| [Sharpening] | Sharpener | off | HelixSR 1.8+. *off* as in DLSS 4, *nvidia* for NVIDIA's sharpening filter, *rcas* for AMD FSR's. |
| [Sharpening] | Sharpness | 0.3 | 0–1, on the FidelityFX RCAS scale |
| [Sharpening] | UseGameSlider | false | HelixSR 1.8+. Follows the game's sharpness slider when it has one. |
| [Sharpening] | MotionAdaptive, MotionThreshold, MotionLimit, MotionReduction | true, 2, 16, 0.6 | Less sharpening on fast-moving pixels. The keys set where the reduction starts and where it is complete, in output pixels per frame, and how much it removes. |
| [ModelE] | Enabled | true | Runs the Model E network. Off, HelixSR uses a placeholder upscale. |
| [ModelE] | Network | auto | *auto* runs the main network at every ratio. On GPUs without matrix cores, that is about 30 % faster than NVIDIA's Ultra Performance network. *nvidia* picks as DLSS does. Or force *main* / *ultraperformance*. |
| [ModelE] | InvertJitter, InvertMotionVectors | false | For games whose jitter or motion vectors come out mirrored |
| [ModelE] | MotionVectorFrontEnd | false | Converts render-resolution motion vectors to display resolution first. HelixSR does that anyway when the game's vectors include the jitter. |
| [Log] | Enabled | true | Writes `helixsr.log` next to the DLL. The log names the network that runs and reports missing network files. |
| [Forwarding] | Dll | (auto) | The DLL for the other FidelityFX effects, such as frame generation. That is `amd_fidelityfx_dx12.original.dll` if present, else `amd_fidelityfx_framegeneration_dx12.dll`. |
| [Forwarding] | UpscalerDll | (empty) | A second FidelityFX upscaler DLL, such as AMD's with FSR 4. OptiScaler's menu lists it after HelixSR. |

Sharpening off costs nothing. Sharpening on costs a little of each frame.

## Privilege model

Everything runs as your normal desktop user: game folders under Steam are yours, the payload and the
deployment list live in your XDG directories. No `pkexec`, no root, no `rpm-ostree` layering. With OptiScaler
the app also changes the game's launch options in your Steam settings (`userdata/<user>/config/localconfig.vdf`),
and only that line.

## Requirements

```text
Python 3.11+
PyQt6>=6.11,<7
```

The PyQt6 wheels bundle Qt. HelixSR itself needs a game with an FSR 3.1 DX12 upscaler (or OptiScaler) and
the network files built by its `helixsr-setup.sh`; see the
[HelixSR README](https://github.com/lonewolf0622/HelixSR#readme) for the game side.

HelixSR is for RDNA 1 and newer, with Mesa RADV and Proton. The DLL that takes the place of a game's FSR 3.1 works
in Direct3D 12 games. DirectX 11 and Vulkan games use HelixSR Scaler, from HelixSR 3 on.

## Install on Bazzite

Install it from the Bazzite Console Suite portal, where it is under Graphics. Or download
`ps5-upscaler-v<version>.tar.gz` from the suite's
[releases](https://github.com/RobertoTorino/bazzite-console/releases), unpack it and run the installer:

```shell
tar -xzf ps5-upscaler-v*.tar.gz
cd ps5-upscaler-v*/
./install.sh
```

It installs the app for your user only: a private venv with PyQt6 and the app under
`~/.local/share/ps5-upscaler`, the launcher `~/.local/bin/ps5-upscaler`, a
desktop entry, the icon and a Desktop icon (`./install.sh --no-desktop-shortcut` leaves the Desktop icon out).
**PS5 Upscaler Manager** then appears in the application menu (and in Steam's
Game Mode via *Add a Non-Steam Game* if you want it there). Run `./install.sh` again from a newer release to
update, `./install.sh --uninstall` to remove it; the imported payload and the deployed games are left alone.
`./install.sh --uninstall --purge` also removes the payload and the settings. The list of deployed games stays, so
a reinstalled app can still restore them.

## Run from the repository

```shell
git clone https://github.com/RobertoTorino/bazzite-console.git
cd bazzite-console/apps/upscaler
python3 -m venv python && python/bin/pip install -r requirements.txt
PYTHONPATH=../../core python/bin/python -m upscaler
```

`--payload DIR`, `--deployments FILE` and `--work DIR` point the app at another payload folder, deployment
list and download folder, for development on a machine without Steam. `--no-update-check` skips the release
lookup at start. `--version` prints the version.

## Pages

- **Overview** – payload status (version from the release's README, DLL, weights, kernels, ini) with
  *Import release folder…* / *Import release zip…* / *Open payload folder*, and the deployment table with
  *Open folder*, *Remove HelixSR from game* (restores the original or deletes the stand-alone folder), *Forget entry*
  and *Update older games*.
- **Setup** – release status for HelixSR with *Check now*; the version to get (latest or 1.8.1) and, for HelixSR 3,
  *Native Vulkan kernels for HLX DLSS*;
  *Download and build* with progress, the script's output, *Cancel*, *Import built release* and *Open work
  folder*; optional local `nvngx_dlss.dll`.
- **Games** – every Steam game with its FSR 3.1 DLL and HelixSR state; *Run with HelixSR*, *Open on Deploy page*,
  *Rescan*.
- **Deploy** – choose a Steam game or browse to any folder, scan for upscaler DLLs, pick the mode, decide
  whether to write the current `helixsr.ini`, deploy or remove. In folder mode the OptiScaler snippet is
  shown with a *Copy OptiScaler.ini lines* button. **Browse…** takes any folder, such as one of Heroic, Lutris
  or Bottles. Each DLL the scan finds shows whether it is the game's own file or HelixSR. It also shows whether
  the network files are next to it. Select the one the game loads, usually the only one. Then click **Deploy
  HelixSR**.
- **helixsr.ini** – the settings form, validation, preview, *Save as payload default* and *Write to game*.
  *Save as payload default* makes the file the one Deploy starts from. *Write to game* replaces the ini of a chosen
  deployment.
- **Help** says what the app does, links to this chapter and shows where the app's files are.

The header shows the payload version, network-file status, deployments (ok / total) and the number of Steam
games found; it refreshes every 5 seconds.

## Good to know

- Steam verifies game files on updates and may put the game's own DLL back. The Overview then shows *Original
  restored*, and the backup stays. *Run with HelixSR* or *Update older games* puts HelixSR back.
- For per-stage GPU timings, set the launch option `HELIXSR_PROFILE=1 %command%`. HelixSR then writes them to
  `helixsr.log`.
- The app keeps its window size and page per user.

## Development

```
upscaler/
  __init__.py       app name, version, XDG paths
  __main__.py       entry point (python -m upscaler)
  backend.py        pure file logic: payload import, DLL discovery, deploy/remove (both modes),
                    helixsr.ini parse/render/validate, deployment store, Steam library discovery
  acquire.py        GitHub release lookup, pinned-source parsing, verified parallel downloads,
                    the build (QThread: helixsr-setup.sh for 1.x, HelixSR's builder for 2.x) and the
                    update checker
  setup_page.py     Setup page
  games_page.py     Games page and the thread that looks through the game folders
  main_window.py    header, navigation, polling, confirmations, wiring of page signals to the backend
  pages.py          Overview, Deploy and helixsr.ini pages
  help.py           Help page
  widgets.py        status pills, metric boxes, rounded tooltip
bazzite_console_core/         the suite's shared code (its steam.py closes and starts Steam), bundled by install.sh and
                    the release
  fonts/            Inter (SIL OFL), used for the header on Linux
install.sh          per-user installer (venv, launcher, desktop entry, icon); --uninstall removes it, keeps the payload
ps5-upscaler.desktop  desktop entry template, Exec is filled in by install.sh
tests/              pytest suite (offscreen Qt, temporary payload and game folders, no real HelixSR needed)
```

Tests: `./test.sh` in the suite's root runs every test suite, this one included (extra arguments go to pytest,
e.g. `./test.sh -k ini`). For this app alone: `pip install -r requirements-dev.txt` then
`QT_QPA_PLATFORM=offscreen python -m pytest -q tests`. They cover the `helixsr.ini` round-trip against the
upstream file, payload import from folders and zips, DLL discovery, deploy/remove in both modes (including
re-deploy over an older build and refusing foreign DLLs), the deployment store, Steam library parsing, the
release lookup and the whole Setup run (downloads over `file://` URLs against a fake `helixsr-setup.sh` and a fake
2.x builder, checksum and script failures, a local DLSS DLL) and the main window driven through its page signals. The suite's CI
(`.github/workflows/ci.yml`) runs them on every push and pull request. Releases are tagged `ps5-upscaler-v<x.y.z>` in
the suite repository; `.github/workflows/release.yml` then builds the tarball and publishes it on GitHub.

The backend has no Qt dependency so it can be exercised from the command line or reused.

## License

The source and the issues are in the
[suite repository](https://github.com/RobertoTorino/bazzite-console/tree/main/apps/upscaler).

GPL-3.0-or-later, see [LICENSE](https://github.com/RobertoTorino/bazzite-console/blob/main/apps/upscaler/LICENSE). The bundled Inter font is under the SIL Open Font License
(`upscaler/fonts/Inter-LICENSE.txt`). HelixSR is a separate project under its own license, the HelixSR
Freeware License. This app ships none of it. Its network files are derived from NVIDIA's DLSS and are never distributed by this app.
