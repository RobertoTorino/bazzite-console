# SPDX-License-Identifier: GPL-3.0-or-later
"""The Bazzite Console Suite portal: installs, opens and removes the suite's apps, one tile per app."""

APP_NAME = "Bazzite Console Suite"
APP_ID = "bazzite-console-suite"
__version__ = "5.7.0"
# The suite's stage, shown beside the version in the header and in a portal release's notes; "" when it leaves
# active development. The README's badge and the wiki's home page say the same (tools/tests/test_stage.py).
STAGE = "Beta"
STAGE_NOTE = "The suite is in active development: features and layout may still change between releases."

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.platform import data_home

ROOT = Path(__file__).resolve().parent.parent           # portal/ in the checkout and in the installed copy
CHECKOUT_FILE = "suite-checkout"                        # in ROOT, written by install.sh when installed from a checkout
MANIFEST = ROOT / "apps.toml"
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"
INTRO_LOGO = ROOT / "images" / f"{APP_ID}-1024.webp"      # the same picture at 1024 px, for the intro
APP_ICONS = ROOT / "images" / "apps"                    # <key>.webp: the small icon on each app's card
CATEGORY_ICONS = ROOT / "images" / "categories"         # <category>.webp: the 512 px icon, drawn on the tiles
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-portal-v",
               settings_app=f"{APP_ID}-portal", settings_ini=True)


def installed_copy() -> Path | None:
    """The installed portal's folder (~/.local/share/bazzite-console-suite/portal, install.sh's copy)
    when this portal runs from it; None from a checkout. A portal installed while this one runs replaces the files
    there, its VERSION with them."""
    return ROOT if ROOT.name == "portal" and ROOT.parent.name == APP_ID else None


def state_dir() -> Path:
    """Per-user portal state: which tag of each app it installed, the extracted releases it installed from (kept, so
    the matching uninstaller is at hand), the wallpaper and the music track. Not the installed portal's own folder
    (portal/), which install.sh replaces at every install."""
    return data_home() / APP_ID / "state"


def is_suite(folder: Path) -> bool:
    """Whether *folder* is a checkout of the repository: the apps in apps/, the shared core and the tools
    (stage_app.py) at the root."""
    return ((folder / "apps").is_dir() and (folder / "tools" / "stage_app.py").is_file()
            and (folder / "core").is_dir())


def suite_folder(checkout: Path) -> Path:
    """The suite's folder in *checkout*: where its apps, portal, docs and tools are, the repository itself."""
    return checkout


def suite_checkout() -> Path | None:
    """The repository when the portal runs from a checkout (ROOT is <checkout>/portal), or was installed from one
    (development): apps then install from the local source instead of a GitHub release."""
    candidates = [ROOT.parent]
    try:
        recorded = (ROOT / CHECKOUT_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        recorded = ""
    if recorded:
        candidates.append(Path(recorded))
    return next((suite for suite in candidates if is_suite(suite)), None)
