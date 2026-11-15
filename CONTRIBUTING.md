<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Contributing

Bug reports, ideas and pull requests are welcome. Report security problems privately, as the
[security policy](docs/SECURITY.md) says, not in an issue or a pull request.

## Licenses

Each app keeps its own `LICENSE`, and what you contribute to a folder is under that folder's license:

- GPL-3.0-or-later: the suite, the portal, `core/`, `tools/`, the development apps in `dev/` and most apps.
- AGPL-3.0-or-later: Remote Play (`apps/remoteplay`), whose protocol code ported from chiaki-ng is AGPL-3.0-only
  (the files marked `SPDX-License-Identifier: AGPL-3.0-only`).

Controller (`apps/controller`) and XBOX Remote Play (`apps/clb`) are GPL-3.0-or-later and include code ported from
MIT-licensed projects; those files keep their attribution, and the app's README keeps the MIT notice.

Icons and sounds are under the license of the folder they are in, the same as the code. Contribute only what you may
license that way: your own work, or work under a compatible license, with its source and license named in the pull
request. Say so when something was made with generative AI tools.

## Icons

Every app in a category has the same icon. A new or changed icon goes in `icons/<category>/`, and
`icons/categories.toml` names each app's category; `python3 tools/sync_icons.py` writes the copies the apps, the
portal and the wiki use. The wiki's [Development](docs/development/index.md#icons) page describes it.

## Before a pull request

- Add a CHANGELOG entry: the app's own for a change to one app, the root `CHANGELOG` for a change to the whole
  suite. The format is a `Changelog: DD-MM-YYYY HH:MM:SS` line (Europe/Amsterdam time), a blank line, then plain
  sentences starting with `Breaking.`, `Added.` or `Fixed.`.
- Leave `VERSION` files and `portal/apps.toml` as they are: versions and releases are the maintainer's.
- Run the checks: `./test.sh` (every test folder) and `tools/ci-local.sh` (the versions, the manifest, the icons'
  copies, and the tests of `tools/` and `dev/`).
