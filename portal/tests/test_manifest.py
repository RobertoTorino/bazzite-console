# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import pytest

from bazzite_console_portal import MANIFEST
from bazzite_console_portal.manifest import CATEGORIES, LEGACY_CATEGORIES, ManifestError, load, parse
from conftest import SUITE

MINIMAL = """
[apps.compute]
name = "CU"
summary = "s"
tag = "ps5-compute-v1.2.3"
install = ["bash a.sh"]
uninstall = ["bash b.sh"]
detect = ["~/.local/bin/x"]
launch = [["Bisect", "~/.local/bin/x"], ["Unlock", "~/.local/bin/y"]]

[apps.check]
name = "BT"
summary = "s"
tag = "ps5-check-v0.1.0"
required = true
install = ["bash install.sh"]
uninstall = ["bash install.sh --uninstall"]
detect = ["~/.local/bin/bt"]
"""


HELPERS = MINIMAL + """
[apps.helpers]
name = "Console Helpers"
summary = "s"
tag = "ps5-helpers-v0.1.0"
required = true
install = ["bash install.sh"]
uninstall = ["bash install.sh --uninstall"]
detect = ["~/.local/bin/h"]
launch = [["Open", "~/.local/bin/h"]]

[[apps.helpers.helpers]]
key = "one"
name = "One"
summary = "the first"
launch = "~/.local/bin/h one"

[[apps.helpers.helpers]]
key = "two"
name = "Two"
summary = "the second"
launch = "~/.local/bin/h two"
changes_board = true
board_change = \"\"\"
Writes a file.
It stays.
\"\"\"
"""


def test_required_apps_first_board_before_the_others():
    assert [e.key for e in parse(HELPERS)] == ["check", "helpers", "compute"]
    # Board Test (board) is the first of the required apps wherever its table is.
    helpers = HELPERS[len(MINIMAL):]
    moved = helpers + MINIMAL.replace("[apps.check]", "[apps.board]").replace("ps5-check-v", "ps5-board-v")
    assert [e.key for e in parse(moved)] == ["board", "helpers", "compute"]


def test_an_app_of_helpers_has_a_tile_per_helper():
    helpers = parse(HELPERS)[1]
    one, two = helpers.tiles()
    assert (one.tile, two.tile) == ("helpers/one", "helpers/two")
    # A helper's tile is its app for installing and the records (key, tag, detect), the helper for the rest.
    assert one.key == two.key == "helpers" and one.tag == helpers.tag and one.detect == helpers.detect
    assert (one.name, one.short, one.summary, one.launch) == ("One", "One", "the first", (("Open", "~/.local/bin/h one"),))
    assert not one.changes_board and two.changes_board and two.board_change == "Writes a file. It stays."
    assert one.release_name == "Console Helpers" and one.helpers == ()
    compute = parse(HELPERS)[2]
    assert compute.tiles() == (compute,) and compute.tile == "compute" and compute.release_name == "CU"


@pytest.mark.parametrize("change, message", [
    (('key = "two"', 'key = "one"'), "two helpers have the same key"),
    (('key = "two"', 'key = "Two"'), "is not lowercase"),
    (('launch = "~/.local/bin/h two"', 'launch = ""'), "non-empty launch"),
    (('name = "Two"\n', ''), "non-empty name"),
])
def test_rejects_a_bad_helper(change, message):
    with pytest.raises(ManifestError, match=message):
        parse(HELPERS.replace(*change))


def test_required_first_then_file_order():
    entries = parse(MINIMAL)
    assert [e.key for e in entries] == ["check", "compute"]
    cu = entries[1]
    assert (cu.version, cu.asset) == ("1.2.3", "ps5-compute-v1.2.3.tar.gz")
    assert cu.launch == (("Bisect", "~/.local/bin/x"), ("Unlock", "~/.local/bin/y"))
    assert not cu.required and not cu.changes_board and cu.sha256 == ""


@pytest.mark.parametrize("change, message", [
    (('tag = "ps5-compute-v1.2.3"', 'tag = "ps5-cores-bisect-v1.2.3"'), "is not ps5-compute-v"),
    (('tag = "ps5-compute-v1.2.3"', 'tag = "compute-v1.2"'), "is not ps5-compute-v"),
    (('install = ["bash a.sh"]', 'install = []'), "must not be empty"),
    (('install = ["bash a.sh"]', 'install = "bash a.sh"'), "list of non-empty strings"),
    (('launch = [["Bisect", "~/.local/bin/x"], ["Unlock", "~/.local/bin/y"]]', 'launch = [["Bisect"]]'), "pairs"),
    (("required = true", "required = false"), "must have a required app"),
    (('name = "CU"', 'name = ""'), "non-empty name"),
])
def test_rejects(change, message):
    with pytest.raises(ManifestError, match=message):
        parse(MINIMAL.replace(*change, 1))


def test_a_withdrawn_release():
    assert parse(MINIMAL)[1].withdrawn == ""
    withdrawn = parse(MINIMAL.replace('name = "CU"', 'name = "CU"\nwithdrawn = " Shows the account ID. "', 1))
    assert withdrawn[1].withdrawn == "Shows the account ID." and withdrawn[1].tag == "ps5-compute-v1.2.3"
    with pytest.raises(ManifestError, match="must say why"):
        parse(MINIMAL.replace('name = "CU"', 'name = "CU"\nwithdrawn = ""', 1))
    with pytest.raises(ManifestError, match="required app cannot be withdrawn"):
        parse(MINIMAL.replace('name = "BT"', 'name = "BT"\nwithdrawn = "broken"', 1))


def test_board_change_text():
    """What an app changes on the board, for its tooltip and the box at the top of its wiki chapter: one line of
    plain sentences, however the manifest wraps it; "" in a manifest from before it."""
    assert parse(MINIMAL)[1].board_change == ""
    cu = parse(MINIMAL.replace('name = "CU"', 'name = "CU"\nchanges_board = true\nboard_change = """\n'
                               'Writes GPU registers.\n  Undo: a cold boot.\n"""', 1))[1]
    assert cu.changes_board and cu.board_change == "Writes GPU registers. Undo: a cold boot."
    with pytest.raises(ManifestError, match="board_change must be a string"):
        parse(MINIMAL.replace('name = "CU"', 'name = "CU"\nboard_change = true', 1))


def test_a_category_for_its_tab():
    assert parse(MINIMAL)[1].category == ""                                # a manifest from before categories
    cu = parse(MINIMAL.replace('name = "CU"', 'name = "CU"\ncategory = "gaming"', 1))[1]
    assert cu.category == "gaming"
    with pytest.raises(ManifestError, match="category must be one of sustainable, graphics, gaming, utilities$"):
        parse(MINIMAL.replace('name = "CU"', 'name = "CU"\ncategory = "games"', 1))


def test_no_development_tab_and_no_earlier_categories():
    """The four categories, no Development tab and no categories of earlier releases; [checkout.*] tables are not
    read."""
    assert "development" not in CATEGORIES and LEGACY_CATEGORIES == ()
    with pytest.raises(ManifestError, match="category must be one of"):
        parse(MINIMAL.replace('name = "CU"', 'name = "CU"\ncategory = "development"', 1))
    assert [e.key for e in parse(MINIMAL + CHECKOUT)] == ["check", "compute"]


def test_shipped_manifest_has_a_category_for_every_app():
    entries = load(MANIFEST)
    assert all(e.category in CATEGORIES for e in entries)
    assert "sftp" in {e.key for e in entries if e.category == "utilities"}
    assert "package" not in {e.key for e in entries}                       # Nexus Deps, a Nexus app since 07-11-2026
    assert "[checkout." not in MANIFEST.read_text(encoding="utf-8")           # only released apps


def test_short_name_for_the_tile():
    assert parse(MINIMAL)[1].short == ""
    assert parse(MINIMAL.replace('name = "CU"', 'name = "CU"\nshort = "C-U"', 1))[1].short == "C-U"
    with pytest.raises(ManifestError, match="short must be a string"):
        parse(MINIMAL.replace('name = "CU"', 'name = "CU"\nshort = 1', 1))


def test_bad_sha_and_toml():
    with pytest.raises(ManifestError, match="sha256"):
        parse(MINIMAL.replace('summary = "s"\ntag = "ps5-co', 'summary = "s"\nsha256 = "abc"\ntag = "ps5-co', 1))
    with pytest.raises(ManifestError, match="not valid TOML"):
        parse("[apps")


def test_shipped_manifest_lists_every_app_with_bazzite_test_first():
    entries = load(MANIFEST)
    assert entries[0].key == "board" and entries[0].required
    # Board Test and the helpers come with the portal (owner, 15-11-2026); every other app is optional.
    assert [e.key for e in entries if e.required] == ["board", "helpers"]
    apps = {p.name for p in (SUITE / "apps").iterdir() if p.is_dir() and not (p / ".standalone").is_file()}
    assert {e.key for e in entries} == apps


def test_shipped_manifest_install_scripts_exist():
    for entry in load(MANIFEST):
        for command in (*entry.install, *entry.uninstall):
            script = command.split()[-1] if command.split()[-1].endswith(".sh") else \
                [w for w in command.split() if w.endswith(".sh")][0]
            assert (SUITE / "apps" / entry.key / script).is_file(), f"{entry.key}: {command}"


def test_board_changing_apps_are_marked():
    marked = {e.key for e in load(MANIFEST) if e.changes_board}
    assert {"fan", "sftp", "webcam"} <= marked
    assert "board" not in marked


CHECKOUT = """
[checkout.gui]
name = "GUI"
summary = "s"
install = ["bash install.sh"]
uninstall = ["bash install.sh --uninstall"]
detect = ["~/.local/bin/gui"]
"""
