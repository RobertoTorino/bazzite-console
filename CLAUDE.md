<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# CLAUDE.md (Bazzite Console Suite)

The rules of the **Bazzite Console Suite**: control your PlayStation 5 running Bazzite. It has a repository of its
own, `github.com/RobertoTorino/bazzite-console` (branch `main`; owner, 13-11-2026: one repository per suite, the
tooling in Nexus). Nexus's CLAUDE.md (`../CLAUDE.md` in the checkout described below) holds the shared rules for git,
releases, changelogs, checks and line endings, and applies here too. Paths below are written from this repository's
root unless they start with `../`, which is the Nexus checkout.

## Inside a Nexus checkout

The suite keeps no copy of the Nexus tools or of the Nexus apps. It is worked on **inside a checkout of Nexus**
(`github.com/RobertoTorino/nexus`), cloned there as the folder `bazzite-console/`, which Nexus's `.gitignore` lists:

```bash
git clone https://github.com/RobertoTorino/nexus.git Nexus
git clone https://github.com/RobertoTorino/bazzite-console.git Nexus/bazzite-console
```

So `../tools/` and `../dev/` are Nexus's, every Nexus tool finds the suite (`--suite bazzite-console`), and
`../test.sh` runs its tests with the Nexus checkout's venv. The two are separate git checkouts: git in this folder is
the suite's (its commits, its tags, its CI), git in `..` is Nexus's, and a change to both is two commits. Cloned on
its own, outside a Nexus checkout, the suite's tools, installer tests and wiki build do not run. `NEXUS_REF` names
the Nexus commit the suite's workflows use (a branch such as `main`, or a commit to hold the suite on a tested Nexus):
every job starts with Nexus's action `RobertoTorino/nexus/.github/actions/suite`, which checks out that Nexus and
this repository inside it.

**The suite's core is its own**: `core/bazzite_console_core/` with `core/VERSION`, not Nexus's `bc250_core`. The
Nexus tools bundle it per app in a release (`../tools/stage_app.py`, `../tools/suites.py`: `core_dir()`), and it
names the suite's own folders (`~/.config/bazzite-console/`, `~/.local/share/bazzite-console-suite/`) and addresses.

## What this is

The suite's system is `bazzite` (`SYSTEM`) and its tags start with `ps5-` (`TAG_PREFIX`). The portal's `apps.toml`
lists the suite's apps. **Bazzite Test** (`apps/bazzite/`, package `bazzite_test`) is the first tile, always
installed and the only required app. App keys, release tags, installer tests and wiki chapters use the same short
folder name.

The portal and its apps are for PlayStation 5 hardware running Bazzite. They read system and device information;
they do not assume that hardware features or paths from another Bazzite device apply here. This suite is maintained
independently from the BC250 Bazzite Suite.

## Layout

- `portal/`: the portal (`bazzite_console_portal`), its pinned app manifest, tests, requirements and installer.
- `apps/<name>/`: one app per folder, with its Python package, `images/`, `tests/`, `install.sh`, requirements and
  `VERSION`, `CHANGELOG`, `LICENSE` and `.gitignore`.
- `core/`: the suite's core.
- `tools/`: the suite's own manifest and release helpers (`check_manifest.py`, `pin_app.py`, `suite_release.py`,
  `publish_release.sh`, `check-release.sh`), its tours, `mkdocs/` (the wiki's hook and overrides) and
  `installer-tests/`.
- `docs/` and `mkdocs.yml`: the suite's wiki, built by Nexus's `docs.yml` and published under the Nexus page, at
  robertotorino.github.io/nexus/bazzite-console-suite/; `icons/`: category icons and their app copies.
- `.github/workflows/`: `ci.yml` and `release.yml`.

## Design and naming

This is a Bazzite suite and follows the Bazzite design: purple for the wiki and the shared Bazzite app theme.
The portal, wiki and category icons use artwork made for this suite. The Bazzite Test app's Python package is
`bazzite_test`; its app folder and manifest key are `bazzite`.

## Checks

From the root of the Nexus checkout:

```bash
./test.sh                                                   # every test suite of this system, this suite's among them
python3 tools/check_versions.py --suite bazzite-console
python3 bazzite-console/tools/check_manifest.py
for t in bazzite-console/tools/installer-tests/*.sh; do [ "${t##*/}" = shims.sh ] || bash "$t"; done
mkdocs build --strict -f bazzite-console/mkdocs.yml         # from the venv; then remove bazzite-console/site
```

## Releases

Everything about releases is the owner's (Nexus's CLAUDE.md): the version bumps, the tags (`ps5-` first), the
release assets and the pins in `portal/apps.toml`. When finished work needs a release, the handover says which app
and why.

The manual (`docs/`, built with MkDocs) is called **the wiki** in user-facing text.
