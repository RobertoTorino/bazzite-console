# SPDX-License-Identifier: GPL-3.0-or-later
"""The saved games Xenia keeps (saves.py) and the Memory cards tab over them (saves_page.py): the saves of every
profile under their game's code, export to a .zip with their headers and back, a .zip that would write outside the
content folder, no profile to import under, delete, and the tab's table and buttons, with nothing changed while
Xenia runs."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QMessageBox

from xenia_manager import saves
from xenia_manager.saves_page import RUNNING, SavesPage

PROFILE = "E03000001234ABCD"


def make_home(home: Path, profile: str | None = PROFILE) -> Path:
    """Xenia's own folder with its content folder, and a profile's folder in it."""
    (home / "content" / saves.COMMON).mkdir(parents=True)                       # add-ons: no saves
    if profile:
        (home / "content" / profile).mkdir()
    return home


def make_save(home: Path, title_id: str, name: str, size: int = 2048, header: bool = True,
              profile: str = PROFILE) -> Path:
    """A saved game as Xenia Canary writes it: its files in <game's code>/00000001/<name>, its header beside."""
    folder = home / "content" / profile / title_id / saves.SAVED_GAME / name
    folder.mkdir(parents=True)
    (folder / "savegame.dat").write_bytes(b"x" * size)
    if header:
        headers = home / "content" / profile / title_id / saves.HEADERS / saves.SAVED_GAME
        headers.mkdir(parents=True, exist_ok=True)
        (headers / f"{name}.header").write_bytes(b"header of " + name.encode())
    return folder


@pytest.fixture
def home(tmp_path):
    return make_home(tmp_path / "Xenia")


def test_the_saves_are_read_from_their_folders(home):
    make_save(home, "4D5307E6", "Save2")
    make_save(home, "4D5307E6", "Save1", 4096, header=False)
    make_save(home, "415607D2", "Autosave", profile="E03000009999FFFF")        # another profile's: listed too
    (home / "content" / PROFILE / "4D5307E6" / "000B0000" / "update").mkdir(parents=True)     # a title update: no save
    (home / "content" / PROFILE / "4D5307E6" / saves.SAVED_GAME / "Empty").mkdir()            # no files: not a save
    found = saves.find_saves(home)
    assert [s.name for s in found] == ["415607D2/00000001/Autosave", "4D5307E6/00000001/Save1",
                                       "4D5307E6/00000001/Save2"]
    assert (found[1].title_id, found[1].title, found[1].size) == ("4D5307E6", "Save1", 4096)
    assert found[1].headers == [] and [h.name for h in found[2].headers] == ["Save2.header"]
    assert found[2].label == "4D5307E6 · Save2" and saves.find_saves(home / "none") == []
    assert saves.save_folder(home).name == PROFILE and saves.save_folder(make_home(home / "new", None)) is None


def test_export_and_import_again_with_the_headers(home, tmp_path):
    make_save(home, "4D5307E6", "Save1")
    make_save(home, "415607D2", "Autosave", header=False)
    target = tmp_path / "out" / "saves.zip"
    target.parent.mkdir()
    assert saves.export_saves(saves.find_saves(home), target) == f"Exported 2 save(s) to {target}."
    with zipfile.ZipFile(target) as archive:
        assert sorted(archive.namelist()) == ["415607D2/00000001/Autosave/savegame.dat",
                                              "4D5307E6/00000001/Save1/savegame.dat",
                                              "4D5307E6/Headers/00000001/Save1.header"]
    assert os.listdir(target.parent) == ["saves.zip"]                           # no work file left
    assert saves.zip_saves(target) == ["415607D2/00000001/Autosave", "4D5307E6/00000001/Save1"]
    other = make_home(tmp_path / "other", "E0300000AAAA0001")
    old = make_save(other, "4D5307E6", "Save1", header=False, profile="E0300000AAAA0001")
    (old / "old.bin").write_bytes(b"old")
    message = saves.import_saves(other, target)
    assert message == "Imported 2 save(s) from saves.zip: 415607D2/00000001/Autosave, 4D5307E6/00000001/Save1."
    again = saves.find_saves(other)
    assert [s.name for s in again] == ["415607D2/00000001/Autosave", "4D5307E6/00000001/Save1"]
    assert not (old / "old.bin").exists() and [h.name for h in again[1].headers] == ["Save1.header"]
    assert again[1].headers[0].read_bytes() == b"header of Save1"


def test_what_is_no_save_or_has_no_profile_is_refused(home, tmp_path):
    text = tmp_path / "notes.zip"
    text.write_text("not a zip")
    with pytest.raises(saves.SaveError, match="could not be read as a .zip"):
        saves.zip_saves(text)
    other = tmp_path / "other.zip"
    with zipfile.ZipFile(other, "w") as archive:
        archive.writestr("4D5307E6/000B0000/update/file", b"a title update")
        archive.writestr("Save1/savegame.dat", b"no code above it")
    with pytest.raises(saves.SaveError, match="holds no XBOX 360 save"):
        saves.import_saves(home, other)
    outside = tmp_path / "outside.zip"
    with zipfile.ZipFile(outside, "w") as archive:
        archive.writestr("4D5307E6/00000001/Save1/savegame.dat", b"in")
        archive.writestr("4D5307E6/00000001/Save1/../../../../../escaped.txt", b"out")
    with pytest.raises(saves.SaveError, match="outside the save folder"):
        saves.import_saves(home, outside)
    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as archive:
        archive.writestr("4D5307E6/00000001/Save1/savegame.dat", b"in")
    with pytest.raises(saves.SaveError, match="Xenia has no profile yet"):
        saves.import_saves(make_home(tmp_path / "fresh", None), good)
    assert saves.find_saves(home) == [] and not (tmp_path / "escaped.txt").exists()


def test_delete_takes_the_header_too(home):
    make_save(home, "4D5307E6", "Save1")
    keep = make_save(home, "4D5307E6", "Save2")
    first = saves.find_saves(home)[0]
    header = first.headers[0]
    assert saves.delete_saves([first]) == "Deleted 1 save(s)."
    assert not header.exists() and [s.title for s in saves.find_saves(home)] == [keep.name]
    assert [h.name for h in saves.find_saves(home)[0].headers] == ["Save2.header"]


def test_the_tab_lists_exports_imports_and_deletes(qapp, home, tmp_path, monkeypatch):
    make_save(home, "4D5307E6", "Save1")
    make_save(home, "415607D2", "Autosave")
    page = SavesPage(home, lambda: {"4D5307E6": "Halo 3"}, lambda: False)
    page.show()
    assert [page.table.horizontalHeaderItem(c).text() for c in range(5)] == ["Game", "Save", "Folder", "Size",
                                                                             "Saved"]
    assert [page.table.item(r, 0).text() for r in range(2)] == ["415607D2", "Halo 3"]   # the title, else the code
    assert page.table.item(1, 1).text() == "Save1" and page.table.item(1, 2).text() == "4D5307E6/00000001/Save1"
    assert page.space.text().startswith("2 save(s), ") and PROFILE in page.hint.text()
    assert not page.export_button.isEnabled() and not page.delete_button.isEnabled() and not page.status.isVisible()
    page.table.selectRow(1)
    assert page.export_button.isEnabled() and page.delete_button.isEnabled()
    page.export_to(page.chosen(), tmp_path / "one")                             # .zip is added to the name
    assert (tmp_path / "one.zip").is_file() and page.status.text().startswith("Exported 1 save(s) to ")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (asked.append(a[2]),
                                                                  QMessageBox.StandardButton.No)[1])
    page.import_file(tmp_path / "one.zip")                                      # there already: it asks first
    assert "on the disk already" in asked[0] and page.status.text() == "Nothing was imported."
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    page.table.selectRow(1)
    page.on_delete()
    assert [s.title for s in page.saves] == ["Autosave"] and page.status.text() == "Deleted 1 save(s)."
    page.import_file(tmp_path / "one.zip")
    assert [s.title for s in page.saves] == ["Autosave", "Save1"]
    page.close()


def test_no_profile_yet_and_nothing_changed_while_xenia_runs(qapp, home, tmp_path):
    make_save(home, "4D5307E6", "Save1")
    page = SavesPage(home, dict, lambda: True)
    page.table.selectRow(0)
    page.export_to(page.chosen(), tmp_path / "one.zip")                         # reading is fine
    page.delete(page.chosen())
    assert page.status.text() == RUNNING and len(saves.find_saves(home)) == 1
    page.close()
    fresh = SavesPage(make_home(tmp_path / "fresh", None), dict, lambda: False)
    assert "no profile yet" in fresh.hint.text() and fresh.space.text() == "No saves yet"
    fresh.import_file(tmp_path / "one.zip")
    assert "Xenia has no profile yet" in fresh.status.text() and "c62828" in fresh.status.styleSheet()
    fresh.close()
