export const meta = {
  name: 'rewrite-text',
  description: 'Rewrite the text of bazzite-console units to .claude/writing.md until tools/text_check.py finds nothing to fix, then check each for changed facts',
  whenToUse: 'Started by the /rewrite-text command, with args {units: ["fan", "portal", "docs/install.md", ...]}',
  phases: [
    { title: 'Rewrite', detail: 'one agent per unit: rewrite until text_check finds nothing left to fix' },
    { title: 'Check', detail: 'one agent per unit: compare old and new against the code, fix, run the checks' },
  ],
}

const REPO = '/var/home/admin/Projects/bazzite-console'
const SITE = '/tmp/rewrite-text-site'

const REWRITE = { type: 'object', properties: {
  files_changed: { type: 'array', items: { type: 'string' } },
  labels_renamed: { type: 'array', items: { type: 'string' }, description: 'old label -> new label, and where else (outside this unit) the wiki or another app names it' },
  facts_corrected: { type: 'array', items: { type: 'string' }, description: 'old text that was wrong, and what the code shows' },
  false_alarms: { type: 'array', items: { type: 'string' }, description: 'text_check problems left on purpose, with why' },
  to_fix_before: { type: 'number' }, to_fix_after: { type: 'number' },
  questions: { type: 'array', items: { type: 'string' }, description: "decisions that are the owner's" } },
  required: ['files_changed', 'labels_renamed', 'facts_corrected', 'false_alarms', 'to_fix_before', 'to_fix_after', 'questions'] }
const CHECK = { type: 'object', properties: {
  problems: { type: 'array', items: { type: 'string' } }, fixed: { type: 'array', items: { type: 'string' } },
  remaining: { type: 'array', items: { type: 'string' } }, checks_pass: { type: 'boolean' },
  output_tail: { type: 'string' }, to_fix_after: { type: 'number' } },
  required: ['problems', 'fixed', 'remaining', 'checks_pass', 'output_tail', 'to_fix_after'] }

// The files of a unit, its tests and its CHANGELOG.
const unit = (name) => {
  if (name === 'apps-toml') return {
    files: 'portal/apps.toml (each app\'s and quickfix\'s name, summary and board_change) and the "!!! warning \\"Changes the board\\"" box in each docs/apps/<key>.md, which must stay word for word the same as its board_change',
    paths: 'portal/apps.toml docs/apps', tests: `cd ${REPO} && python3 tools/check_manifest.py --base origin/main && (cd portal && QT_QPA_PLATFORM=offscreen ${REPO}/.venv-linux/bin/python -m pytest -q tests)`,
    changelog: 'portal/CHANGELOG (one entry for the summaries and texts), and the CHANGELOG of each app whose board_change changed' }
  if (name === 'portal') return { files: 'docs/portal.md, portal/README.md and the text in portal/ (its .py files and install.sh), but NOT portal/apps.toml',
    paths: 'docs/portal.md portal/README.md portal/bazzite_console_portal portal/install.sh', tests: `cd ${REPO}/portal && QT_QPA_PLATFORM=offscreen ${REPO}/.venv-linux/bin/python -m pytest -q tests`, changelog: 'portal/CHANGELOG' }
  if (name === 'core') return { files: 'core/README.md and the text in core/bazzite_console_core/*.py',
    paths: 'core', tests: `cd ${REPO}/core && QT_QPA_PLATFORM=offscreen ${REPO}/.venv-linux/bin/python -m pytest -q tests, and the tests of each app, dev app or the portal that name a string you changed (find them with grep -rl in apps/*/tests dev/*/tests portal/tests); never the whole ./test.sh`, changelog: 'core/CHANGELOG' }
  if (name === 'design') return { files: 'DESIGN.md, whose text is in tools/make_design.py: change the text there, then regenerate with python3 tools/make_design.py (never hand-edit DESIGN.md)',
    paths: 'DESIGN.md', tests: `cd ${REPO} && python3 tools/make_design.py --check`, changelog: 'the root CHANGELOG' }
  if (name.startsWith('dev/')) return { files: `${name}/ (its README and the text in its .py files)`, paths: name,
    tests: `cd ${REPO}/${name} && QT_QPA_PLATFORM=offscreen ${REPO}/.venv-linux/bin/python -m pytest -q tests`, changelog: `${name}/CHANGELOG` }
  if (name.endsWith('.md')) return { files: name, paths: name,
    tests: `cd ${REPO}/tools && ${REPO}/.venv-linux/bin/python -m pytest -q tests`, changelog: 'the root CHANGELOG' }
  return { files: `docs/apps/${name}.md (the wiki chapter, except its "Changes the board" box) and apps/${name}/ (README.md, the text in its .py files, its install.sh and launcher, its .desktop file), but NOT portal/apps.toml`,
    paths: `docs/apps/${name}.md apps/${name}`,
    tests: `cd ${REPO}/apps/${name} && QT_QPA_PLATFORM=offscreen ${REPO}/.venv-linux/bin/python -m pytest -q tests`, changelog: `apps/${name}/CHANGELOG` }
}

const rewritePrompt = (name, u = unit(name)) => `You rewrite the text of ONE unit ("${name}") of the Bazzite Console Suite, in the git checkout ${REPO}. Nothing is committed.

Read first, and follow exactly: ${REPO}/.claude/writing.md (the standard), ${REPO}/.claude/text-decisions.md (the owner's decisions) and the repository's CLAUDE.md naming rules.

Your files, and nothing else: ${u.files}.

1. Run: cd ${REPO} && python3 tools/text_check.py --details ${u.paths} | tail -n 400. Record the number "to fix" as to_fix_before. Every problem it lists is either fixed or a false alarm you can name (a name or term LanguageTool does not know, a label quoted exactly). Add a word that is right here to tools/text_check/words.txt only if it is a real name or term of this suite.
2. Rewrite the text in your files to the standard: short sentences, one fact each, no chains, plain American English, the purpose first. Take Vale's advice (passive voice, wordy phrases) where the sentence reads better for it. Keep every command, path, number, link, heading, code span and limit: move them, never drop them. Keep strings the code compares or parses, settings keys, log formats parsed by code, f-string placeholders and the disclaimer. A label changes only to correct its English (Untick -> Uncheck): then change every test and wiki line in your files that names it, and list the label in labels_renamed with any place outside your files that names it.
3. Check every fact against the code. If the old text was wrong, correct it and list it in facts_corrected. Never invent a claim the old text did not make.
4. Run text_check again on ${u.paths} until nothing is left to fix but false alarms. Then: cd ${REPO} && python3 tools/text_check.py --gone <each file you changed>. Each line it reports is put back, or is a rewording that keeps the fact.
5. Run: ${u.tests}. Where your files hold wiki pages, also: cd ${REPO} && .venv-linux/bin/mkdocs build --strict -q -d ${SITE}-${name.replace(/\W/g, '_')}. Everything must pass. Update a test only where it asserts the old wording of a string you changed.
6. Add one entry at the top of ${u.changelog}: "Changelog: <time>" (python3 -c "import datetime, zoneinfo; print(datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Amsterdam')).strftime('%d-%m-%Y %H:%M:%S'))"), a blank line, then a paragraph starting "Fixed." that says what was rewritten, the labels renamed, each fact corrected, "Nothing the app does has changed." and the tests that changed. Wrap at 120 columns.

Return the structured result.`

const checkPrompt = (name, r, u = unit(name)) => `You are the second pass over a rewrite of ONE unit ("${name}") of ${REPO}. A rewrite changes wording only, and corrects facts that were wrong. The rewriter reported: ${JSON.stringify(r)}

Read ${REPO}/.claude/writing.md and ${REPO}/.claude/text-decisions.md. Read git -C ${REPO} diff -- ${u.paths}. Compare every changed sentence, old and new, with the code. Look for:
- a fact that changed: a number, a condition, an order, what happens when, who is asked, what is kept or removed
- a fact that is gone: run python3 tools/text_check.py --gone on the changed files
- a claim the old text did not make and the code does not back; a list of examples made closed, or a closed list made open
- a heading, link, anchor or code span that changed; a label changed for any reason but its English
- a string the code compares, parses or a test reads, reworded so it breaks
- a decision in text-decisions.md that was not kept
- the rewriter's facts_corrected: confirm each one against the code, and put the old text back where it was right
- the CHANGELOG entry: accurate, starts with "Fixed."
- a sentence you must read twice to understand: rewrite it
Fix what you find, in the unit's files only. Then run: cd ${REPO} && python3 tools/text_check.py ${u.paths} | tail -n 5, and ${u.tests}, and the wiki build if the unit holds wiki pages (cd ${REPO} && .venv-linux/bin/mkdocs build --strict -q -d ${SITE}-${name.replace(/\W/g, '_')}). Report.`

const units = args.units
return await pipeline(units,
  name => agent(rewritePrompt(name), { label: `rewrite:${name}`, phase: 'Rewrite', schema: REWRITE }),
  (r, name) => r ? agent(checkPrompt(name, r), { label: `check:${name}`, phase: 'Check', schema: CHECK })
    .then(c => ({ unit: name, rewrite: r, check: c })) : { unit: name, rewrite: null, check: null })
