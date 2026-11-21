# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/new_app.py writes a new app of the suite as the architecture chapter describes it, and lists it wherever the
suite lists its apps, on a small repository laid out as this one is."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "icons" / "utilities"

spec = importlib.util.spec_from_file_location("new_app", ROOT / "tools" / "new_app.py")
na = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = na
spec.loader.exec_module(na)

MANIFEST = '''# the pins

[apps.alpha]
name = "Alpha"
summary = "s"
tag = "alpha-v0.1.0"
sha256 = ""
required = true
changes_board = false
category = "sustainable"
install = ["bash install.sh"]
uninstall = ["bash install.sh --uninstall"]
detect = ["~/.local/bin/ps5-alpha"]
'''

INDEX = '''# The apps

**Sustainable**: the board itself.

| App | What it does |
|---|---|
| ![](../assets/apps/alpha.webp){ .app-icon } [Alpha](alpha.md) | s |

**Utilities**: handy tools around the board.

| App | What it does |
|---|---|
| ![](../assets/apps/beta.webp){ .app-icon } [Beta](beta.md) | t |

Apps that **change the board** ask first.
'''

CATEGORIES_MD = '''# App categories

| App | Category |
|---|---|
| ![](../assets/apps/alpha.webp){ .app-icon } [Alpha](alpha.md) | Sustainable |
| ![](../assets/apps/beta.webp){ .app-icon } [Beta](beta.md) | Utilities |
| ![](../assets/apps/mtool.webp){ .app-icon } [Media Tool](../other-tools/media-tool.md) | Development |
'''

README = '''# Bazzite Console Suite

**Sustainable**: the board itself.

- <img src="portal/images/apps/alpha.webp" width="20" height="20" alt=""/> **[Alpha](apps/alpha)**: s

**Utilities**: handy tools around the board.

- <img src="portal/images/apps/beta.webp" width="20" height="20" alt=""/> **[Beta](apps/beta)**: t

How to install and use them: the wiki.
'''

MKDOCS = '''site_name: Bazzite Console Suite
site_url: https://example.invalid/nexus/bazzite-console-suite/
nav:
  - Home: index.md
  - Apps:
      - apps/index.md
      - Alpha: apps/alpha.md
  - Development:
      - development/index.md
'''

HOME = '''# The suite

<div class="home-grid" markdown>
<div class="home-card" markdown>
#### Diagnostics

[Alpha](apps/alpha.md) checks the board.
</div>
<div class="home-card" markdown>
#### Living room

[Beta](apps/beta.md) helps.
</div>
</div>

[All the apps](apps/index.md){ .md-button }
'''

BUG_REPORT = '''name: Bug report
body:
  - type: dropdown
    id: app
    attributes:
      label: App
      options:
        - portal
        - alpha
    validations:
      required: true
  - type: dropdown
    id: system
    attributes:
      options:
        - Bazzite
    validations:
      required: true
'''

REQUIREMENTS_DEV = '''# The development venv.
-r core/requirements-dev.txt
-r portal/requirements-dev.txt
-r apps/alpha/requirements-dev.txt
-r apps/zeta/requirements-dev.txt       # a comment stays
-r dev/deps/requirements-dev.txt
'''

CATALOG = '''# Runtime dependencies. [[tool]] a tool; [[dependency]] a Python package.

[app.portal]
name = "Portal"
launchers = ["~/.local/bin/bazzite-console-suite"]

[app.alpha]
name = "Alpha"
launchers = ["~/.local/bin/ps5-alpha"]

[[tool]]
name = "pkexec"
description = "Runs a command as root."
executables = ["pkexec"]

[[dependency]]
name = "PyQt6"
description = "Qt 6."

[[dependency.source]]
owner = "portal"
specifier = ">=6.11,<7"

[[dependency.source]]
owner = "alpha"
specifier = ">=6.11,<7"

[[dependency]]
name = "pillow"
description = "Pictures."

[[dependency.source]]
owner = "alpha"
specifier = ">=10"
'''

CI = '''jobs:
  pytest:
    strategy:
      matrix:
        dir: [portal,
              apps/alpha]   # every folder with tests/
  shell:
    steps:
      - name: shellcheck (warnings)
        run: |
          shellcheck -S warning apps/alpha/install.sh
          shellcheck -S warning tools/check-release.sh

      # The repository's rules: ci-nexus.yml.
      - name: Every former repo has its LICENSE, .gitignore, VERSION and CHANGELOG
        run: ls
  installers:
    steps:
      - name: alpha installer
        run: bash tools/installer-tests/alpha.sh
      - name: release tarballs, end to end
        run: bash tools/installer-tests/release.sh
'''


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def checkout(tmp_path) -> Path:
    """A repository laid out as this one is: the suite at the root with core and the files the generator lists an
    app in, and one category's icons (tools/sync_icons.py, the real one, writes the copies)."""
    root = tmp_path / "bazzite-console"
    suite = root
    write(suite / "TAG_PREFIX", "ps5-\n")
    write(root / "core" / "bazzite_console_core" / "__init__.py", "")
    write(suite / "portal" / "apps.toml", MANIFEST)
    write(suite / "portal" / "bazzite_console_portal" / "__init__.py", 'APP_NAME = "Bazzite Console Suite"\nAPP_ID = "bazzite-console-suite"\n')
    write(suite / "portal" / "LICENSE", "GPL-3.0-or-later\n")
    write(suite / "mkdocs.yml", MKDOCS)
    write(suite / "docs" / "apps" / "index.md", INDEX)
    write(suite / "docs" / "apps" / "categories.md", CATEGORIES_MD)
    write(suite / "README.md", README)
    write(suite / "docs" / "index.md", HOME)
    write(suite / "requirements-dev.txt", REQUIREMENTS_DEV)
    write(root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml", BUG_REPORT)
    write(suite / "icons" / "categories.toml", "# the apps' icons\n")
    (suite / "icons" / "utilities").mkdir(parents=True)
    for size, kind in ((1024, "webp"), (512, "webp"), (256, "webp"), (128, "png")):   # real pictures: sync_icons reads them
        shutil.copy(ICONS / f"utilities-{size}.{kind}", suite / "icons" / "utilities" / f"utilities-{size}.{kind}")
    (suite / "tools" / "installer-tests").mkdir(parents=True)
    write(root / "dev" / "deps" / "nexus_deps" / "catalogs" / f"{suite.name}.toml", CATALOG)
    write(root / ".github" / "workflows" / "ci.yml", CI)
    return root


def test_defaults():
    assert na.default_package("PS5 Fan Control") == "fan_control"
    assert na.default_package("Bazzite DatStation") == "datstation"
    assert na.default_package("Turing Screen 3.5") == "turing_screen_3_5"
    assert na.default_package("3D Thing") == "app_3d_thing"
    suite = na.read_suite(ROOT)
    assert (suite.name, suite.app_id, suite.prefix, suite.core) == ("Bazzite Console Suite", "bazzite-console-suite",
                                                                   "ps5", "bazzite_console_core")
    assert suite.wiki == "https://robertotorino.github.io/bazzite-console/"
    assert suite.categories == ("sustainable", "graphics", "gaming", "utilities")      # no Development tab
    assert suite.tag_prefix == "ps5-"


def test_writes_the_app_and_lists_it_everywhere(checkout, capsys):
    assert na.main(["fan2", "PS5 Fan Two", "--summary", "A second fan.", "--no-check", "--root",
                    str(checkout)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("PS5 Fan Two (apps/fan2, package fan_two, id ps5-fan2, utilities):")
    suite = checkout
    app = suite / "apps" / "fan2"
    for name in ("fan_two/__init__.py", "fan_two/__main__.py", "fan_two/main_window.py", "tests/conftest.py",
                 "tests/test_main_window.py", "install.sh", "requirements.txt", "requirements-dev.txt", "VERSION",
                 "CHANGELOG", "LICENSE", ".gitignore", "README.md", "images/ps5-fan2.webp",
                 "images/ps5-fan2-128.png"):
        assert (app / name).is_file(), name
    assert (app / "VERSION").read_text() == "0.1.0\n" and (app / "LICENSE").read_text() == "GPL-3.0-or-later\n"
    assert (app / "CHANGELOG").read_text().startswith("Changelog: ") and "\n\nAdded. PS5 Fan Two" in (app / "CHANGELOG").read_text()
    init = (app / "fan_two" / "__init__.py").read_text()
    assert 'APP_NAME = "PS5 Fan Two"' in init and 'APP_ID = "ps5-fan2"' in init and '__version__ = "0.1.0"' in init
    assert 'tag_prefix="ps5-fan2-v"' in init and "from bazzite_console_core import AppInfo" in init
    for name in ("fan_two/__init__.py", "fan_two/__main__.py", "fan_two/main_window.py", "tests/conftest.py",
                 "tests/test_main_window.py"):
        compile((app / name).read_text(), name, "exec")                   # valid Python
    window = (app / "fan_two" / "main_window.py").read_text()
    assert "class MainWindow(CardWindow):" in window and "A second fan." in window
    # The installer: the standard options, the refusal of root, pip --upgrade -r (tools/tests/test_layout.py).
    installer = (app / "install.sh").read_text()
    for option in ("--no-desktop-shortcut)", "--uninstall)", "--purge)", "--help)"):
        assert option in installer
    assert "only goes with --uninstall" in installer and "not with sudo" in installer
    assert "--upgrade -r" in installer and 'APP_ID="ps5-fan2"' in installer and "-m fan_two" in installer
    assert "bazzite-console-suite/venv" in installer.replace("$DATA_DIR/bazzite-console-suite", "x/bazzite-console-suite/venv")
    test = suite / "tools" / "installer-tests" / "fan2.sh"
    assert (app / "install.sh").stat().st_mode & 0o111 and test.stat().st_mode & 0o111
    assert "apps/fan2/install.sh" in test.read_text()
    assert "stage_app.py\" fan2" in test.read_text() and "--suite" not in test.read_text()
    if shutil.which("bash"):
        subprocess.run(["bash", "-n", str(app / "install.sh"), str(test)], check=True)
    # The icons: copies of the category's, written by sync_icons.py; the tile too.
    assert (app / "images" / "ps5-fan2.webp").read_bytes() == (ICONS / "utilities-512.webp").read_bytes()
    assert (app / "images" / "ps5-fan2-128.png").read_bytes() == (ICONS / "utilities-128.png").read_bytes()
    assert (suite / "portal" / "images" / "apps" / "fan2.webp").read_bytes() == (ICONS / "utilities-256.webp").read_bytes()
    categories = (suite / "icons" / "categories.toml").read_text()
    assert '[fan2]\ncategory = "utilities"\nicons = ["apps/fan2/images/ps5-fan2"]\ntile = "portal/images/apps/fan2.webp"' in categories
    # The portal's manifest, at its end, and the root's copy with it.
    manifest = (suite / "portal" / "apps.toml").read_text()
    entry = manifest.index("[apps.fan2]")
    assert manifest.index("[apps.alpha]") < entry
    assert 'tag = "ps5-fan2-v0.1.0"\nsha256 = ""' in manifest and 'detect = ["~/.local/bin/ps5-fan2"]' in manifest
    assert "\n\n[apps.fan2]" in manifest and manifest.endswith("]]\n")
    assert (checkout / "portal" / "apps.toml").read_text() == manifest
    # The wiki: the chapter with its icon, the nav before Development, the rows in the category's table.
    chapter = (suite / "docs" / "apps" / "fan2.md").read_text()
    assert "![PS5 Fan Two](../assets/fan2/ps5-fan2.webp){ .app-logo }\n\n# PS5 Fan Two" in chapter
    nav = (suite / "mkdocs.yml").read_text()
    assert "      - Alpha: apps/alpha.md\n      - PS5 Fan Two: apps/fan2.md\n  - Development:" in nav
    index = (suite / "docs" / "apps" / "index.md").read_text()
    assert ("[Beta](beta.md) | t |\n| ![](../assets/apps/fan2.webp){ .app-icon } [PS5 Fan Two](fan2.md) | "
            "A second fan. |\n\nApps that") in index
    table = (suite / "docs" / "apps" / "categories.md").read_text()
    assert ("[Beta](beta.md) | Utilities |\n| ![](../assets/apps/fan2.webp){ .app-icon } [PS5 Fan Two](fan2.md) "
            "| Utilities |\n| ![](../assets/apps/mtool.webp)") in table
    readme = (suite / "README.md").read_text()
    assert ("**[Beta](apps/beta)**: t\n- <img src=\"portal/images/apps/fan2.webp\" width=\"20\" height=\"20\" alt=\"\"/> "
            "**[PS5 Fan Two](apps/fan2)**: A second fan.\n\nHow to install") in readme
    # The home page (a line at the end of the last card), the bug report's dropdown, the development venv.
    assert "[Beta](apps/beta.md) helps.\n\n[PS5 Fan Two](apps/fan2.md): A second fan.\n</div>\n</div>" in \
        (suite / "docs" / "index.md").read_text()
    assert (checkout / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text() == BUG_REPORT.replace(
        "        - alpha\n", "        - alpha\n        - fan2\n")
    assert (suite / "requirements-dev.txt").read_text() == REQUIREMENTS_DEV.replace(
        "-r apps/zeta", "-r apps/fan2/requirements-dev.txt\n-r apps/zeta")
    # The installer says when there is nothing to remove.
    assert 'info "$APP_NAME is not installed: nothing to remove."' in installer
    assert '"${VENV_USERS:?}/${APP_ID:?}" \\\n        && found=true' in installer
    # Nexus Deps' catalog of the suite: the app before the tools, PyQt6 with the app as a source.
    catalog = (checkout / "dev" / "deps" / "nexus_deps" / "catalogs" / f"{suite.name}.toml").read_text()
    assert ('launchers = ["~/.local/bin/ps5-alpha"]\n\n[app.fan2]\nname = "PS5 Fan Two"\n'
            'launchers = ["~/.local/bin/ps5-fan2"]\n\n[[tool]]') in catalog
    assert ('owner = "alpha"\nspecifier = ">=6.11,<7"\n\n[[dependency.source]]\nowner = "fan2"\n'
            'specifier = ">=6.11,<7"\n\n[[dependency]]\nname = "pillow"') in catalog
    import tomllib
    assert tomllib.loads(catalog)["app"]["fan2"]["name"] == "PS5 Fan Two"
    assert tomllib.loads(manifest)["apps"]["fan2"]["category"] == "utilities"
    # CI needs no edit (stage 2, 04-11-2026): its matrix, installer tests and shellcheck come from the folders.
    assert (checkout / ".github" / "workflows" / "ci.yml").read_text() == CI


def test_names_are_the_owners(checkout):
    assert na.main(["cam", "USB Cam Thing", "--id", "ps5-usb-cam", "--package", "usb_cam", "--category",
                    "utilities", "--no-check", "--root", str(checkout)]) == 0
    init = (checkout / "apps" / "cam" / "usb_cam" / "__init__.py").read_text()
    assert 'APP_ID = "ps5-usb-cam"' in init
    assert (checkout / "apps" / "cam" / "install.sh").read_text().count("-m usb_cam") == 1


@pytest.mark.parametrize("argv, message", [
    (["Bad Name", "X"], "not a name"),
    (["x", "X", "--category", "games"], "not a category"),
    (["x", "X", "--package", "Not-Valid"], "not a package name"),
    (["x", "X", "--id", "Bad_Id"], "not an app id"),
    (["alpha", "Alpha again"], "exists already"),
])
def test_refusals(checkout, argv, message):
    (checkout / "apps" / "alpha").mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit, match=message):
        na.main([*argv, "--no-check", "--root", str(checkout)])
    assert not (checkout / "apps" / "x").exists()


def test_a_folder_without_a_portal_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="no portal/apps.toml"):
        na.main(["x", "X", "--no-check", "--root", str(tmp_path)])


def test_the_help_names_the_steps():
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "new_app.py"), "--help"], capture_output=True,
                            text=True)
    assert result.returncode == 0 and "--category" in result.stdout and "architecture chapter" in result.stdout


def test_a_nav_by_category_gets_the_app_under_its_category_by_name():
    """The wiki lists the apps by category, by name in each: a new app's line goes where its name belongs."""
    nav = ("nav:\n  - Apps:\n      - apps/index.md\n      - Gaming:\n          - Alpha: apps/alpha.md\n"
           "      - Utilities:\n          - Beta: apps/beta.md\n          - \"SSD: Check\": apps/ssd.md\n"
           "  - Development:\n      - development/index.md\n")
    added = na.insert_nav(nav, "Utilities", "Fan Two", "fan2", "mkdocs.yml")
    assert ("          - Beta: apps/beta.md\n          - Fan Two: apps/fan2.md\n          - \"SSD: Check\": apps/ssd.md\n"
            in added)
    assert na.insert_nav(nav, "Utilities", "Zeta", "zeta", "mkdocs.yml").count(
        "apps/ssd.md\n          - Zeta: apps/zeta.md\n  - Development:") == 1
    assert "      - Gaming:\n          - Aaa: apps/aaa.md\n          - Alpha:" in na.insert_nav(
        nav, "Gaming", "Aaa", "aaa", "mkdocs.yml")
    # A category without a header in the nav: as before, the last of the Apps.
    assert "apps/ssd.md\n      - Mesh: apps/mesh.md\n  - Development:" in na.insert_nav(
        nav, "Graphics", "Mesh", "mesh", "mkdocs.yml")


def test_a_quote_mark_in_the_summary_is_escaped_between_quotes():
    """A summary with a quote mark (3.5") left apps.toml unreadable; in the wiki's text it stays as written."""
    import tomllib
    app = na.NewApp("screen2", "PS5 Screen Two", "ps5-screen2", "screen2", "utilities",
                    'A 3.5" screen, and a back\\slash.')
    suite = na.read_suite(ROOT)
    entry = tomllib.loads(na.fill(na.MANIFEST_ENTRY, app, suite))
    assert entry["apps"]["screen2"]["summary"] == 'A 3.5" screen, and a back\\slash.'
    compile(na.fill(na.WINDOW_PY, app, suite), "main_window.py", "exec")
    compile(na.fill(na.INIT_PY, app, suite), "__init__.py", "exec")
    assert 'A 3.5" screen' in na.fill(na.CHAPTER_MD, app, suite)
