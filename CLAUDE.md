<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# CLAUDE.md (Bazzite Console Suite)

The rules of the **Bazzite Console Suite**: control your PlayStation 5 running Bazzite. The repository is
`github.com/RobertoTorino/bazzite-console` (branch `main`).

**It is standalone** (owner, 13-11-2026: "it is and stays a standalone repo ... it should run on its own using its
own tooling"). Everything it needs is in this repository: its tools, its core and its development apps. Nothing here
depends on a checkout of Nexus or of another suite, and nothing is to be taken from one at run, test or release
time. The tooling began as a copy of Nexus's and is this repository's own now: a change to it is made here.

## Rules from the owner

- **Never commit, tag or push.** The owner does every git commit, tag and push. Finish work in the working tree and
  say what is ready.
- **Releases are the owner's**: the version bumps, the tags (`ps5-` first), the release assets, the pins in
  `portal/apps.toml` and the release entries in the CHANGELOGs. When finished work needs a release, say which app
  and why.
- **CHANGELOG for every change**: the root CHANGELOG for suite-wide changes, the app's, core's or the portal's for
  its own. A `Changelog: DD-MM-YYYY HH:MM:SS` line (Europe/Amsterdam), a blank line, then plain sentences; newest
  first. Every entry starts with its kind: `Breaking.`, `Added.` or `Fixed.`.
- **VERSION is the single source** of each app's version; copies in code must match (`tools/check_versions.py`).
- **American English**, plain short sentences, written for the person using the tool. READMEs and the wiki hold no
  status or plans.
- **Open by default; no personal data** (names, host and user names, serial numbers, MAC and IP addresses, keys).

## What this is

The suite's system is `bazzite` (`SYSTEM`) and its tags start with `ps5-` (`TAG_PREFIX`). The portal's `apps.toml`
lists the suite's apps. **Bazzite Test** (`apps/bazzite/`, package `bazzite_test`) is the first tile, always
installed and the only required app. App keys, release tags, installer tests and wiki chapters use the same short
folder name.

The portal and its apps are for PlayStation 5 hardware running Bazzite. They read system and device information;
they do not assume that hardware features or paths from another Bazzite device apply here. An app that changes the
console is marked `changes_board` in `apps.toml` with a `board_change` text, and its wiki chapter opens with the
same text in a `!!! warning "Changes the board"` box (`tools/check_manifest.py` compares them).

## Layout

- `portal/`: the portal (`bazzite_console_portal`), its pinned app manifest, tests, requirements and installer.
- `apps/<name>/`: one app per folder, with its Python package, `images/`, `tests/`, `install.sh`, requirements and
  `VERSION`, `CHANGELOG`, `LICENSE` and `.gitignore`.
- `core/bazzite_console_core/` with `core/VERSION`: the shared code, bundled per app in a release
  (`tools/stage_app.py`). It names the suite's folders (`~/.config/bazzite-console/`,
  `~/.local/share/bazzite-console-suite/`) and addresses.
- `tools/`: the release and check tools (`build_release.py`, `stage_app.py`, `check_versions.py`,
  `check_manifest.py`, `pin_app.py`, `suite_release.py`, `publish_release.sh`, `tag-release.sh`, `check-release.sh`,
  `suites.py`, `fix-modes.sh`), the CHANGELOG merge driver and check, the tours, `mkdocs/` (the wiki's hooks and overrides),
  `tools/tests/` and `tools/installer-tests/` (one per app, the portal and a release).
- `dev/`: the development apps, run from the checkout and never released.
- `docs/` and `mkdocs.yml`: the wiki, robertotorino.github.io/bazzite-console/; `icons/`: the category icons and
  `categories.toml`, which assigns them to the apps.
- `.github/workflows/ci.yml`: the checks on every push.

## Design and naming

This is a Bazzite suite and follows the Bazzite design: purple for the wiki and the shared Bazzite app theme.
The portal, wiki and category icons use artwork made for this suite. The Bazzite Test app's Python package is
`bazzite_test`; its app folder and manifest key are `bazzite`.

## Checks

From the repository root, as `.github/workflows/ci.yml` runs them (a venv with the folders' `requirements-dev.txt`):

```bash
(cd <folder> && python -m pytest tests)                     # portal, tools and each apps/<name>
python3 tools/check_manifest.py
find apps portal tools -name '*.sh' -print0 | xargs -0 -n1 bash -n
for t in tools/installer-tests/*.sh; do [ "${t##*/}" = shims.sh ] || bash "$t"; done   # needs fakeroot
mkdocs build --strict
```

A release is built and published with `tools/tag-release.sh ps5-<app>-v<x.y.z>`, by the owner.

The manual (`docs/`, built with MkDocs) is called **the wiki** in user-facing text.
