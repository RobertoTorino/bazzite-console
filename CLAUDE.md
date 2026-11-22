<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Claude rules

1. A suite is standalone: all it needs is in its repository, and nothing is taken from Nexus or another suite at run, test or release time. Its tooling is its own; change it there.
2. The suites are twins: release logic (NRT, `tools/`, workflows, CI), design features, category icons and app design stay equal. Make every change in each suite in the same piece of work, with each one's CHANGELOG and wiki. Only the hardware differs (names, `TAG_PREFIX`, the board's apps and checks). The handover names what changed in each.
3. A suite stands apart: a change never edits another suite's folder, CI or release workflow. A change two suites want is two changes, each with its own release.
4. Never run git actions: no commit, tag, push, clone, add, mv or rm. Edit with file tools, finish in the working tree, say what is ready and don't offer to commit.
5. `bazzite-console-image` is a different project: read it with `gh api`, never clone or edit it. Rows about it stay for the owner.
6. Releases are the owner's. Never bump a `VERSION` (or its copies, or `portal/VERSION`), tag, build or publish release assets, pin a release in `portal/apps.toml` or write release entries in the CHANGELOGs, and don't offer to. The handover says which app needs a release and why. Claude may change the release tools and their tests.
7. NRT works out versions from the CHANGELOG kinds since the last tag. `dev/` apps are never released.
8. READMEs, docs and the wiki hold no status, plans, step numbers or decision notes, and no placeholder folders for future work. CHANGELOG entries are history and may mention steps. Plans go in `ACTION-LIST.md` in the workspace root for the Bazzite suites, and in `MIGRATION.md` in Nexus. What either marks "on hold" is the backlog.
9. Keep the wiki current: new information, ways of working or logic go into its chapter in the same change as the code, written for the person using it. The handover names the chapters changed. Nexus's tooling is documented on the Nexus page (`nexus/docs/`); the Bazzite suites document their own copies in their own wikis.
10. Every change gets a CHANGELOG entry: the root one for suite-wide changes, otherwise the app's, core's, portal's or dev app's. Format: a `Changelog: DD-MM-YYYY HH:MM:SS` line, a blank line, then plain sentences, newest first. Use Europe/Amsterdam time: `python3 -c "import datetime, zoneinfo; print(datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Amsterdam')).strftime('%d-%m-%Y %H:%M:%S'))"` (on Windows with `.venv-windows/Scripts/python.exe`; never `TZ=Europe/Amsterdam date`).
11. Every CHANGELOG entry starts with its kind: `Breaking.` (major), `Added.` (minor) or `Fixed.` (patch), 0.x apps too.
12. `VERSION` is the single source of an app's version. Copies in code (`__version__`, shell `VERSION=`, pyproject, Cargo) must match: `tools/check_versions.py`.
13. Every former repo folder (each app, `core/`, `portal/`) keeps LICENSE, .gitignore, VERSION and CHANGELOG. Each `dev/` app keeps LICENSE, .gitignore and CHANGELOG, and has no VERSION. Workflows live only in the root `.github/`.
14. No long text in a window. Where space is limited, core's `InfoButton` opens the text on a click, with a link to the wiki. A short line under a control stays a `hint_label`.
15. Personal data stays out (names, addresses, host and user names, serial numbers, MAC and IP addresses, keys, account details). Ask when in doubt.
16. Ask before decisions that are the owner's (what an app does, version numbers, repo layout, anything on the board). Do obvious housekeeping without asking.
17. An app that changes how the board runs is marked `changes_board` and the portal asks first. Frame it as standard caution: the apps are software-only and reversible.
18. Every such app has a `board_change` in `portal/apps.toml`: a few plain sentences, written from the code, on what it touches, what stays after a reboot or power off, what it never touches and how it is undone. The tile tooltip shows it under "Changes the board". The app's wiki chapter opens with the same text, word for word, in a `!!! warning "Changes the board"` box after the title. Rewrite both together; `tools/check_manifest.py` compares them.
19. The portal's question before such an app keeps "Read the app's manual first and know how to undo the change." and "Read their manuals first."
20. The PS5 that runs Bazzite is "the board", never "the console", in every text (code, comments, tests, wiki, READMEs, windows), as in "changes the board". "Console" stays only where it means something else: a console as a product or another machine, Remote Play's consoles, emulated systems, PlayStation history, the kernel's `console=` and `/dev/console`, and the names Bazzite Console Suite, `bazzite-console`, `bazzite_console` and Console Link. DatStation's texts stay. CHANGELOG entries keep their words.
21. Call the project `bazzite-console` and the system "Bazzite OS running on a PS5 board". Never "the PS5 suite" or "on the PS5" as the name.
22. The current releases are the baseline, tested on the hardware (two boards). Moving code must not change behavior. A finding in existing code is "a code path to check", not a known failure. Prove "unchanged" with diffs, pixel comparisons and installer tests.
23. Don't limit an app to the owner's setup. Read what the hardware reports, offer every option it supports, and say where an option doesn't apply. Recorded data from the owner's board makes good fixtures, but tests also cover other setups. Don't assume features or paths of another device. Hardware is never found by a name written in code.
24. Every app is built the same way. `apps/<name>/` holds its Python package directly (`<package>/__main__.py`, no wrapper folder), plus `images/`, `tests/`, `install.sh` and the four files. `<package>` is the app's name without the suite's prefix. A renamed app's old key goes in `RENAMED` in the portal's `manifest.py`. `tools/tests/test_layout.py` checks the layout.
25. Shared code comes from core (bundled per app). The installer writes a launcher in `~/.local/bin` whose exec line names the app's python, a menu entry and an optional Desktop icon. Every app and every `portal/apps.toml` entry has an installer test, `tools/installer-tests/<name>.sh`, run by CI (`tools/tests/test_installer_tests.py` checks it).
26. An app's icons are copies of its category's icon: `icons/categories.toml` assigns them and `tools/sync_icons.py` writes them.
27. An app window starts with the app's icon at 96 px on the left, spanning the title (with the version) and a second line below it. Actions are core's `ActionPill`, never small buttons. What is applied already cannot be applied again (Apply is off). A new app copies an existing one's structure; any deviation is the owner's decision.
28. A new app's name carries the device prefix: "PS5 <Name>" in bazzite-console, "BC-250 <Name>" in bc250-bazzite.
29. A suite keeps the design of its system. Bazzite suites use the Bazzite design (purple), the Windows suites their own, Nexus its own (`nexus/docs/stylesheets/nexus.css`). Never carry one system's design to another. `dev/` apps use Nexus's names and design (teal, theme `NEXUS`, icon from `tools/make_icons.py`).
30. Scope is the suite, not the system. We answer for the portal and its apps, not the operating system. A system-wide package is in scope only where one of our apps uses it. Nexus Deps shows every update of the machine, installs them after it asks, and reminds hourly. Its Fix lists the commands first and asks, then installs what an app needs: pip for Python packages, Homebrew for a tool, else rpm-ostree.
31. Text: every text file is LF in git and in the working tree (`* text=auto eol=lf`). On Windows, check line endings by counting bytes in Python.
32. A checkout with `core.fileMode=false` records new files as 100644. Run `tools/fix-modes.sh` before committing so every `.sh` is executable; CI fails otherwise.
33. One venv per OS at the repo root, `.venv-linux/` and `.venv-windows/`; `./test.sh` picks it. The system `python3` has no PyQt6. Create one with `python3 -m venv .venv-linux && .venv-linux/bin/python -m pip install -r requirements-dev.txt` (Windows, Git Bash: `py -m venv .venv-windows && .venv-windows/Scripts/python.exe -m pip install -r requirements-dev.txt`).
34. Tests keep settings in a temp folder (conftest fixtures turn them into .ini files) and never write to the Windows registry.
35. Keep path and link case exact: Linux and GitHub are case-sensitive.
36. The development tools run on Linux only; the Windows suite's tests and builds run on Windows. `./test.sh` runs core, tools and `dev/` everywhere, and only the suites whose `SYSTEM` matches (`NEXUS_SYSTEM=bazzite` or `windows` picks by hand).
37. Test only the relevant changed code. Never run the full CI (`tools/ci-local.sh`) or the whole `./test.sh`. Run only one FFmpeg build at a time.
38. Install missing tooling right away and go on (`brew install` on Bazzite, or a distrobox); never ask first and never work around it. A tool needed more than once is installed for good and listed under The development machine in the Development chapter (`docs/development/index.md`) in each Bazzite suite, and in `nexus/docs/machine.md` in Nexus. Delete scratch files as soon as they are not needed. Put anything large under `/var/tmp` and remove it when done; never leave large files under `/tmp/claude-<uid>`.
39. Releases are tagged with `tools/tag-release.sh <prefix><app>-v<x.y.z>`, which tags only a pushed commit that passed CI. `tools/check_upstream.py` says when an upstream an app pins moved past the pin.
40. Code reads like the code around it: the same comment density, naming and idiom. Docs are plain, short sentences for the person using the tool, as `.claude/writing.md` describes. Run `python3 tools/text_check.py --details FILE` on new text in both twins.
41. American English in everything written: color, gray, center, canceled, license, catalog, labeled, behavior, authorized, afterward, toward, anymore; **check** and **uncheck** a box; **ID**. Identifiers, settings keys, file names and recorded data keep their spelling.
42. Pictures are WebP wherever WebP is accepted. A PNG stays only where WebP isn't accepted: a favicon, the `-128.png` menu and Desktop icons, the source drawings in `icons/` and `nexus/images/`, and pictures a ported tool brought with it.
43. The manual (`docs/`, built with MkDocs) is called "the wiki" in user-facing text. The header link and the Home page's footer say Wiki. The repository's own GitHub wiki stays unused.
44. Purpose first: say what the reader gets before how it works.
45. One fact per sentence, under 25 words, never over 30.
46. No chains: no semicolon between facts, no colon followed by more sentence, no facts in parentheses. Parentheses hold a short name or unit of at most four words.
47. Three or more parts make a list. A list item that isn't a sentence has no period and no semicolon.
48. Explain a term the first time, and use the project's own terms only after that.
49. Talk to the reader: "you", what they see and do. Name window labels in **bold**, exactly as the window shows them.
50. Plain words: "turn on" over "enable", "remove" over "uninstall", "restart" over "reboot".
51. A hint under a control is one or two short lines. A longer explanation goes behind an `InfoButton` with a wiki link.
52. A dialog asks one question: the question first, then what will happen one fact per line, and last when you'll be asked for your password. The exception is the question before closing while a job runs: "A download ... is still running. Close anyway?"
53. A rewrite keeps every command, path, number, link, limit, parsed string, settings key and the disclaimer. Headings stay word for word. Button and field labels change only to correct their English, with tests and wiki changing along. A wrong fact is corrected and named in the CHANGELOG.
54. A label in the wiki is written as the window shows it (**Install all apps**).
55. No version or build numbers in new text, except where the text is about that version.
56. An app's README has a short introduction, then "How to install and use it: [<app name> in the wiki](https://robertotorino.github.io/bazzite-console/apps/<key>/).", then its License section (in bc250-bazzite the address is `https://robertotorino.github.io/bc250-bazzite/apps/<key>/`). Badges, install blocks and license notices stay.
57. The emulator managers (PCSX2, RPCS3, shadPS4, PPSSPP, Vita3K, Xenia) show no introduction under their pills, only the emulator's release notes and wiki links, and no info symbol.
58. Nexus Release Tool's confirmations end with "Go ahead?". RPCS3's message after an install joins its parts with "; ".
59. Sound Lab's checkbox is **Keep the audio link awake**, and its tooltip says it plays a silent loop while the window is open.
60. The Upscaler Manager's Help page is short: what the app does, a link to its wiki chapter, and where its files are. What only the Help page said goes into the chapter first.
61. The Development index keeps "`launch_in_terminal()` takes an exit file the caller can watch." and "board-test's manual tooltips". DESIGN.md describes active red `#8b0000` as a toggle button while its state is on.
62. Nothing Nintendo-related is built, proposed or mentioned anywhere in the suites.
63. The BC-250 suite never offers BIOS flashing or a modded BIOS, since software covers what custom BIOSes do. It always advises the latest stock P5.00 BIOS.
64. The Windows suite's apps are for a small handheld screen used with touch and a controller, so UX and UI weigh more. It uses the portable design (`../DESIGN.md`) and fits 1280 x 720 logical pixels at 150 %.
65. Every action in a Windows suite app is reachable by controller and touch. The legend at the bottom is the row of actions, every action is a button and a legend entry, and panes hold no pills (pills stay only inside popups). Nothing is grayed out: a button that can't run says why on the status line. No dialogs: a careful action asks for a second press within five seconds. Windows' own windows aren't used: choose folders and files in core's `browse.Browser`, read long text in a `TextView`.
66. The Windows suite's emulator apps never start a game; games are played from Steam, and A on a game is its Steam mark. Nothing runs before it is asked for.
67. No user name on screen or in a log: show paths through core's `platform.private()` and log with `applog.setup(..., private=True)`. Never read out serial numbers, MAC addresses, SSIDs, access point addresses or paired Bluetooth devices.
68. Windows installers refuse an administrator's window and write only to `%LOCALAPPDATA%\windows-portable-suite\` and `%APPDATA%\windows-portable-suite\`. Nothing goes in the registry. A portal-installed app gets a Start-menu entry and no Desktop shortcut. An action that needs an administrator is the owner's to approve per use case, with one Windows prompt for that action only.
69. An app never deletes anything of the user's on its own. It shows core's `keep.py` page first: a row each with its size, marked Delete at first, A turns one to Keep, X deletes the rows still marked Delete, B deletes nothing.
70. The Windows suite is unsigned.
71. An issue reported by someone else is not work by itself. First check that it matches our hardware, firmware, kernel revision and OS. A single unreproduced report goes in as a note at most. Only an issue reproduced on several boards is worth testing.
72. When something changes how the PS5 behaves (Board Test, Quickfix, the image), first explain the issue and the options and wait for the owner's decision. Don't edit right away.
73. When I change something to cure a failing workflow, CI run or crash, don't write "fixed" or "it works now". Write that a patch was applied and that running the workflow will show whether the issue is gone.
74. When a report lists things for the owner, a note that needs no action says it is only informative and doesn't sit between actionable items.
75. Don't mention that the wiki's Portal Tour needs recording again (`tools/tests/test_portal_tour_stamp.py`, `tools/portal_tour.py --check`) in reports or handovers.
76. Install every app through the portal, so what is installed stays in step. A portal run from a checkout installs the released apps from that checkout.
77. The portal installs as a copy in the home folder, with no `/opt` and no sudo.
78. There is no Development category: the portal lists only released apps. The categories are sustainable, graphics, gaming and utilities, and an app's `category` matches its icon's in `icons/categories.toml`.
79. Core is bundled per app at release time. The suite's shared venv holds only PyQt6 and pygame-ce. `dev/` apps carry `.checkout-only`, import core directly and are in no portal.
80. Data an app's package reads sits in the package or beside it in the app folder. `docs/development/architecture.md` has the steps for a new app.
81. System-wide packages' updates and security fixes are the system's. Our own code and the Python packages in our apps' environments are ours. An rpm-ostree change is active after a restart, which Nexus Deps advises and never does.
82. Checks before handing work over: `python3 tools/check_versions.py`, `python3 tools/check_manifest.py --base origin/main`, `python3 tools/sync_icons.py --check`, `shellcheck -x -S warning tools/*.sh apps/*/install.sh portal/install.sh`, every installer test in `tools/installer-tests/` except `shims.sh`, `mkdocs build --strict`, and `python3 tools/check_wiki.py --base origin/main`, whose every listed section is read against the change.
83. GitHub's Latest release is the newest portal. The Windows suite's `release.yml` never makes it, and Nexus's `docs.yml` publishes its wiki.
84. `.claude/text-decisions.md` holds the owner's decisions on the text. The `/rewrite-text` command rewrites text with its workflow.
85. The Windows suite is worked on inside a Nexus checkout, as two separate git checkouts. A change to both is two commits.
86. A Nexus tool or test that needs the Windows suite says so or skips, and never fails for its absence.
87. Nexus's tooling serves the Windows suite alone. A change to Nexus's `tools/`, `core/` or `dev/` doesn't reach the Bazzite suites, and the reverse.
88. The root `VERSION` is Nexus's own, bumped by the owner.
89. Tests of shared parts that need Linux (sysfs, file modes, bash) skip on Windows with their reason.
90. The Windows suite is named exactly "Windows Portable Suite". Its `SYSTEM` is `windows` and its `TAG_PREFIX` is `wp-`. Tags are `wp-<app>-v<x.y.z>` and `wp-portal-v<x.y.z>`. Windows Portable Test is always installed and listed first. There are no `[checkout.*]` apps.
91. The Windows suite keeps no copy of core or the Nexus tools. Its venv is the Nexus checkout's plus `windows-portable/requirements-dev.txt`. `NEXUS_REF` names the Nexus commit its workflows use. Cloned alone, its tests and tools don't run.
92. Windows suite controls: the d-pad moves an amber focus, A acts, B goes back, View (⧉) exits and Menu (☰) opens the info. An action without a button of its own takes a free one (Remove BIOS on LB, Remove game on RB). The info icon is touch only. Never `setEnabled(False)` on a `Pill` or a row.
93. An app's `summary` in `portal/apps.toml` fits one line at 1280 x 720 (`portal/tests/test_main_window.py` measures it). The wallpaper is on or off for every app at once on the portal's Settings page.
94. The Windows header status line is `<weekday> DD/MM/YYYY | HH:MM | 82%`, with no space before % and the battery last. Windows Portable Test adds `CPU 47° GPU 45° | 18 W | 120 Hz | 82%` under it and has no icon in its header.
95. Approved administrator actions: the portal's Operating Mode helper, USB HD Cam's Allow access and BIOS Reader's Read the settings. Never run a whole app as administrator. An app installed by hand gets both the Start-menu entry and the Desktop shortcut.
96. A Windows app has `apps/<name>/<package>/` with `__init__.py` (`APP_NAME`, `APP_ID` = `windows-portable-<name>`, `EXE_NAME`, `SUITE`, `__version__`, an `AppInfo` with `settings_org=SUITE, settings_ini=True`), `__main__.py` and `main_window.py` on `PortableWindow`. Beside it are `images/` (`<app id>.webp` and `-128.png`), `tests/` (its conftest keeps settings out of the registry), `install.ps1`, `run.ps1`, `requirements.txt`, `requirements-dev.txt`, README.md and the four files.
97. A Windows app's wiki chapter is `docs/apps/<name>.md` with a nav line in `mkdocs.yml`. The release carries it as MANUAL.md.
98. A Windows app's release is `wp-<name>-v<x.y.z>.zip` from `tools/build_release.py`: `program/` (PyInstaller one-folder, `<EXE_NAME>.exe` beside `_internal/`), `install.ps1`, LICENSE, THIRD-PARTY-NOTICES.txt and MANUAL.md, with SHA256SUMS and notes.md.
99. Read what Windows reports through its own APIs (ctypes) or one CIM or PowerShell query that returns JSON, never through the text of a tool such as netsh or powercfg. Run slow reads off the window's thread.
100. A new Windows app adds its `portal/apps.toml` entry and its installer test `tools/installer-tests/<name>.ps1`. `../tools/new_app.py --suite windows-portable` does all of it. CI needs no edit.
101. Windows suite checks, from PowerShell at the root of the Nexus checkout: `.venv-windows\Scripts\python.exe tools\check_versions.py --suite windows-portable`, `.venv-windows\Scripts\python.exe windows-portable\tools\check_manifest.py --base origin/main`, every `windows-portable\tools\installer-tests\*.ps1`, and `.venv-windows\Scripts\mkdocs.exe build --strict -f windows-portable\mkdocs.yml`, then remove `windows-portable\site`. `./test.sh` in Git Bash runs every test suite of this system.
102. A window's layout is checked at 1280 x 720 offscreen, with its minimum height at most 720. The owner looks at it on the Ally.
103. A Windows app works on any Windows handheld and says where something doesn't apply (no AMD driver, no Wi-Fi, no back buttons).
104. Rules and states are added to `CLAUDE.md` after the owner's review, and nowhere else.
105. Before a change to a window's design, show a screenshot of the proposal and wait.
106. What other projects report is a lead with its conditions, not a fact. We test it ourselves. Never conclude "cannot be done" or "out of scope" from a write-up.
107. Work that is not suite work becomes a derived project with its own rules.
108. No pill or button stands alone in a window's title row. Refresh is the round symbol at the right end.
109. A row holds five boxes and pills at most, all as wide as the widest. A card is as wide as a full row.
110. The info symbol is always filled. It says what the app does, and holds text only where the window has no room.
111. The analyses are kept in one file, `ANALYSIS.md`, in the workspace root.
112. A finished or declined row is removed from `ACTION-LIST.md`, and the rows are renumbered from 1. A row is done when the work is done, even if the owner's own try or release is still open.
113. When the owner asks for a list or a table, give the items word for word, numbered, with no extra columns, notes or advice.
114. `CLAUDE.md` has five identical copies: the `Projects` root, `bc250-bazzite`, `bazzite-console`, `Nexus` and `Nexus/windows-portable`. A change goes into all five. Ask before editing it.
115. bazzite-console runs on the owner's own image, not the community image. Its repository is private, so nothing from it is quoted in public files.
116. An unverified outside claim is never written into the wiki or an app as fact, and is not put on the action list.
117. Don't start heavy test runs while the owner's own local CI run is going.
118. The exception to rule 62: DatStation's quiz keeps its questions that name Nintendo as console history, and old CHANGELOG entries keep their words.
119. bazzite-console's existing text was never rewritten to the writing standard, so only new lines must be clean there. The full text rewrite is not started unasked.
120. Nexus TTS (`dev/text`) and Nexus Remix Studio (`dev/studio`) exist in both Bazzite suites. A change to one goes into both.
121. Nexus TTS offers English female voices only and takes English text only. It has its own environment, because its engine has no build for the development venv's Python.
122. A new app goes to both Bazzite suites. If an app seems not to be compatible with bazzite-console, we explore, analyze and then build alternatives.
123. Nexus Garbage Remover (`dev/garbage`, in both Bazzite suites) handles the garbage on the machine. It lists crash dumps, Steam's crash reports, the Trash and caches with their size and command, deletes what is checked after it asks, and notifies from 1 GB on.
124. Our tools' own leftovers stay with `tools/clean_caches.py` before a local CI run. No garbage check goes into CI or a test run.
125. When I see garbage on the machine, I name it with its size and the command, and point to Nexus Garbage Remover.
126. A controller reader gives SDL its dummy drivers only while SDL starts. A program our apps start never inherits them, and core starts Steam without them.
127. The managers' title row shows names only: **Installed**, **shadNet** or **RPCN**, **Controller** and **Steam**. The dot is green when all is well and red otherwise, and the tooltip holds the full state.
128. Every text file opens with its `SPDX-License-Identifier` line, in the comment of its format: GPL-3.0-or-later, or the app's own license where it has another. `tools/tests/test_spdx.py` checks it and lists each file that would break with it, with the reason. A generated file gets the line from its generator.
129. When code changes, search the whole wiki for the changed files and the names they define, and correct every mention, not only the app's own chapter. `tools/check_wiki.py` lists the sections that name a changed file, and `tools/tests/test_wiki_names.py` fails on a name the wiki gives that is gone.
130. When I assume something, I first ask the owner whether the assumption is right, and only then act on it. I say what I assume and what I would do with it. Wrong assumptions have too often meant doing the work again.
