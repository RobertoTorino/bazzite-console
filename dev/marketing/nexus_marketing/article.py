# SPDX-License-Identifier: GPL-3.0-or-later
"""The article: one HTML page that presents the portal and every app in it, written from the checkout as it is now.

What it is made of, so it keeps up with the suite:
  * portal/apps.toml: the apps, in the portal's order and categories, with their names, the quickfixes and the
    "changes the board" mark; the category names come from the portal's manifest.py
  * copy.md beside this file: the words, a line for each category and each app (missing() lists what lacks one),
    and the board's numbers with their notes, when it has a "Specs" part
  * the README's License section's first paragraph (the licenses: the paragraphs after it name development
    apps) and its Disclaimer, word for word
  * the portal's pictures: the suite's icon and the apps' tile icons
  * the stills of the portal (tools/portal_shots.py) in images/shots/ of the app folder
  * images/hero.webp in the app folder as the hero's background, when there is one; else a drawn placeholder

The links go to the latest release (the newest portal), the wiki with a chapter per app, the Portal Tour video
itself (owner, 26-11-2026: no detour through the wiki), the wiki's Portal Tour page and the repository on GitHub. Only the portal and its apps are in it: the development apps in dev/ never
are (owner, 25-11-2026)."""

from __future__ import annotations

import importlib.util
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from bazzite_console_core import SUITE_MANUAL_URL, SUITE_REPO_URL

from . import CHECKOUT, ROOT

HERE = Path(__file__).resolve().parent
COPY = HERE / "copy.md"
STYLE = HERE / "article.css"
SHOTS = ROOT / "images" / "shots"                   # the stills of the portal, from tools/portal_shots.py
HERO = ROOT / "images" / "hero.webp"                # the hero's background; a drawn placeholder without it
RELEASE_URL = f"{SUITE_REPO_URL}/releases/latest"   # GitHub's Latest release is the newest portal
TOUR_URL = f"{SUITE_MANUAL_URL}portal-tour/"
VIDEO_URL = f"{SUITE_MANUAL_URL}videos/portal-tour.mp4"   # the video itself, as the Portal Tour page plays it
FONTS = ("Inter-SemiBold.ttf", "Inter-Bold.ttf", "Inter-ExtraBold.ttf", "Inter-LICENSE.txt")
SECTIONS = ("Headline", "Claim", "Portal", "And more", "Safety", "Categories", "Apps", "Video", "Get it", "Closing")
NOTE_MARK = re.compile(r"\s*(\*+)$")              # a spec's note: one asterisk or more at the end of its label


@dataclass
class App:
    key: str
    name: str
    category: str
    changes_board: bool
    quickfixes: list[str] = field(default_factory=list)
    tile: str = ""                                  # apps.toml's short: the name on its tile

    @property
    def short(self) -> str:
        """The name as the portal's tile shows it: apps.toml's short, else the name without the suite's prefix."""
        return self.tile or re.sub(r"^(BC-250|BC250|PS5) ", "", self.name)


@dataclass
class Article:
    html: str
    files: dict[str, Path]          # the path in the exported folder: the file it is copied from


def suite_name(root: Path = CHECKOUT) -> str:
    """The suite's name as its portal calls itself (APP_NAME in portal/<package>/__init__.py)."""
    for init in sorted((root / "portal").glob("*/__init__.py")):
        found = re.search(r'^APP_NAME = "([^"]+)"', init.read_text(encoding="utf-8"), re.M)
        if found:
            return found.group(1)
    return root.name


def categories(root: Path = CHECKOUT) -> dict[str, str]:
    """The portal's categories (key: name) in their order, from the portal package's manifest.py. Loaded as a file,
    so the portal's package (and its Qt) is not imported."""
    manifest = next((root / "portal").glob("*/manifest.py"))
    spec = importlib.util.spec_from_file_location("portal_manifest", manifest)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module             # dataclasses look their module up while the class is built
    spec.loader.exec_module(module)
    return dict(module.CATEGORIES)


def apps(root: Path = CHECKOUT) -> list[App]:
    """The portal's apps from portal/apps.toml, in its order. A withdrawn app is left out: the portal removes it."""
    data = tomllib.loads((root / "portal" / "apps.toml").read_text(encoding="utf-8")).get("apps", {})
    return [App(key, entry["name"], entry["category"], bool(entry.get("changes_board")),
                [fix["name"] for fix in entry.get("quickfixes", [])], entry.get("short", ""))
            for key, entry in data.items() if isinstance(entry, dict) and not entry.get("withdrawn")]


# --- the words -----------------------------------------------------------------------------------------------------

def read_copy(path: Path = COPY) -> dict[str, list[str]]:
    """copy.md by its "##" parts: each part's lines, without the comments and the blank lines."""
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    parts: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = parts.setdefault(line[3:].strip(), [])
        elif current is not None and line.strip():
            current.append(line.rstrip())
    return parts


def paragraphs(lines: list[str]) -> list[str]:
    """The prose of a part, its lines that are no list item, as one paragraph (copy.md gives each part one)."""
    prose = [line.strip() for line in lines if not re.match(r"^\s*(-|\d+\.) ", line)]
    return [" ".join(prose)] if prose else []


def items(lines: list[str]) -> list[str]:
    """The list items of a part, bullets or numbers."""
    return [re.sub(r"^\s*(-|\d+\.) ", "", line) for line in lines if re.match(r"^\s*(-|\d+\.) ", line)]


def table(lines: list[str]) -> dict[str, str]:
    """A part's table as key: line, without its heading and its rule."""
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines if line.startswith("|")]
    return {row[0]: row[1] for row in rows[2:] if len(row) >= 2}


def missing(root: Path = CHECKOUT, path: Path = COPY) -> list[str]:
    """What copy.md lacks for the portal as it is, and what it holds that the portal does not have: a sentence each.
    Empty when the article covers every category and app."""
    words = read_copy(path)
    problems = [f'copy.md has no "{name}" part.' for name in SECTIONS if not words.get(name)]
    lines = table(words.get("Apps", []))
    keys = [app.key for app in apps(root)]
    problems += [f"No line for the app {key}." for key in keys if key not in lines]
    problems += [f"A line for {key}, which the portal does not have." for key in lines if key not in keys]
    lines = table(words.get("Categories", []))
    names = categories(root)
    problems += [f"No line for the category {key}." for key in names if key not in lines]
    problems += [f"A line for the category {key}, which the portal does not have." for key in lines
                 if key not in names]
    return problems


def specs(lines: list[str]) -> list[tuple[str, str, str]]:
    """The board's numbers under the hero, from copy.md's "Specs" items: (number, label, note mark). An item is the
    number, a space and its label, written as the page shows it. A label that ends in asterisks has the note in
    "Spec notes" that starts with the same asterisks."""
    found = []
    for item in items(lines):
        number, _, label = item.partition(" ")
        mark = NOTE_MARK.search(label)
        found.append((number, NOTE_MARK.sub("", label), mark.group(1) if mark else ""))
    return found


def spec_notes(lines: list[str]) -> list[tuple[str, str]]:
    """The notes of the specs, from copy.md's "Spec notes" items: (mark, text). Each item starts with its asterisks."""
    return [(found.group(1), found.group(2)) for found in (re.match(r"^(\*+)\s+(.*)$", item) for item in items(lines))
            if found]


# --- the license and the disclaimer, from the README ---------------------------------------------------------------

def readme_section(heading: str, root: Path = CHECKOUT) -> list[str]:
    """The paragraphs of a "##" section of the suite's README, each on one line."""
    text = (root / "README.md").read_text(encoding="utf-8")
    found = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, flags=re.S | re.M)
    if not found:
        return []
    return [" ".join(block.split()) for block in re.split(r"\n\s*\n", found.group(1)) if block.strip()]


def inline(text: str) -> str:
    """A line of Markdown as HTML: links (the README's own links to the repository), bold and code."""
    out = escape(text, quote=False)

    def link(match: re.Match) -> str:
        target = match.group(2)
        if not re.match(r"^[a-z]+://", target):
            target = f"{SUITE_REPO_URL}/blob/main/{target}"
        return f'<a href="{escape(target)}">{match.group(1)}</a>'

    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    # names that never break in two: a hyphen and a space that hold
    return out.replace("BC-250", "BC&#8209;250").replace("PlayStation 5", "PlayStation&nbsp;5")


# --- the page ------------------------------------------------------------------------------------------------------

def shots(folder: Path = SHOTS) -> dict[str, Path]:
    """The stills there are: name (a category or settings): file."""
    return {path.stem: path for path in sorted(folder.glob("*.webp"))}


def build(root: Path = CHECKOUT, shot_folder: Path = SHOTS, hero: Path = HERO) -> Article:
    words = read_copy(COPY)
    entries = apps(root)
    names = categories(root)
    app_lines = table(words.get("Apps", []))
    category_lines = table(words.get("Categories", []))
    stills = shots(shot_folder)
    count = len(entries)
    quickfixes = sum(len(app.quickfixes) for app in entries)
    suite = suite_name(root)
    icon = next(path for path in sorted((root / "portal" / "images").glob("*-suite.webp")))   # the portal's icon
    fonts = next((root / "core").glob("*/fonts"))                                            # core's Inter
    files: dict[str, Path] = {"article.css": STYLE, "images/suite.webp": icon}
    for name in FONTS:
        files[f"fonts/{name}"] = fonts / name

    def text(part: str) -> str:
        return " ".join(paragraphs(words.get(part, []))).replace("{apps}", str(count))

    def still(name: str, alt: str) -> str:
        if name not in stills:
            return ""
        files[f"images/portal-{name}.webp"] = stills[name]
        return f'<img class="shot" src="images/portal-{name}.webp" alt="{escape(alt)}" loading="lazy">'

    hero_class, hero_style = "hero hero--placeholder", ""
    if hero.is_file():
        files["images/hero.webp"] = hero
        hero_class, hero_style = "hero", ' style="background-image:url(images/hero.webp)"'

    buttons = (f'<a class="button button--primary" href="{RELEASE_URL}">Download the latest release</a>'
               f'<a class="button" href="{VIDEO_URL}">Watch the tour</a>'
               f'<a class="button" href="{SUITE_MANUAL_URL}">Read the wiki</a>'
               f'<a class="button" href="{SUITE_REPO_URL}">View on GitHub</a>')

    def sup(mark: str) -> str:
        return f'<sup><a href="#spec-notes">{escape(mark)}</a></sup>' if mark else ""

    # the board's numbers and their notes: only when copy.md has them
    numbers = specs(words.get("Specs", []))
    spec_band = ('<div class="band band--specs"><div class="inner numbers specs">'
                 + "".join(f"<div><strong>{escape(number)}</strong><span>{inline(label)}{sup(mark)}</span></div>"
                           for number, label, mark in numbers) + "</div></div>\n") if numbers else ""
    notes = spec_notes(words.get("Spec notes", []))
    notes_html = ('<div id="spec-notes">' + "".join(f'<p><span class="mark">{escape(mark)}</span> {inline(note)}</p>'
                                                    for mark, note in notes) + "</div>") if notes else ""
    page = [f"""<header class="{hero_class}"{hero_style}>
<div class="inner">
<img class="hero__logo" src="images/suite.webp" alt="">
<span class="hero__stage">{escape(suite)}</span>
<h1>{"<br>".join(inline(line.strip()) for line in words.get("Headline", []))}</h1>
<p class="hero__claim">{inline(text("Claim"))}</p>
<div class="buttons">{buttons}</div>
</div>
</header>
{spec_band}<div class="band"><div class="inner numbers">
<div><strong>{count}</strong><span>Apps</span></div>
<div><strong>{len(names)}</strong><span>Categories</span></div>
<div><strong>{quickfixes}</strong><span>Quickfixes</span></div>
<div><strong>1</strong><span>Portal</span></div>
</div></div>
<section class="glow"><div class="inner split">
<div>
<p class="kicker">The portal</p>
<h2>Your launch pad</h2>
<p class="lead">{inline(text("Portal"))}</p>
<ul class="features">{"".join(f"<li>{inline(item)}</li>" for item in items(words.get("Portal", [])))}</ul>
</div>
<div>{still("settings", "The portal's Settings page")}</div>
</div></section>"""]

    for index, (key, name) in enumerate(names.items()):
        cards = []
        for app in (app for app in entries if app.category == key):
            mark = '<span class="tag">Changes the board</span>' if app.changes_board else ""
            files[f"images/apps/{app.key}.webp"] = root / "portal" / "images" / "apps" / f"{app.key}.webp"
            cards.append(f"""<a class="card" href="{SUITE_MANUAL_URL}apps/{app.key}/">
<header><img src="images/apps/{app.key}.webp" alt=""><h3>{escape(app.short)}</h3></header>
<p>{inline(app_lines.get(app.key, ""))}</p>{mark}
</a>""")
        page.append(f"""<section class="category {"dark" if index % 2 == 0 else "glow"}" id="{key}"><div class="inner">
<p class="kicker">{escape(name)}</p>
<h2>{inline(category_lines.get(key, ""))}</h2>
{still(key, f"The portal's {name} tab")}
<div class="cards">{"".join(cards)}</div>
</div></section>""")

    poster = root / "docs" / "images" / "portal" / "portal-tour-poster.webp"
    video = ""
    if poster.is_file():
        files["images/tour.webp"] = poster
        video = (f'<a class="video" href="{VIDEO_URL}">'
                 '<img class="shot" src="images/tour.webp" alt="The Portal Tour"></a>')
    page.append(f"""<section class="more"><div class="inner">
<p class="kicker">And more...</p>
<h2>{inline(text("And more"))}</h2>
<ul class="chips">{"".join(f"<li>{inline(item)}</li>" for item in items(words.get("And more", [])))}</ul>
</div></section>""")
    page.append(f"""<section class="safety"><div class="inner">
<p class="kicker kicker--warn">Changes the board</p>
<p class="lead">{inline(text("Safety"))}</p>
</div></section>
<section class="dark"><div class="inner split">
<div>
<p class="kicker">The Portal Tour</p>
<h2>See it in action</h2>
<p class="lead">{inline(text("Video"))}</p>
<a class="button button--primary" href="{VIDEO_URL}">Watch the tour</a>
</div>
<div>{video}</div>
</div></section>
<section class="glow" id="get-it"><div class="inner">
<p class="kicker">Get it</p>
<h2>{inline(text("Get it"))}</h2>
<ol class="steps">{"".join(f"<li>{inline(item)}</li>" for item in items(words.get("Get it", [])))}</ol>
<div class="buttons">{buttons}</div>
</div></section>
<footer><div class="inner">
<p class="lead" style="color:#fff">{inline(text("Closing"))}</p>
<div class="links"><a href="{RELEASE_URL}">Latest release</a><a href="{SUITE_MANUAL_URL}">Wiki</a>
<a href="{TOUR_URL}">Portal Tour</a><a href="{SUITE_REPO_URL}">GitHub</a></div>
<h4>License</h4>
{"".join(f"<p>{inline(p)}</p>" for p in readme_section("License", root)[:1])}
<h4>Disclaimer</h4>
{"".join(f"<p>{inline(p)}</p>" for p in readme_section("Disclaimer", root))}
{notes_html}
</div></footer>""")

    html = f"""<!DOCTYPE html>
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(suite)}</title>
<meta name="description" content="{escape(text("Claim"))}">
<link rel="icon" href="images/suite.webp">
<link rel="stylesheet" href="article.css">
</head>
<body>
{chr(10).join(page)}
</body>
</html>
"""
    return Article(html, files)


MIME = {".css": "text/css", ".webp": "image/webp", ".png": "image/png", ".ttf": "font/ttf"}


def single(article: Article) -> str:
    """The article as one HTML file: the style sheet, the fonts and the pictures inside it as data. A browser in a
    sandbox (a Flatpak) is given only the file it opens, not the files beside it, so the preview is this one file."""
    import base64

    def data(name: str) -> str:
        source = article.files[name]
        return f"data:{MIME[source.suffix]};base64,{base64.b64encode(source.read_bytes()).decode('ascii')}"

    style = STYLE.read_text(encoding="utf-8")
    style = re.sub(r'url\("(fonts/[^"]+)"\)', lambda m: f'url("{data(m.group(1))}")', style)
    html = article.html.replace('<link rel="stylesheet" href="article.css">', f"<style>\n{style}</style>")
    html = re.sub(r'(src|href)="((?:images)/[^"]+)"', lambda m: f'{m.group(1)}="{data(m.group(2))}"', html)
    return re.sub(r"url\((images/[^)]+)\)", lambda m: f"url({data(m.group(1))})", html)


def write(article: Article, folder: Path) -> Path:
    """The article in *folder*: index.html and its files beside it. Returns the page."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, source in article.files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    page = folder / "index.html"
    page.write_text(article.html, encoding="utf-8", newline="\n")
    return page


# --- the website: a checkout of the repository GitHub Pages serves ------------------------------------------------

MANAGED = ("index.html", "article.css", "images", "fonts")     # what the article owns in the website's folder
COMMIT_MESSAGE = "see the changelog"                            # every publish (owner, 25-11-2026)


def _wanted(article: Article) -> dict[str, bytes]:
    files = {name: source.read_bytes() for name, source in article.files.items()}
    files["index.html"] = article.html.encode("utf-8")
    return files


def _present(folder: Path) -> set[str]:
    """The files the article owns in *folder* now: index.html, article.css and everything under images/ and fonts/."""
    found = {name for name in MANAGED[:2] if (folder / name).is_file()}
    for sub in MANAGED[2:]:
        found |= {path.relative_to(folder).as_posix() for path in (folder / sub).rglob("*") if path.is_file()}
    return found


def changes(article: Article, folder: Path) -> list[str]:
    """The files that differ between the article as built now and *folder*: new, changed and gone ones. Empty when
    the folder has the article as it is. Other files there (.nojekyll, a README, .git) are not the article's."""
    wanted = _wanted(article)
    changed = [name for name, data in wanted.items()
               if not (folder / name).is_file() or (folder / name).read_bytes() != data]
    return sorted(changed + [name for name in _present(folder) if name not in wanted])


def publish(article: Article, folder: Path) -> list[str]:
    """Writes the article into *folder* and removes the pictures and fonts it no longer has. Only the article's own
    files are touched. Returns what changed (changes())."""
    changed = changes(article, folder)
    wanted = _wanted(article)
    for name in changed:
        target = folder / name
        if name in wanted:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(wanted[name])
        else:
            target.unlink()
    return changed


def publish_commands(folder: Path) -> list[list[str]]:
    """The git commands that send the written files to GitHub: stage the article's files (gone ones too), commit
    only those with COMMIT_MESSAGE, and push."""
    git = ["git", "-C", str(folder)]
    return [[*git, "add", "-A", "--", *MANAGED],
            [*git, "commit", "-m", COMMIT_MESSAGE, "--", *MANAGED],
            [*git, "push"]]
