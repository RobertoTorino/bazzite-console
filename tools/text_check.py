#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lists what is wrong with the suite's text, file by file. Run it whenever you want:

    python3 tools/text_check.py                    # all of it: the worst files first, with their counts
    python3 tools/text_check.py docs/apps/fan.md   # only these files or folders
    python3 tools/text_check.py --details PATH     # every problem, with its line, the text and a suggestion
    python3 tools/text_check.py --json FILE        # every problem as JSON, for the rewrite (/rewrite-text)
    python3 tools/text_check.py --gone PATH        # what a rewrite lost: commands, paths, numbers, links, headings

The text is everything a person reads: the wiki and the READMEs, the text in the apps' windows (hints, tooltips,
dialogs, messages, and the labels of buttons, boxes, tabs and columns), the portal's texts in portal/apps.toml
(each app's name, summary and Changes the board text), the messages the apps' scripts print (install.sh,
test-board.sh, the launchers) and the menu entries' names and comments. The CHANGELOGs are history and stay out. Code, commands,
paths and link addresses are not text.

Three checks read it:
    rules           .claude/writing.md: a sentence over 30 words, a semicolon or colon that chains facts, a
                    parenthesis of more than four words, a British spelling, "manual" for the wiki
    LanguageTool    spelling, grammar and American English (en-US), in a podman container on this machine
    Vale            style and readability (the rule sets write-good, proselint and Readability, in
                    tools/text_check/styles)

Nothing is sent anywhere. The first run downloads LanguageTool (about 250 MB, its SHA-256 checked) and builds its
image once. Words that are right here but unknown to LanguageTool (names, programs) go in
tools/text_check/words.txt, one per line. It is not a test and not a CI check."""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "tools" / "text_check"
CACHE = Path.home() / ".cache" / f"{ROOT.name}-text-check"
LT_VERSION = "6.6"
LT_URL = f"https://languagetool.org/download/LanguageTool-{LT_VERSION}.zip"
LT_SHA256 = "53600506b399bb5ffe1e4c8dec794fd378212f14aaf38ccef9b6f89314d11631"
IMAGE = f"localhost/{ROOT.name}-languagetool:{LT_VERSION}"
SERVER = f"{ROOT.name}-languagetool"     # the shared server of --server start, used by every run while it runs
WORKERS = 4

# The rules of .claude/writing.md.
LONG_WORDS = 30
ASIDE_WORDS = 4
LEAD_WORDS = 4                          # a colon after fewer words ends a name: "Turn on…: ..."
STRING_WORDS = 4                        # a shorter string in the code is text only when a window shows it as a label
SKIP_NAMES = {"CHANGELOG", "MIGRATION.md", "LICENSE", "CLAUDE.md"}
SKIP_PARTS = {"tests", "node_modules", "site", "__pycache__", "styles"}
WORDS = {
    "colour": "color", "colours": "colors", "coloured": "colored", "grey": "gray", "centre": "center",
    "centred": "centered", "cancelled": "canceled", "cancelling": "canceling", "licence": "license",
    "catalogue": "catalog", "labelled": "labeled", "behaviour": "behavior", "favourite": "favorite",
    "manual": "wiki (unless it means done by hand)",
}
_WORD = re.compile(r"\b(" + "|".join(WORDS) + r")\b", re.IGNORECASE)
_MANUAL_BY_HAND = re.compile(r"\bmanual (value|mode|fan|speed|step|setting|\d)|\bmanual\b[^.]*%", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(*\[])")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SKIP_LINE = re.compile(r"^\s*(#|<!--|!\[|\[!\[|!!!|\?\?\?|\|\s*-{3}|-{3,}\s*$|<[a-z/])")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
_LEAD = re.compile(r"^\*\*[^*]{1,80}\*\*:?\s*")     # a list item's bold name, with its colon
_MID_COLON = re.compile(r":\s+(?=[a-z*\[])")
_PAREN = re.compile(r"\(([^()]*)\)")

# The calls whose strings a window shows as labels, titles and hints.
UI_CALLS = {"QPushButton", "QCheckBox", "QRadioButton", "QGroupBox", "QLabel", "QAction", "addTab", "setText",
            "setToolTip", "setTabToolTip", "setPlaceholderText", "setWindowTitle", "window_title",
            "setHorizontalHeaderLabels", "setHeaderLabels", "addItem", "addItems", "Pill", "action_pill",
            "accent_button", "hint_label", "page_header", "MetricBox", "StatusPill", "InfoButton", "TextDialog",
            "setTitle", "setStatusTip"}
_IDENTIFIER = re.compile(r"^[a-z0-9_.:/-]*$|^[A-Z0-9_]+$|^\W*$")

# LanguageTool: rules that only see Markdown and code, and the suite's style choices (no serial comma, a window's
# labels as names: "the Install page"), which are not mistakes.
LT_OFF = ["WHITESPACE_RULE", "COMMA_PARENTHESIS_WHITESPACE", "UPPERCASE_SENTENCE_START", "EN_QUOTES", "DASH_RULE",
          "PUNCTUATION_PARAGRAPH_END", "SENTENCE_WHITESPACE", "EN_UNPAIRED_BRACKETS", "EN_UNPAIRED_QUOTES", "ARROWS",
          "MULTIPLICATION_SIGN", "PLUS_MINUS", "CONSECUTIVE_SPACES", "UNIT_SPACE", "NUMBERS_IN_WORDS",
          "EN_WORD_COHERENCY", "TOO_LONG_SENTENCE", "TOO_LONG_PARAGRAPH", "LC_AFTER_PERIOD", "ELLIPSIS",
          "WORD_CONTAINS_UNDERSCORE", "ID_CASING", "COPYRIGHT", "SERIAL_COMMA_ON", "ENGLISH_WORD_REPEAT_BEGINNING_RULE",
          "A_INSTALL", "IT_IS_2"]
LT_KINDS = {"misspelling": "spelling", "grammar": "grammar", "style": "style", "typographical": "punctuation",
            "locale-violation": "British English", "inconsistency": "consistency", "duplication": "repeated word",
            "whitespace": "punctuation", "register": "style", "non-conformance": "style"}
# Inline code and placeholders read as one neutral word; Markdown, tags and emphasis read as nothing.
_MARKUP = re.compile(r"`[^`]*`|&lt;[^&]*&gt;|\]\([^)]*\)|[\[\]]|<br\s*/?>|</?(?:p|li|ul|ol)\b[^>]*>|<[^>]+>|&[a-z]+;"
                     r"|\{[^}]*\}|%[\dsd]|\*\*|(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)")
_NOT_TEXT = re.compile(r"^\s*(SELECT|UPDATE|INSERT|CREATE|DELETE|WITH)\b|:\s*\d+px|^\s*[A-Z_]+=")

# Vale: rules that would flag the suite's plain style itself ("is" on every line, "so", the many short sentences
# the readability scores were not made for) are off; the rest stays.
VALE_OFF = {"write-good.E-Prime", "write-good.So", "Readability.AutomatedReadability", "Readability.ColemanLiau",
            "Readability.GunningFog", "Readability.LIX", "Readability.SMOG", "Readability.Polysyllables",
            "proselint.Typography"}


@dataclass
class Problem:
    path: str
    line: int
    check: str                          # rules, LanguageTool or Vale
    kind: str
    message: str
    text: str
    suggestion: str = ""


# The text.

def wanted(path: str) -> bool:
    parts = Path(path).parts
    if parts[-1] in SKIP_NAMES or SKIP_PARTS.intersection(parts) or parts[0] in (".github", ".claude"):
        return False
    if path == "portal/apps.toml" or path.endswith((".md", ".desktop")):
        return True
    if parts[0] == "tools":
        return False
    return path.endswith((".py", ".sh")) or (parts[0] == "apps" and path.endswith("-run"))


def tracked(targets: list[str], root: Path = ROOT) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "--", *targets], cwd=root,
                         capture_output=True, text=True, check=True).stdout
    return sorted(p for p in out.splitlines() if wanted(p) and (root / p).is_file())


def markdown_passages(text: str):
    """(line, passage) for each paragraph, list item and table cell of a Markdown file."""
    passage: list[str] = []
    start = 0
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line) or not line.strip() or (not fenced and _SKIP_LINE.match(line)):
            if passage:
                yield start, " ".join(passage)
                passage.clear()
            if _FENCE.match(line):
                fenced = not fenced
            continue
        if fenced:
            continue
        if line.lstrip().startswith("|"):                       # a table row: every cell by itself
            if passage:
                yield start, " ".join(passage)
                passage.clear()
            for cell in line.strip().strip("|").split("|"):
                yield number, cell
            continue
        bullet = _BULLET.match(line)
        if bullet:
            if passage:
                yield start, " ".join(passage)
                passage.clear()
            line = line[bullet.end():]
        if not passage:
            start = number
        passage.append(line.strip())
    if passage:
        yield start, " ".join(passage)


def _string(node: ast.AST) -> str | None:
    """A literal string, or an f-string with each value as "thing"."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else "thing"
                       for v in node.values)
    return None


def python_passages(text: str):
    """(line, passage) for the text a program shows: its strings of four words or more that start with a capital
    (not docstrings), and every string a window shows as a label, title or hint (UI_CALLS)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(id(first.value))
    seen: set[tuple[int, str]] = set()
    found: list[tuple[int, str]] = []

    def add(line: int, value: str) -> None:
        for passage in re.split(r"\n\s*\n|<br><br>", value):
            passage = passage.replace("<br>", " ").strip()
            if passage and (line, passage) not in seen:
                seen.add((line, passage))
                found.append((line, passage))

    inside = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            inside.update(id(v) for v in node.values)
    for node in ast.walk(tree):
        if id(node) in docstrings or id(node) in inside:
            continue
        value = _string(node)
        if value and len(value.split()) >= STRING_WORDS and value[:1].isupper() and "\n    " not in value:
            add(node.lineno, value)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        if name not in UI_CALLS:
            continue
        for arg in node.args:
            for item in (arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else [arg]):
                value = _string(item)
                if value and not _IDENTIFIER.match(value.strip()):
                    add(item.lineno, value)
    yield from sorted(found)


def toml_passages(text: str):
    """(line, passage) for the portal's texts in apps.toml: each app's and quickfix's name, summary and board_change."""
    data = tomllib.loads(text)
    lines = text.splitlines()

    def line_of(value: str) -> int:
        first = value.strip().splitlines()[0][:40]
        return next((n for n, line in enumerate(lines, 1) if first and first in line), 0)

    for app in data.get("apps", {}).values():
        for entry in [app, *app.get("quickfixes", [])]:
            for key in ("name", "summary", "board_change"):
                value = entry.get(key)
                if isinstance(value, str) and value.strip():
                    yield line_of(value), " ".join(value.split())


_SHELL_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"|\'([^\']*)\'')
_SHELL_VALUE = re.compile(r"\$\{[^}]*\}|\$\([^)]*\)|\$\w+")


def shell_passages(text: str):
    """(line, passage) for the messages a script prints: its quoted strings of four words or more, on lines that
    are not comments, each $VALUE read as "thing"."""
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for match in _SHELL_STRING.finditer(line):
            value = _SHELL_VALUE.sub("thing", match.group(1) if match.group(1) is not None else match.group(2))
            words = value.split()
            if len(words) >= STRING_WORDS and sum(w.strip(".,:;()").isalpha() for w in words) >= len(words) / 2:
                yield number, value.replace("\\n", " ").replace('\\"', '"')


def desktop_passages(text: str):
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith(("Name=", "Comment=", "GenericName=")):
            yield number, line.split("=", 1)[1]


def passages(path: str, text: str) -> list[tuple[int, str]]:
    if path.endswith(".py"):
        found = python_passages(text)
    elif path.endswith((".sh", "-run")):
        found = shell_passages(text)
    elif path.endswith(".desktop"):
        found = desktop_passages(text)
    elif path.endswith(".toml"):
        found = toml_passages(text)
    else:
        found = markdown_passages(text)
    return [(line, p) for line, p in found if p.strip() and not _NOT_TEXT.search(p)]


def plain(text: str) -> str:
    text = re.sub(r"`[^`]*`", "code", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\{[^}]*\}", "", text)


# The rules of .claude/writing.md.

def check_rules(path: str, line: int, passage: str) -> list[Problem]:
    found = []
    passage = _LEAD.sub("", plain(passage).strip())
    for sentence in _SENTENCE_END.split(passage):
        short = sentence if len(sentence) <= 160 else sentence[:157] + "..."
        count = len(sentence.split())
        if count > LONG_WORDS:
            found.append(Problem(path, line, "rules", "long sentence", f"{count} words. Split it.", short))
        for _ in range(sentence.count(";")):
            found.append(Problem(path, line, "rules", "semicolon", "A semicolon chains two facts. Make two "
                                 "sentences.", short))
        bare = sentence.replace("**", "")
        for match in _MID_COLON.finditer(bare):
            after = bare[match.end():].split(None, 1)[0].strip(".,")
            if len(bare[:match.start()].split()) >= LEAD_WORDS and after not in ("code", "thing"):
                found.append(Problem(path, line, "rules", "colon", "The sentence goes on after a colon. Make two "
                                     "sentences, or a list.", short))
        for inside in _PAREN.findall(sentence):
            if len(inside.split()) > ASIDE_WORDS:
                found.append(Problem(path, line, "rules", "parenthesis", "More than four words in parentheses. "
                                     "Make it a sentence.", f"({inside})"))
        for match in _WORD.finditer(sentence):
            word = match.group(1).lower()
            if not (word == "manual" and _MANUAL_BY_HAND.search(sentence)):
                found.append(Problem(path, line, "rules", "word", f"Write {WORDS[word]}.", short,
                                     WORDS[word].split()[0]))
    return found


# LanguageTool, in podman.

def podman(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["podman", *args], text=True, check=False, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_image() -> None:
    if podman("image", "exists", IMAGE).returncode == 0:
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    zip_path = CACHE / f"LanguageTool-{LT_VERSION}.zip"
    if not zip_path.is_file() or sha256(zip_path) != LT_SHA256:
        print(f"Downloading LanguageTool {LT_VERSION} (about 250 MB, once)...", flush=True)
        tmp = zip_path.with_suffix(".part")
        request = urllib.request.Request(LT_URL, headers={"User-Agent": "text-check"})   # the default is refused
        with urllib.request.urlopen(request, timeout=600) as answer, tmp.open("wb") as out:
            shutil.copyfileobj(answer, out)
        if sha256(tmp) != LT_SHA256:
            tmp.unlink()
            raise SystemExit(f"The download of {LT_URL} is not the file this tool pins. Its SHA-256 differs.")
        tmp.replace(zip_path)
    with tempfile.TemporaryDirectory() as context:
        shutil.copy(HERE / "Containerfile", Path(context) / "Containerfile")
        shutil.copy(zip_path, Path(context) / zip_path.name)
        print("Building LanguageTool's image (once)...", flush=True)
        built = podman("build", "-q", "--build-arg", f"LT_VERSION={LT_VERSION}", "-t", IMAGE, context,
                       capture_output=True)
        if built.returncode:
            raise SystemExit(f"Building LanguageTool's image failed.\n{built.stderr[-2000:]}")
    zip_path.unlink()                   # the image holds it now


def shared_server() -> str | None:
    """The address of the shared server, when --server start left it running."""
    out = podman("port", SERVER, "8081", capture_output=True)
    return f"http://{out.stdout.split()[0]}" if out.returncode == 0 and out.stdout.strip() else None


def start_server(name: str | None = None) -> tuple[str, str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    out = podman("run", "-d", "--rm", *(["--name", name] if name else []), "-p", f"127.0.0.1:{port}:8081", IMAGE,
                 capture_output=True)
    if out.returncode:
        raise SystemExit(f"LanguageTool's container did not start. {out.stderr.strip()}")
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            urllib.request.urlopen(f"{url}/v2/languages", timeout=2).close()
            return out.stdout.strip(), url
        except OSError:
            time.sleep(1)
    podman("stop", out.stdout.strip(), capture_output=True)
    raise SystemExit("LanguageTool did not answer within two minutes.")


def known_words(root: Path = ROOT) -> set[str]:
    path = root / "tools" / "text_check" / "words.txt"
    words = set()
    if path.is_file():
        words = {w.strip().lower() for w in path.read_text().splitlines() if w.strip() and not w.startswith("#")}
    for folder in ("apps", "dev"):                      # the apps' keys are names too
        if (root / folder).is_dir():
            words.update(p.name.lower() for p in (root / folder).iterdir() if p.is_dir())
    return words


def _interpret(token: str) -> str:
    if token.startswith(("`", "{", "%", "&lt;")):
        return "thing"
    if token.startswith("&"):
        return html.unescape(token)
    return " " if re.match(r"<br|</?(p|li|ul|ol)\b", token) else ""


def annotate(found: list[tuple[int, str]]) -> tuple[list[dict], list[tuple[int, int]]]:
    """LanguageTool's annotated text: each passage a paragraph, its markup marked; and where each passage starts."""
    parts: list[dict] = []
    starts: list[tuple[int, int]] = []
    at = 0
    for line, passage in found:
        if parts:
            parts.append({"markup": "\n\n", "interpretAs": "\n\n"})
            at += 2
        starts.append((at, line))
        pos = 0
        for match in _MARKUP.finditer(passage):
            if match.start() > pos:
                parts.append({"text": passage[pos:match.start()]})
            parts.append({"markup": match.group(0), "interpretAs": _interpret(match.group(0))})
            pos = match.end()
        if pos < len(passage):
            parts.append({"text": passage[pos:]})
        at += len(passage)
    return parts, starts


def _line_at(starts: list[tuple[int, int]], offset: int) -> int:
    line = starts[0][1] if starts else 0
    for start, number in starts:
        if start > offset:
            break
        line = number
    return line


def _lt_wanted(match: dict, known: set[str]) -> bool:
    rule = match["rule"]
    if rule["id"] in LT_OFF or rule["id"].startswith("EN_REPEATEDWORDS"):
        return False                                    # the server keeps some on at the level picky
    context = match["context"]
    word = context["text"][context["offset"]:context["offset"] + context["length"]]
    if "thing" in word and word != "thing" or (rule["id"] == "ENGLISH_WORD_REPEAT_RULE" and word.startswith("thing")):
        return False                                    # an f-string's values
    if not (rule["id"].startswith("MORFOLOGIK_RULE_EN") or rule.get("issueType") == "misspelling"):
        return True
    if len(word) < 2 or word.lower() in known or word.lower().rstrip("s") in known:
        return False
    return not re.search(r"\d|_|/|\.\w|[a-z][A-Z]|^[A-Z]{2,}|^-|-$", word)


def check_languagetool(url: str, path: str, found: list[tuple[int, str]], known: set[str]) -> list[Problem]:
    parts, starts = annotate(found)
    body = urllib.parse.urlencode({"data": json.dumps({"annotation": parts}), "language": "en-US",
                                   "level": "picky", "disabledRules": ",".join(LT_OFF)}).encode()
    with urllib.request.urlopen(urllib.request.Request(f"{url}/v2/check", data=body), timeout=600) as answer:
        result = json.load(answer)
    problems = []
    for match in result.get("matches", []):
        if not _lt_wanted(match, known):
            continue
        context = match["context"]
        start, end = context["offset"], context["offset"] + context["length"]
        text = context["text"][:start] + "[" + context["text"][start:end] + "]" + context["text"][end:]
        fixes = [r["value"] for r in match.get("replacements", [])[:3]]
        problems.append(Problem(path, _line_at(starts, match["offset"]), "LanguageTool",
                                LT_KINDS.get(match["rule"].get("issueType", ""), "other"), match["message"],
                                " ".join(text.split()), " / ".join(fixes)))
    return problems


# Vale.

def check_vale(texts: dict[str, list[tuple[int, str]]]) -> list[Problem]:
    """Vale reads each file's passages, one paragraph each, from a copy in Markdown; its lines map back."""
    if shutil.which("vale") is None:
        raise SystemExit("This tool needs Vale: brew install vale")
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        maps: dict[str, tuple[str, list[int]]] = {}
        for n, (path, found) in enumerate(texts.items()):
            copy = Path(tmp) / f"{n}.md"
            lines: list[int] = []
            out = []
            for line, passage in found:
                for part in passage.splitlines() or [""]:
                    out.append(part)
                    lines.append(line)
                out.append("")
                lines.append(line)
            copy.write_text("\n".join(out) + "\n", encoding="utf-8")
            maps[str(copy)] = (path, lines)
        result = subprocess.run(["vale", "--config", str(HERE / "vale.ini"), "--output", "JSON", "--no-exit",
                                 *maps], capture_output=True, text=True, check=False)
        try:
            alerts = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            raise SystemExit(f"Vale did not run. {result.stderr.strip()}")
        for copy, items in alerts.items():
            path, lines = maps[copy]
            for alert in items:
                if alert["Check"] in VALE_OFF or "thing" in alert.get("Match", ""):
                    continue                    # "thing" stands for an f-string's value
                number = lines[alert["Line"] - 1] if 0 < alert["Line"] <= len(lines) else 0
                # Readability is a must; the style rules (passive voice, wordy phrases) are advice: fix them where
                # the sentence reads better for it.
                kind = "readability" if alert["Check"].startswith("Readability") else "advice"
                problems.append(Problem(path, number, "Vale", kind, f"{alert['Message']} ({alert['Check']})",
                                        alert.get("Match", ""),
                                        ", ".join(alert.get("Action", {}).get("Params") or [])))
    return problems


# What a rewrite must keep.

def _facts(text: str) -> dict[str, dict[str, int]]:
    fences = re.findall(r"^\s*```.*?^\s*```", text, re.MULTILINE | re.DOTALL)
    body = re.sub(r"^\s*```.*?^\s*```", "", text, flags=re.MULTILINE | re.DOTALL)
    found = {"code block": fences, "code": re.findall(r"`([^`]+)`", body),
             "link": re.findall(r"\]\(([^)\s]+)\)", body) + re.findall(r"href='([^']+)'", body),
             "heading": re.findall(r"^#{1,6} .*$", body, re.MULTILINE),
             "number": re.findall(r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s?(?:°C|%|s|MB|GB|MiB|GiB|MHz|W|V))?(?![\w])", body),
             "path": re.findall(r"(?:~|/)[\w.\-/]+\w", body)}
    counted: dict[str, dict[str, int]] = {}
    for kind, items in found.items():
        for item in items:
            counted.setdefault(kind, {})[item.strip()] = counted.get(kind, {}).get(item.strip(), 0) + 1
    return counted


def gone(paths: list[str], root: Path = ROOT) -> list[str]:
    """What the files had at HEAD and lack now: a code block, code, a link, a heading, a number or a path. Each one
    is either put back or is a rewording that keeps the fact (10 s written as 10 seconds)."""
    lost = []
    for path in paths:
        old = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=root, capture_output=True, text=True,
                             check=False).stdout
        new = (root / path).read_text(encoding="utf-8", errors="replace") if (root / path).is_file() else ""
        before, after = _facts(old), _facts(new)
        for kind, items in before.items():
            for item in items:
                if item not in after.get(kind, {}) and not (kind == "heading" and path.endswith(".py")):
                    lost.append(f"{path}: {kind} gone: {item}")
    return lost


# The run.

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lists what is wrong with the suite's text.")
    parser.add_argument("paths", nargs="*", help="files or folders, from the repository root (default: all)")
    parser.add_argument("--details", action="store_true", help="every problem, with its line")
    parser.add_argument("--json", type=Path, help="write every problem as JSON to this file")
    parser.add_argument("--gone", action="store_true", help="what the files lost since HEAD, instead of the checks")
    parser.add_argument("--server", choices=("start", "stop"),
                        help="keep one LanguageTool running for many runs (start), or end it (stop)")
    args = parser.parse_args(argv)
    if args.server == "stop":
        podman("stop", "-t", "2", SERVER, capture_output=True)
        print("LanguageTool stopped.")
        return 0
    if args.server == "start":
        if shared_server() is None:
            ensure_image()
            start_server(SERVER)
        print(f"LanguageTool runs at {shared_server()}. Stop it with: python3 tools/text_check.py --server stop")
        return 0
    if args.gone:
        lost = gone([p for p in args.paths if (ROOT / p).is_file()] or tracked(args.paths))
        print("\n".join(lost) or "Nothing is gone.")
        return 1 if lost else 0
    if shutil.which("podman") is None:
        raise SystemExit("This tool needs podman.")

    texts = {}
    words = {}
    for path in tracked(args.paths):
        found = passages(path, (ROOT / path).read_text(encoding="utf-8", errors="replace"))
        if found:
            texts[path] = found
            words[path] = sum(len(plain(p).split()) for _, p in found)
    print(f"Checking {len(texts)} files, {sum(words.values())} words...", flush=True)
    problems = [p for path, found in texts.items() for line, passage in found for p in check_rules(path, line, passage)]
    problems += check_vale(texts)
    url = shared_server()
    container = None
    if url is None:
        ensure_image()
        container, url = start_server()
    known = known_words()
    try:
        with ThreadPoolExecutor(WORKERS) as pool:
            for found in pool.map(lambda item: check_languagetool(url, item[0], item[1], known), texts.items()):
                problems += found
    finally:
        if container:
            podman("stop", "-t", "2", container, capture_output=True)

    by_file: dict[str, list[Problem]] = {}
    for p in problems:
        by_file.setdefault(p.path, []).append(p)
    if args.json:
        args.json.write_text(json.dumps([asdict(p) for p in sorted(problems, key=lambda p: (p.path, p.line))],
                                        indent=1), encoding="utf-8")
    must = {f: [p for p in found if p.kind != "advice"] for f, found in by_file.items()}
    order = sorted(by_file, key=lambda f: (-1000 * len(must[f]) / max(words.get(f, 1), 100), f))
    print(f"{'to fix':>8} {'per 1000':>8} {'advice':>7} {'words':>7}  file")
    for path in order:
        found = by_file[path]
        print(f"{len(must[path]):8d} {1000 * len(must[path]) / max(words[path], 1):8.1f} "
              f"{len(found) - len(must[path]):7d} {words[path]:7d}  {path}")
        if args.details:
            for p in sorted(found, key=lambda p: (p.line, p.check)):
                fix = f"  ->  {p.suggestion}" if p.suggestion else ""
                print(f"{'':10}{p.line}: {p.check}, {p.kind}: {p.message}{fix}\n{'':14}{p.text}")
    advice = sum(p.kind == "advice" for p in problems)
    print(f"\n{len(problems) - advice} to fix and {advice} pieces of advice (Vale's style hints).", end="")
    kinds: dict[str, int] = {}
    for p in problems:
        kinds[f"{p.check} {p.kind}"] = kinds.get(f"{p.check} {p.kind}", 0) + 1
    total = sum(words.values())
    print(f"\n{len(problems)} problems in {len(by_file)} of {len(texts)} files, {total} words"
          + (f" ({1000 * len(problems) / total:.1f} per 1000 words)" if total else "") + ".")
    print(", ".join(f"{k} {n}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
