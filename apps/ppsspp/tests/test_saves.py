# SPDX-License-Identifier: GPL-3.0-or-later
"""The saves on PPSSPP's memory stick (saves.py) and the Memory cards tab over them (saves_page.py): what a save's
PARAM.SFO says, export to a .zip and back, a .zip that would write outside the save folder, delete, and the tab's
table, picture and buttons, with nothing changed while PPSSPP runs."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QMessageBox

from conftest import _png, make_memstick, make_sfo

from ppsspp_manager import saves
from ppsspp_manager.saves_page import RUNNING, SavesPage


def make_save(memstick: Path, name: str, game: str = "Lumines", title: str = "Autosave",
              detail: str = "Level 12", picture: bool = True) -> Path:
    folder = saves.save_folder(memstick) / name
    folder.mkdir(parents=True)
    (folder / "PARAM.SFO").write_bytes(make_sfo({"CATEGORY": "MS", "SAVEDATA_DETAIL": detail,
                                                 "SAVEDATA_TITLE": title, "TITLE": game}))
    (folder / "DATA.BIN").write_bytes(b"x" * 2048)
    if picture:
        (folder / "ICON0.PNG").write_bytes(_png((144, 80), "#1565c0"))
    return folder


@pytest.fixture
def stick(tmp_path):
    return make_memstick(tmp_path / "ppsspp")


def test_the_saves_are_read_from_their_folders(stick):
    make_save(stick, "ULUS10001DATA00", "Lumines", "Autosave", "Level\n12")
    make_save(stick, "ULES00043SLOT1", "Alpha", "Slot 1", picture=False)
    (saves.save_folder(stick) / "EMPTY").mkdir()                                # no files: not a save
    plain = saves.save_folder(stick) / "NOSFO"
    plain.mkdir()
    (plain / "DATA.BIN").write_bytes(b"1234")
    found = saves.find_saves(stick)
    assert [s.name for s in found] == ["NOSFO", "ULES00043SLOT1", "ULUS10001DATA00"]    # by game, then folder
    lumines = found[2]
    assert (lumines.game, lumines.title, lumines.detail) == ("Lumines", "Autosave", "Level 12")
    assert lumines.size > 2048 and lumines.label == "Lumines · Autosave" and found[0].label == "NOSFO"
    assert saves.icon(lumines) and saves.icon(found[1]) is None
    assert saves.find_saves(stick / "none") == []
    assert [saves.size_text(n) for n in (812, 24 * 1024, 1500000)] == ["812 B", "24 KB", "1.4 MB"]


def test_export_and_import_again(stick, tmp_path):
    make_save(stick, "ULUS10001DATA00")
    make_save(stick, "ULES00043SLOT1", "Alpha", "Slot 1")
    found = saves.find_saves(stick)
    target = tmp_path / "out" / "saves.zip"
    target.parent.mkdir()
    assert saves.export_saves(found, target) == f"Exported 2 save(s) to {target}."
    with zipfile.ZipFile(target) as archive:
        assert "ULUS10001DATA00/PARAM.SFO" in archive.namelist() and "ULES00043SLOT1/DATA.BIN" in archive.namelist()
    assert os.listdir(target.parent) == ["saves.zip"]                           # no work file left
    assert saves.zip_saves(target) == ["ULES00043SLOT1", "ULUS10001DATA00"]
    other = make_memstick(tmp_path / "other")
    old = make_save(other, "ULUS10001DATA00", detail="Level 1")
    (old / "OLD.BIN").write_bytes(b"old")
    message = saves.import_saves(other, target)
    assert message == "Imported 2 save(s) from saves.zip: ULES00043SLOT1, ULUS10001DATA00."
    again = saves.find_saves(other)
    assert [s.name for s in again] == ["ULES00043SLOT1", "ULUS10001DATA00"] and again[1].detail == "Level 12"
    assert not (old / "OLD.BIN").exists()                                       # in place of the save that was there
    assert sorted(os.listdir(saves.save_folder(other))) == ["ULES00043SLOT1", "ULUS10001DATA00"]


def test_a_zip_with_the_files_at_the_top_takes_its_own_name(stick, tmp_path):
    file = tmp_path / "ULUS10001DATA05.zip"
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("PARAM.SFO", make_sfo({"SAVEDATA_TITLE": "Slot 5", "TITLE": "Lumines"}))
        archive.writestr("DATA.BIN", b"data")
    saves.import_saves(stick, file)
    assert [(s.name, s.title) for s in saves.find_saves(stick)] == [("ULUS10001DATA05", "Slot 5")]


def test_what_is_no_save_is_refused(stick, tmp_path):
    text = tmp_path / "notes.zip"
    text.write_text("not a zip")
    with pytest.raises(saves.SaveError, match="could not be read as a .zip"):
        saves.zip_saves(text)
    empty = tmp_path / "pictures.zip"
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("holiday/photo.png", b"png")
    with pytest.raises(saves.SaveError, match="holds no PSP save"):
        saves.import_saves(stick, empty)
    outside = tmp_path / "outside.zip"
    with zipfile.ZipFile(outside, "w") as archive:
        archive.writestr("SAVE/PARAM.SFO", make_sfo({"TITLE": "Game"}))
        archive.writestr("SAVE/../../../escaped.txt", b"out")
    with pytest.raises(saves.SaveError, match="outside the save folder"):
        saves.import_saves(stick, outside)
    assert saves.find_saves(stick) == [] and not (tmp_path / "escaped.txt").exists()


def test_delete(stick):
    make_save(stick, "ULUS10001DATA00")
    keep = make_save(stick, "ULES00043SLOT1", "Alpha")
    lumines = [s for s in saves.find_saves(stick) if s.game == "Lumines"]
    assert saves.delete_saves(lumines) == "Deleted 1 save(s)."
    assert os.listdir(saves.save_folder(stick)) == [keep.name]


def test_the_tab_lists_the_saves_with_the_picture(qapp, stick):
    make_save(stick, "ULUS10001DATA00")
    make_save(stick, "ULES00043SLOT1", "Alpha", "Slot 1", "", picture=False)
    page = SavesPage(stick, lambda: False)
    page.show()
    assert [page.table.horizontalHeaderItem(c).text() for c in range(5)] == ["Game", "Save", "Folder", "Size",
                                                                             "Saved"]
    assert [page.table.item(r, 0).text() for r in range(2)] == ["Alpha", "Lumines"]
    assert page.space.text().startswith("2 save(s), ") and "PSP/SAVEDATA" in page.hint.text()
    assert not page.export_button.isEnabled() and not page.delete_button.isEnabled() and not page.side.isVisible()
    page.table.selectRow(1)
    assert page.export_button.isEnabled() and page.delete_button.isEnabled() and page.side.isVisible()
    assert not page.picture.pixmap().isNull() and page.details.text() == "<b>Autosave</b><br>Level 12"
    page.table.selectRow(0)
    assert page.picture.text() == "No picture" and page.details.text() == "<b>Slot 1</b>"
    page.close()


def test_the_tab_exports_imports_and_deletes(qapp, stick, tmp_path, monkeypatch):
    make_save(stick, "ULUS10001DATA00")
    page = SavesPage(stick, lambda: False)
    page.table.selectRow(0)
    page.export_to(page.chosen(), tmp_path / "one")                             # .zip is added to the name
    assert (tmp_path / "one.zip").is_file() and page.status.text().startswith("Exported 1 save(s) to ")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (asked.append(a[2]),
                                                                  QMessageBox.StandardButton.No)[1])
    page.import_file(tmp_path / "one.zip")                                      # there already: it asks first
    assert "on the memory stick already" in asked[0] and page.status.text() == "Nothing was imported."
    page.on_delete()
    assert "export it first" in asked[1] and len(page.saves) == 1               # No: nothing deleted
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    page.table.selectRow(0)
    page.on_delete()
    assert page.saves == [] and page.status.text() == "Deleted 1 save(s)." and page.space.text() == "No saves yet"
    page.import_file(tmp_path / "one.zip")
    assert [s.name for s in page.saves] == ["ULUS10001DATA00"] and page.table.rowCount() == 1
    page.import_file(tmp_path / "none.zip")
    assert "could not be read as a .zip" in page.status.text() and "c62828" in page.status.styleSheet()
    page.close()


def test_nothing_is_changed_while_ppsspp_runs(qapp, stick, tmp_path):
    make_save(stick, "ULUS10001DATA00")
    page = SavesPage(stick, lambda: True)
    page.table.selectRow(0)
    page.export_to(page.chosen(), tmp_path / "one.zip")                         # reading is fine
    page.delete(page.chosen())
    assert page.status.text() == RUNNING and len(saves.find_saves(stick)) == 1
    saves.delete_saves(saves.find_saves(stick))
    page.import_file(tmp_path / "one.zip")
    assert page.status.text() == RUNNING and saves.find_saves(stick) == []
    page.close()
