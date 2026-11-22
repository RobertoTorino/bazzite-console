# SPDX-License-Identifier: GPL-3.0-or-later
"""What the wiki names, and whether it is still there (owner, 22-11-2026: "keep it in sync so it stays accurate").
tools/tests/test_wiki_names.py fails on a name that is gone, and tools/check_wiki.py lists the wiki's sections that
name a changed file. A page names:

- a path of the repository in code style (`apps/gpu/install.sh`): it must exist;
- a constant or a function in code style (`KNOWN_VERSION`, `steam.signed_in()`): the code must have it;
- an option after one of our scripts (`dev/garbage/run.sh --remind`): that script must take it;
- in an app's chapter, a window label in bold where the page uses it as a control ("click **Delete**", "the
  **Install** pill"): the app's code, core's or the portal's must have its text. A pill's two lines may be written
  together (**PCSX2 Install**): each part is then a string in the code.

A name of something outside the suite (another program's setting, an environment variable) goes in OUTSIDE, with
why. Only the standard library."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = ("apps", "core", "portal", "tools", "dev", "docs", "icons", "design")
CODE = ("*.py", "*.sh", "*.rs", "*.toml", "*.yml", "*.js", "*.c", "*.desktop", "*.ini", "*.service", "*.example")
SKIP = ("/.venv", "/.cache/", "/site/", "/node_modules/", "/target/", "/docs/", "/__pycache__/")
# Names of things outside the suite that a page may name: name -> why
OUTSIDE = {
    "GDK_BACKEND": "GTK's environment variable",
    "self.tr()": "Qt's translation function, which the apps do not use",
    "Enable remote features": "the Xbox's own setting",
    "Watch → Custom → Releases": "GitHub's menu",
    "Add folder…": "PPSSPP Manager's button of version 1.0 and older, named as history",
}
PATH = re.compile(r"(?:%s)/[\w./-]+" % "|".join(TOP))
CONST = re.compile(r"(?:[a-z_][\w.]*\.)?([A-Z][A-Z0-9_]{3,})")
FUNC = re.compile(r"(?:([\w.]+)\.)?([a-z_]\w+)\(\)")
SCRIPT = re.compile(r"((?:apps|core|portal|tools|dev)/[\w./-]+)\s+(.*)")
OPTION = re.compile(r"(?<![\w-])(--[a-z][\w-]*)")
PLAYSTATION_ID = re.compile(r"[A-Z]{4}\d{5}")            # a PlayStation game's title ID, such as CUSA41215
KEY = re.compile(r"(?:(?:Shift|Ctrl|Alt|Super)\+)*(?:F\d{1,2}|Tab|Enter|Escape|Esc|Space|Delete|[A-Z])")
CONTROL = re.compile(r"(?:click|clicks|press|presses|pressing|choose|check|uncheck|select|open|opens|turn on)"
                     r"(?: on| the)? \*\*([^*\n]{2,40})\*\*", re.I)
TEMPLATE = re.compile(r"[\"']([^\"'\n]*\{[^{}\n]*\}[^\"'\n]*)[\"']")   # a code string with a placeholder
WIDGET = re.compile(r"\*\*([^*\n]{2,40})\*\* (?:pill|pills|tab|tabs|button|buttons|box|checkbox|menu|field|column)\b")


def code_files(root: Path = ROOT) -> dict[Path, str]:
    """The repository's code, the wiki left out."""
    found = {}
    for pattern in CODE:
        for path in root.rglob(pattern):
            if any(part in path.as_posix() for part in SKIP):
                continue
            try:
                found[path] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return found


def spans(text: str) -> list[str]:
    """The text of each code span on a page."""
    return [span.strip() for span in re.findall(r"`([^`\n]+)`", text)]


def labels(text: str) -> list[str]:
    """The bold labels a page uses as a control."""
    return [label.strip() for label in CONTROL.findall(text) + WIDGET.findall(text)]


def _label_found(label: str, source: str) -> bool:
    text = label.rstrip(":.").replace("…", "")
    if text in source or label in OUTSIDE or KEY.fullmatch(label):
        return True
    parts = text.split()
    if len(parts) > 1 and all(f'"{part}"' in source or f"'{part}'" in source for part in parts):
        return True
    return any(re.fullmatch(_template(found), text) for found in TEMPLATE.findall(source))


def _template(text: str) -> str:
    """A code string with placeholders ({0}, {name}) as a pattern: each placeholder stands for any text."""
    return ".+".join(re.escape(part) for part in re.split(r"\{[^{}]*\}", text.rstrip(":.")))


def problems(root: Path = ROOT) -> list[str]:
    """Each name the wiki gives that is not there: "page: name (what is wrong)"."""
    code = code_files(root)
    everything = "\n".join(code.values())
    out = []
    for page in sorted((root / "docs").rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        name = page.relative_to(root).as_posix()
        for span in spans(text):
            if span in OUTSIDE:
                continue
            path = PATH.fullmatch(span.rstrip(".,:;)"))
            if path and not (root / path.group(0)).exists():
                out.append(f"{name}: {span} (no such path)")
                continue
            const = CONST.fullmatch(span)
            if const and not PLAYSTATION_ID.fullmatch(const.group(1)) and const.group(1) not in everything:
                out.append(f"{name}: {span} (no such name in the code)")
                continue
            func = FUNC.fullmatch(span)
            if func and not re.search(r"(?:def|fn) %s\b|\b%s\(" % (func.group(2), func.group(2)), everything):
                out.append(f"{name}: {span} (no such function in the code)")
                continue
            script = SCRIPT.match(span)
            if script and (root / script.group(1)).is_file():
                body = (root / script.group(1)).read_text(encoding="utf-8", errors="replace")
                out += [f"{name}: {span} ({option} is not an option of {script.group(1)})"
                        for option in OPTION.findall(script.group(2)) if option not in body]
        app = root / "apps" / page.stem
        if name.startswith("docs/apps/") and app.is_dir():
            source = "\n".join(text_ for path, text_ in code.items()
                               if app in path.parents or path.relative_to(root).parts[0] in ("core", "portal"))
            out += [f"{name}: **{label}** (no such label in the app)" for label in labels(text)
                    if not _label_found(label, source)]
    return out
