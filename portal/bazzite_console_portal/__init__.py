# SPDX-License-Identifier: GPL-3.0-or-later
"""The Bazzite Console Suite portal: installs, opens and removes the suite's apps."""

APP_NAME = "Bazzite Console Suite"
APP_ID = "bazzite-console-suite"
CHECKOUT_FILE = "suite-checkout"
__version__ = "1.0.0"
STAGE = ""
STAGE_NOTE = ""

from pathlib import Path

from bazzite_console_core import AppInfo
from bazzite_console_core.platform import data_home

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "apps.toml"
LOGO_PATH = ROOT / "images" / f"{APP_ID}.webp"
INTRO_LOGO = ROOT / "images" / f"{APP_ID}-1024.webp"
APP_ICONS = ROOT / "images" / "apps"
CATEGORY_ICONS = ROOT / "images" / "categories"
CARD_ICONS = ROOT / "images" / "cards"
CARDS = ROOT / "cards.toml"
SUITE_MANUAL_URL = "https://robertotorino.github.io/bazzite-console/"
INFO = AppInfo(app_id=APP_ID, name=APP_NAME, version=__version__, logo=LOGO_PATH, tag_prefix="ps5-portal-v",
               settings_app=f"{APP_ID}-portal", settings_ini=True)


def installed_copy() -> Path | None:
    """The link install.sh points at the installed portal, or None when running from a checkout."""
    return ROOT.parent / APP_ID if ROOT.name.startswith(f"{APP_ID}-v") else None


def state_dir() -> Path:
    """Per-user portal state: installed app tags, prepared releases, the wallpaper. Not the installed portal's own
    folder (portal/), which install.sh replaces at every install."""
    return data_home() / APP_ID / "state"


def is_suite(folder: Path) -> bool:
    """Whether *folder* is a checkout of the standalone Bazzite Console repository."""
    return ((folder / "apps").is_dir() and (folder / "tools" / "stage_app.py").is_file()
            and (folder / "core").is_dir())


def suite_folder(checkout: Path) -> Path:
    """The standalone suite is the repository root."""
    return checkout


def suite_checkout() -> Path | None:
    """The repository when this portal runs from a checkout or was installed from one."""
    candidates = [ROOT.parent]
    try:
        recorded = (ROOT / CHECKOUT_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        recorded = ""
    if recorded:
        candidates.append(Path(recorded))
    return next((suite for suite in candidates if is_suite(suite)), None)
