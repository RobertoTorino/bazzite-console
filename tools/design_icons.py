# SPDX-License-Identifier: GPL-3.0-or-later
"""DESIGN.md's Icons: every icon of the suite and where it is used (owner, 22-11-2026: the listing ICONS.md was, kept
in DESIGN.md since the suite left Nexus). tools/make_design.py writes it; most of it is read from the repository, so
it stays current by itself:

- the suite's own icon files (SUITE_ICONS below, the only listing kept by hand; a file it names must be there);
- the category icons and their apps, from icons/categories.toml and portal/apps.toml;
- the portal's symbols, one for each function of the portal's glyphs.py, with its docstring;
- the icons the apps take from the desktop's style, from the code;
- the Material Design icons of the wiki, from its pages;
- the characters the apps use as icons, from the code.

Only the standard library: the portal's symbols and the style's icons are listed by name, without pictures."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

MDI = "https://cdn.jsdelivr.net/npm/@mdi/svg@7.4.47/svg"      # Material Design Icons, as MkDocs Material bundles them
# file (with {suite}, the suite's id in its image names), what it is used for
SUITE_ICONS = [
    ("portal/images/{suite}-suite.webp", "The portal's header (a click opens the wiki), its window icon and its tray "
                                         "icon."),
    ("portal/images/{suite}-suite-1024.webp", "The portal's intro."),
    ("portal/images/{suite}-suite-128.png", "The portal's menu entry and Desktop icon."),
    ("portal/images/apps/portal.webp", "The portal's own tile."),
    ("docs/images/wiki-icon.webp", "The wiki's header logo, its home page's footer and its favicon (with the .png)."),
    ("dev/nrt/images/nexus-release-tool.webp", "Every development app's icon in dev/<name>/images/: the Nexus "
                                               "drawing, as Nexus's apps have it."),
]
SYMBOLS = "✔✓✗✖✕⚠▶■◀●☰↻↓↑←›△○□◇◆★💡🎮"   # characters the apps use as icons (→ and • are text: left out)
STYLE = re.compile(r"QStyle\.StandardPixmap\.(SP_\w+)|QIcon\.fromTheme\(\s*[\"']([\w-]+)[\"']")


def suite_id(root: Path) -> str:
    """The suite's id in its image names: portal/images/<id>-suite.webp."""
    found = sorted(p.name[:-len("-suite.webp")] for p in (root / "portal" / "images").glob("*-suite.webp"))
    return found[0] if found else ""


def package(root: Path, folder: str, suffix: str) -> Path | None:
    found = sorted(p for p in (root / folder).glob(f"*{suffix}") if p.is_dir())
    return found[0] if found else None


def glyphs(root: Path) -> list[tuple[str, str]]:
    """The portal's symbols: each function of glyphs.py that draws one in a color, with its docstring's first line."""
    portal = package(root, "portal", "_portal")
    path = portal / "glyphs.py" if portal else None
    if path is None or not path.is_file():
        return []
    found = []
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_") \
                and [a.arg for a in node.args.args] == ["color"]:
            found.append((node.name, (ast.get_docstring(node) or "").split("\n")[0]))
    return found


def _sources(root: Path) -> dict[str, list[Path]]:
    """Each app's Python files (and the portal's and the development apps'), tests left out."""
    out: dict[str, list[Path]] = {}
    for folder in ("portal", "core", *(f"apps/{p.name}" for p in sorted((root / "apps").iterdir()) if p.is_dir()),
                   *(f"dev/{p.name}" for p in sorted((root / "dev").iterdir()) if p.is_dir())):
        out[folder] = [p for p in sorted((root / folder).rglob("*.py"))
                       if "tests" not in p.parts and ".venv" not in str(p)]
    return out


def names(root: Path) -> dict[str, str]:
    """Each folder's app name: portal/apps.toml's, a development app's APP_NAME, else the folder."""
    apps = tomllib.loads((root / "portal" / "apps.toml").read_text(encoding="utf-8")).get("apps", {})
    out = {f"apps/{key}": entry["name"] for key, entry in apps.items() if "name" in entry}
    out |= {"portal": "Portal", "core": "Every app on core"}
    for init in (root / "dev").glob("*/*/__init__.py"):
        found = re.search(r'^APP_NAME = "([^"]+)"', init.read_text(encoding="utf-8"), re.M)
        if found:
            out[f"dev/{init.parent.parent.name}"] = found.group(1)
    return out


def style_icons(root: Path) -> dict[str, list[str]]:
    """The desktop style's icons the code asks for, and the apps that ask."""
    found: dict[str, list[str]] = {}
    label = names(root)
    for folder, files in _sources(root).items():
        for path in files:
            for pixmap, themed in STYLE.findall(path.read_text(encoding="utf-8", errors="replace")):
                name = pixmap or themed
                app = label.get(folder, folder)
                if app not in found.setdefault(name, []):
                    found[name].append(app)
    return dict(sorted(found.items()))


def symbols(root: Path) -> dict[str, list[str]]:
    """The characters of SYMBOLS each app's code uses."""
    label = names(root)
    out: dict[str, list[str]] = {}
    for folder, files in _sources(root).items():
        text = "".join(path.read_text(encoding="utf-8", errors="replace") for path in files)
        used = "".join(c for c in SYMBOLS if c in text)
        if used:
            out[label.get(folder, folder)] = list(used)
    return dict(sorted(out.items(), key=lambda item: (item[0] != "Portal", item[0])))


def material(root: Path) -> dict[str, list[str]]:
    """The wiki's Material Design icons, and the pages (by their title) that show them."""
    found: dict[str, list[str]] = {}
    for page in sorted((root / "docs").rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", text, re.M)
        name = title.group(1).strip() if title else page.stem
        for icon in dict.fromkeys(re.findall(r":material-([a-z0-9-]+):", text)):
            if name not in found.setdefault(icon, []):
                found[icon].append(name)
    return dict(sorted(found.items()))


def _table(head: str, rows) -> list[str]:
    cols = head.split(",")
    return [f"| {' | '.join(cols)} |", f"| {' | '.join('---' for _ in cols)} |",
            *(f"| {' | '.join(row)} |" for row in rows), ""]


def _img(path: str, width: int = 48) -> str:
    return f'<img src="{path}" width="{width}" alt="">'


def missing(root: Path) -> list[str]:
    """The files the listing names that are not there."""
    suite = suite_id(root)
    return [path.format(suite=suite) for path, _ in SUITE_ICONS if not (root / path.format(suite=suite)).is_file()]


def section(root: Path) -> str:
    """DESIGN.md's Icons, as Markdown."""
    suite = suite_id(root)
    apps = tomllib.loads((root / "portal" / "apps.toml").read_text(encoding="utf-8")).get("apps", {})
    by_category: dict[str, list[str]] = {}
    for key, entry in tomllib.loads((root / "icons" / "categories.toml").read_text(encoding="utf-8")).items():
        if isinstance(entry, dict) and "category" in entry:
            name = apps.get(key, {}).get("name", key)
            by_category.setdefault(entry["category"], []).append(f"{name} (`{key}`)")
    out = ["## Icons", "",
           "Every icon of the suite and where it is used. `tools/design_icons.py` reads most of this from the "
           "repository, so it stays current.", "",
           "### The suite's icon", ""]
    out += _table("Icon,File,Used for", ((_img(path.format(suite=suite)), f"`{path.format(suite=suite)}`", use)
                                         for path, use in SUITE_ICONS))
    out += ["### The category icons", "",
            "Every app has the icon of its category. `icons/categories.toml` assigns them, and `tools/sync_icons.py` "
            "copies each category's icon from `icons/<category>/` to the app's `images/`, the portal's "
            "`images/apps/` and `images/categories/`, and the wiki. The wiki's App categories page shows each app "
            "with its icon.", ""]
    out += _table("Icon,Category,Apps", ((_img(f"icons/{category}/{category}-128.png", 64), category.capitalize(),
                                          "<br>".join(sorted(entries)))
                                         for category, entries in sorted(by_category.items())))
    out += ["### The portal's symbols", "",
            "Drawn with QPainter in the portal's `glyphs.py`, in the theme's text color. Each function draws one.", ""]
    out += _table("Name,What it shows", ((f"`{name}`", doc) for name, doc in glyphs(root)))
    out += ["### The desktop style's icons", "",
            "Icons the apps take from the desktop's style or icon theme, so they look different on every desktop. "
            "The name is Qt's standard pixmap or the icon theme's name.", ""]
    out += _table("Name,Used by", ((f"`{name}`", ", ".join(users))
                                        for name, users in style_icons(root).items()))
    out += ["### Material Design icons in the wiki", "", "Drawn by MkDocs Material in the wiki's colors.", ""]
    out += _table("Icon,Name,Pages", ((_img(f"{MDI}/{icon}.svg", 24), f"`material-{icon}`", ", ".join(pages))
                                      for icon, pages in material(root).items()))
    out += ["### Characters as icons", "", "Characters of the font that the apps use as icons in labels and buttons.",
            ""]
    out += _table("App,Characters", ((app, " ".join(chars)) for app, chars in symbols(root).items()))
    return "\n".join(out)
