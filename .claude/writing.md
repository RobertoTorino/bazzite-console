<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# How to write the text

The standard for every text a person reads: the wiki, the READMEs, the text in the apps' windows (hints,
tooltips, dialogs, notes, labels, log lines), the portal's texts in `portal/apps.toml` and the messages the apps'
scripts print. It comes from the pilot on a fan app's texts, as the owner corrected it (owner, 12-11-2026: "Most of
the text in this project is very badly written"). The CHANGELOGs are history and stay as they are. A new CHANGELOG
entry follows this standard too. The owner's decisions on particular texts are in
[text-decisions.md](text-decisions.md).

`tools/text_check.py` checks a text by these rules, with LanguageTool (spelling, grammar, American English) and
Vale (style, readability). Run `python3 tools/text_check.py --details FILE` after writing. A text is done when it
has nothing left to fix: every problem is fixed, or is a false alarm. Vale's advice (passive voice, wordy phrases)
is taken where the sentence reads better for it. Then read it back as the person who uses the app.

## The rules

1. **Purpose first.** Say what the reader gets before you say how it works. The service, the file path and sysfs
   come later, or in the Files section.
2. **One fact per sentence.** Keep sentences under 25 words. Never over 30.
3. **No chains.** Do not join facts with a semicolon. Do not go on after a colon with more of the sentence. Do not
   hide a fact in parentheses. Put a short name or a unit in parentheses, nothing longer than four words.
4. **A list for three or more parts.** When a sentence would name three or more things with their details, make it
   a list. A list item that is not a sentence has no period and no semicolon.
5. **Explain a term the first time.** Write "a thermal guard, a background service that keeps watching when no app
   is open", not just "the guard". Write the project's own terms only after they are explained.
6. **Talk to the reader.** Write "you" and say what they see and do. Name the labels in the window in **bold**,
   exactly as the window shows them.
7. **Plain words, in American English.** "Turn on" over "enable", "remove" over "uninstall it from the system",
   "restart" over "reboot". The manual is **the wiki**. American English, also in labels: color, gray, canceled,
   behavior, license, catalog, labeled, authorized; **check** and **uncheck** a box, never tick or untick; **ID**;
   afterward, toward; anymore.
8. **No long text in the window** (owner, 01-11-2026). A hint under a control is one or two short lines. A longer
   explanation goes behind an info symbol (core's `InfoButton`) in its group, with a link to the wiki.
9. **Dialogs ask one question.** The first line is the question. Then what will happen, one fact per line. The last
   line says when you will be asked for your password.
10. **Correct facts, never change them.** A rewrite keeps every command, path, number, link and limit. When the old
    text was wrong, fix it and say so in the CHANGELOG.

## What stays

- **Headings** stay word for word, so the links to them keep working.
- **Button and field labels** change only to correct their English (Untick becomes Uncheck). The tests and the wiki
  that name a label change with it.
- **The "Changes the board" box** is the portal's `board_change` in `apps.toml`, word for word. Rewrite both
  together, so `tools/check_manifest.py` still finds them equal. It is a portal change.
- **Commands, paths, code and numbers** stay exactly as they are. So do the strings the code compares or parses,
  settings keys, and the disclaimer.

## Before and after

From a fan app's wiki chapter:

> **Before:** Shows the temperatures and fans of the PlayStation 5 on Bazzite, and runs a thermal guard: a system
> service that watches the GPU and the CPU, also when no app is open, and warns, cools and at a critical
> temperature shuts the board down cleanly.
>
> **After:** PS5 Fan Controller shows the temperatures and fan speeds of the **PlayStation 5** on **Bazzite**. It
> can also turn on a **thermal guard**, a background service that protects the board from overheating. The guard
> keeps watching when no app is open. When the board gets too hot it warns you. If it gets hotter still, it runs
> the fans at full speed. As a last resort it shuts the board down cleanly.

A dialog:

> **Before:** Stop and remove the thermal guard? Nothing then watches the temperatures while this window is closed;
> the fans follow the firmware's curve. It needs your password.
>
> **After:** Turn the thermal guard off? After that, nothing watches the temperatures while this window is closed.
> The fans go back to how they were. You will be asked for your password.

A log line:

> **Before:** The GPU is back at 79 °C: the fans are back as they were.
>
> **After:** The GPU is back at 79 °C. The fans are back to how they were.

A tooltip:

> **Before:** Stop and remove the guard; the fans go back as they were
>
> **After:** Stop the guard and remove it. The fans go back to how they were
