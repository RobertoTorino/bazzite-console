---
description: Rewrite the suite's text to .claude/writing.md, checked by tools/text_check.py, with every fact kept
argument-hint: all | <app key> | portal | core | design | dev/<name> | <page.md> | apps-toml ...
---

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Rewrite the text of these units of bazzite-console: $ARGUMENTS

The owner opted in to the workflow by running this command. Do it in this order, and do not commit.

1. **The units.** `all` means every unit, in this order:
   - each app under `apps/` (its key, such as `fan`)
   - `portal`, `core` and `design`
   - each development app (`dev/<name>`)
   - each wiki page that is no app's chapter: `docs/*.md`, `docs/development/*.md` and `docs/history/*.md`, except
     `docs/portal.md`
   - the root's `README.md`, `CONTRIBUTING.md` and `ALL-TESTS.md`
   - `apps-toml` last: the portal's texts in `portal/apps.toml`, with the "Changes the board" boxes of the chapters

   Never run `apps-toml` alongside an app's unit: both edit the app's chapter.
2. **Before:** run `python3 tools/text_check.py --server start`, then `python3 tools/text_check.py <the units' paths>`
   and note the number to fix.
3. **The rewrite:** run the saved workflow `rewrite-text` (Workflow tool, `name: "rewrite-text"`) with
   `args: {units: [...]}`, at most 8 units a run unless the owner asked for more. Run `apps-toml` in a run of its own,
   after the rest. Between runs, read each unit's result. Act on `labels_renamed` that name places outside the unit:
   change those too. Collect the questions and the facts corrected.
4. **After:** run `python3 tools/text_check.py --server stop`, then the checks in CLAUDE.md: `./test.sh`,
   `python3 tools/check_versions.py`, `python3 tools/check_manifest.py --base origin/main`,
   `.venv-linux/bin/mkdocs build --strict` and `tools/ci-local.sh`, then `python3 tools/check_wiki.py --base origin/main`
   (read each section it lists against the change) and `tools/tests/test_wiki_names.py`. Run `python3 tools/text_check.py` on all the
   units once more and give the number to fix, before and after.
5. **The handover:** what was rewritten, each fact corrected, each label renamed, the owner's questions, and which
   apps, the portal and core need a release (NRT does it). Short, for the owner.
